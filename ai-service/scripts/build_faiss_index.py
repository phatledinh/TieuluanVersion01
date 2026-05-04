"""
Build FAISS Index — Chapter 3.6.2

Creates vector database from product descriptions:
    1. Fetch products from product-service API (PDF 4.5.1)
    2. Encode descriptions using SentenceTransformer (PDF 3.6.2: Embedding từ mô tả sản phẩm)
    3. Build FAISS index (PDF 3.6.2: FAISS)
    4. Save index + mapping

Usage:
    python scripts/build_faiss_index.py
    python scripts/build_faiss_index.py --product-url http://localhost:8001
"""

import argparse
import json
import logging
from pathlib import Path

import faiss
import httpx
import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def fetch_products(base_url: str) -> list:
    """Fetch all products from product-service — PDF 4.5.1 (handles DRF pagination)"""
    url = f"{base_url}/api/products/"
    all_products = []
    page = 1
    try:
        while True:
            resp = httpx.get(url, params={"page": page}, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            if isinstance(results, list):
                all_products.extend(results)
            # Check if there's a next page
            next_url = data.get("next") if isinstance(data, dict) else None
            if not next_url:
                break
            page += 1
        logger.info("Fetched %d products from %s", len(all_products), url)
        return all_products
    except Exception as e:
        logger.error("Failed to fetch products: %s", e)
        return all_products


def build_index(products: list, output_dir: Path):
    """Build FAISS index from product descriptions — PDF 3.6.2"""
    if not products:
        logger.error("No products to index.")
        return

    # Load SentenceTransformer (PDF 3.6.2: Embedding từ mô tả sản phẩm)
    logger.info("Loading SentenceTransformer model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Prepare texts: name + description + category
    texts = []
    mapping = {}  # faiss_idx → product info
    for i, p in enumerate(products):
        name = p.get("name", "")
        desc = p.get("description", "")
        cat = p.get("category_name", "")
        text = f"{name}. {desc}. Danh mục: {cat}"
        texts.append(text)
        mapping[i] = {
            "id": p.get("id"),
            "name": name,
            "price": p.get("price", 0),
            "category_name": cat,
        }

    # Encode to vectors
    logger.info("Encoding %d product descriptions...", len(texts))
    vectors = model.encode(texts, show_progress_bar=True)
    vectors = np.array(vectors).astype("float32")
    logger.info("Vectors shape: %s", vectors.shape)

    # Build FAISS index (PDF 3.6.2)
    dimension = vectors.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    logger.info("FAISS index built: %d vectors, dimension=%d", index.ntotal, dimension)

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "product_index.faiss"
    mapping_path = output_dir / "product_mapping.json"

    faiss.write_index(index, str(index_path))
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    logger.info("Saved: %s (%d vectors)", index_path, index.ntotal)
    logger.info("Saved: %s (%d products)", mapping_path, len(mapping))


def main():
    parser = argparse.ArgumentParser(description="Build FAISS Index — PDF 3.6.2")
    parser.add_argument("--product-url", default="http://localhost:8001",
                        help="Product service base URL")
    parser.add_argument("--output-dir", default=str(Path(__file__).parent.parent / "trained_models"))
    args = parser.parse_args()

    products = fetch_products(args.product_url)
    build_index(products, Path(args.output_dir))

    print(f"\n✓ FAISS index built with {len(products)} products!")


if __name__ == "__main__":
    main()
