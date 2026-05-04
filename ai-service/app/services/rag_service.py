"""
RAG Service — Chapter 3.6

Retrieval-Augmented Generation pipeline:
    1. Retrieve: tìm sản phẩm liên quan từ vector DB (FAISS) — PDF 3.6.1
    2. Generate: sinh câu trả lời bằng LLM (Groq) — PDF 3.6.1

Vector Database: FAISS (PDF 3.6.2)
Embedding: SentenceTransformers — mô tả sản phẩm

Example (PDF 3.6.3):
    query = "laptop gaming"
    results = vector_db.search(query)
    response = LLM.generate(results)
"""

import json
import logging
import os
from typing import Any, Dict, List

import faiss
import numpy as np
import httpx

from app.config import get_settings
from app.services.graph_service import get_user_context

logger = logging.getLogger(__name__)


class RAGService:
    """RAG pipeline: FAISS retrieval + Groq LLM generation."""

    def __init__(self):
        self.faiss_index = None
        self.product_mapping: Dict[int, dict] = {}  # faiss_idx → product info
        self.sentence_model = None
        self.groq_client = None
        self.enabled = False
        self._load_resources()

    def _load_resources(self):
        """Load FAISS index + SentenceTransformer + Groq client."""
        settings = get_settings()

        # 1. Load FAISS index (PDF 3.6.2)
        if os.path.exists(settings.FAISS_INDEX_PATH) and os.path.exists(settings.FAISS_MAPPING_PATH):
            try:
                self.faiss_index = faiss.read_index(settings.FAISS_INDEX_PATH)
                with open(settings.FAISS_MAPPING_PATH, "r", encoding="utf-8") as f:
                    self.product_mapping = {int(k): v for k, v in json.load(f).items()}
                logger.info("FAISS index loaded: %d vectors", self.faiss_index.ntotal)
            except Exception as e:
                logger.error("Failed to load FAISS: %s", e)
        else:
            logger.warning("FAISS index not found. RAG retrieve will use API fallback.")

        # 2. Load SentenceTransformer for query encoding
        try:
            from sentence_transformers import SentenceTransformer
            self.sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer loaded for query embedding.")
        except Exception as e:
            logger.warning("SentenceTransformer not available: %s", e)

        # 3. Init Groq client (PDF 3.6.1 — LLM)
        if settings.GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
                self.enabled = True
                logger.info("Groq LLM client initialized.")
            except Exception as e:
                logger.warning("Failed to init Groq: %s", e)
        else:
            logger.warning("GROQ_API_KEY not set. Chatbot will use template responses.")

    # ─────────────────────────────────────────────
    # RETRIEVE — PDF 3.6.1
    # ─────────────────────────────────────────────

    def retrieve_products(self, query: str, k: int = 5) -> List[dict]:
        """
        Retrieve relevant products using FAISS vector search.
        Fallback: search product-service API by keyword.
        """
        # Strategy 1: FAISS vector search (PDF 3.6.2)
        if self.faiss_index is not None and self.sentence_model is not None:
            try:
                query_vector = self.sentence_model.encode([query]).astype("float32")
                distances, indices = self.faiss_index.search(query_vector, k)
                results = []
                for idx in indices[0]:
                    if idx >= 0 and idx in self.product_mapping:
                        results.append(self.product_mapping[idx])
                if results:
                    return results
            except Exception as e:
                logger.error("FAISS search failed: %s", e)

        # Strategy 2: Fallback — search product-service API
        return self._search_product_api(query, k)

    def _search_product_api(self, query: str, k: int = 5) -> List[dict]:
        """Search product-service API by keyword — PDF 4.5.1"""
        settings = get_settings()
        url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
        try:
            resp = httpx.get(url, params={"search": query, "page_size": k}, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            if isinstance(results, list):
                return [
                    {"id": p.get("id"), "name": p.get("name", ""), "price": p.get("price", 0),
                     "category_name": p.get("category_name", "")}
                    for p in results[:k]
                ]
        except Exception as e:
            logger.error("Product API search failed: %s", e)
        return []

    def _get_product_names(self, product_ids: List[str]) -> Dict[str, str]:
        """Fetch product names from product-service by IDs."""
        if not product_ids:
            return {}
        settings = get_settings()
        url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
        names = {}
        try:
            resp = httpx.get(url, params={"page_size": 100}, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            if isinstance(results, list):
                for p in results:
                    pid = str(p.get("id", ""))
                    if pid in product_ids:
                        names[pid] = p.get("name", f"Sản phẩm {pid}")
        except Exception as e:
            logger.error("Product name lookup failed: %s", e)
        return names

    # ─────────────────────────────────────────────
    # GENERATE — PDF 3.6.1
    # ─────────────────────────────────────────────

    def generate_response(self, user_id: int | None, message: str) -> dict:
        """
        Full RAG pipeline (PDF 3.6):
        1. Retrieve relevant products (FAISS / API)
        2. Get user context from KB Graph
        3. Generate response using LLM (Groq)

        Chatbot always responds in Vietnamese.
        """
        # Step 1: Retrieve products
        retrieved = self.retrieve_products(message, k=5)

        # Step 2: Get user graph context
        user_context = ""
        if user_id:
            ctx = get_user_context(str(user_id))
            if ctx["purchases"]:
                pids = [p["product_id"] for p in ctx["purchases"]]
                names = self._get_product_names(pids)
                items = [names.get(pid, f"SP #{pid}") for pid in pids[:5]]
                if items:
                    user_context = "Sản phẩm khách đã mua: " + ", ".join(items)

        # Step 3: Build product context
        product_context = ""
        if retrieved:
            items = []
            for p in retrieved:
                name = p.get("name", "")
                price = p.get("price", 0)
                if price:
                    price_str = f"{int(price):,}".replace(",", ".") + " ₫"
                    items.append(f"- {name} — {price_str}")
                else:
                    items.append(f"- {name}")
            product_context = "Sản phẩm liên quan:\n" + "\n".join(items)

        # Step 4: Generate with LLM
        if self.groq_client:
            return self._generate_with_groq(message, user_context, product_context)
        else:
            return self._generate_template(message, retrieved)

    def _generate_with_groq(self, message: str, user_context: str, product_context: str) -> dict:
        """Generate response using Groq LLM — PDF 3.6.1"""
        system_prompt = f"""Bạn là nhân viên tư vấn bán hàng chuyên nghiệp, thân thiện.
LUÔN trả lời bằng tiếng Việt.

{user_context}

{product_context}

QUY TẮC:
- Trả lời ngắn gọn, tự nhiên (2-4 câu).
- Gợi ý sản phẩm cụ thể từ danh sách trên kèm giá nếu có.
- KHÔNG bịa tên sản phẩm không có trong dữ liệu.
- CHỈ giới thiệu các loại sản phẩm, chất liệu hoặc danh mục CÓ XUẤT HIỆN trong danh sách trên. TUYỆT ĐỐI KHÔNG tự ý liệt kê các phân loại (ví dụ: dép thể thao, dép vải...) nếu không có dữ liệu thực tế cung cấp.
- KHÔNG nhắc đến thuật ngữ kỹ thuật (FAISS, Knowledge Graph, AI, vector, database).
"""
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            reply = response.choices[0].message.content
            return {"reply": reply, "provider": "groq"}
        except Exception as e:
            logger.error("Groq LLM call failed: %s", e)
            return self._generate_template(message, [])

    def _generate_template(self, message: str, products: List[dict]) -> dict:
        """Fallback template response when LLM is unavailable."""
        if products:
            items = ", ".join(p.get("name", "") for p in products[:3] if p.get("name"))
            reply = f"Dựa trên yêu cầu của bạn, tôi gợi ý: {items}. Bạn muốn tìm hiểu thêm về sản phẩm nào?"
        else:
            reply = "Xin lỗi, tôi chưa tìm thấy sản phẩm phù hợp. Bạn có thể mô tả chi tiết hơn được không?"
        return {"reply": reply, "provider": "template"}

    def get_rag_scores(self, query: str, top_k: int = 20) -> Dict[int, float]:
        """Return product_id → relevance score for hybrid model."""
        retrieved = self.retrieve_products(query, k=top_k)
        scores = {}
        for rank, p in enumerate(retrieved):
            pid = p.get("id")
            if pid:
                # Score decreases with rank (1.0 for top, 0.5 for bottom)
                scores[int(pid)] = 1.0 - (rank / max(len(retrieved), 1)) * 0.5
        return scores


# Singleton
rag_service = RAGService()
