import csv
import random
from collections import defaultdict
from pathlib import Path

def downsample_csv(filepath, output_path, max_users):
    print(f"Processing {filepath.name}...")
    
    # Read all rows
    rows = []
    user_counts = defaultdict(int)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            user_counts[row['user_id']] += 1
            
    print(f"  Total original rows: {len(rows)}")
    print(f"  Total original users: {len(user_counts)}")
    
    # Filter users with at least 10 interactions (to ensure enough sequence data)
    valid_users = [u for u, count in user_counts.items() if count >= 10]
    print(f"  Users with >= 10 interactions: {len(valid_users)}")
    
    # Randomly sample max_users
    random.seed(42)
    if len(valid_users) > max_users:
        selected_users = set(random.sample(valid_users, max_users))
    else:
        selected_users = set(valid_users)
        
    print(f"  Selected users for downsampling: {len(selected_users)}")
    
    # Filter rows
    filtered_rows = [row for row in rows if row['user_id'] in selected_users]
    print(f"  Total new rows: {len(filtered_rows)}")
    
    # Write new CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        if len(filtered_rows) > 0:
            writer = csv.DictWriter(f, fieldnames=filtered_rows[0].keys())
            writer.writeheader()
            writer.writerows(filtered_rows)
            
    print(f"  Saved to {output_path.name}")
    print("-" * 50)

def main():
    data_dir = Path("data/real")
    
    # Configuration: Dataset name -> Max users to keep
    # We reduce the number of users significantly to speed up training.
    configs = {
        "retail_rocket.csv": 3000,      # Orig: 36k users -> Keep 3k
        "movielens_1m.csv": 500,        # Orig: 6k users -> Keep 500
        "amazon_electronics.csv": 5000, # Orig: 86k users -> Keep 5k
    }
    
    for filename, max_users in configs.items():
        filepath = data_dir / filename
        if not filepath.exists():
            print(f"File not found: {filepath}")
            continue
            
        # Downsample and overwrite the original file to keep project clean
        downsample_csv(filepath, filepath, max_users)

if __name__ == "__main__":
    main()
