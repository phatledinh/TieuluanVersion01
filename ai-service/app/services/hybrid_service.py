"""
Hybrid Service — Chapter 3.7

Combines three recommendation sources:
    - LSTM:  dự đoán hành vi (sequence modeling)
    - Graph: quan hệ sản phẩm (Knowledge Graph CF)
    - RAG:   hiểu ngữ nghĩa (vector similarity)

Final Recommendation (PDF 3.7):
    final_score = w1 * lstm + w2 * graph + w3 * rag
"""

import logging
from typing import Dict, List

from app.services.lstm_service import lstm_service
from app.services.graph_service import get_graph_scores, get_graph_recommendations
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

# Default weights (PDF 3.7)
W1_LSTM = 0.4
W2_GRAPH = 0.35
W3_RAG = 0.25


def hybrid_recommend(user_id: int, query: str = "", k: int = 5) -> List[int]:
    """
    Hybrid recommendation combining LSTM + Graph + RAG — PDF 3.7

    final_score = w1 * lstm + w2 * graph + w3 * rag

    Args:
        user_id: ID of the user
        query: optional search query for RAG scoring
        k: number of recommendations to return

    Returns:
        List of recommended product IDs sorted by final_score
    """
    uid = str(user_id)

    # 1. LSTM scores (PDF 3.4)
    lstm_scores: Dict[int, float] = lstm_service.get_scores(uid, top_k=20)

    # 2. Graph scores (PDF 3.5)
    graph_scores: Dict[int, float] = get_graph_scores(uid, top_k=20)

    # 3. RAG scores (PDF 3.6) — only if query provided
    rag_scores: Dict[int, float] = {}
    if query:
        rag_scores = rag_service.get_rag_scores(query, top_k=20)

    # Collect all candidate product IDs
    all_pids = set(lstm_scores.keys()) | set(graph_scores.keys()) | set(rag_scores.keys())

    if not all_pids:
        # Fallback: get popular products from graph
        return get_graph_recommendations(uid, k=k)

    # Compute hybrid score (PDF 3.7)
    final_scores: Dict[int, float] = {}
    for pid in all_pids:
        s_lstm = lstm_scores.get(pid, 0.0)
        s_graph = graph_scores.get(pid, 0.0)
        s_rag = rag_scores.get(pid, 0.0)

        final_scores[pid] = W1_LSTM * s_lstm + W2_GRAPH * s_graph + W3_RAG * s_rag

    # Sort by final score, return top-k
    sorted_pids = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    result = [pid for pid, _ in sorted_pids[:k]]

    logger.info(
        "Hybrid recommend for user %s: %d candidates → top-%d = %s",
        user_id, len(all_pids), k, result,
    )
    return result
