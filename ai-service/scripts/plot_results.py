"""
Plot Training Results — Tiểu luận Chapter 3

Đọc history.json từ tất cả trained models và vẽ đầy đủ các biểu đồ:

    1. Training curves (Loss & Accuracy) — mỗi model trên mỗi dataset
    2. Validation Loss so sánh 3 model cùng dataset
    3. Validation Accuracy so sánh 3 model cùng dataset
    4. Radar chart — tổng hợp đa chiều (Precision, NDCG, Speed, Params)
    5. Bar chart tổng hợp — Precision@5, NDCG@5 theo model × dataset
    6. Heatmap — NDCG@5 matrix (model × dataset)
    7. Model complexity — #Params vs NDCG@5 scatter
    8. Training time comparison

Output:
    experiment_results/plots/
        01_training_curves_<model>_<dataset>.png   — Loss+Acc theo epoch
        02_val_loss_comparison_<dataset>.png        — 3 model trên 1 dataset
        03_val_acc_comparison_<dataset>.png         — tương tự
        04_radar_chart.png                          — đa chiều tổng hợp
        05_bar_precision_ndcg.png                   — grouped bar
        06_heatmap_ndcg.png                         — heatmap matrix
        07_params_vs_ndcg.png                       — scatter complexity
        08_train_time.png                           — thời gian train

Usage:
    python scripts/plot_results.py
    python scripts/plot_results.py --save-dpi 200
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent.parent
MODELS_DIR  = ROOT_DIR / "trained_models"
RESULTS_DIR = ROOT_DIR / "experiment_results"
PLOTS_DIR   = RESULTS_DIR / "plots"

# ── Style ─────────────────────────────────────────────────────────────────────
MODEL_COLORS = {
    "SimpleRNN": "#E74C3C",   # Đỏ
    "LSTM":      "#3498DB",   # Xanh dương
    "BiLSTM":    "#2ECC71",   # Xanh lá
}
MODEL_MARKERS = {
    "SimpleRNN": "o",
    "LSTM":      "s",
    "BiLSTM":    "^",
}
MODEL_LINES = {
    "SimpleRNN": "--",
    "LSTM":      "-.",
    "BiLSTM":    "-",
}
DATASET_LABELS = {
    "retail_rocket":      "Retail Rocket",
    "movielens_1m":       "MovieLens 1M",
    "amazon_electronics": "Amazon Electronics",
}
DATASET_ORDER = ["retail_rocket", "movielens_1m", "amazon_electronics"]
MODEL_ORDER   = ["SimpleRNN", "LSTM", "BiLSTM"]

plt.rcParams.update({
    "font.family":    "DejaVu Sans",
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 100,
})


# ── Data loading ──────────────────────────────────────────────────────────────

def load_all_histories():
    """Đọc history.json từ tất cả trained model directories."""
    histories = {}   # (model_name, dataset_name) → history dict
    metas     = {}   # (model_name, dataset_name) → meta dict

    if not MODELS_DIR.exists():
        print(f"  ✗ trained_models/ not found at {MODELS_DIR}")
        return histories, metas

    for model_dir in sorted(MODELS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        history_file = model_dir / "history.json"
        meta_file    = model_dir / "meta.json"
        if not history_file.exists() or not meta_file.exists():
            continue

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            model_name   = meta.get("model", "Unknown")
            dataset_name = meta.get("dataset", "Unknown")

            # Normalize model name capitalization
            model_norm = {
                "simplernn": "SimpleRNN",
                "lstm":      "LSTM",
                "bilstm":    "BiLSTM",
            }.get(model_name.lower(), model_name)

            key = (model_norm, dataset_name)
            histories[key] = history
            metas[key]     = meta
            print(f"  ✓ Loaded: {model_norm} / {dataset_name} — {len(history.get('train_loss', []))} epochs")

        except Exception as e:
            print(f"  ✗ Error reading {model_dir}: {e}")

    return histories, metas


def load_comparison_log():
    """Đọc comparison_log.json nếu có."""
    log_path = RESULTS_DIR / "comparison_log.json"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ── Plot 1: Training curves (Loss + Accuracy) per model per dataset ───────────

def plot_training_curves(histories: dict, dpi: int = 150):
    """
    Vẽ biểu đồ Loss & Accuracy theo epoch cho từng (model, dataset).
    → File: 01_training_curves_<Model>_<dataset>.png
    """
    print("\n  [1] Training Curves (Loss + Accuracy per epoch)...")
    count = 0

    for (model_name, dataset_name), history in histories.items():
        if model_name not in MODEL_ORDER:
            continue

        epochs     = list(range(1, len(history["train_loss"]) + 1))
        train_loss = history["train_loss"]
        val_loss   = history["val_loss"]
        train_acc  = history["train_acc"]
        val_acc    = history["val_acc"]

        color = MODEL_COLORS.get(model_name, "#999")
        ds_label = DATASET_LABELS.get(dataset_name, dataset_name)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        fig.suptitle(
            f"Training Curves — {model_name} trên {ds_label}",
            fontsize=13, fontweight="bold", y=1.01
        )

        # ── Loss ──
        ax1.plot(epochs, train_loss, color=color, lw=2, marker="o", markersize=3,
                 markevery=max(1, len(epochs)//10), label="Train Loss")
        ax1.plot(epochs, val_loss, color=color, lw=2, ls="--", marker="s", markersize=3,
                 markevery=max(1, len(epochs)//10), alpha=0.8, label="Val Loss")
        ax1.fill_between(epochs, train_loss, val_loss, alpha=0.08, color=color)
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Cross-Entropy Loss")
        ax1.set_title("Loss theo Epoch")
        ax1.legend()
        ax1.grid(True, alpha=0.25, linestyle="--")
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)

        # Annotate best val loss
        best_epoch = int(np.argmin(val_loss)) + 1
        best_val   = min(val_loss)
        ax1.annotate(
            f"Best: {best_val:.4f}\n(epoch {best_epoch})",
            xy=(best_epoch, best_val),
            xytext=(best_epoch + max(1, len(epochs)*0.05), best_val + (max(val_loss)-min(val_loss))*0.1),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1),
            fontsize=8, color="gray"
        )

        # ── Accuracy ──
        ax2.plot(epochs, train_acc, color=color, lw=2, marker="o", markersize=3,
                 markevery=max(1, len(epochs)//10), label="Train Acc")
        ax2.plot(epochs, val_acc, color=color, lw=2, ls="--", marker="s", markersize=3,
                 markevery=max(1, len(epochs)//10), alpha=0.8, label="Val Acc")
        ax2.fill_between(epochs, train_acc, val_acc, alpha=0.08, color=color)
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("Accuracy (%)")
        ax2.set_title("Accuracy theo Epoch")
        ax2.legend()
        ax2.grid(True, alpha=0.25, linestyle="--")
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)

        # Annotate best val acc
        best_acc_epoch = int(np.argmax(val_acc)) + 1
        best_acc_val   = max(val_acc)
        ax2.annotate(
            f"Best: {best_acc_val:.2f}%\n(epoch {best_acc_epoch})",
            xy=(best_acc_epoch, best_acc_val),
            xytext=(best_acc_epoch + max(1, len(epochs)*0.05), best_acc_val - (max(val_acc)-min(val_acc))*0.15),
            arrowprops=dict(arrowstyle="->", color="gray", lw=1),
            fontsize=8, color="gray"
        )

        plt.tight_layout()
        fname = PLOTS_DIR / f"01_training_curves_{model_name}_{dataset_name}.png"
        plt.savefig(fname, dpi=dpi, bbox_inches="tight")
        plt.close()
        count += 1

    print(f"     → {count} curves saved")


# ── Plot 2: Val Loss comparison (3 models on same dataset) ────────────────────

def plot_val_loss_comparison(histories: dict, dpi: int = 150):
    """
    Vẽ Val Loss của 3 model trên cùng 1 dataset.
    → File: 02_val_loss_comparison_<dataset>.png
    """
    print("\n  [2] Val Loss Comparison (3 models per dataset)...")

    datasets = sorted(set(d for _, d in histories.keys()))
    for dataset_name in datasets:
        ds_label = DATASET_LABELS.get(dataset_name, dataset_name)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_title(f"Validation Loss — 3 Model trên {ds_label}", fontsize=12, fontweight="bold")

        for model_name in MODEL_ORDER:
            key = (model_name, dataset_name)
            if key not in histories:
                continue
            history = histories[key]
            epochs   = list(range(1, len(history["val_loss"]) + 1))
            val_loss = history["val_loss"]

            ax.plot(
                epochs, val_loss,
                color=MODEL_COLORS[model_name],
                lw=2.5,
                ls=MODEL_LINES[model_name],
                marker=MODEL_MARKERS[model_name],
                markersize=5,
                markevery=max(1, len(epochs)//8),
                label=f"{model_name} (best={min(val_loss):.4f})",
            )

        ax.set_xlabel("Epoch")
        ax.set_ylabel("Cross-Entropy Loss")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.25, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        plt.tight_layout()
        fname = PLOTS_DIR / f"02_val_loss_comparison_{dataset_name}.png"
        plt.savefig(fname, dpi=dpi, bbox_inches="tight")
        plt.close()
        print(f"     → {fname.name}")


# ── Plot 3: Val Accuracy comparison ───────────────────────────────────────────

def plot_val_acc_comparison(histories: dict, dpi: int = 150):
    """
    Vẽ Val Accuracy của 3 model trên cùng 1 dataset.
    → File: 03_val_acc_comparison_<dataset>.png
    """
    print("\n  [3] Val Accuracy Comparison (3 models per dataset)...")

    datasets = sorted(set(d for _, d in histories.keys()))
    for dataset_name in datasets:
        ds_label = DATASET_LABELS.get(dataset_name, dataset_name)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_title(f"Validation Accuracy — 3 Model trên {ds_label}", fontsize=12, fontweight="bold")

        for model_name in MODEL_ORDER:
            key = (model_name, dataset_name)
            if key not in histories:
                continue
            history = histories[key]
            epochs  = list(range(1, len(history["val_acc"]) + 1))
            val_acc = history["val_acc"]

            ax.plot(
                epochs, val_acc,
                color=MODEL_COLORS[model_name],
                lw=2.5,
                ls=MODEL_LINES[model_name],
                marker=MODEL_MARKERS[model_name],
                markersize=5,
                markevery=max(1, len(epochs)//8),
                label=f"{model_name} (best={max(val_acc):.2f}%)",
            )

        ax.set_xlabel("Epoch")
        ax.set_ylabel("Accuracy (%)")
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.25, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        plt.tight_layout()
        fname = PLOTS_DIR / f"03_val_acc_comparison_{dataset_name}.png"
        plt.savefig(fname, dpi=dpi, bbox_inches="tight")
        plt.close()
        print(f"     → {fname.name}")


# ── Plot 4: Grouped Bar — Precision@5 & NDCG@5 ───────────────────────────────

def plot_bar_metrics(comparison_log: list, dpi: int = 150):
    """
    Grouped bar chart: Precision@5 và NDCG@5 theo model × dataset.
    → File: 05_bar_precision_ndcg.png
    """
    if not comparison_log:
        print("\n  [4] Skipped — comparison_log.json not found")
        return

    print("\n  [4] Bar Chart: Precision@5 & NDCG@5...")

    result_map = {(r["model"], r["dataset"]): r for r in comparison_log}
    datasets   = [d for d in DATASET_ORDER if any(d == r["dataset"] for r in comparison_log)]
    ds_labels  = [DATASET_LABELS.get(d, d) for d in datasets]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("So Sánh SimpleRNN / LSTM / BiLSTM — Precision@5 & NDCG@5",
                 fontsize=13, fontweight="bold")

    x     = np.arange(len(datasets))
    width = 0.25

    for ax, metric_key, title in [
        (ax1, "precision@5", "Precision@5 (%)"),
        (ax2, "ndcg@5",      "NDCG@5 (%)"),
    ]:
        for i, model_name in enumerate(MODEL_ORDER):
            vals = [
                result_map.get((model_name, d), {}).get(metric_key, 0)
                for d in datasets
            ]
            offset = (i - 1) * width
            bars = ax.bar(
                x + offset, vals, width,
                label=model_name,
                color=MODEL_COLORS[model_name],
                alpha=0.88,
                edgecolor="white",
                linewidth=0.8,
            )
            for bar, v in zip(bars, vals):
                if v > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.002,
                        f"{v:.2f}%",
                        ha="center", va="bottom", fontsize=7.5, fontweight="bold",
                        color=MODEL_COLORS[model_name]
                    )

        ax.set_xlabel("Dataset")
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(ds_labels, fontsize=9)
        ax.legend()
        ax.grid(axis="y", alpha=0.25, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(0, max(
            result_map.get((m, d), {}).get(metric_key, 0)
            for m in MODEL_ORDER for d in datasets
        ) * 1.2 or 1)

    plt.tight_layout()
    fname = PLOTS_DIR / "05_bar_precision_ndcg.png"
    plt.savefig(fname, dpi=dpi, bbox_inches="tight")
    plt.close()
    print(f"     → {fname.name}")


# ── Plot 5: Heatmap NDCG@5 ────────────────────────────────────────────────────

def plot_heatmap(comparison_log: list, dpi: int = 150):
    """
    Heatmap: model × dataset → NDCG@5.
    → File: 06_heatmap_ndcg.png
    """
    if not comparison_log:
        return

    print("\n  [5] Heatmap: NDCG@5 matrix...")

    result_map = {(r["model"], r["dataset"]): r for r in comparison_log}
    datasets   = [d for d in DATASET_ORDER if any(d == r["dataset"] for r in comparison_log)]
    ds_labels  = [DATASET_LABELS.get(d, d) for d in datasets]

    matrix = np.zeros((len(MODEL_ORDER), len(datasets)))
    for i, m in enumerate(MODEL_ORDER):
        for j, d in enumerate(datasets):
            matrix[i, j] = result_map.get((m, d), {}).get("ndcg@5", 0)

    fig, ax = plt.subplots(figsize=(9, 5))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0)

    ax.set_xticks(range(len(datasets)))
    ax.set_xticklabels(ds_labels, fontsize=10)
    ax.set_yticks(range(len(MODEL_ORDER)))
    ax.set_yticklabels(MODEL_ORDER, fontsize=11, fontweight="bold")

    # Annotate each cell
    for i in range(len(MODEL_ORDER)):
        for j in range(len(datasets)):
            val = matrix[i, j]
            text_color = "white" if val > matrix.max() * 0.6 else "black"
            ax.text(j, i, f"{val:.2f}%", ha="center", va="center",
                    fontsize=12, fontweight="bold", color=text_color)

    plt.colorbar(im, ax=ax, label="NDCG@5 (%)")
    ax.set_title("NDCG@5 Heatmap — Model × Dataset", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Dataset", fontsize=10)
    ax.set_ylabel("Model", fontsize=10)

    plt.tight_layout()
    fname = PLOTS_DIR / "06_heatmap_ndcg.png"
    plt.savefig(fname, dpi=dpi, bbox_inches="tight")
    plt.close()
    print(f"     → {fname.name}")


# ── Plot 6: #Params vs NDCG@5 Scatter ────────────────────────────────────────

def plot_params_vs_ndcg(comparison_log: list, metas: dict, dpi: int = 150):
    """
    Scatter: Model complexity (#Params) vs NDCG@5.
    → File: 07_params_vs_ndcg.png
    """
    if not comparison_log:
        return

    print("\n  [6] Scatter: #Params vs NDCG@5...")

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_title("#Parameters vs NDCG@5 — Complexity vs Quality Trade-off",
                 fontsize=12, fontweight="bold")

    added_labels = set()
    for r in comparison_log:
        model_name   = r["model"]
        dataset_name = r["dataset"]
        n_params     = r.get("n_params", 0)
        ndcg         = r.get("ndcg@5", 0)

        if model_name not in MODEL_COLORS:
            continue

        color  = MODEL_COLORS[model_name]
        marker = MODEL_MARKERS[model_name]
        label  = model_name if model_name not in added_labels else None
        added_labels.add(model_name)

        ds_label = DATASET_LABELS.get(dataset_name, dataset_name)[:3].upper()

        ax.scatter(
            n_params / 1e6, ndcg,
            c=color, marker=marker, s=120, alpha=0.85,
            edgecolors="white", linewidth=0.8,
            label=label, zorder=3
        )
        ax.annotate(
            ds_label,
            xy=(n_params / 1e6, ndcg),
            xytext=(5, 5), textcoords="offset points",
            fontsize=7.5, color=color, alpha=0.9
        )

    ax.set_xlabel("#Parameters (Millions)", fontsize=10)
    ax.set_ylabel("NDCG@5 (%)", fontsize=10)
    ax.legend(title="Model", fontsize=9)
    ax.grid(True, alpha=0.2, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fname = PLOTS_DIR / "07_params_vs_ndcg.png"
    plt.savefig(fname, dpi=dpi, bbox_inches="tight")
    plt.close()
    print(f"     → {fname.name}")


# ── Plot 7: Training Time Comparison ─────────────────────────────────────────

def plot_train_time(comparison_log: list, dpi: int = 150):
    """
    Horizontal bar chart: training time per model per dataset.
    → File: 08_train_time.png
    """
    if not comparison_log:
        return

    print("\n  [7] Train Time Comparison...")

    result_map = {(r["model"], r["dataset"]): r for r in comparison_log}
    datasets   = [d for d in DATASET_ORDER if any(d == r["dataset"] for r in comparison_log)]
    ds_labels  = [DATASET_LABELS.get(d, d) for d in datasets]

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.set_title("Thời Gian Training (giây) — SimpleRNN / LSTM / BiLSTM",
                 fontsize=12, fontweight="bold")

    x     = np.arange(len(datasets))
    width = 0.25

    for i, model_name in enumerate(MODEL_ORDER):
        vals = [
            result_map.get((model_name, d), {}).get("train_time", 0)
            for d in datasets
        ]
        offset = (i - 1) * width
        bars = ax.bar(
            x + offset, vals, width,
            label=model_name,
            color=MODEL_COLORS[model_name],
            alpha=0.88,
            edgecolor="white",
            linewidth=0.8,
        )
        for bar, v in zip(bars, vals):
            if v > 0:
                label_txt = f"{v:.0f}s" if v < 3600 else f"{v/3600:.1f}h"
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 2,
                    label_txt,
                    ha="center", va="bottom", fontsize=8
                )

    ax.set_xlabel("Dataset")
    ax.set_ylabel("Train Time (giây)")
    ax.set_xticks(x)
    ax.set_xticklabels(ds_labels)
    ax.legend()
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fname = PLOTS_DIR / "08_train_time.png"
    plt.savefig(fname, dpi=dpi, bbox_inches="tight")
    plt.close()
    print(f"     → {fname.name}")


# ── Plot 8: Radar Chart ───────────────────────────────────────────────────────

def plot_radar_chart(comparison_log: list, dpi: int = 150):
    """
    Radar chart tổng hợp các chiều: Precision@5, NDCG@5, Val Acc, Speed.
    → File: 04_radar_chart.png
    """
    if not comparison_log:
        return

    print("\n  [8] Radar Chart (aggregate across datasets)...")

    # Aggregate metrics per model (mean across datasets)
    model_metrics = defaultdict(lambda: defaultdict(list))
    for r in comparison_log:
        m = r["model"]
        if m not in MODEL_ORDER:
            continue
        model_metrics[m]["precision@5"].append(r.get("precision@5", 0))
        model_metrics[m]["ndcg@5"].append(r.get("ndcg@5", 0))
        model_metrics[m]["val_acc"].append(r.get("val_acc", 0))
        # Speed: normalize — higher is better → invert train_time
        model_metrics[m]["train_time"].append(r.get("train_time", 1))

    if not model_metrics:
        return

    # Compute aggregates
    agg = {}
    for m in MODEL_ORDER:
        if m not in model_metrics:
            continue
        d = model_metrics[m]
        avg_p  = np.mean(d["precision@5"])
        avg_n  = np.mean(d["ndcg@5"])
        avg_a  = np.mean(d["val_acc"])
        avg_t  = np.mean(d["train_time"])
        agg[m] = {
            "Precision@5": avg_p,
            "NDCG@5":      avg_n,
            "Val Acc":     avg_a,
            "Speed":       avg_t,   # will be inverted later
        }

    # Normalize each axis to [0, 1]
    axes_names = ["Precision@5", "NDCG@5", "Val Acc", "Speed"]
    raw = {m: [agg[m][k] for k in axes_names] for m in agg}

    # Speed: invert (lower time = faster = better)
    max_time = max(agg[m]["Speed"] for m in agg) or 1
    for m in raw:
        raw[m][3] = max_time / agg[m]["Speed"]   # invert

    # Normalize to 0-1
    for axis_idx in range(len(axes_names)):
        vals = [raw[m][axis_idx] for m in raw]
        max_v = max(vals) or 1
        for m in raw:
            raw[m][axis_idx] /= max_v

    N = len(axes_names)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    axes_display = ["Precision@5", "NDCG@5", "Val Acc (%)", "Speed\n(Fast=Better)"]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_title("Radar Chart — So Sánh Tổng Hợp (Avg across datasets)",
                 fontsize=12, fontweight="bold", pad=25)

    for model_name in MODEL_ORDER:
        if model_name not in raw:
            continue
        values = raw[model_name] + raw[model_name][:1]
        color  = MODEL_COLORS[model_name]
        ax.plot(angles, values, color=color, lw=2.5, ls=MODEL_LINES[model_name], label=model_name)
        ax.fill(angles, values, color=color, alpha=0.1)

        # Dot markers
        ax.scatter(angles[:-1], raw[model_name], color=color, s=60, zorder=5)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(axes_display, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], fontsize=7, color="gray")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=10)

    plt.tight_layout()
    fname = PLOTS_DIR / "04_radar_chart.png"
    plt.savefig(fname, dpi=dpi, bbox_inches="tight")
    plt.close()
    print(f"     → {fname.name}")


# ── Plot 9: Master Summary Figure ─────────────────────────────────────────────

def plot_master_summary(comparison_log: list, histories: dict, dpi: int = 150):
    """
    Tạo một ảnh tổng hợp duy nhất (poster-style) cho tiểu luận.
    → File: 00_master_summary.png
    """
    if not comparison_log or not histories:
        return

    print("\n  [9] Master Summary Figure...")

    result_map = {(r["model"], r["dataset"]): r for r in comparison_log}
    datasets   = [d for d in DATASET_ORDER if any(d == r["dataset"] for r in comparison_log)]
    ds_labels  = [DATASET_LABELS.get(d, d) for d in datasets]

    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor("#F8F9FA")
    gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.45, wspace=0.38)

    title_ax = fig.add_subplot(gs[0, :])
    title_ax.axis("off")
    title_ax.text(
        0.5, 0.6,
        "So Sánh Mô Hình: SimpleRNN vs LSTM vs BiLSTM",
        transform=title_ax.transAxes, ha="center", va="center",
        fontsize=18, fontweight="bold", color="#2C3E50"
    )
    title_ax.text(
        0.5, 0.15,
        "Thực nghiệm trên 3 dataset thật: Retail Rocket | MovieLens 1M | Amazon Electronics   |   Window=8, Hidden=128, Epochs=30",
        transform=title_ax.transAxes, ha="center", va="center",
        fontsize=10, color="#7F8C8D"
    )

    # Row 1: Val Loss curves per dataset (3 datasets)
    for col_idx, dataset_name in enumerate(datasets[:3]):
        ax = fig.add_subplot(gs[1, col_idx])
        ds_label = DATASET_LABELS.get(dataset_name, dataset_name)
        ax.set_title(f"Val Loss — {ds_label}", fontsize=10, fontweight="bold")

        for model_name in MODEL_ORDER:
            key = (model_name, dataset_name)
            if key not in histories:
                continue
            h = histories[key]
            epochs   = list(range(1, len(h["val_loss"]) + 1))
            ax.plot(
                epochs, h["val_loss"],
                color=MODEL_COLORS[model_name],
                lw=2, ls=MODEL_LINES[model_name],
                label=model_name
            )

        ax.set_xlabel("Epoch", fontsize=8)
        ax.set_ylabel("Loss", fontsize=8)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.2, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Row 1 col 3: NDCG@5 bar
    ax_ndcg = fig.add_subplot(gs[1, 3])
    ax_ndcg.set_title("NDCG@5 by Model", fontsize=10, fontweight="bold")
    x = np.arange(len(datasets))
    width = 0.25
    for i, model_name in enumerate(MODEL_ORDER):
        vals = [result_map.get((model_name, d), {}).get("ndcg@5", 0) for d in datasets]
        ax_ndcg.bar(x + (i-1)*width, vals, width,
                    color=MODEL_COLORS[model_name], alpha=0.85,
                    edgecolor="white", label=model_name)
    ax_ndcg.set_xticks(x)
    ax_ndcg.set_xticklabels([l[:8] for l in ds_labels], fontsize=8)
    ax_ndcg.set_ylabel("NDCG@5 (%)", fontsize=8)
    ax_ndcg.legend(fontsize=7)
    ax_ndcg.grid(axis="y", alpha=0.2, linestyle="--")
    ax_ndcg.spines["top"].set_visible(False)
    ax_ndcg.spines["right"].set_visible(False)

    # Row 2: Val Acc curves per dataset
    for col_idx, dataset_name in enumerate(datasets[:3]):
        ax = fig.add_subplot(gs[2, col_idx])
        ds_label = DATASET_LABELS.get(dataset_name, dataset_name)
        ax.set_title(f"Val Acc — {ds_label}", fontsize=10, fontweight="bold")

        for model_name in MODEL_ORDER:
            key = (model_name, dataset_name)
            if key not in histories:
                continue
            h = histories[key]
            epochs  = list(range(1, len(h["val_acc"]) + 1))
            ax.plot(
                epochs, h["val_acc"],
                color=MODEL_COLORS[model_name],
                lw=2, ls=MODEL_LINES[model_name],
                label=model_name
            )

        ax.set_xlabel("Epoch", fontsize=8)
        ax.set_ylabel("Acc (%)", fontsize=8)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.2, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Row 2 col 3: Train Time
    ax_time = fig.add_subplot(gs[2, 3])
    ax_time.set_title("Train Time (s)", fontsize=10, fontweight="bold")
    for i, model_name in enumerate(MODEL_ORDER):
        vals = [result_map.get((model_name, d), {}).get("train_time", 0) for d in datasets]
        ax_time.bar(x + (i-1)*width, vals, width,
                    color=MODEL_COLORS[model_name], alpha=0.85,
                    edgecolor="white", label=model_name)
    ax_time.set_xticks(x)
    ax_time.set_xticklabels([l[:8] for l in ds_labels], fontsize=8)
    ax_time.set_ylabel("Seconds", fontsize=8)
    ax_time.legend(fontsize=7)
    ax_time.grid(axis="y", alpha=0.2, linestyle="--")
    ax_time.spines["top"].set_visible(False)
    ax_time.spines["right"].set_visible(False)

    fname = PLOTS_DIR / "00_master_summary.png"
    plt.savefig(fname, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"     → {fname.name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Plot training results for tiểu luận")
    parser.add_argument("--save-dpi", type=int, default=150, help="DPI for saved images (default: 150)")
    parser.add_argument("--only",
                        choices=["curves", "val_loss", "val_acc", "bar", "heatmap", "scatter", "time", "radar", "summary"],
                        help="Chỉ vẽ một loại biểu đồ")
    args = parser.parse_args()

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Plot Results — Tiểu luận Chapter 3")
    print(f"  Output: {PLOTS_DIR}")
    print("=" * 60)

    # Load data
    print("\n  Loading training histories...")
    histories, metas = load_all_histories()

    comparison_log = load_comparison_log()
    if comparison_log:
        print(f"  ✓ comparison_log.json: {len(comparison_log)} results")
    else:
        print("  ℹ No comparison_log.json found — skipping metric charts")

    if not histories and not comparison_log:
        print("\n  ✗ No trained models found!")
        print("  → Chạy trước: python scripts/compare_models.py --epochs 30")
        sys.exit(1)

    dpi = args.save_dpi
    only = args.only

    # Generate plots
    if not only or only == "curves":
        plot_training_curves(histories, dpi)
    if not only or only == "val_loss":
        plot_val_loss_comparison(histories, dpi)
    if not only or only == "val_acc":
        plot_val_acc_comparison(histories, dpi)
    if not only or only == "bar":
        plot_bar_metrics(comparison_log, dpi)
    if not only or only == "heatmap":
        plot_heatmap(comparison_log, dpi)
    if not only or only == "scatter":
        plot_params_vs_ndcg(comparison_log, metas, dpi)
    if not only or only == "time":
        plot_train_time(comparison_log, dpi)
    if not only or only == "radar":
        plot_radar_chart(comparison_log, dpi)
    if not only or only == "summary":
        plot_master_summary(comparison_log, histories, dpi)

    # Count outputs
    plot_files = list(PLOTS_DIR.glob("*.png"))
    print("\n" + "=" * 60)
    print(f"  ✅ Done! {len(plot_files)} plots saved to:")
    print(f"     {PLOTS_DIR}")
    print("\n  Files:")
    for pf in sorted(plot_files):
        size_kb = pf.stat().st_size / 1024
        print(f"     {pf.name:<55} {size_kb:6.0f} KB")
    print("=" * 60)


if __name__ == "__main__":
    main()
