"""
Generate Behavior Data — Chapter 3.3

Creates synthetic user behavior dataset with schema (PDF 3.3.1):
    user_id, product_id, action, timestamp

Actions: view, click, add_to_cart, purchase, search (PDF 3.3.1)

Example (PDF 3.3.2):
    user_id, product_id, action, time
    1, 101, view, t1
    1, 102, add_to_cart, t2

Usage:
    python scripts/generate_behavior_data.py
    python scripts/generate_behavior_data.py --users 500 --products 50
"""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


# Actions from PDF 3.3.1 (extended)
ACTIONS = ["view", "click", "add_to_cart", "purchase", "search"]

# Markov transition probabilities for realistic sequences
TRANSITIONS = {
    "view":        {"view": 0.25, "click": 0.30, "search": 0.15, "add_to_cart": 0.20, "purchase": 0.10},
    "click":       {"view": 0.20, "click": 0.15, "search": 0.10, "add_to_cart": 0.35, "purchase": 0.20},
    "search":      {"view": 0.30, "click": 0.25, "search": 0.15, "add_to_cart": 0.20, "purchase": 0.10},
    "add_to_cart":  {"view": 0.10, "click": 0.10, "search": 0.05, "add_to_cart": 0.15, "purchase": 0.60},
    "purchase":    {"view": 0.40, "click": 0.20, "search": 0.25, "add_to_cart": 0.10, "purchase": 0.05},
}

START_PROBS = {"view": 0.35, "click": 0.15, "search": 0.30, "add_to_cart": 0.15, "purchase": 0.05}


def weighted_choice(rng: random.Random, probs: dict) -> str:
    labels = list(probs.keys())
    weights = [probs[k] for k in labels]
    return rng.choices(labels, weights=weights, k=1)[0]


def generate_rows(n_users: int, n_products: int, interactions_per_user: int, seed: int = 42):
    """Generate behavior data rows."""
    rng = random.Random(seed)
    start_time = datetime(2025, 1, 1)
    end_time = datetime(2025, 12, 31, 23, 59, 59)
    total_seconds = int((end_time - start_time).total_seconds())

    rows = []
    for user_id in range(1, n_users + 1):
        offsets = sorted(rng.randint(0, total_seconds) for _ in range(interactions_per_user))
        prev_action = None

        for offset in offsets:
            # Action selection with Markov chain
            if prev_action is None:
                action = weighted_choice(rng, START_PROBS)
            elif rng.random() < 0.1:  # 10% exploration
                action = rng.choice(ACTIONS)
            else:
                action = weighted_choice(rng, TRANSITIONS[prev_action])

            # Product selection: 60% preference-based, 40% random
            if rng.random() < 0.6:
                product_id = ((user_id * 7 + len(rows) * 3) % n_products) + 1
            else:
                product_id = rng.randint(1, n_products)

            event_time = start_time + timedelta(seconds=offset)
            rows.append({
                "user_id": user_id,
                "product_id": product_id,
                "action": action,
                "timestamp": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            prev_action = action

    return rows


def main():
    parser = argparse.ArgumentParser(description="Generate user behavior data — PDF 3.3")
    parser.add_argument("--output", default=str(Path(__file__).parent.parent / "data" / "behavior_data.csv"))
    parser.add_argument("--users", type=int, default=500, help="Number of users")
    parser.add_argument("--products", type=int, default=50, help="Number of products")
    parser.add_argument("--interactions", type=int, default=20, help="Interactions per user")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = generate_rows(args.users, args.products, args.interactions, args.seed)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "product_id", "action", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} behavior records → {output}")
    print(f"  Users: {args.users}, Products: {args.products}")
    print(f"  Actions: {', '.join(ACTIONS)}")


if __name__ == "__main__":
    main()
