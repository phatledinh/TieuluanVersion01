"""
Recommendation Router — Chapter 3.8.1

GET /recommend?user_id=1

Use cases (PDF 3.8.1):
    - Khi search
    - Khi add-to-cart

Output (PDF 3.8.1):
    [101, 102, 205]

Uses Hybrid Model (PDF 3.7):
    final_score = w1 * lstm + w2 * graph + w3 * rag
"""

from fastapi import APIRouter, Query
import logging

from app.services.hybrid_service import hybrid_recommend

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Recommendation"])


@router.get("/recommend")
async def recommend(
    user_id: int = Query(..., description="ID of the user"),
    k: int = Query(5, description="Number of recommendations"),
    query: str = Query("", description="Optional search query for RAG scoring"),
):
    """
    Get product recommendations for a user — PDF 3.8.1

    Combines:
        - LSTM sequence prediction (PDF 3.4)
        - Knowledge Graph CF (PDF 3.5)
        - RAG vector similarity (PDF 3.6)

    Returns: list of recommended product IDs
    """
    recommendations = hybrid_recommend(user_id=user_id, query=query, k=k)

    logger.info("Recommendations for user %d: %s", user_id, recommendations)
    return recommendations
