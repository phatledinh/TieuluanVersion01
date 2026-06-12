"""
LSTM Recommender — Model 1 (Tiểu luận Chapter 3)

Cải tiến so với LSTMModel cũ (lstm_model.py):
    - Learnable Embedding layers cho product_id và action
      (thay vì feature vector thủ công với normalized index)
    - 2 LSTM layers thay vì 1
    - Dropout regularization

Architecture:
    product_embed (n_products+2, embed_dim)  ─┐
                                               ├─ cat → LSTM(2 layers) → Dropout → FC → logits
    action_embed  (n_actions+2,  8)           ─┘

Input:
    product_ids : LongTensor (batch, seq_len)
    action_ids  : LongTensor (batch, seq_len)
Output:
    logits      : FloatTensor (batch, n_products)  — CrossEntropyLoss target
"""

import torch
import torch.nn as nn


class LSTMRecommender(nn.Module):
    """
    LSTM-based next-item recommendation — Model 1.

    Args:
        n_products (int): Số lượng sản phẩm trong catalog.
        n_actions  (int): Số loại action (view, click, add_to_cart, purchase, search).
        embed_dim  (int): Chiều embedding của product (default=32).
        hidden_dim (int): Chiều hidden state của LSTM (default=128).
        n_layers   (int): Số LSTM layers (default=2).
        dropout    (float): Dropout rate (default=0.3).
    """

    def __init__(
        self,
        n_products: int,
        n_actions: int,
        embed_dim: int = 32,
        hidden_dim: int = 128,
        n_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.n_products = n_products
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers

        # Embedding layers (padding_idx=0 → <PAD> token không tham gia học)
        self.product_embed = nn.Embedding(n_products + 2, embed_dim, padding_idx=0)
        self.action_embed  = nn.Embedding(n_actions + 2,  8,         padding_idx=0)

        input_dim = embed_dim + 8  # Concatenated embedding dim

        # LSTM: 2 layers với dropout giữa các layer
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )

        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, n_products)

    def forward(self, product_ids: torch.Tensor, action_ids: torch.Tensor) -> torch.Tensor:
        """
        Args:
            product_ids : (batch_size, seq_len) — LongTensor
            action_ids  : (batch_size, seq_len) — LongTensor
        Returns:
            logits      : (batch_size, n_products) — raw scores
        """
        p_emb = self.product_embed(product_ids)         # (B, T, embed_dim)
        a_emb = self.action_embed(action_ids)            # (B, T, 8)
        x = torch.cat([p_emb, a_emb], dim=-1)           # (B, T, embed_dim+8)

        out, _ = self.lstm(x)                            # (B, T, hidden_dim)
        out = self.dropout(out[:, -1, :])                # Last timestep (B, hidden_dim)
        return self.fc(out)                              # (B, n_products)
