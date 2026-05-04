"""
Track Behavior Router — Chapter 3.3

POST /track-behavior
Records user behavior into Neo4j Knowledge Graph.

User Behavior Data fields (PDF 3.3.1):
    - user_id
    - product_id
    - action (view, click, add_to_cart, purchase, search)
    - timestamp
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.db.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Behavior Tracking"])


class BehaviorRequest(BaseModel):
    """Request body for tracking user behavior — PDF 3.3.1"""
    user_id: int = Field(..., description="ID of the user")
    product_id: int = Field(..., description="ID of the product")
    action: str = Field(..., description="Action type: view, click, add_to_cart, purchase, search")
    timestamp: str | None = Field(None, description="Event timestamp (ISO format)")


# Action weight mapping for graph edges
ACTION_WEIGHTS = {
    "view": 1.0,
    "click": 2.0,
    "search": 2.5,
    "add_to_cart": 3.0,
    "purchase": 5.0,
}


@router.post("/track-behavior")
async def track_behavior(req: BehaviorRequest):
    """
    Track user behavior and store in Neo4j Knowledge Graph.

    Creates/updates:
        - User node
        - Product node
        - Relationship edge with action type and weight
    """
    action = req.action.lower().strip()
    if action not in ACTION_WEIGHTS:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    event_ts = req.timestamp or datetime.utcnow().isoformat()
    weight = ACTION_WEIGHTS[action]

    # Determine edge type based on action (PDF 3.5.1: BUY, VIEW)
    edge_type = "BUY" if action == "purchase" else "VIEW"

    # MERGE nodes and relationship (PDF 3.5.2)
    query = """
    MERGE (u:User {id: $user_id})
    MERGE (p:Product {id: $product_id})
    MERGE (u)-[r:%s]->(p)
    ON CREATE SET
        r.action = $action,
        r.weight = $weight,
        r.count = 1,
        r.first_ts = $event_ts,
        r.last_ts = $event_ts
    ON MATCH SET
        r.count = r.count + 1,
        r.last_ts = $event_ts,
        r.weight = r.weight + $weight
    """ % edge_type

    try:
        neo4j_client.execute_write(query, {
            "user_id": str(req.user_id),
            "product_id": str(req.product_id),
            "action": action,
            "weight": weight,
            "event_ts": event_ts,
        })
        logger.info("Tracked: user=%s product=%s action=%s", req.user_id, req.product_id, action)
        return {"status": "Behavior tracked successfully"}
    except Exception as e:
        logger.error("Failed to track behavior: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
