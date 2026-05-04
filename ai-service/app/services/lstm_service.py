"""
LSTM Inference Service — Chapter 3.4

Loads trained LSTM model and predicts next products
based on user's behavior sequence from Neo4j.
"""

import json
import logging
import os
from typing import Dict, List

import numpy as np
import torch

from app.models.lstm_model import LSTMModel
from app.db.neo4j_client import neo4j_client
from app.config import get_settings

logger = logging.getLogger(__name__)


class LSTMService:
    """Service for LSTM-based next-item prediction."""

    def __init__(self):
        self.model: LSTMModel | None = None
        self.product_to_idx: Dict[str, int] = {}
        self.idx_to_product: Dict[int, str] = {}
        self.action_to_idx: Dict[str, int] = {}
        self.input_dim: int = 10
        self.n_products: int = 100
        self.window: int = 8
        self.enabled: bool = False
        self._load_model()

    def _load_model(self):
        """Load trained LSTM model and vocabularies."""
        settings = get_settings()
        model_path = settings.LSTM_MODEL_PATH
        meta_path = settings.LSTM_META_PATH

        if not os.path.exists(model_path) or not os.path.exists(meta_path):
            logger.warning("LSTM model not found at %s. Service disabled.", model_path)
            return

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            self.input_dim = int(meta.get("input_dim", 10))
            self.n_products = int(meta.get("n_products", 100))
            self.window = int(meta.get("window", 8))
            self.product_to_idx = meta.get("product_to_idx", {})
            self.idx_to_product = {int(v): k for k, v in self.product_to_idx.items()}
            self.action_to_idx = meta.get("action_to_idx", {})

            self.model = LSTMModel(
                input_dim=self.input_dim,
                hidden_dim=int(meta.get("hidden_dim", 64)),
                output_dim=self.n_products,
            )
            self.model.load_state_dict(
                torch.load(model_path, map_location="cpu", weights_only=True)
            )
            self.model.eval()
            self.enabled = True
            logger.info("LSTM model loaded. window=%d, n_products=%d", self.window, self.n_products)
        except Exception as e:
            logger.error("Failed to load LSTM model: %s", e)

    def _fetch_user_sequence(self, user_id: str) -> List[dict]:
        """Fetch user's recent behavior sequence from Neo4j."""
        query = """
        MATCH (u:User {id: $uid})-[r]->(p:Product)
        WHERE type(r) IN ['BUY', 'VIEW']
        RETURN p.id AS product_id, type(r) AS action, r.last_ts AS ts
        ORDER BY r.last_ts ASC
        LIMIT $limit
        """
        return neo4j_client.execute_read(query, {
            "uid": str(user_id),
            "limit": self.window * 3,
        })

    def _encode_sequence(self, events: List[dict]) -> torch.Tensor | None:
        """Encode behavior sequence into tensor for LSTM input."""
        if len(events) < self.window:
            return None

        tail = events[-self.window:]
        features = []
        for ev in tail:
            pid = str(ev.get("product_id", ""))
            action = str(ev.get("action", "VIEW")).lower()

            p_idx = self.product_to_idx.get(pid, 0)
            a_idx = self.action_to_idx.get(action, 0)

            # Create feature vector: one-hot-ish encoding
            feat = np.zeros(self.input_dim, dtype=np.float32)
            feat[0] = p_idx / max(self.n_products, 1)   # normalized product index
            feat[1] = a_idx / max(len(self.action_to_idx), 1)  # normalized action
            feat[2] = 1.0 if action == "purchase" else 0.0
            feat[3] = 1.0 if action == "add_to_cart" else 0.0
            feat[4] = 1.0 if action == "click" else 0.0
            feat[5] = 1.0 if action == "view" else 0.0
            features.append(feat)

        # Shape: (1, window, input_dim)
        return torch.tensor([features], dtype=torch.float32)

    def predict_next_products(self, user_id: str, k: int = 5) -> List[int]:
        """
        Predict next-k products for a user based on behavior sequence.

        Returns list of product IDs.
        """
        if not self.enabled:
            return []

        events = self._fetch_user_sequence(str(user_id))
        x = self._encode_sequence(events)
        if x is None:
            return []

        with torch.no_grad():
            logits = self.model(x)                    # (1, n_products)
            probs = torch.softmax(logits, dim=-1)
            values, indices = torch.topk(probs[0], k=min(k, self.n_products))

        results = []
        for idx in indices.tolist():
            pid = self.idx_to_product.get(idx)
            if pid and pid not in ("<PAD>", "<UNK>"):
                results.append(int(pid))
        return results

    def get_scores(self, user_id: str, top_k: int = 20) -> Dict[int, float]:
        """Return product_id → score mapping for hybrid model."""
        if not self.enabled:
            return {}

        events = self._fetch_user_sequence(str(user_id))
        x = self._encode_sequence(events)
        if x is None:
            return {}

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=-1)
            values, indices = torch.topk(probs[0], k=min(top_k, self.n_products))

        scores = {}
        for score, idx in zip(values.tolist(), indices.tolist()):
            pid = self.idx_to_product.get(idx)
            if pid and pid not in ("<PAD>", "<UNK>"):
                scores[int(pid)] = float(score)
        return scores


# Singleton
lstm_service = LSTMService()
