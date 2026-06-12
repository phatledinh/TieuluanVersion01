#!/bin/bash
# ── AI Service Entrypoint — Auto-build FAISS, Train Model, Load Graph ──
# Waits for product-service, builds FAISS index if missing,
# generates behavior data & trains SimpleRNN if missing,
# loads graph data into Neo4j if empty, then starts FastAPI.

set -e

MODEL_DIR="${SEQUENCE_MODEL_DIR:-trained_models/simplernn_behavior_data}"
MODEL_PATH="${MODEL_DIR}/model.pt"
MODEL_META="${MODEL_DIR}/meta.json"
FAISS_PATH="${FAISS_INDEX_PATH:-trained_models/product_index.faiss}"
BEHAVIOR_CSV="data/behavior_data.csv"
PRODUCT_URL="${PRODUCT_SERVICE_URL:-http://product-service:8001}"

# ── Wait for product-service to be ready ──
echo "⏳ Waiting for product-service at ${PRODUCT_URL}..."
MAX_RETRIES=30
RETRY=0
until curl -sf "${PRODUCT_URL}/api/products/?page_size=1" > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ "$RETRY" -ge "$MAX_RETRIES" ]; then
        echo "⚠️  product-service not reachable after ${MAX_RETRIES} retries. Starting without FAISS."
        break
    fi
    echo "   retry ${RETRY}/${MAX_RETRIES}..."
    sleep 3
done

# ── Build FAISS index if missing ──
if [ ! -f "$FAISS_PATH" ]; then
    echo "🔨 Building FAISS index..."
    python scripts/build_faiss_index.py --product-url "$PRODUCT_URL" || echo "⚠️  FAISS build failed, continuing with API fallback."
else
    echo "✅ FAISS index already exists at ${FAISS_PATH}"
fi

# ── Generate behavior data & Train SimpleRNN if model is missing ──
if [ ! -f "$MODEL_PATH" ] || [ ! -f "$MODEL_META" ]; then
    echo "🔨 Model not found at ${MODEL_DIR}. Generating behavior data and training..."

    # Step 1: Generate synthetic behavior data if CSV is missing
    if [ ! -f "$BEHAVIOR_CSV" ]; then
        echo "   📊 Generating synthetic behavior data..."
        python scripts/generate_behavior_data.py --output "$BEHAVIOR_CSV" --users 500 --products 50 --interactions 20 \
            || { echo "⚠️  Behavior data generation failed."; }
    else
        echo "   ✅ Behavior data already exists at ${BEHAVIOR_CSV}"
    fi

    # Step 2: Train SimpleRNN model (best per experiment — Avg NDCG@5 = 35.51%)
    if [ -f "$BEHAVIOR_CSV" ]; then
        echo "   🧠 Training SimpleRNN model..."
        python scripts/train_model.py --model simplernn --csv "$BEHAVIOR_CSV" \
            --output-dir "$MODEL_DIR" --epochs 30 --window 8 \
            || echo "⚠️  Model training failed. Service will start without sequence model."
    fi
else
    echo "✅ Model already exists at ${MODEL_DIR}"
fi

# ── Load graph data into Neo4j if graph is empty ──
echo "🔍 Checking Neo4j graph data..."
GRAPH_COUNT=$(python -c "
from neo4j import GraphDatabase
import os
uri = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
user = os.environ.get('NEO4J_USER', 'neo4j')
pwd = os.environ.get('NEO4J_PASSWORD', 'password123')
try:
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session() as s:
        r = s.run('MATCH (n) RETURN count(n) AS c').single()
        print(r['c'] if r else 0)
    driver.close()
except:
    print(0)
" 2>/dev/null || echo "0")

if [ "$GRAPH_COUNT" -le "0" ] 2>/dev/null; then
    if [ -f "$BEHAVIOR_CSV" ]; then
        echo "   📊 Neo4j is empty. Loading graph data from behavior CSV..."
        python scripts/load_graph_data.py --csv "$BEHAVIOR_CSV" --clear \
            || echo "⚠️  Graph data loading failed. Graph service will have no data."
    else
        echo "   ⚠️  No behavior CSV found to load into Neo4j."
    fi
else
    echo "✅ Neo4j already has ${GRAPH_COUNT} nodes."
fi

# ── Start FastAPI ──
echo "🚀 Starting AI Service..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8002

