"""
AI Service Configuration — Chapter 3.9 / 4.1.2

Reads settings from environment variables.
Each service has its own config, communicates via REST API only.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """AI Service settings loaded from environment variables."""

    # ── Service Info ──
    SERVICE_NAME: str = "ai-service"
    SERVICE_PORT: int = 8002
    DEBUG: bool = True

    # ── Neo4j Knowledge Graph (PDF 3.5) ──
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password123"

    # ── Product Service (inter-service REST — PDF 4.5.1) ──
    PRODUCT_SERVICE_URL: str = "http://product-service:8001"

    # ── LLM Provider — Groq (PDF 3.6.1) ──
    GROQ_API_KEY: str = ""

    # ── Model Paths ──
    LSTM_MODEL_PATH: str = "trained_models/lstm_model.pt"
    LSTM_META_PATH: str = "trained_models/lstm_meta.json"
    FAISS_INDEX_PATH: str = "trained_models/product_index.faiss"
    FAISS_MAPPING_PATH: str = "trained_models/product_mapping.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
