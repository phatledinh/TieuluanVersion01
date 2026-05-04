"""
LSTM Model — Chapter 3.4.2

Exactly follows the PDF specification:

    class LSTMModel(nn.Module):
        def __init__(self, input_dim=10, hidden_dim=64, output_dim=100):
            super().__init__()
            self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
            self.fc = nn.Linear(hidden_dim, output_dim)

        def forward(self, x):
            out, _ = self.lstm(x)
            out = out[:, -1, :]
            return self.fc(out)

Usage:
    - input_dim:  embedding dimension (product + action encoded)
    - hidden_dim: LSTM hidden state size
    - output_dim: number of products (predict next product)
"""

import torch
import torch.nn as nn


class LSTMModel(nn.Module):
    """
    LSTM Sequence Model for next-product prediction — PDF 3.4.2

    Input:  (batch_size, sequence_length, input_dim)
    Output: (batch_size, output_dim)  — logits over all products
    """

    def __init__(self, input_dim=10, hidden_dim=64, output_dim=100):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]   # Take last timestep output
        return self.fc(out)
