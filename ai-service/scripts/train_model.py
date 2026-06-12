"""
Universal Model Trainer — Tiểu luận Chapter 3

Train bất kỳ model nào (SimpleRNN / LSTM / BiLSTM) trên bất kỳ dataset nào.

Usage:
    python scripts/train_model.py --model simplernn --csv data/real/retail_rocket.csv
    python scripts/train_model.py --model lstm      --csv data/real/movielens_1m.csv
    python scripts/train_model.py --model bilstm    --csv data/real/amazon_electronics.csv

    # Đầy đủ tham số
    python scripts/train_model.py \\
        --model lstm \\
        --csv data/behavior_medium_real.csv \\
        --output-dir trained_models/ \\
        --epochs 50 \\
        --window 8 \\
        --batch-size 64 \\
        --lr 0.001 \\
        --early-stopping 5

Output:
    trained_models/lstm_small/model.pt
    trained_models/lstm_small/meta.json
    trained_models/lstm_small/history.json
"""

import argparse
import csv
import json
import logging
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from tqdm import tqdm
from torch.utils.data import Dataset, DataLoader, random_split

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.lstm_recommender    import LSTMRecommender
from app.models.simplernn_recommender import SimpleRNNRecommender
from app.models.bilstm_recommender  import BiLSTMRecommender

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── Dataset Classes ─────────────────────────────────────────────────────────────

class SequenceDataset(Dataset):
    """
    Dataset cho LSTM/BiLSTM: sliding window trên chuỗi hành vi.
    Mỗi sample: (product_ids_window, action_ids_window) → target_product_id
    """

    def __init__(self, sequences: list):
        self.sequences = sequences

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        product_ids, action_ids, target = self.sequences[idx]
        return (
            torch.tensor(product_ids, dtype=torch.long),
            torch.tensor(action_ids,  dtype=torch.long),
            torch.tensor(target,      dtype=torch.long),
        )




# ── Data Loading ────────────────────────────────────────────────────────────────

def load_csv(csv_path: str) -> list:
    """Load behavior CSV."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    logger.info("Loaded %d rows from %s", len(rows), csv_path)
    return rows


def build_vocabularies(rows: list) -> Tuple[Dict, Dict]:
    """Xây dựng product_to_idx và action_to_idx."""
    products = sorted(set(str(r["product_id"]) for r in rows))
    actions  = sorted(set(r["action"].strip().lower() for r in rows))

    product_to_idx = {"<PAD>": 0, "<UNK>": 1}
    for i, p in enumerate(products, start=2):
        product_to_idx[p] = i

    action_to_idx = {"<PAD>": 0, "<UNK>": 1}
    for i, a in enumerate(actions, start=2):
        action_to_idx[a] = i

    logger.info("Vocab: %d products, %d actions", len(product_to_idx), len(action_to_idx))
    return product_to_idx, action_to_idx


def prepare_sequence_data(rows: list, product_to_idx: dict, action_to_idx: dict,
                           window: int = 8) -> list:
    """Tạo sliding window sequences cho LSTM/BiLSTM."""
    user_events = defaultdict(list)
    for row in rows:
        uid = row["user_id"]
        pid = str(row["product_id"])
        action = row["action"].strip().lower()
        user_events[uid].append((pid, action))

    sequences = []
    for uid, events in user_events.items():
        if len(events) < window + 1:
            continue
        for i in range(len(events) - window):
            window_events = events[i:i + window]
            target_pid    = events[i + window][0]

            product_ids = [product_to_idx.get(p, 1) for p, _ in window_events]
            action_ids  = [action_to_idx.get(a, 1)  for _, a in window_events]
            target_idx  = product_to_idx.get(target_pid, 1)

            sequences.append((product_ids, action_ids, target_idx))

    logger.info("Created %d sequence samples (window=%d)", len(sequences), window)
    return sequences




# ── Evaluation Metrics ──────────────────────────────────────────────────────────

def precision_recall_ndcg_at_k(
    model,
    val_dataset: SequenceDataset,
    product_to_idx: dict,
    k: int = 5,
    model_type: str = "lstm",
    device: torch.device = None,
    max_samples: int = 500,
) -> Dict[str, float]:
    """
    Tính Precision@K, Recall@K, NDCG@K.
    Dùng Leave-one-out: dự đoán item cuối cùng trong sequence.
    """
    if device is None:
        device = torch.device("cpu")

    model.eval()
    hits_p = 0
    hits_r = 0
    ndcg_sum = 0.0
    total = 0

    # Limit samples để không mất quá nhiều thời gian
    indices = list(range(len(val_dataset)))
    if len(indices) > max_samples:
        import random
        random.shuffle(indices)
        indices = indices[:max_samples]

    with torch.no_grad():
        for idx in indices:
            sample = val_dataset[idx]
            target = sample[2].item()

            if model_type in ("simplernn", "lstm", "bilstm"):
                p_ids = sample[0].unsqueeze(0).to(device)  # (1, seq_len)
                a_ids = sample[1].unsqueeze(0).to(device)
                logits = model(p_ids, a_ids)                # (1, n_products)
                _, top_k = torch.topk(logits[0], k=k)
                top_k = top_k.tolist()

            total += 1

            # Precision@K: target trong top-k?
            if target in top_k:
                hits_p += 1
                hits_r += 1
                # NDCG: discount dựa trên vị trí
                rank = top_k.index(target) + 1
                ndcg_sum += 1.0 / (math.log2(rank + 1))

    precision = hits_p / total if total > 0 else 0.0
    recall    = hits_r / total if total > 0 else 0.0
    ndcg      = ndcg_sum / total if total > 0 else 0.0

    return {
        f"precision@{k}": precision * 100,
        f"recall@{k}":    recall    * 100,
        f"ndcg@{k}":      ndcg      * 100,
    }


# ── Training Functions ───────────────────────────────────────────────────────────

def train_sequence_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int,
    lr: float,
    early_stopping: int,
    device: torch.device,
) -> Tuple[dict, float]:
    """Training loop cho sequence models."""
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", patience=3, factor=0.5
    )

    history = {
        "epoch": [], "train_loss": [], "train_acc": [],
        "val_loss": [], "val_acc": []
    }

    best_val_loss = float("inf")
    patience_counter = 0
    best_state = None
    start = time.time()

    for epoch in range(epochs):
        # ── Train ──
        model.train()
        t_loss, t_correct, t_total = 0.0, 0, 0
        for p_ids, a_ids, targets in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs} [Train]", leave=False):
            p_ids, a_ids, targets = p_ids.to(device), a_ids.to(device), targets.to(device)
            optimizer.zero_grad()
            logits = model(p_ids, a_ids)
            loss = criterion(logits, targets)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            t_loss += loss.item() * p_ids.size(0)
            _, preds = torch.max(logits, 1)
            t_correct += (preds == targets).sum().item()
            t_total += targets.size(0)

        # ── Validation ──
        model.eval()
        v_loss, v_correct, v_total = 0.0, 0, 0
        with torch.no_grad():
            for p_ids, a_ids, targets in tqdm(val_loader, desc=f"Epoch {epoch+1}/{epochs} [Val]", leave=False):
                p_ids, a_ids, targets = p_ids.to(device), a_ids.to(device), targets.to(device)
                logits = model(p_ids, a_ids)
                loss = criterion(logits, targets)
                v_loss += loss.item() * p_ids.size(0)
                _, preds = torch.max(logits, 1)
                v_correct += (preds == targets).sum().item()
                v_total += targets.size(0)

        avg_t = t_loss / max(t_total, 1)
        avg_v = v_loss / max(v_total, 1)
        t_acc = t_correct / max(t_total, 1) * 100
        v_acc = v_correct / max(v_total, 1) * 100

        history["epoch"].append(epoch + 1)
        history["train_loss"].append(round(avg_t, 6))
        history["train_acc"].append(round(t_acc, 4))
        history["val_loss"].append(round(avg_v, 6))
        history["val_acc"].append(round(v_acc, 4))

        scheduler.step(avg_v)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info(
                "Epoch [%d/%d] train_loss=%.4f train_acc=%.2f%% val_loss=%.4f val_acc=%.2f%%",
                epoch + 1, epochs, avg_t, t_acc, avg_v, v_acc
            )

        # Early stopping
        if avg_v < best_val_loss:
            best_val_loss = avg_v
            patience_counter = 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= early_stopping:
                logger.info("Early stopping at epoch %d", epoch + 1)
                break

    if best_state:
        model.load_state_dict(best_state)

    train_time = time.time() - start
    return history, train_time




# ── Main ─────────────────────────────────────────────────────────────────────────

DATA_DIR   = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "trained_models"

DATASET_FILES = {
    "small":  "behavior_small_real.csv",
    "medium": "behavior_medium_real.csv",
    "large":  "behavior_large_real.csv",
}


def main():
    parser = argparse.ArgumentParser(description="Universal Model Trainer")
    parser.add_argument("--model",    choices=["simplernn", "lstm", "bilstm"], required=True)
    parser.add_argument("--dataset",  choices=["small", "medium", "large"], default=None,
                        help="Preset dataset size (dùng thay cho --csv)")
    parser.add_argument("--csv",      default=None,
                        help="Path to CSV file (ưu tiên hơn --dataset)")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: trained_models/<model>_<dataset>)")
    parser.add_argument("--epochs",       type=int,   default=50)
    parser.add_argument("--window",       type=int,   default=8,
                        help="Sequence window size")
    parser.add_argument("--batch-size",   type=int,   default=64)
    parser.add_argument("--lr",           type=float, default=0.001)
    parser.add_argument("--embed-dim",    type=int,   default=32)
    parser.add_argument("--hidden-dim",   type=int,   default=128)
    parser.add_argument("--n-layers",     type=int,   default=2)
    parser.add_argument("--dropout",      type=float, default=0.3)
    parser.add_argument("--early-stopping", type=int, default=7)
    parser.add_argument("--val-split",    type=float, default=0.2)
    args = parser.parse_args()

    # Resolve CSV path
    if args.csv:
        csv_path = Path(args.csv)
    elif args.dataset:
        csv_path = DATA_DIR / DATASET_FILES[args.dataset]
    else:
        # Default: medium
        csv_path = DATA_DIR / DATASET_FILES["medium"]
        args.dataset = "medium"

    if not csv_path.exists():
        logger.error("CSV not found: %s — Run generate_realistic_behavior.py first!", csv_path)
        sys.exit(1)

    # Resolve output dir
    dataset_name = args.dataset or csv_path.stem
    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        out_dir = OUTPUT_DIR / f"{args.model}_{dataset_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)
    logger.info("Training %s on %s", args.model.upper(), csv_path.name)

    # ── Load data ──
    rows = load_csv(str(csv_path))
    product_to_idx, action_to_idx = build_vocabularies(rows)
    n_products = len(product_to_idx)
    n_actions  = len(action_to_idx)

    if args.model in ("simplernn", "lstm", "bilstm"):
        # ── Sequence model (RNN family) ──
        sequences = prepare_sequence_data(rows, product_to_idx, action_to_idx, window=args.window)
        if not sequences:
            logger.error("No sequences created. Increase interactions per user.")
            sys.exit(1)

        dataset = SequenceDataset(sequences)
        val_size   = max(1, int(len(dataset) * args.val_split))
        train_size = len(dataset) - val_size
        train_ds, val_ds = random_split(
            dataset, [train_size, val_size],
            generator=torch.Generator().manual_seed(42)
        )

        train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,  num_workers=0)
        val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, num_workers=0)

        # Build model — chọn theo --model flag
        MODEL_MAP = {
            "simplernn": SimpleRNNRecommender,
            "lstm":      LSTMRecommender,
            "bilstm":    BiLSTMRecommender,
        }
        ModelClass = MODEL_MAP[args.model]
        model = ModelClass(
            n_products=n_products,
            n_actions=n_actions,
            embed_dim=args.embed_dim,
            hidden_dim=args.hidden_dim,
            n_layers=args.n_layers,
            dropout=args.dropout,
        ).to(device)

        n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        logger.info("Model parameters: %d", n_params)

        history, train_time = train_sequence_model(
            model, train_loader, val_loader,
            epochs=args.epochs, lr=args.lr,
            early_stopping=args.early_stopping,
            device=device,
        )

        logger.info("Computing ranking metrics...")
        metrics = precision_recall_ndcg_at_k(
            model=model,
            val_dataset=val_ds,
            product_to_idx=product_to_idx,
            k=5,
            model_type=args.model,
            device=device,
        )

        meta = {
            "model": args.model,
            "dataset": dataset_name,
            "csv": str(csv_path),
            "n_products": n_products,
            "n_actions": n_actions,
            "embed_dim": args.embed_dim,
            "hidden_dim": args.hidden_dim,
            "n_layers": args.n_layers,
            "dropout": args.dropout,
            "window": args.window,
            "n_params": n_params,
            "train_time_seconds": round(train_time, 2),
            "final_val_loss": history["val_loss"][-1],
            "final_val_acc":  history["val_acc"][-1],
            "precision@5":    metrics["precision@5"],
            "recall@5":       metrics["recall@5"],
            "ndcg@5":         metrics["ndcg@5"],
            "product_to_idx": product_to_idx,
            "action_to_idx":  action_to_idx,
        }



    # ── Save ──
    torch.save(model.state_dict(), out_dir / "model.pt")
    with open(out_dir / "meta.json",    "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    with open(out_dir / "history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 55)
    print(f"  ✅ Training complete: {args.model.upper()} on {dataset_name}")
    print(f"  📁 Output: {out_dir}")
    print(f"  ⏱  Time: {train_time:.1f}s")
    print(f"  📉 Val Loss: {meta['final_val_loss']:.4f}")
    print(f"  🎯 Val Acc:  {meta['final_val_acc']:.2f}%")
    print(f"  📊 Precision@5: {meta['precision@5']:.2f}%")
    print(f"  📊 Recall@5:    {meta['recall@5']:.2f}%")
    print(f"  🏆 NDCG@5:      {meta['ndcg@5']:.2f}%")
    print("=" * 55)


if __name__ == "__main__":
    main()
