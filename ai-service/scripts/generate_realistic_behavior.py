"""
Generate Realistic Behavior Datasets — Chapter 3 (Tiểu luận)

Sinh 3 bộ dataset thật hơn synthetic cũ:
    - behavior_small_real.csv   : 200 users  × 50  products  (~4,000  records)
    - behavior_medium_real.csv  : 1,000 users × 100 products (~25,000 records)
    - behavior_large_real.csv   : 5,000 users × 200 products (~150,000 records)

Đặc điểm thực tế (khác với generate_behavior_data.py cũ):
    1. Power-law (Zipf) product popularity  — 20% SP chiếm 80% traffic
    2. User segments: casual / regular / power  — hành vi khác nhau
    3. Conversion funnel thực tế: view → click → cart → purchase
    4. Temporal patterns: buổi tối mua nhiều hơn buổi sáng
    5. Session-based: mỗi session có ngữ cảnh riêng

Usage:
    python scripts/generate_realistic_behavior.py
    python scripts/generate_realistic_behavior.py --output-dir data/
"""

import argparse
import csv
import random
import math
from datetime import datetime, timedelta
from pathlib import Path


# ── Cấu hình dataset ──────────────────────────────────────────────────────────

DATASET_CONFIGS = {
    "small": {
        "n_users": 200,
        "n_products": 50,
        "filename": "behavior_small_real.csv",
        "description": "Small (200 users, 50 products)",
    },
    "medium": {
        "n_users": 1_000,
        "n_products": 100,
        "filename": "behavior_medium_real.csv",
        "description": "Medium (1,000 users, 100 products)",
    },
    "large": {
        "n_users": 5_000,
        "n_products": 200,
        "filename": "behavior_large_real.csv",
        "description": "Large (5,000 users, 200 products)",
    },
}

# Tỉ lệ số session / user theo segment
USER_SEGMENTS = {
    "casual":  {"ratio": 0.6, "sessions_range": (2,  6),  "session_depth": (2, 5)},
    "regular": {"ratio": 0.3, "sessions_range": (6,  15), "session_depth": (3, 8)},
    "power":   {"ratio": 0.1, "sessions_range": (15, 35), "session_depth": (5, 12)},
}

# Conversion funnel thực tế e-commerce
FUNNEL_TRANSITIONS = {
    "view":        {"view": 0.40, "click": 0.30, "search": 0.20, "add_to_cart": 0.08, "purchase": 0.02},
    "click":       {"view": 0.25, "click": 0.20, "search": 0.10, "add_to_cart": 0.30, "purchase": 0.15},
    "search":      {"view": 0.45, "click": 0.25, "search": 0.15, "add_to_cart": 0.10, "purchase": 0.05},
    "add_to_cart": {"view": 0.15, "click": 0.10, "search": 0.05, "add_to_cart": 0.20, "purchase": 0.50},
    "purchase":    {"view": 0.50, "click": 0.15, "search": 0.25, "add_to_cart": 0.08, "purchase": 0.02},
}

ACTIONS = list(FUNNEL_TRANSITIONS.keys())


# ── Utility functions ──────────────────────────────────────────────────────────

def zipf_weights(n: int, alpha: float = 1.2) -> list:
    """
    Tạo trọng số Zipf (power-law) cho n sản phẩm.
    alpha=1.2 → sản phẩm phổ biến nhất được chọn ~300x nhiều hơn sản phẩm ít nhất.
    """
    weights = [1.0 / (i ** alpha) for i in range(1, n + 1)]
    total = sum(weights)
    return [w / total for w in weights]


def weighted_choice(rng: random.Random, options: list, weights: list) -> object:
    """Chọn ngẫu nhiên có trọng số."""
    cumulative = 0.0
    r = rng.random()
    for option, w in zip(options, weights):
        cumulative += w
        if r <= cumulative:
            return option
    return options[-1]


def next_action(rng: random.Random, current_action: str) -> str:
    """Chuyển trạng thái theo funnel probabilities."""
    trans = FUNNEL_TRANSITIONS[current_action]
    return weighted_choice(rng, list(trans.keys()), list(trans.values()))


def hour_weight(hour: int) -> float:
    """
    Temporal pattern: người dùng mua sắm nhiều vào tối 20-22h.
    Giả lập peak hours thực tế Việt Nam.
    """
    # Peak: 20h-22h (weight=3.0), 12h-13h (weight=2.0), thấp nhất: 3h-6h (weight=0.2)
    peaks = {
        range(0, 4):   0.2,
        range(4, 7):   0.3,
        range(7, 9):   1.0,
        range(9, 12):  1.5,
        range(12, 14): 2.0,
        range(14, 17): 1.2,
        range(17, 19): 1.8,
        range(19, 22): 3.0,
        range(22, 24): 1.5,
    }
    for h_range, w in peaks.items():
        if hour in h_range:
            return w
    return 1.0


def assign_user_segment(rng: random.Random) -> str:
    """Phân loại user vào segment theo tỉ lệ."""
    r = rng.random()
    cumulative = 0.0
    for seg, cfg in USER_SEGMENTS.items():
        cumulative += cfg["ratio"]
        if r <= cumulative:
            return seg
    return "casual"


# ── Core generator ─────────────────────────────────────────────────────────────

def generate_realistic_rows(
    n_users: int,
    n_products: int,
    seed: int = 42,
) -> list:
    """
    Sinh behavior data với phân phối thực tế.

    Returns:
        List of dicts: {user_id, product_id, action, timestamp}
    """
    rng = random.Random(seed)
    rows = []

    # Zipf distribution cho product popularity
    product_ids = list(range(1, n_products + 1))
    prod_weights = zipf_weights(n_products, alpha=1.2)

    # Shuffle product order để mỗi dataset có "popular products" khác nhau
    popular_order = list(range(n_products))
    rng.shuffle(popular_order)
    product_ids_ordered = [product_ids[i] for i in popular_order]

    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)
    total_days = (end_date - start_date).days

    # User preferences: mỗi user có danh sách SP yêu thích
    user_preferences = {}
    for uid in range(1, n_users + 1):
        # Mỗi user thích 10-20% sản phẩm
        n_pref = max(3, int(n_products * rng.uniform(0.05, 0.20)))
        pref_indices = rng.sample(range(n_products), n_pref)
        user_preferences[uid] = [product_ids_ordered[i] for i in pref_indices]

    for uid in range(1, n_users + 1):
        segment = assign_user_segment(rng)
        seg_cfg = USER_SEGMENTS[segment]

        n_sessions = rng.randint(*seg_cfg["sessions_range"])
        user_prefs = user_preferences[uid]

        for _ in range(n_sessions):
            # Chọn ngày ngẫu nhiên trong năm
            day_offset = rng.randint(0, total_days)
            base_date = start_date + timedelta(days=day_offset)

            # Chọn giờ theo temporal weight
            hours = list(range(24))
            hour_weights = [hour_weight(h) for h in hours]
            session_hour = weighted_choice(rng, hours, [w / sum(hour_weights) for w in hour_weights])
            session_start = base_date.replace(hour=session_hour, minute=rng.randint(0, 59))

            # Session depth: số hành động trong session
            depth = rng.randint(*seg_cfg["session_depth"])
            current_action = "view"  # Mọi session bắt đầu bằng view

            for step in range(depth):
                ts = session_start + timedelta(seconds=step * rng.randint(15, 300))

                # Chọn sản phẩm: 65% từ preferences, 35% theo Zipf global
                if rng.random() < 0.65 and user_prefs:
                    pid = rng.choice(user_prefs)
                else:
                    pid = weighted_choice(rng, product_ids_ordered, prod_weights)

                rows.append({
                    "user_id": uid,
                    "product_id": pid,
                    "action": current_action,
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                })

                # Chuyển sang action tiếp theo
                if current_action == "purchase":
                    break  # Session thường kết thúc sau purchase
                current_action = next_action(rng, current_action)

    # Sắp xếp theo timestamp
    rows.sort(key=lambda r: r["timestamp"])
    return rows


# ── Main ───────────────────────────────────────────────────────────────────────

def save_csv(rows: list, output_path: Path):
    """Lưu rows ra CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "product_id", "action", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)


def print_stats(rows: list, cfg: dict):
    """In thống kê dataset."""
    from collections import Counter
    action_counts = Counter(r["action"] for r in rows)
    users = len(set(r["user_id"] for r in rows))
    products = len(set(r["product_id"] for r in rows))

    print(f"\n  📊 {cfg['description']}")
    print(f"     Total records : {len(rows):,}")
    print(f"     Unique users  : {users:,}")
    print(f"     Unique products: {products:,}")
    print(f"     Actions breakdown:")
    for action, count in sorted(action_counts.items()):
        pct = count / len(rows) * 100
        print(f"       {action:15s}: {count:7,} ({pct:5.1f}%)")

    # Top 5 sản phẩm phổ biến nhất
    prod_counts = Counter(r["product_id"] for r in rows)
    top5 = prod_counts.most_common(5)
    top5_pct = sum(c for _, c in top5) / len(rows) * 100
    print(f"     Top-5 products: {top5_pct:.1f}% of total traffic (Zipf validation)")


def main():
    parser = argparse.ArgumentParser(description="Generate realistic behavior datasets")
    parser.add_argument("--output-dir", default=str(Path(__file__).parent.parent / "data"),
                        help="Output directory for CSV files")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--size", choices=["small", "medium", "large", "all"],
                        default="all", help="Which dataset(s) to generate")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    sizes = ["small", "medium", "large"] if args.size == "all" else [args.size]

    print("=" * 60)
    print("  Generating Realistic Behavior Datasets")
    print("  Distribution: Zipf power-law (α=1.2)")
    print("  User segments: casual / regular / power")
    print("  Temporal: peak hours 20-22h (Vietnamese pattern)")
    print("=" * 60)

    for size in sizes:
        cfg = DATASET_CONFIGS[size]
        print(f"\n⏳ Generating {cfg['description']}...")

        rows = generate_realistic_rows(
            n_users=cfg["n_users"],
            n_products=cfg["n_products"],
            seed=args.seed,
        )

        output_path = output_dir / cfg["filename"]
        save_csv(rows, output_path)
        print_stats(rows, cfg)
        print(f"  ✓ Saved → {output_path}")

    print("\n" + "=" * 60)
    print("  ✅ All datasets generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
