"""
BiLSTM Recommender — Model Mạnh nhất (Tiểu luận Chapter 3)

Bidirectional LSTM + Self-Attention — kiến trúc tiên tiến nhất trong 3 model.

Tại sao BiLSTM tốt hơn LSTM đơn chiều?
    - LSTM thông thường chỉ đọc sequence từ trái sang phải (past → present)
    - BiLSTM đọc cả 2 chiều: forward (1→T) + backward (T→1)
    - → Capture được context tốt hơn: "item 3 quan trọng vì có item 7 phía sau"

Self-Attention layer:
    - Không phải mọi timestep đều quan trọng như nhau
    - Attention học cách weight: timestep nào đáng chú ý nhất
    - → Tương tự Transformer attention nhưng lightweight hơn

Architecture:
    product_embed (n_products+2, embed_dim)  ─┐
                                               ├─ cat → BiLSTM → Attention pooling → Dropout → FC → logits
    action_embed  (n_actions+2,  8)           ─┘

    BiLSTM output: hidden_dim × 2 (vì concat forward + backward)
    Attention: (B, T, hidden*2) → weighted sum → (B, hidden*2)

Input:
    product_ids : LongTensor (batch, seq_len)
    action_ids  : LongTensor (batch, seq_len)
Output:
    logits      : FloatTensor (batch, n_products)

References:
    - Schuster & Paliwal (1997): "Bidirectional Recurrent Neural Networks"
    - Bahdanau et al. (2015): "Neural Machine Translation by Jointly Learning to Align and Translate"
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class AttentionLayer(nn.Module):
    """
    Additive Self-Attention (Bahdanau-style) để aggregate BiLSTM outputs.

    Thay vì chỉ lấy timestep cuối cùng như LSTM,
    Attention học cách gán trọng số cho từng timestep.

    Score(h_t) = v^T · tanh(W · h_t + b)
    α_t        = softmax(Score(h_t))
    context    = Σ α_t · h_t
    """

    def __init__(self, hidden_dim: int):
        super().__init__()
        # Projection layer: hidden_dim → 1 score per timestep
        self.attention_fc = nn.Linear(hidden_dim, 1, bias=True)

    def forward(self, lstm_output: torch.Tensor, mask: torch.Tensor = None) -> torch.Tensor:
        """
        Args:
            lstm_output : (batch_size, seq_len, hidden_dim) — BiLSTM all timesteps
            mask        : (batch_size, seq_len) — True for padded positions (optional)
        Returns:
            context     : (batch_size, hidden_dim) — attention-weighted sum
        """
        # Compute attention scores: (B, T, 1)
        scores = self.attention_fc(torch.tanh(lstm_output))
        scores = scores.squeeze(-1)  # (B, T)

        # Mask padding positions with -inf before softmax
        if mask is not None:
            scores = scores.masked_fill(mask, float("-inf"))

        # Softmax over time dimension → attention weights
        alpha = F.softmax(scores, dim=-1)          # (B, T)

        # Weighted sum of LSTM outputs
        context = torch.bmm(alpha.unsqueeze(1), lstm_output)  # (B, 1, hidden_dim)
        return context.squeeze(1)                              # (B, hidden_dim)


class BiLSTMRecommender(nn.Module):
    """
    Bidirectional LSTM + Attention next-item recommendation — Model Mạnh nhất.

    Cải tiến so với LSTMRecommender:
        1. Bidirectional: forward + backward pass → context phong phú hơn
        2. Attention pooling: thay vì lấy timestep cuối, học cách weight timesteps
        3. Layer Normalization: ổn định hóa quá trình train

    Args:
        n_products (int): Số lượng sản phẩm trong catalog.
        n_actions  (int): Số loại action.
        embed_dim  (int): Chiều embedding của product (default=64).
        hidden_dim (int): Chiều hidden state MỖI CHIỀU của BiLSTM (default=128).
                          → Output thực tế = hidden_dim × 2 (vì bidirectional)
        n_layers   (int): Số BiLSTM layers (default=2).
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
        self.bidirectional_dim = hidden_dim * 2  # Output dim sau concat fwd+bwd

        # Embedding layers — cùng cấu trúc với SimpleRNN/LSTM
        self.product_embed = nn.Embedding(n_products + 2, embed_dim, padding_idx=0)
        self.action_embed  = nn.Embedding(n_actions + 2,  8,         padding_idx=0)

        input_dim = embed_dim + 8

        # Bidirectional LSTM — điểm khác biệt cốt lõi
        self.bilstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            bidirectional=True,  # ← KEY: forward + backward
            dropout=dropout if n_layers > 1 else 0.0,
        )

        # Self-Attention để aggregate tất cả timesteps
        self.attention = AttentionLayer(hidden_dim=self.bidirectional_dim)

        # Layer Normalization — ổn định hóa sau attention
        self.layer_norm = nn.LayerNorm(self.bidirectional_dim)

        self.dropout = nn.Dropout(dropout)

        # Output FC: bidirectional_dim (hidden*2) → n_products
        self.fc = nn.Linear(self.bidirectional_dim, n_products)

        # Weight initialization
        self._init_weights()

    def _init_weights(self):
        """Xavier initialization cho embedding layers."""
        nn.init.xavier_uniform_(self.product_embed.weight[1:])  # Skip padding idx
        nn.init.xavier_uniform_(self.action_embed.weight[1:])

    def forward(self, product_ids: torch.Tensor, action_ids: torch.Tensor) -> torch.Tensor:
        """
        Args:
            product_ids : (batch_size, seq_len) — LongTensor
            action_ids  : (batch_size, seq_len) — LongTensor
        Returns:
            logits      : (batch_size, n_products) — raw scores
        """
        # Embedding lookup
        p_emb = self.product_embed(product_ids)         # (B, T, embed_dim)
        a_emb = self.action_embed(action_ids)            # (B, T, 8)
        x = torch.cat([p_emb, a_emb], dim=-1)           # (B, T, embed_dim+8)

        # BiLSTM: output có cả forward và backward hidden states
        # bilstm_out: (B, T, hidden_dim*2) — concat [fwd_h, bwd_h] mỗi timestep
        bilstm_out, _ = self.bilstm(x)                  # (B, T, hidden*2)

        # Padding mask: product_id == 0 là <PAD>
        pad_mask = (product_ids == 0)                    # (B, T) — True where padded

        # Attention pooling: aggregate all timesteps → single vector
        context = self.attention(bilstm_out, mask=pad_mask)  # (B, hidden*2)

        # Layer norm + dropout
        context = self.layer_norm(context)
        context = self.dropout(context)

        return self.fc(context)                          # (B, n_products)
