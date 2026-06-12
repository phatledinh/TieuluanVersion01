"""
Sequence Model Inference Service — Chapter 3.4

Loads trained model (SimpleRNN / LSTM / BiLSTM) và dự đoán next products
dựa trên chuỗi hành vi user từ Neo4j.

Cập nhật so với phiên bản cũ:
    - Hỗ trợ 3 model types: SimpleRNN, LSTM, BiLSTM
    - Load từ SEQUENCE_MODEL_DIR (meta.json + model.pt)
    - Auto-detect model type từ meta.json
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import torch

from app.config import get_settings
from app.db.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


def _load_model_class(model_type: str):
    """Lazy import model class theo model_type."""
    model_type = model_type.lower()
    if model_type == "simplernn":
        from app.models.simplernn_recommender import SimpleRNNRecommender
        return SimpleRNNRecommender
    elif model_type == "lstm":
        from app.models.lstm_recommender import LSTMRecommender
        return LSTMRecommender
    elif model_type == "bilstm":
        from app.models.bilstm_recommender import BiLSTMRecommender
        return BiLSTMRecommender
    else:
        raise ValueError(f"Unknown model type: {model_type}")


class SequenceModelService:
    """
    Service cho sequence-based next-item prediction.

    Tự động load đúng model class dựa trên meta.json['model'].
    Tương thích ngược với LSTMService cũ qua alias.
    """

    def __init__(self):
        self.model = None
        self.model_type: str = "lstm"
        self.product_to_idx: Dict[str, int] = {}
        self.idx_to_product: Dict[int, str] = {}
        self.action_to_idx: Dict[str, int] = {}
        self.n_products: int = 100
        self.n_actions: int = 5
        self.window: int = 8
        self.enabled: bool = False
        self._load_model()

    def _load_model(self):
        """Load trained model từ SEQUENCE_MODEL_DIR."""
        settings = get_settings()

        seq_dir = Path(settings.SEQUENCE_MODEL_DIR)
        meta_path  = seq_dir / "meta.json"
        model_path = seq_dir / "model.pt"

        if not model_path.exists() or not meta_path.exists():
            logger.warning(
                "No trained model found at %s. Service disabled.",
                seq_dir,
            )
            return

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            self.model_type    = meta.get("model", "lstm").lower()
            self.n_products    = int(meta.get("n_products", 100))
            self.n_actions     = int(meta.get("n_actions", 5))
            self.window        = int(meta.get("window", 8))
            self.product_to_idx = meta.get("product_to_idx", {})
            self.idx_to_product = {int(v): k for k, v in self.product_to_idx.items()}
            self.action_to_idx  = meta.get("action_to_idx", {})

            # Build model theo model_type
            ModelClass = _load_model_class(self.model_type)
            self.model = ModelClass(
                n_products=self.n_products,
                n_actions=self.n_actions,
                embed_dim=int(meta.get("embed_dim", 64)),
                hidden_dim=int(meta.get("hidden_dim", 128)),
                n_layers=int(meta.get("n_layers", 2)),
                dropout=float(meta.get("dropout", 0.3)),
            )
            self.model.load_state_dict(
                torch.load(model_path, map_location="cpu", weights_only=True)
            )
            self.model.eval()
            self.enabled = True

            logger.info(
                "✓ Loaded %s model | window=%d | n_products=%d | from=%s",
                self.model_type.upper(), self.window, self.n_products, model_path
            )

        except Exception as e:
            logger.error("Failed to load sequence model: %s", e)

    def _fetch_user_sequence(self, user_id: str) -> List[dict]:
        """Fetch user's recent behavior sequence from Neo4j."""
        query = """
        MATCH (u:User {id: $uid})-[r]->(p:Product)
        WHERE type(r) IN ['BUY', 'VIEW', 'ADD_TO_CART']
        RETURN p.id AS product_id,
               COALESCE(r.action, type(r)) AS action,
               r.last_ts AS ts
        ORDER BY r.last_ts ASC
        LIMIT $limit
        """
        return neo4j_client.execute_read(query, {
            "uid": str(user_id),
            "limit": self.window * 3,
        })

    def _encode_sequence(self, events: List[dict]) -> Optional[tuple]:
        """Encode behavior sequence thành product_ids + action_ids tensors."""
        if len(events) < self.window:
            return None

        tail = events[-self.window:]

        # Fallback remap: nếu r.action không có, dùng edge type → action phổ biến
        edge_type_remap = {
            "BUY":         "purchase",
            "VIEW":        "view",
            "ADD_TO_CART": "add_to_cart",
        }

        product_ids = []
        action_ids  = []
        for ev in tail:
            pid    = str(ev.get("product_id", ""))
            action = str(ev.get("action", "view")).lower()

            # Nếu action là edge type (uppercase), remap sang tên action
            if action.upper() in edge_type_remap:
                action = edge_type_remap[action.upper()]

            p_idx = self.product_to_idx.get(pid, 1)
            a_idx = self.action_to_idx.get(action, 1)  # <UNK> nếu không tìm thấy
            product_ids.append(p_idx)
            action_ids.append(a_idx)

        p_tensor = torch.tensor([product_ids], dtype=torch.long)  # (1, window)
        a_tensor = torch.tensor([action_ids],  dtype=torch.long)  # (1, window)
        return p_tensor, a_tensor

    def predict_next_products(self, user_id: str, k: int = 5) -> List[int]:
        """
        Dự đoán top-k sản phẩm tiếp theo cho user.
        Returns list of product IDs.
        """
        if not self.enabled:
            return []

        events = self._fetch_user_sequence(str(user_id))
        encoded = self._encode_sequence(events)
        if encoded is None:
            return []

        p_tensor, a_tensor = encoded
        with torch.no_grad():
            logits = self.model(p_tensor, a_tensor)    # (1, n_products)
            probs  = torch.softmax(logits, dim=-1)
            values, indices = torch.topk(probs[0], k=min(k, self.n_products))

        results = []
        for idx in indices.tolist():
            pid = self.idx_to_product.get(idx)
            if pid and pid not in ("<PAD>", "<UNK>"):
                try:
                    results.append(int(pid))
                except ValueError:
                    results.append(pid)
        return results

    def get_scores(self, user_id: str, top_k: int = 20) -> Dict[int, float]:
        """Return product_id → score mapping cho hybrid model."""
        if not self.enabled:
            return {}

        events = self._fetch_user_sequence(str(user_id))
        encoded = self._encode_sequence(events)
        if encoded is None:
            return {}

        p_tensor, a_tensor = encoded
        with torch.no_grad():
            logits = self.model(p_tensor, a_tensor)
            probs  = torch.softmax(logits, dim=-1)
            values, indices = torch.topk(probs[0], k=min(top_k, self.n_products))

        scores = {}
        for score, idx in zip(values.tolist(), indices.tolist()):
            pid = self.idx_to_product.get(idx)
            if pid and pid not in ("<PAD>", "<UNK>"):
                try:
                    scores[int(pid)] = float(score)
                except ValueError:
                    scores[str(pid)] = float(score)
        return scores


# ── Singleton ─────────────────────────────────────────────────────────────────
# Alias ngược với tên cũ để tương thích với main.py
lstm_service = SequenceModelService()
