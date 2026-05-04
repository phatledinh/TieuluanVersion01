"""
Graph Service — Chapter 3.5

Knowledge Graph recommendation using Neo4j.
Collaborative Filtering via shared user purchases.

Graph Model (PDF 3.5.1):
    Nodes: User, Product
    Edges: BUY, VIEW, SIMILAR

Recommendation Query (PDF 3.5.3):
    MATCH (u:User {id:1})-[:BUY]->(p)-[:SIMILAR]->(rec)
    RETURN rec
"""

import logging
from typing import Dict, List

from app.db.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


def get_graph_recommendations(user_id: str, k: int = 5) -> List[int]:
    """
    Get product recommendations from Knowledge Graph — PDF 3.5.3

    Strategy:
    1. Find products user has bought/viewed
    2. Find SIMILAR products (if edges exist)
    3. Collaborative Filtering: find what similar users bought

    Returns: list of recommended product IDs
    """
    # Strategy 1: SIMILAR edges (PDF 3.5.3)
    similar_query = """
    MATCH (u:User {id: $uid})-[:BUY]->(p)-[:SIMILAR]->(rec:Product)
    WHERE NOT (u)-[:BUY]->(rec)
    RETURN DISTINCT rec.id AS product_id, count(*) AS score
    ORDER BY score DESC LIMIT $k
    """
    results = neo4j_client.execute_read(similar_query, {"uid": str(user_id), "k": k})

    if results:
        return [int(r["product_id"]) for r in results]

    # Strategy 2: Collaborative Filtering — users who bought same products
    cf_query = """
    MATCH (u:User {id: $uid})-[:BUY]->(p:Product)<-[:BUY]-(other:User)
    MATCH (other)-[:BUY]->(rec:Product)
    WHERE NOT (u)-[:BUY]->(rec) AND rec.id <> p.id
    RETURN rec.id AS product_id, COUNT(DISTINCT other) AS shared_users
    ORDER BY shared_users DESC LIMIT $k
    """
    results = neo4j_client.execute_read(cf_query, {"uid": str(user_id), "k": k})

    if results:
        return [int(r["product_id"]) for r in results]

    # Strategy 3: Popular products fallback
    popular_query = """
    MATCH ()-[r:BUY]->(p:Product)
    RETURN p.id AS product_id, COUNT(r) AS buy_count
    ORDER BY buy_count DESC LIMIT $k
    """
    results = neo4j_client.execute_read(popular_query, {"k": k})
    return [int(r["product_id"]) for r in results]


def get_graph_scores(user_id: str, top_k: int = 20) -> Dict[int, float]:
    """
    Get product_id → score mapping for hybrid model.
    Score based on how many shared users recommend the product.
    """
    cf_query = """
    MATCH (u:User {id: $uid})-[:BUY]->(p:Product)<-[:BUY]-(other:User)
    MATCH (other)-[r:BUY]->(rec:Product)
    WHERE NOT (u)-[:BUY]->(rec)
    RETURN rec.id AS product_id,
           COUNT(DISTINCT other) AS shared_users,
           SUM(r.weight) AS total_weight
    ORDER BY shared_users DESC LIMIT $k
    """
    results = neo4j_client.execute_read(cf_query, {"uid": str(user_id), "k": top_k})

    scores = {}
    if results:
        max_shared = max(r["shared_users"] for r in results)
        for r in results:
            pid = int(r["product_id"])
            # Normalize score to 0-1
            scores[pid] = float(r["shared_users"]) / max(max_shared, 1)
    return scores


def get_user_context(user_id: str, limit: int = 10) -> dict:
    """Get user's full context from graph for RAG pipeline."""
    # Purchases
    purchases = neo4j_client.execute_read(
        """MATCH (u:User {id: $uid})-[r:BUY]->(p:Product)
        RETURN p.id AS product_id, r.count AS times
        ORDER BY r.weight DESC LIMIT $limit""",
        {"uid": str(user_id), "limit": limit},
    )
    # Views
    views = neo4j_client.execute_read(
        """MATCH (u:User {id: $uid})-[r:VIEW]->(p:Product)
        RETURN p.id AS product_id, r.action AS action, r.weight AS weight
        ORDER BY r.weight DESC LIMIT $limit""",
        {"uid": str(user_id), "limit": limit},
    )

    return {
        "purchases": [{"product_id": str(r.get("product_id", "")),
                        "times": int(r.get("times", 0))} for r in purchases],
        "views": [{"product_id": str(r.get("product_id", "")),
                   "weight": float(r.get("weight", 0))} for r in views],
    }
