"""
Download & Prepare Real E-Commerce Datasets — Tiểu luận Chapter 3

Tải 3 bộ dataset THƯƠNG MẠI ĐIỆN TỬ thật và chuẩn hóa về schema chung:
    {user_id, product_id, action, timestamp}

Datasets (tất cả đều là e-commerce):
    1. Retail Rocket  (Kaggle)   — e-commerce event stream, map 1-1 với schema
    2. REES46 Electronics Store (Kaggle) — e-commerce events (view/cart/purchase)
    3. REES46 Cosmetics Store   (Kaggle) — multi-category e-commerce events

Usage:
    python scripts/download_datasets.py
    python scripts/download_datasets.py --dataset retail_rocket
    python scripts/download_datasets.py --dataset rees46_electronics
    python scripts/download_datasets.py --dataset rees46_cosmetics
    python scripts/download_datasets.py --all
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent.parent
DATA_DIR    = ROOT_DIR / "data" / "real"
RAW_DIR     = ROOT_DIR / "data" / "raw"   # Raw downloaded files


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


# ── Kaggle helper ─────────────────────────────────────────────────────────────

def setup_kaggle_credentials():
    """
    Copy kaggle.json từ project root → ~/.kaggle/kaggle.json
    Hệ thống Windows: %USERPROFILE%\.kaggle\kaggle.json
    """
    project_kaggle = ROOT_DIR.parent / "kaggle.json"
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)
    target = kaggle_dir / "kaggle.json"

    if project_kaggle.exists():
        shutil.copy2(project_kaggle, target)
        try:
            target.chmod(0o600)
        except Exception:
            pass
        print(f"  ✓ Kaggle credentials copied → {target}")
    elif target.exists():
        print(f"  ✓ Kaggle credentials already exist at {target}")
    else:
        print(f"  ✗ kaggle.json not found at {project_kaggle}")
        sys.exit(1)


def run_kaggle_download(dataset: str, output_dir: Path):
    """Chạy `kaggle datasets download` và giải nén."""
    print(f"  → Downloading {dataset} from Kaggle...")
    result = subprocess.run(
        [sys.executable, "-m", "kaggle", "datasets", "download",
         "-d", dataset, "-p", str(output_dir), "--unzip"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ✗ Kaggle download failed:\n{result.stderr}")
        print("  → Installing kaggle...")
        subprocess.run([sys.executable, "-m", "pip", "install", "kaggle", "-q"], check=True)
        result = subprocess.run(
            [sys.executable, "-m", "kaggle", "datasets", "download",
             "-d", dataset, "-p", str(output_dir), "--unzip"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ✗ Still failed: {result.stderr}")
            sys.exit(1)
    print(f"  ✓ Downloaded and extracted to {output_dir}")


# ═══════════════════════════════════════════════════════════════════════════
# DATASET 1: Retail Rocket (giữ nguyên)
# ═══════════════════════════════════════════════════════════════════════════

def download_retail_rocket():
    """
    Retail Rocket E-Commerce Dataset (Kaggle)
    URL: https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset
    
    Schema gốc:
        events.csv: timestamp, visitorid, event(view/addtocart/transaction), itemid
    
    Ánh xạ:
        visitorid  → user_id
        itemid     → product_id
        event      → action  (view→view, addtocart→add_to_cart, transaction→purchase)
        timestamp  → timestamp (Unix ms → ISO datetime)
    """
    print("\n" + "=" * 60)
    print("  [1/3] Retail Rocket — E-Commerce Event Stream")
    print("  Source: kaggle.com/datasets/retailrocket/ecommerce-dataset")
    print("=" * 60)

    raw_dir = RAW_DIR / "retail_rocket"
    output_csv = DATA_DIR / "retail_rocket.csv"

    if output_csv.exists():
        print(f"  ✓ Already exists: {output_csv} — skipping download")
        return output_csv

    # Download
    raw_dir.mkdir(parents=True, exist_ok=True)
    run_kaggle_download("retailrocket/ecommerce-dataset", raw_dir)

    # Tìm events.csv
    events_file = None
    for f in raw_dir.rglob("events.csv"):
        events_file = f
        break

    if not events_file:
        print(f"  ✗ events.csv not found in {raw_dir}")
        sys.exit(1)

    print(f"  → Processing {events_file} ...")

    # Action mapping
    action_map = {
        "view":        "view",
        "addtocart":   "add_to_cart",
        "transaction": "purchase",
    }

    # Lọc: chỉ lấy users có ≥ 5 interactions
    user_events = defaultdict(list)

    with open(events_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid  = row.get("visitorid", "").strip()
            pid  = row.get("itemid", "").strip()
            evt  = row.get("event", "").strip().lower()
            ts   = row.get("timestamp", "0").strip()

            if not uid or not pid or evt not in action_map:
                continue

            try:
                ts_sec = int(ts) / 1000.0
                dt = datetime.utcfromtimestamp(ts_sec)
                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                ts_str = "2015-01-01 00:00:00"

            user_events[uid].append({
                "user_id":    uid,
                "product_id": pid,
                "action":     action_map[evt],
                "timestamp":  ts_str,
            })

    # Lọc users có ≥ 5 events
    filtered_rows = []
    for uid, events in user_events.items():
        if len(events) >= 5:
            filtered_rows.extend(events)

    filtered_rows.sort(key=lambda r: r["timestamp"])

    # Giới hạn ~300K records
    MAX_ROWS = 300_000
    if len(filtered_rows) > MAX_ROWS:
        user_counts = defaultdict(int)
        for r in filtered_rows:
            user_counts[r["user_id"]] += 1
        top_users = set(sorted(user_counts, key=user_counts.get, reverse=True)[:50_000])
        filtered_rows = [r for r in filtered_rows if r["user_id"] in top_users]
        filtered_rows = filtered_rows[:MAX_ROWS]

    _save_csv(filtered_rows, output_csv)
    _print_stats("Retail Rocket", filtered_rows)
    return output_csv


# ═══════════════════════════════════════════════════════════════════════════
# DATASET 2: REES46 eCommerce Events — Electronics Store
# ═══════════════════════════════════════════════════════════════════════════

def download_rees46_electronics():
    """
    REES46 eCommerce Events History in Electronics Store (Kaggle)
    URL: https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-electronics-store

    Schema gốc:
        event_time, event_type(view/cart/purchase), product_id, 
        category_id, category_code, brand, price, user_id, user_session

    Ánh xạ:
        user_id    → user_id
        product_id → product_id
        event_type → action  (view→view, cart→add_to_cart, purchase→purchase)
        event_time → timestamp
    """
    print("\n" + "=" * 60)
    print("  [2/3] REES46 Electronics Store — E-Commerce Events")
    print("  Source: kaggle.com/datasets/mkechinov/ecommerce-events-history-in-electronics-store")
    print("=" * 60)

    raw_dir = RAW_DIR / "rees46_electronics"
    output_csv = DATA_DIR / "rees46_electronics.csv"

    if output_csv.exists():
        print(f"  ✓ Already exists: {output_csv} — skipping download")
        return output_csv

    raw_dir.mkdir(parents=True, exist_ok=True)
    run_kaggle_download("mkechinov/ecommerce-events-history-in-electronics-store", raw_dir)

    # Tìm CSV file (thường là 2019-Oct.csv, 2019-Nov.csv, hoặc tương tự)
    csv_files = sorted(raw_dir.rglob("*.csv"))
    if not csv_files:
        print(f"  ✗ No CSV files found in {raw_dir}")
        sys.exit(1)

    print(f"  → Found {len(csv_files)} CSV file(s): {[f.name for f in csv_files]}")

    action_map = {
        "view":              "view",
        "cart":              "add_to_cart",
        "purchase":          "purchase",
        "remove_from_cart":  None,  # Bỏ qua
    }

    user_events = defaultdict(list)
    total_read = 0

    for csv_file in csv_files:
        print(f"  → Processing {csv_file.name} ...")
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_read += 1
                uid = row.get("user_id", "").strip()
                pid = row.get("product_id", "").strip()
                evt = row.get("event_type", "").strip().lower()
                ts  = row.get("event_time", "").strip()

                if not uid or not pid:
                    continue

                action = action_map.get(evt)
                if action is None:
                    continue

                # Parse timestamp (format: 2019-10-01 00:00:00 UTC)
                ts_str = ts.replace(" UTC", "").strip()
                if not ts_str:
                    ts_str = "2019-10-01 00:00:00"

                user_events[uid].append({
                    "user_id":    uid,
                    "product_id": pid,
                    "action":     action,
                    "timestamp":  ts_str,
                })

                # Giới hạn đọc tối đa 5M rows (dataset rất lớn)
                if total_read >= 5_000_000:
                    break
        if total_read >= 5_000_000:
            break

    print(f"  → Total rows read: {total_read:,}")

    # Lọc users có ≥ 9 events (đủ cho window=8 + 1 target)
    filtered_rows = []
    for uid, events in user_events.items():
        if len(events) >= 9:
            filtered_rows.extend(events)

    filtered_rows.sort(key=lambda r: r["timestamp"])

    # Giới hạn ~300K records
    MAX_ROWS = 300_000
    if len(filtered_rows) > MAX_ROWS:
        user_counts = defaultdict(int)
        for r in filtered_rows:
            user_counts[r["user_id"]] += 1
        # Lấy users có nhiều interaction nhất
        sorted_users = sorted(user_counts, key=user_counts.get, reverse=True)
        selected_users = set()
        selected_count = 0
        for u in sorted_users:
            selected_users.add(u)
            selected_count += user_counts[u]
            if selected_count >= MAX_ROWS:
                break
        filtered_rows = [r for r in filtered_rows if r["user_id"] in selected_users]
        filtered_rows = filtered_rows[:MAX_ROWS]

    _save_csv(filtered_rows, output_csv)
    _print_stats("REES46 Electronics", filtered_rows)
    return output_csv


# ═══════════════════════════════════════════════════════════════════════════
# DATASET 3: REES46 eCommerce Behavior — Multi-Category (Cosmetics) Store
# ═══════════════════════════════════════════════════════════════════════════

def download_rees46_cosmetics():
    """
    REES46 eCommerce Behavior Data from Multi-Category Store (Kaggle)
    URL: https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

    Schema gốc: (giống Electronics Store)
        event_time, event_type(view/cart/purchase), product_id,
        category_id, category_code, brand, price, user_id, user_session

    Ánh xạ:
        user_id    → user_id
        product_id → product_id
        event_type → action  (view→view, cart→add_to_cart, purchase→purchase)
        event_time → timestamp
    """
    print("\n" + "=" * 60)
    print("  [3/3] REES46 Multi-Category (Cosmetics) Store — E-Commerce Events")
    print("  Source: kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store")
    print("=" * 60)

    raw_dir = RAW_DIR / "rees46_cosmetics"
    output_csv = DATA_DIR / "rees46_cosmetics.csv"

    if output_csv.exists():
        print(f"  ✓ Already exists: {output_csv} — skipping download")
        return output_csv

    raw_dir.mkdir(parents=True, exist_ok=True)
    run_kaggle_download("mkechinov/ecommerce-behavior-data-from-multi-category-store", raw_dir)

    # Tìm CSV file(s)
    csv_files = sorted(raw_dir.rglob("*.csv"))
    if not csv_files:
        print(f"  ✗ No CSV files found in {raw_dir}")
        sys.exit(1)

    print(f"  → Found {len(csv_files)} CSV file(s): {[f.name for f in csv_files]}")

    action_map = {
        "view":              "view",
        "cart":              "add_to_cart",
        "purchase":          "purchase",
        "remove_from_cart":  None,
    }

    user_events = defaultdict(list)
    total_read = 0

    for csv_file in csv_files:
        print(f"  → Processing {csv_file.name} ...")
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_read += 1
                uid = row.get("user_id", "").strip()
                pid = row.get("product_id", "").strip()
                evt = row.get("event_type", "").strip().lower()
                ts  = row.get("event_time", "").strip()

                if not uid or not pid:
                    continue

                action = action_map.get(evt)
                if action is None:
                    continue

                ts_str = ts.replace(" UTC", "").strip()
                if not ts_str:
                    ts_str = "2019-11-01 00:00:00"

                user_events[uid].append({
                    "user_id":    uid,
                    "product_id": pid,
                    "action":     action,
                    "timestamp":  ts_str,
                })

                # Giới hạn đọc tối đa 5M rows
                if total_read >= 5_000_000:
                    break
        if total_read >= 5_000_000:
            break

    print(f"  → Total rows read: {total_read:,}")

    # Lọc users có ≥ 9 events
    filtered_rows = []
    for uid, events in user_events.items():
        if len(events) >= 9:
            filtered_rows.extend(events)

    filtered_rows.sort(key=lambda r: r["timestamp"])

    # Giới hạn ~300K records
    MAX_ROWS = 300_000
    if len(filtered_rows) > MAX_ROWS:
        user_counts = defaultdict(int)
        for r in filtered_rows:
            user_counts[r["user_id"]] += 1
        sorted_users = sorted(user_counts, key=user_counts.get, reverse=True)
        selected_users = set()
        selected_count = 0
        for u in sorted_users:
            selected_users.add(u)
            selected_count += user_counts[u]
            if selected_count >= MAX_ROWS:
                break
        filtered_rows = [r for r in filtered_rows if r["user_id"] in selected_users]
        filtered_rows = filtered_rows[:MAX_ROWS]

    _save_csv(filtered_rows, output_csv)
    _print_stats("REES46 Cosmetics", filtered_rows)
    return output_csv


# ── Utilities ─────────────────────────────────────────────────────────────────

def _save_csv(rows: list, output_path: Path):
    """Lưu ra CSV chuẩn schema."""
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "product_id", "action", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  ✓ Saved: {output_path} ({size_mb:.1f} MB)")


def _print_stats(name: str, rows: list):
    """In thống kê dataset."""
    from collections import Counter
    users    = len(set(r["user_id"]    for r in rows))
    products = len(set(r["product_id"] for r in rows))
    actions  = Counter(r["action"]     for r in rows)

    print(f"\n  📊 {name} — Thống kê:")
    print(f"     Total records  : {len(rows):,}")
    print(f"     Unique users   : {users:,}")
    print(f"     Unique products: {products:,}")
    print(f"     Actions:")
    for action, count in sorted(actions.items()):
        pct = count / len(rows) * 100
        print(f"       {action:15s}: {count:8,} ({pct:5.1f}%)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download & prepare real e-commerce datasets for training")
    parser.add_argument("--dataset", choices=["retail_rocket", "rees46_electronics", "rees46_cosmetics"],
                        help="Download specific dataset only")
    parser.add_argument("--all", action="store_true", default=True,
                        help="Download all datasets (default)")
    args = parser.parse_args()

    ensure_dirs()
    setup_kaggle_credentials()

    print("\n" + "=" * 60)
    print("  Real E-Commerce Dataset Downloader — Tiểu luận Chapter 3")
    print("  Schema đích: user_id, product_id, action, timestamp")
    print("  Tất cả đều là dataset THƯƠNG MẠI ĐIỆN TỬ thật")
    print("=" * 60)

    if args.dataset == "retail_rocket":
        download_retail_rocket()
    elif args.dataset == "rees46_electronics":
        download_rees46_electronics()
    elif args.dataset == "rees46_cosmetics":
        download_rees46_cosmetics()
    else:
        # Download all
        download_retail_rocket()
        download_rees46_electronics()
        download_rees46_cosmetics()

    print("\n" + "=" * 60)
    print("  ✅ All e-commerce datasets ready!")
    print(f"  📁 Location: {DATA_DIR}")
    print("\n  Bước tiếp theo:")
    print("    python scripts/compare_models.py --epochs 15")
    print("=" * 60)


if __name__ == "__main__":
    main()
