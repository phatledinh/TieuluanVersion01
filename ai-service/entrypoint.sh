#!/bin/bash
# ── AI Service Entrypoint — Auto-build FAISS index ──
# Waits for product-service, builds FAISS index if missing, then starts FastAPI.

set -e

FAISS_PATH="${FAISS_INDEX_PATH:-trained_models/product_index.faiss}"
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

# ── Start FastAPI ──
echo "🚀 Starting AI Service..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8002
