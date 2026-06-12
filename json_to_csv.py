import json
import csv
import os
from collections import defaultdict

def process_file(filepath, output_dir):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return
        
    with open(filepath, 'r', encoding='utf-16') as f:
        data = json.load(f)
        
    # Group by model
    models = defaultdict(list)
    for item in data:
        # e.g. "products.category" -> "category"
        model_name = item['model'].split('.')[-1]
        row = {'id': item['pk']}
        row.update(item['fields'])
        
        # Convert nested structures to string for CSV
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                row[k] = json.dumps(v, ensure_ascii=False)
                
        models[model_name].append(row)
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for model_name, rows in models.items():
        if not rows:
            continue
        
        # Gather all possible keys for headers
        headers = []
        for r in rows:
            for k in r.keys():
                if k not in headers:
                    headers.append(k)
                    
        out_path = os.path.join(output_dir, f"{model_name}.csv")
        # utf-8-sig allows Excel to properly read unicode characters like Vietnamese
        with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Exported {model_name}.csv with {len(rows)} records.")

if __name__ == '__main__':
    base_dir = r'c:\TieuLuan01'
    output_dir = os.path.join(base_dir, 'csv_exports')
    
    product_json = os.path.join(base_dir, 'product_data.json')
    user_json = os.path.join(base_dir, 'user_data.json')
    
    process_file(product_json, output_dir)
    process_file(user_json, output_dir)
    
    print(f"All done! CSVs are located in: {output_dir}")
