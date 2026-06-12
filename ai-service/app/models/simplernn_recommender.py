"""
SimpleRNN Recommender — Model So sánh (Tiểu luận Chapter 3)

Vanilla RNN (Elman RNN) — baseline đơn giản nhất trong họ recurrent models.

Vấn đề của SimpleRNN:
    - Vanishing gradient: khó học long-range dependency
    - Không có cơ chế gate như LSTM (forget/input/output gate)
    - Phù hợp với sequence ngắn (window ≤ 8)

Tại sao vẫn cần SimpleRNN trong thực nghiệm?
    - Là baseline cơ sở để chứng minh LSTM/BiLSTM cải thiện đáng kể
    - Nhanh nhất, ít tham số nhất → benchmark tốc độ

Architecture:
    product_embed (n_products+2, embed_dim)  ─┐
                                               ├─ cat → RNN(vanilla) → Dropout → FC → logits
    action_embed  (n_actions+2,  8)           ─┘

Input:
    product_ids : LongTensor (batch, seq_len)
    action_ids  : LongTensor (batch, seq_len)
Output:
    logits      : FloatTensor (batch, n_products) — CrossEntropyLoss target
"""

import torch
import torch.nn as nn


class SimpleRNNRecommender(nn.Module):
    """
    Simple RNN (Elman RNN) next-item recommendation — Baseline Model.

    Kiến trúc đồng nhất với LSTM/BiLSTM để so sánh công bằng:
    - Cùng embedding layers (product + action)
    - Cùng hidden_dim, n_layers, dropout
    - Chỉ khác ở lớp recurrent: nn.RNN thay vì nn.LSTM

    Args:
        n_products (int): Số lượng sản phẩm trong catalog.
        n_actions  (int): Số loại action (view, click, add_to_cart, purchase, search).
        embed_dim  (int): Chiều embedding của product (default=64).
        hidden_dim (int): Chiều hidden state của RNN (default=128).
        n_layers   (int): Số RNN layers (default=2).
        dropout    (float): Dropout rate (default=0.3).
    """

    def __init__(
        self,
        n_products: int,
        n_actions: int,
        embed_dim: int = 64,
        hidden_dim: int = 128,
        n_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.n_products = n_products
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers

        # Embedding layers — giống hệt LSTM/BiLSTM để so sánh công bằng
        # padding_idx=0 → <PAD> token không tham gia học
        self.product_embed = nn.Embedding(n_products + 2, embed_dim, padding_idx=0)
        self.action_embed  = nn.Embedding(n_actions + 2,  8,         padding_idx=0)

        input_dim = embed_dim + 8  # Concatenated embedding dim

        # Vanilla RNN — điểm khác biệt duy nhất so với LSTM/BiLSTM
        # nonlinearity='tanh' (mặc định) → dễ vanishing gradient hơn 'relu'
        self.rnn = nn.RNN(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
            nonlinearity="tanh",
        )

        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, n_products)

        # Weight initialization — Xavier uniform cho RNN weights
        self._init_weights()

    def _init_weights(self):
        """Khởi tạo weights RNN để giảm vanishing gradient ban đầu."""
        for name, param in self.rnn.named_parameters():
            if "weight_ih" in name:
                nn.init.xavier_uniform_(param.data)
            elif "weight_hh" in name:
                nn.init.orthogonal_(param.data)
            elif "bias" in name:
                nn.init.zeros_(param.data)

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

        out, _ = self.rnn(x)                             # (B, T, hidden_dim)
        out = self.dropout(out[:, -1, :])                # Last timestep (B, hidden_dim)
        return self.fc(out)                              # (B, n_products)
