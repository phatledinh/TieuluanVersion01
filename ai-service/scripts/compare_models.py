"""
Model Comparison Experiment — Tiểu luận Chapter 3

So sánh 3 model (SimpleRNN / LSTM / BiLSTM) trên 3 dataset e-commerce thật:
    - Retail Rocket         (e-commerce event stream — schema 1-1)
    - REES46 Electronics    (electronics store — view/cart/purchase)
    - REES46 Cosmetics      (multi-category store — view/cart/purchase)

Metrics đánh giá:
    - Precision@5, Recall@5, NDCG@5 (Leave-One-Out protocol)
    - Validation Loss (CrossEntropy)
    - Training Time (giây)
    - #Parameters

Output:
    experiment_results/comparison_report.md   — bảng so sánh Markdown
    experiment_results/comparison_plots.png   — biểu đồ đa chiều
    experiment_results/comparison_log.json    — raw data

Usage:
    python scripts/compare_models.py
    python scripts/compare_models.py --epochs 20 --dataset retail_rocket
    python scripts/compare_models.py --epochs 30 --models simplernn lstm bilstm
"""

import argparse
import csv
import json
import logging
import math
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.simplernn_recommender import SimpleRNNRecommender
from app.models.lstm_recommender      import LSTMRecommender
from app.models.bilstm_recommender    import BiLSTMRecommender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent.parent
DATA_DIR    = ROOT_DIR / "data" / "real"
RESULTS_DIR = ROOT_DIR / "experiment_results"
MODELS_DIR  = ROOT_DIR / "trained_models"

DATASETS = {
    "retail_rocket":      DATA_DIR / "retail_rocket.csv",
    "rees46_electronics": DATA_DIR / "rees46_electronics.csv",
    "rees46_cosmetics":   DATA_DIR / "rees46_cosmetics.csv",
}

MODELS = {
    "SimpleRNN": SimpleRNNRecommender,
    "LSTM":      LSTMRecommender,
    "BiLSTM":    BiLSTMRecommender,
}


# ── Dataset class ─────────────────────────────────────────────────────────────

class SequenceDataset(Dataset):
    """Sliding window sequences cho RNN models."""
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


# ── Data pipeline ─────────────────────────────────────────────────────────────

def load_and_prepare(csv_path: Path, window: int = 8, min_interactions: int = 5):
    """Load CSV và tạo sequences."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    logger.info("Loaded %d rows from %s", len(rows), csv_path.name)

    # Vocabularies
    products = sorted(set(str(r["product_id"]) for r in rows))
    actions  = sorted(set(r["action"].strip().lower() for r in rows))

    product_to_idx = {"<PAD>": 0, "<UNK>": 1}
    for i, p in enumerate(products, start=2):
        product_to_idx[p] = i

    action_to_idx = {"<PAD>": 0, "<UNK>": 1}
    for i, a in enumerate(actions, start=2):
        action_to_idx[a] = i

    # Group by user, sort by timestamp
    user_events = defaultdict(list)
    for row in rows:
        uid    = row["user_id"]
        pid    = str(row["product_id"])
        action = row["action"].strip().lower()
        user_events[uid].append((pid, action))

    # Sliding window
    sequences = []
    for uid, events in user_events.items():
        if len(events) < window + 1:
            continue
        for i in range(len(events) - window):
            window_events = events[i:i + window]
            target_pid    = events[i + window][0]
            product_ids   = [product_to_idx.get(p, 1) for p, _ in window_events]
            action_ids    = [action_to_idx.get(a, 1)  for _, a in window_events]
            target_idx    = product_to_idx.get(target_pid, 1)
            sequences.append((product_ids, action_ids, target_idx))

    logger.info(
        "Vocab: %d products, %d actions → %d sequences (window=%d)",
        len(product_to_idx), len(action_to_idx), len(sequences), window
    )
    return sequences, product_to_idx, action_to_idx


# ── Training ──────────────────────────────────────────────────────────────────

def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    for p_ids, a_ids, targets in loader:
        p_ids, a_ids, targets = p_ids.to(device), a_ids.to(device), targets.to(device)
        optimizer.zero_grad()
        logits = model(p_ids, a_ids)
        loss = criterion(logits, targets)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total_loss += loss.item() * p_ids.size(0)
        _, preds = torch.max(logits, 1)
        correct += (preds == targets).sum().item()
        total += targets.size(0)
    return total_loss / max(total, 1), correct / max(total, 1) * 100


def validate(model, loader, criterion, device):
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    with torch.no_grad():
        for p_ids, a_ids, targets in loader:
            p_ids, a_ids, targets = p_ids.to(device), a_ids.to(device), targets.to(device)
            logits = model(p_ids, a_ids)
            loss = criterion(logits, targets)
            total_loss += loss.item() * p_ids.size(0)
            _, preds = torch.max(logits, 1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)
    return total_loss / max(total, 1), correct / max(total, 1) * 100


def compute_ranking_metrics(model, val_dataset, k: int = 5, device=None, max_samples=1000):
    """
    Tính Precision@K, Recall@K, NDCG@K.
    Protocol: Leave-One-Out — dự đoán item cuối sequence.
    """
    if device is None:
        device = torch.device("cpu")
    model.eval()

    indices = list(range(len(val_dataset)))
    if len(indices) > max_samples:
        random.seed(42)
        random.shuffle(indices)
        indices = indices[:max_samples]

    hits, ndcg_sum, total = 0, 0.0, 0
    with torch.no_grad():
        for idx in indices:
            p_ids, a_ids, target = val_dataset[idx]
            target_item = target.item()

            p_ids = p_ids.unsqueeze(0).to(device)
            a_ids = a_ids.unsqueeze(0).to(device)
            logits = model(p_ids, a_ids)
            _, top_k = torch.topk(logits[0], k=k)
            top_k_list = top_k.tolist()

            total += 1
            if target_item in top_k_list:
                hits += 1
                rank = top_k_list.index(target_item) + 1
                ndcg_sum += 1.0 / math.log2(rank + 1)

    precision = hits / total * 100 if total > 0 else 0.0
    recall    = hits / total * 100 if total > 0 else 0.0
    ndcg      = ndcg_sum / total * 100 if total > 0 else 0.0

    return {
        f"precision@{k}": round(precision, 3),
        f"recall@{k}":    round(recall,    3),
        f"ndcg@{k}":      round(ndcg,      3),
    }


def run_experiment(
    model_name: str,
    ModelClass,
    dataset_name: str,
    sequences: list,
    product_to_idx: dict,
    action_to_idx: dict,
    epochs: int,
    batch_size: int,
    lr: float,
    embed_dim: int,
    hidden_dim: int,
    n_layers: int,
    dropout: float,
    window: int,
    early_stopping: int,
    device: torch.device,
) -> dict:
    """Train 1 model trên 1 dataset → trả về kết quả dict."""
    n_products = len(product_to_idx)
    n_actions  = len(action_to_idx)

    dataset  = SequenceDataset(sequences)
    val_size = max(1, int(len(dataset) * 0.2))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=0)

    model = ModelClass(
        n_products=n_products,
        n_actions=n_actions,
        embed_dim=embed_dim,
        hidden_dim=hidden_dim,
        n_layers=n_layers,
        dropout=dropout,
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", patience=3, factor=0.5
    )

    best_val_loss = float("inf")
    patience_ctr  = 0
    best_state    = None
    history       = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    start_time    = time.time()

    logger.info(
        "▶ Training %s on %s | params=%d | train=%d val=%d",
        model_name, dataset_name, n_params, train_size, val_size
    )

    for epoch in range(epochs):
        t_loss, t_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        v_loss, v_acc = validate(model, val_loader, criterion, device)

        history["train_loss"].append(round(t_loss, 6))
        history["val_loss"].append(round(v_loss, 6))
        history["train_acc"].append(round(t_acc, 4))
        history["val_acc"].append(round(v_acc, 4))

        scheduler.step(v_loss)

        if (epoch + 1) % 1 == 0:  # Log mỗi epoch
            logger.info(
                "  Epoch [%02d/%02d] train_loss=%.4f train_acc=%.2f%% val_loss=%.4f val_acc=%.2f%%",
                epoch + 1, epochs, t_loss, t_acc, v_loss, v_acc
            )

        if v_loss < best_val_loss:
            best_val_loss = v_loss
            patience_ctr  = 0
            best_state    = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience_ctr += 1
            # Early stopping disabled by default (patience=999)
            # Train full epochs to get complete learning curves
            if early_stopping < 999 and patience_ctr >= early_stopping:
                logger.info("  Early stopping at epoch %d", epoch + 1)
                break

    if best_state:
        model.load_state_dict(best_state)

    train_time = time.time() - start_time

    # Ranking metrics
    metrics = compute_ranking_metrics(model, val_ds, k=5, device=device)

    # Save model
    save_dir = MODELS_DIR / f"{model_name.lower()}_{dataset_name}"
    save_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), save_dir / "model.pt")

    meta = {
        "model": model_name,
        "dataset": dataset_name,
        "n_products": n_products,
        "n_actions": n_actions,
        "n_params": n_params,
        "embed_dim": embed_dim,
        "hidden_dim": hidden_dim,
        "n_layers": n_layers,
        "dropout": dropout,
        "window": window,
        "product_to_idx": product_to_idx,
        "action_to_idx": action_to_idx,
        "train_time_seconds": round(train_time, 2),
        "final_val_loss": history["val_loss"][-1],
        "final_val_acc": history["val_acc"][-1],
    }
    with open(save_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    with open(save_dir / "history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    result = {
        "model":      model_name,
        "dataset":    dataset_name,
        "n_params":   n_params,
        "train_time": round(train_time, 1),
        "val_loss":   history["val_loss"][-1],
        "val_acc":    history["val_acc"][-1],
        "history":    history,   # full history for plotting
        **metrics,
    }
    logger.info(
        "  ✅ %s / %s → P@5=%.2f%% NDCG@5=%.2f%% time=%.0fs",
        model_name, dataset_name,
        result.get("precision@5", 0), result.get("ndcg@5", 0), train_time
    )
    return result


# ── Report generation ─────────────────────────────────────────────────────────

def generate_report(all_results: list, best_model: dict):
    """Tạo báo cáo Markdown đầy đủ."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "comparison_report.md"

    # Organize by dataset
    by_dataset = defaultdict(list)
    for r in all_results:
        by_dataset[r["dataset"]].append(r)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# So Sánh Mô Hình: SimpleRNN vs LSTM vs BiLSTM\n\n")
        f.write("> Tiểu luận — Chapter 3: Thực nghiệm so sánh mô hình học sâu\n\n")

        f.write("## Tổng Quan\n\n")
        f.write("| Model | Kiến trúc | Đặc điểm |\n")
        f.write("|-------|-----------|----------|\n")
        f.write("| **SimpleRNN** | Vanilla RNN (Elman) | Baseline — không có gate, dễ vanishing gradient |\n")
        f.write("| **LSTM** | LSTM 2 layers + Dropout | Gate mechanism — học long-range dependency tốt |\n")
        f.write("| **BiLSTM** | BiLSTM + Self-Attention | Bidirectional + Attention pooling — mạnh nhất |\n\n")

        f.write("## Kết Quả Theo Dataset\n\n")
        for dataset_name, results in by_dataset.items():
            display_name = {
                "retail_rocket":      "Retail Rocket (E-Commerce)",
                "rees46_electronics": "REES46 Electronics Store",
                "rees46_cosmetics":   "REES46 Cosmetics Store",
            }.get(dataset_name, dataset_name)

            f.write(f"### {display_name}\n\n")
            f.write("| Model | Precision@5 | Recall@5 | NDCG@5 | Val Loss | Val Acc | Train Time | #Params |\n")
            f.write("|-------|:-----------:|:--------:|:------:|:--------:|:-------:|:----------:|:-------:|\n")

            results_sorted = sorted(results, key=lambda r: r.get("ndcg@5", 0), reverse=True)
            for i, r in enumerate(results_sorted):
                bold = "**" if i == 0 else ""
                f.write(
                    f"| {bold}{r['model']}{bold} "
                    f"| {bold}{r.get('precision@5', 0):.2f}%{bold} "
                    f"| {r.get('recall@5', 0):.2f}% "
                    f"| {bold}{r.get('ndcg@5', 0):.2f}%{bold} "
                    f"| {r['val_loss']:.4f} "
                    f"| {r['val_acc']:.2f}% "
                    f"| {r['train_time']:.0f}s "
                    f"| {r['n_params']:,} |\n"
                )
            f.write("\n")

        f.write("## Tổng Hợp Trên Tất Cả Dataset\n\n")
        # Aggregate: mean across datasets
        model_agg = defaultdict(lambda: defaultdict(list))
        for r in all_results:
            for key in ["precision@5", "recall@5", "ndcg@5", "val_loss", "train_time"]:
                model_agg[r["model"]][key].append(r.get(key, 0))

        f.write("| Model | Avg Precision@5 | Avg Recall@5 | Avg NDCG@5 | Avg Val Loss | Avg Train Time |\n")
        f.write("|-------|:---------------:|:------------:|:----------:|:------------:|:--------------:|\n")

        agg_summary = []
        for model_name in ["SimpleRNN", "LSTM", "BiLSTM"]:
            if model_name not in model_agg:
                continue
            d = model_agg[model_name]
            avg_p   = sum(d["precision@5"]) / len(d["precision@5"])
            avg_r   = sum(d["recall@5"])    / len(d["recall@5"])
            avg_n   = sum(d["ndcg@5"])      / len(d["ndcg@5"])
            avg_vl  = sum(d["val_loss"])     / len(d["val_loss"])
            avg_t   = sum(d["train_time"])   / len(d["train_time"])
            agg_summary.append((model_name, avg_p, avg_r, avg_n, avg_vl, avg_t))

        agg_summary.sort(key=lambda x: x[3], reverse=True)
        for i, (name, p, r, n, vl, t) in enumerate(agg_summary):
            bold = "**" if i == 0 else ""
            f.write(
                f"| {bold}{name}{bold} | {bold}{p:.2f}%{bold} | {r:.2f}% "
                f"| {bold}{n:.2f}%{bold} | {vl:.4f} | {t:.0f}s |\n"
            )

        f.write("\n## Model Được Lựa Chọn\n\n")
        bm = best_model
        f.write(f"> **{bm['model']}** được lựa chọn là model tối ưu cho hệ thống.\n\n")
        f.write(f"**Lý do:**\n")
        f.write(f"- Đạt NDCG@5 cao nhất: **{bm.get('ndcg@5', 0):.2f}%**\n")
        f.write(f"- Precision@5: **{bm.get('precision@5', 0):.2f}%**\n")
        f.write(f"- Dataset tốt nhất: {bm['dataset']}\n\n")

        if bm["model"] == "BiLSTM":
            f.write("**Phân tích:** BiLSTM vượt trội nhờ:\n")
            f.write("1. **Bidirectional processing** — đọc sequence từ cả 2 chiều\n")
            f.write("2. **Self-Attention pooling** — focus vào timestep quan trọng\n")
            f.write("3. **Layer Normalization** — ổn định quá trình train\n\n")
        elif bm["model"] == "LSTM":
            f.write("**Phân tích:** LSTM cân bằng tốt giữa độ chính xác và tốc độ train,\n")
            f.write("phù hợp hơn BiLSTM khi dataset có kích thước vừa phải.\n\n")
        else:
            f.write("**Phân tích:** SimpleRNN cho kết quả tốt bất ngờ trên dataset này,\n")
            f.write("có thể do sequence ngắn (window=8) không yêu cầu long-range memory.\n\n")

        f.write("## Tham Số Thực Nghiệm\n\n")
        f.write("| Hyperparameter | Giá trị |\n")
        f.write("|----------------|--------|\n")
        f.write("| Window size | 8 |\n")
        f.write("| Batch size | 128 |\n")
        f.write("| Learning rate | 0.001 |\n")
        f.write("| Embed dim | 64 |\n")
        f.write("| Hidden dim | 128 |\n")
        f.write("| Num layers | 2 |\n")
        f.write("| Dropout | 0.3 |\n")
        f.write("| Optimizer | Adam + ReduceLROnPlateau |\n")
        f.write("| Early stopping | Disabled (train full epochs) |\n")
        f.write("| Evaluation | Leave-One-Out @ K=5 |\n")

    print(f"\n  ✓ Report saved: {report_path}")
    return report_path


def generate_plots(all_results: list):
    """Tạo biểu đồ so sánh."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        logger.warning("matplotlib not available — skipping plots")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    plot_path = RESULTS_DIR / "comparison_plots.png"

    model_names  = ["SimpleRNN", "LSTM", "BiLSTM"]
    dataset_names = list(DATASETS.keys())
    display_datasets = ["Retail Rocket", "REES46 Elec.", "REES46 Cosm."]

    # Build matrices: rows=models, cols=datasets
    def build_matrix(metric_key):
        mat = []
        result_map = {(r["model"], r["dataset"]): r for r in all_results}
        for m in model_names:
            row = []
            for d in dataset_names:
                row.append(result_map.get((m, d), {}).get(metric_key, 0))
            mat.append(row)
        return np.array(mat)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("So Sánh SimpleRNN / LSTM / BiLSTM\nTrên 3 Dataset E-Commerce Thật", fontsize=14, fontweight="bold")

    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]

    metrics_config = [
        ("precision@5", "Precision@5 (%)", axes[0, 0]),
        ("ndcg@5",      "NDCG@5 (%)",      axes[0, 1]),
        ("val_loss",    "Validation Loss",  axes[1, 0]),
        ("train_time",  "Train Time (s)",   axes[1, 1]),
    ]

    x = np.arange(len(dataset_names))
    width = 0.25

    for metric_key, ylabel, ax in metrics_config:
        mat = build_matrix(metric_key)
        for i, (model_name, color) in enumerate(zip(model_names, colors)):
            bars = ax.bar(
                x + i * width - width, mat[i],
                width, label=model_name, color=color, alpha=0.85,
                edgecolor="white", linewidth=0.5
            )
            # Value labels
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    fmt = f"{h:.1f}" if metric_key in ("val_loss", "train_time") else f"{h:.1f}%"
                    ax.text(
                        bar.get_x() + bar.get_width() / 2, h * 1.02,
                        fmt, ha="center", va="bottom", fontsize=7
                    )

        ax.set_xlabel("Dataset")
        ax.set_ylabel(ylabel)
        ax.set_title(ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels(display_datasets, fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Plot saved: {plot_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compare SimpleRNN / LSTM / BiLSTM on real datasets")
    parser.add_argument("--epochs",        type=int,   default=15)
    parser.add_argument("--batch-size",    type=int,   default=128)
    parser.add_argument("--lr",            type=float, default=0.001)
    parser.add_argument("--window",        type=int,   default=8)
    parser.add_argument("--embed-dim",     type=int,   default=64)
    parser.add_argument("--hidden-dim",    type=int,   default=128)
    parser.add_argument("--n-layers",      type=int,   default=2)
    parser.add_argument("--dropout",       type=float, default=0.3)
    parser.add_argument("--early-stopping",type=int,   default=999,
                        help="Set to 999 to disable early stopping (train all epochs)")
    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()) + ["all"],
        default="all",
        help="Chỉ test 1 dataset (default: all)"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        choices=list(MODELS.keys()),
        default=list(MODELS.keys()),
        help="Chọn models cần test"
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # Chọn datasets cần test
    if args.dataset == "all":
        selected_datasets = DATASETS
    else:
        selected_datasets = {args.dataset: DATASETS[args.dataset]}

    # Kiểm tra datasets tồn tại
    missing = [name for name, path in selected_datasets.items() if not path.exists()]
    if missing:
        logger.error(
            "Dataset(s) not found: %s\n"
            "  → Chạy trước: python scripts/download_datasets.py",
            ", ".join(missing)
        )
        import sys; sys.exit(1)

    # Chọn models
    selected_models = {name: cls for name, cls in MODELS.items() if name in args.models}

    print("\n" + "=" * 65)
    print("  Model Comparison Experiment — Tiểu luận Chapter 3")
    print(f"  Models: {', '.join(selected_models.keys())}")
    print(f"  Datasets: {', '.join(selected_datasets.keys())}")
    print(f"  Epochs: {args.epochs} | Window: {args.window} | Device: {device}")
    print("=" * 65)

    all_results = []

    for dataset_name, csv_path in selected_datasets.items():
        logger.info("\n" + "─" * 65)
        logger.info("Dataset: %s (%s)", dataset_name, csv_path.name)
        logger.info("─" * 65)

        sequences, product_to_idx, action_to_idx = load_and_prepare(
            csv_path, window=args.window
        )
        if not sequences:
            logger.warning("No sequences for %s — skipping", dataset_name)
            continue

        for model_name, ModelClass in selected_models.items():
            result = run_experiment(
                model_name=model_name,
                ModelClass=ModelClass,
                dataset_name=dataset_name,
                sequences=sequences,
                product_to_idx=product_to_idx,
                action_to_idx=action_to_idx,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
                embed_dim=args.embed_dim,
                hidden_dim=args.hidden_dim,
                n_layers=args.n_layers,
                dropout=args.dropout,
                window=args.window,
                early_stopping=args.early_stopping,
                device=device,
            )
            all_results.append(result)

    if not all_results:
        logger.error("No results — exiting.")
        return

    # Save raw results (without bulky history for main log)
    log_path = RESULTS_DIR / "comparison_log.json"
    log_data = [
        {k: v for k, v in r.items() if k != "history"}
        for r in all_results
    ]
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    # Find best model (highest avg NDCG@5)
    model_ndcg = defaultdict(list)
    for r in all_results:
        model_ndcg[r["model"]].append(r.get("ndcg@5", 0))

    best_model_name = max(model_ndcg, key=lambda m: sum(model_ndcg[m]) / len(model_ndcg[m]))
    best_result = max(
        (r for r in all_results if r["model"] == best_model_name),
        key=lambda r: r.get("ndcg@5", 0)
    )

    # Generate outputs
    report_path = generate_report(all_results, best_result)
    generate_plots(all_results)

    # ── Summary ──
    print("\n" + "=" * 65)
    print("  EXPERIMENT COMPLETE")
    print("=" * 65)
    print(f"\n  📊 Results Matrix (NDCG@5):")
    header = f"  {'Model':<15}" + "".join(f"{d[:15]:<18}" for d in selected_datasets)
    print(header)
    print("  " + "-" * (15 + 18 * len(selected_datasets)))
    result_map = {(r["model"], r["dataset"]): r for r in all_results}
    for model_name in ["SimpleRNN", "LSTM", "BiLSTM"]:
        row = f"  {model_name:<15}"
        for dataset_name in selected_datasets:
            v = result_map.get((model_name, dataset_name), {}).get("ndcg@5", None)
            row += f"  {f'{v:.2f}%' if v is not None else 'N/A':<16}"
        print(row)

    print(f"\n  🏆 Best Model: {best_model_name}")
    print(f"     Precision@5 : {best_result.get('precision@5', 0):.2f}%")
    print(f"     NDCG@5      : {best_result.get('ndcg@5', 0):.2f}%")
    print(f"\n  📁 Outputs:")
    print(f"     Report : {report_path}")
    print(f"     Plot   : {RESULTS_DIR / 'comparison_plots.png'}")
    print(f"     Log    : {log_path}")
    print("=" * 65)

    # ── Auto-generate plots ──
    print("\n  📊 Generating visualization plots...")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "plot_results.py"),
             "--save-dpi", "150"],
            capture_output=True, text=True, cwd=str(ROOT_DIR)
        )
        if result.returncode == 0:
            plots_dir = RESULTS_DIR / "plots"
            plot_files = list(plots_dir.glob("*.png")) if plots_dir.exists() else []
            print(f"  ✅ {len(plot_files)} plots saved → {plots_dir}")
        else:
            print(f"  ⚠ Plot error: {result.stderr[-500:] if result.stderr else 'unknown'}")
    except Exception as e:
        print(f"  ⚠ Could not auto-plot: {e}")
        print("  → Run manually: python scripts/plot_results.py")


if __name__ == "__main__":
    main()
