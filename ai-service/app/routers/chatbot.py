"""
Chatbot Router — Chapter 3.8.2

POST /chatbot

Input (PDF 3.8.2):
    "tôi cần laptop giá rẻ"

Pipeline (PDF 3.8.2):
    1. NLP hiểu intent
    2. Retrieve sản phẩm
    3. Generate response

Output (PDF 3.8.2):
    "Bạn có thể tham khảo Laptop XYZ giá 10 triệu..."

Chatbot luôn trả lời tiếng Việt.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging

from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chatbot"])


class ChatRequest(BaseModel):
    """Request body for chatbot — PDF 3.8.2"""
    message: str = Field(..., description="User message, e.g. 'tôi cần laptop giá rẻ'")
    user_id: int | None = Field(None, description="Optional user ID for personalized response")


class ChatResponse(BaseModel):
    """Response from chatbot — PDF 3.8.2"""
    reply: str = Field(..., description="Chatbot response in Vietnamese")
    provider: str = Field("groq", description="LLM provider used (groq/template)")


@router.post("/chatbot", response_model=ChatResponse)
async def chatbot(req: ChatRequest):
    """
    Chatbot tư vấn sản phẩm — PDF 3.8.2

    RAG Pipeline:
        1. Retrieve sản phẩm liên quan (FAISS / Product API)
        2. Get user context (Neo4j Knowledge Graph)
        3. Generate response (Groq LLM / template)

    Always responds in Vietnamese.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    logger.info("Chat from user=%s: %s", req.user_id, req.message)

    result = rag_service.generate_response(
        user_id=req.user_id,
        message=req.message,
    )

    return ChatResponse(
        reply=result["reply"],
        provider=result.get("provider", "unknown"),
    )
