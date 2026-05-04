"""
Train LSTM Model — Chapter 3.4.3

Training loop exactly follows PDF specification:

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters())
    for epoch in range(epochs):
        output = model(x)
        loss = criterion(output, y)
        loss.backward()
        optimizer.step()

Input data: behavior CSV → sliding window sequences
Output: trained model weights (lstm_model.pt) + metadata (lstm_meta.json)

Usage:
    python scripts/train_lstm.py
    python scripts/train_lstm.py --epochs 50 --window 8
"""

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.models.lstm_model import LSTMModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── Dataset ──

class BehaviorSequenceDataset(Dataset):
    """Sliding window dataset from behavior CSV."""

    def __init__(self, sequences, input_dim):
        self.sequences = sequences  # list of (x_features, y_label)
        self.input_dim = input_dim

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        x, y = self.sequences[idx]
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.long)


def load_and_prepare_data(csv_path: str, window: int = 8):
    """Load CSV and create sliding window sequences."""
    # Read CSV
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    logger.info("Loaded %d rows from %s", len(rows), csv_path)

    # Build vocabularies
    product_set = set()
    action_set = set()
    for row in rows:
        product_set.add(str(row["product_id"]))
        action_set.add(row["action"].strip().lower())

    product_to_idx = {"<PAD>": 0, "<UNK>": 1}
    for i, pid in enumerate(sorted(product_set), start=2):
        product_to_idx[pid] = i

    action_to_idx = {"<PAD>": 0, "<UNK>": 1}
    for i, act in enumerate(sorted(action_set), start=2):
        action_to_idx[act] = i

    idx_to_product = {v: k for k, v in product_to_idx.items()}
    n_products = len(product_to_idx)
    n_actions = len(action_to_idx)
    input_dim = 6  # Feature vector size per timestep

    # Group by user and create sequences
    user_events = defaultdict(list)
    for row in rows:
        uid = row["user_id"]
        pid = str(row["product_id"])
        action = row["action"].strip().lower()
        user_events[uid].append((pid, action))

    # Sliding window
    sequences = []
    for uid, events in user_events.items():
        if len(events) < window + 1:
            continue
        for i in range(len(events) - window):
            window_events = events[i:i + window]
            target_pid = events[i + window][0]

            # Encode input features
            x = []
            for pid, action in window_events:
                feat = np.zeros(input_dim, dtype=np.float32)
                feat[0] = product_to_idx.get(pid, 1) / max(n_products, 1)
                feat[1] = action_to_idx.get(action, 1) / max(n_actions, 1)
                feat[2] = 1.0 if action == "purchase" else 0.0
                feat[3] = 1.0 if action == "add_to_cart" else 0.0
                feat[4] = 1.0 if action == "click" else 0.0
                feat[5] = 1.0 if action == "view" else 0.0
                x.append(feat)

            y = product_to_idx.get(target_pid, 1)
            sequences.append((x, y))

    logger.info("Created %d sequences (window=%d)", len(sequences), window)

    meta = {
        "n_products": n_products,
        "n_actions": n_actions,
        "input_dim": input_dim,
        "hidden_dim": 64,
        "window": window,
        "product_to_idx": product_to_idx,
        "action_to_idx": action_to_idx,
    }

    return sequences, meta


def train(sequences, meta, epochs: int = 30, batch_size: int = 64, lr: float = 0.001):
    """
    Train LSTM model — exactly following PDF 3.4.3

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters())
    for epoch in range(epochs):
        output = model(x)
        loss = criterion(output, y)
        loss.backward()
        optimizer.step()
    """
    dataset = BehaviorSequenceDataset(sequences, meta["input_dim"])
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # Create model (PDF 3.4.2)
    model = LSTMModel(
        input_dim=meta["input_dim"],
        hidden_dim=meta["hidden_dim"],
        output_dim=meta["n_products"],
    )

    # Training setup (PDF 3.4.3)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    logger.info("Training LSTM: input_dim=%d, hidden_dim=%d, output_dim=%d",
                meta["input_dim"], meta["hidden_dim"], meta["n_products"])

    # Training loop (PDF 3.4.3)
    for epoch in range(epochs):
        total_loss = 0.0
        correct = 0
        total = 0

        model.train()
        for x, y in dataloader:
            optimizer.zero_grad()
            output = model(x)            # PDF 3.4.3: output = model(x)
            loss = criterion(output, y)   # PDF 3.4.3: loss = criterion(output, y)
            loss.backward()               # PDF 3.4.3: loss.backward()
            optimizer.step()              # PDF 3.4.3: optimizer.step()

            total_loss += loss.item() * x.size(0)
            _, predicted = torch.max(output, 1)
            correct += (predicted == y).sum().item()
            total += y.size(0)

        avg_loss = total_loss / max(total, 1)
        accuracy = correct / max(total, 1) * 100
        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info("Epoch [%d/%d] — Loss: %.4f, Accuracy: %.2f%%", epoch + 1, epochs, avg_loss, accuracy)

    return model


def main():
    parser = argparse.ArgumentParser(description="Train LSTM Model — PDF 3.4.3")
    parser.add_argument("--csv", default=str(Path(__file__).parent.parent / "data" / "behavior_data.csv"))
    parser.add_argument("--output-dir", default=str(Path(__file__).parent.parent / "trained_models"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--window", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.001)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Prepare data
    sequences, meta = load_and_prepare_data(args.csv, window=args.window)

    if not sequences:
        logger.error("No sequences generated. Check CSV data and window size.")
        sys.exit(1)

    # 2. Train model (PDF 3.4.3)
    model = train(sequences, meta, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

    # 3. Save model weights
    model_path = output_dir / "lstm_model.pt"
    torch.save(model.state_dict(), model_path)
    logger.info("Model saved to %s", model_path)

    # 4. Save metadata
    meta_path = output_dir / "lstm_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    logger.info("Metadata saved to %s", meta_path)

    print(f"\n✓ Training complete!")
    print(f"  Model: {model_path}")
    print(f"  Meta:  {meta_path}")


if __name__ == "__main__":
    main()
