import os
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# ── Cấu hình ──────────────────────────────────────────────────────────

BASE_DIR = Path(r"c:\TieuLuan01")
USER_CSV = BASE_DIR / "csv_exports" / "user.csv"
PRODUCT_CSV = BASE_DIR / "csv_exports" / "product.csv"
OUTPUT_DIR = BASE_DIR / "ai-service" / "data"
OUTPUT_CSV = OUTPUT_DIR / "behavior_500users_50products.csv"

# Các hành vi
ACTIONS = [
    "search", "view_list", "view_detail", "add_to_wishlist",
    "add_to_cart", "remove_from_cart", "checkout_start", "purchase"
]

# Tỉ lệ user
USER_SEGMENTS = {
    "casual":  {"ratio": 0.6, "sessions_range": (5,  15), "session_depth": (3,  8)},
    "regular": {"ratio": 0.3, "sessions_range": (15, 30), "session_depth": (5, 12)},
    "power":   {"ratio": 0.1, "sessions_range": (30, 60), "session_depth": (8, 20)},
}

# Funnel: [Trạng thái hiện tại] -> {Trạng thái kế tiếp: xác suất}
FUNNEL_TRANSITIONS = {
    "search":           {"view_list": 0.60, "view_detail": 0.20, "search": 0.10, "dropout": 0.10},
    "view_list":        {"view_detail": 0.40, "search": 0.30, "view_list": 0.20, "dropout": 0.10},
    "view_detail":      {"add_to_wishlist": 0.10, "add_to_cart": 0.10, "view_list": 0.30, "search": 0.20, "dropout": 0.30},
    "add_to_wishlist":  {"view_detail": 0.40, "view_list": 0.30, "search": 0.20, "dropout": 0.10},
    "add_to_cart":      {"checkout_start": 0.40, "remove_from_cart": 0.10, "view_detail": 0.20, "view_list": 0.20, "dropout": 0.10},
    "remove_from_cart": {"view_list": 0.40, "view_detail": 0.30, "search": 0.20, "dropout": 0.10},
    "checkout_start":   {"purchase": 0.70, "dropout": 0.30},
    "purchase":         {"dropout": 1.00},
}

# ── Hàm tiện ích ──────────────────────────────────────────────────────────

def zipf_weights(n: int, alpha: float = 1.2) -> list:
    weights = [1.0 / (i ** alpha) for i in range(1, n + 1)]
    total = sum(weights)
    return [w / total for w in weights]

def weighted_choice(rng: random.Random, options: list, weights: list):
    cumulative = 0.0
    r = rng.random()
    for option, w in zip(options, weights):
        cumulative += w
        if r <= cumulative:
            return option
    return options[-1]

def next_action(rng: random.Random, current_action: str) -> str:
    trans = FUNNEL_TRANSITIONS.get(current_action, {"dropout": 1.0})
    return weighted_choice(rng, list(trans.keys()), list(trans.values()))

def get_hour_weight(hour: int) -> float:
    # 20-22h là cao điểm
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

# ── Main Generator ────────────────────────────────────────────────────────

def main():
    print("🚀 Bắt đầu đọc dữ liệu khách hàng và sản phẩm...")
    
    # 1. Đọc Users
    user_ids = []
    if USER_CSV.exists():
        with open(USER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Chỉ lấy customer
                if row.get("role") == "customer" or not row.get("role"):
                    user_ids.append(row["id"])
    
    # 2. Đọc Products
    product_ids = []
    if PRODUCT_CSV.exists():
        with open(PRODUCT_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                product_ids.append(row["id"])
                
    if not user_ids or not product_ids:
        print("❌ Lỗi: Không tìm thấy dữ liệu user hoặc product.")
        return

    print(f"✅ Đã tải {len(user_ids)} khách hàng và {len(product_ids)} sản phẩm.")
    
    rng = random.Random(42)
    rows = []
    
    # Sản phẩm phổ biến theo Zipf
    n_products = len(product_ids)
    prod_weights = zipf_weights(n_products, alpha=1.2)
    # Xáo trộn product list để sản phẩm hot phân bố tự nhiên
    popular_order = list(range(n_products))
    rng.shuffle(popular_order)
    product_ids_ordered = [product_ids[i] for i in popular_order]
    
    start_date = datetime(2025, 6, 1)
    end_date = datetime(2025, 12, 31)
    total_days = (end_date - start_date).days
    
    print("⏳ Đang sinh dữ liệu mô phỏng, vui lòng đợi...")
    
    for uid in user_ids:
        # Gán phân khúc
        r = rng.random()
        cumulative = 0.0
        segment = "casual"
        for seg, cfg in USER_SEGMENTS.items():
            cumulative += cfg["ratio"]
            if r <= cumulative:
                segment = seg
                break
                
        seg_cfg = USER_SEGMENTS[segment]
        n_sessions = rng.randint(*seg_cfg["sessions_range"])
        
        # Sở thích: mỗi user thích ~5-15 sản phẩm
        n_pref = max(2, int(n_products * rng.uniform(0.1, 0.3)))
        pref_indices = rng.sample(range(n_products), n_pref)
        user_prefs = [product_ids_ordered[i] for i in pref_indices]
        
        for _ in range(n_sessions):
            # Chọn ngày (Cuối tuần có xác suất cao hơn 20%)
            while True:
                day_offset = rng.randint(0, total_days)
                base_date = start_date + timedelta(days=day_offset)
                if base_date.weekday() >= 5: # T7, CN
                    break
                elif rng.random() < 0.8: # Ngày thường có 80% được giữ lại
                    break
            
            # Chọn giờ
            hours = list(range(24))
            hour_weights = [get_hour_weight(h) for h in hours]
            session_hour = weighted_choice(rng, hours, [w/sum(hour_weights) for w in hour_weights])
            session_start = base_date.replace(hour=session_hour, minute=rng.randint(0, 59))
            
            depth = rng.randint(*seg_cfg["session_depth"])
            
            # Khởi đầu session bằng 1 trong 3 hành động
            current_action = weighted_choice(rng, ["search", "view_list", "view_detail"], [0.4, 0.4, 0.2])
            
            # Session current selected product
            current_pid = rng.choice(user_prefs) if rng.random() < 0.6 else weighted_choice(rng, product_ids_ordered, prod_weights)
            
            for step in range(depth):
                ts = session_start + timedelta(seconds=step * rng.randint(10, 120))
                
                # Lưu log
                rows.append({
                    "user_id": uid,
                    "product_id": current_pid,
                    "action": current_action,
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # Chuyển trạng thái
                current_action = next_action(rng, current_action)
                
                if current_action == "dropout":
                    break
                    
                # Có tỉ lệ 30% khi qua bước mới người dùng sẽ đổi sang xem sản phẩm khác
                if current_action in ["search", "view_list"] and rng.random() < 0.3:
                    current_pid = rng.choice(user_prefs) if rng.random() < 0.6 else weighted_choice(rng, product_ids_ordered, prod_weights)

    # Sắp xếp lại theo thời gian thực (để giống log streaming thật)
    rows.sort(key=lambda r: r["timestamp"])
    
    # Ghi file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "product_id", "action", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"🎉 Hoàn thành! Đã tạo ra {len(rows):,} dòng log hành vi.")
    print(f"📁 Đường dẫn: {OUTPUT_CSV}")
    
    # In phân phối
    print("\n--- PHÂN PHỐI HÀNH VI ---")
    action_counts = Counter(r["action"] for r in rows)
    for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {action:17s}: {count:7,} ({count/len(rows)*100:5.1f}%)")

if __name__ == "__main__":
    main()
