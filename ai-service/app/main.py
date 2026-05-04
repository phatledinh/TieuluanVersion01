"""
AI Service — FastAPI Application — Chapter 3.9 / 4.1.1

Tech stack (PDF 3.9.1):
    - FastAPI (service)
    - PyTorch (LSTM)
    - Neo4j (Graph)
    - FAISS (Vector DB)

Endpoints:
    GET  /                     → Health check
    POST /track-behavior       → Track user behavior (3.3)
    GET  /recommend?user_id=   → Recommendation list (3.8.1)
    POST /chatbot              → Chatbot tư vấn (3.8.2)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import get_settings
from app.db.neo4j_client import neo4j_client
from app.routers import behavior, recommend, chatbot

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / Shutdown lifecycle."""
    settings = get_settings()
    logger.info("Starting %s on port %d", settings.SERVICE_NAME, settings.SERVICE_PORT)

    # Connect to Neo4j on startup
    neo4j_client.connect()
    logger.info("Neo4j client initialized.")

    # Reload ML models (they may fail at import-time if files aren't ready)
    from app.services.lstm_service import lstm_service
    from app.services.rag_service import rag_service
    if not lstm_service.enabled:
        lstm_service._load_model()
    if not rag_service.faiss_index:
        rag_service._load_resources()

    yield

    # Cleanup on shutdown
    neo4j_client.close()
    logger.info("AI Service shutdown complete.")


# ── Create FastAPI app ──
app = FastAPI(
    title="AI Service — E-Commerce Product Advisor",
    description=(
        "Microservice AI cho tư vấn sản phẩm (Chapter 3).\n\n"
        "Pipeline: LSTM + Knowledge Graph + RAG → Recommendation & Chatbot"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routers ──
app.include_router(behavior.router)
app.include_router(recommend.router)
app.include_router(chatbot.router)


# ── Health Check ──
@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "AI Service is running"}
