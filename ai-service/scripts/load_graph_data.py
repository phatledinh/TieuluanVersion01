"""
Load Graph Data — Chapter 3.5.2

Loads behavior CSV data into Neo4j Knowledge Graph.

Creates (PDF 3.5.1 / 3.5.2):
    Nodes: User, Product
    Edges: BUY, VIEW, SIMILAR

Cypher examples from PDF:
    CREATE (u:User {id:1})
    CREATE (p:Product {id:101})
    CREATE (u)-[:BUY]->(p)

Usage:
    python scripts/load_graph_data.py
    python scripts/load_graph_data.py --csv data/behavior_data.csv
"""

import argparse
import csv
import logging
import os
import sys
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Action → edge type mapping (PDF 3.5.1)
ACTION_TO_EDGE = {
    "purchase": "BUY",
    "view": "VIEW",
    "click": "VIEW",
    "search": "VIEW",
    "add_to_cart": "VIEW",
}


def load_csv(csv_path: str):
    """Load behavior data from CSV."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    logger.info("Loaded %d rows from %s", len(rows), csv_path)
    return rows


def clear_graph(driver):
    """Clear all existing data in Neo4j."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    logger.info("Cleared all Neo4j data.")


def create_nodes_and_edges(driver, rows):
    """Create User and Product nodes with relationship edges."""
    # Batch: create User and Product nodes
    user_ids = set()
    product_ids = set()
    for row in rows:
        user_ids.add(str(row["user_id"]))
        product_ids.add(str(row["product_id"]))

    with driver.session() as session:
        # Create User nodes (PDF 3.5.2: CREATE (u:User {id:1}))
        for uid in user_ids:
            session.run("MERGE (u:User {id: $uid})", {"uid": uid})
        logger.info("Created %d User nodes.", len(user_ids))

        # Create Product nodes (PDF 3.5.2: CREATE (p:Product {id:101}))
        for pid in product_ids:
            session.run("MERGE (p:Product {id: $pid})", {"pid": pid})
        logger.info("Created %d Product nodes.", len(product_ids))

        # Create edges (PDF 3.5.2: CREATE (u)-[:BUY]->(p))
        edge_counts = defaultdict(int)
        for row in rows:
            uid = str(row["user_id"])
            pid = str(row["product_id"])
            action = row.get("action", "view").lower().strip()
            edge_type = ACTION_TO_EDGE.get(action, "VIEW")
            ts = row.get("timestamp", "")

            query = f"""
            MATCH (u:User {{id: $uid}})
            MATCH (p:Product {{id: $pid}})
            MERGE (u)-[r:{edge_type}]->(p)
            ON CREATE SET r.count = 1, r.action = $action,
                          r.first_ts = $ts, r.last_ts = $ts,
                          r.weight = $weight
            ON MATCH SET r.count = r.count + 1,
                         r.last_ts = $ts,
                         r.weight = r.weight + $weight
            """
            weight = 5.0 if edge_type == "BUY" else 1.0
            session.run(query, {"uid": uid, "pid": pid, "action": action, "ts": ts, "weight": weight})
            edge_counts[edge_type] += 1

        for etype, count in edge_counts.items():
            logger.info("Created/updated %d %s edges.", count, etype)


def create_similar_edges(driver):
    """
    Create SIMILAR edges between products — PDF 3.5.1

    Products are SIMILAR if they share buyers (Collaborative Filtering).
    """
    query = """
    MATCH (p1:Product)<-[:BUY]-(u:User)-[:BUY]->(p2:Product)
    WHERE p1.id < p2.id
    WITH p1, p2, COUNT(DISTINCT u) AS shared_buyers
    WHERE shared_buyers >= 2
    MERGE (p1)-[r:SIMILAR]->(p2)
    SET r.weight = shared_buyers
    RETURN COUNT(r) AS similar_count
    """
    with driver.session() as session:
        result = session.run(query).single()
        count = result["similar_count"] if result else 0
        logger.info("Created %d SIMILAR edges.", count)


def main():
    parser = argparse.ArgumentParser(description="Load behavior data into Neo4j — PDF 3.5")
    parser.add_argument("--csv", default=str(Path(__file__).parent.parent / "data" / "behavior_data.csv"))
    parser.add_argument("--neo4j-uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--neo4j-user", default=os.environ.get("NEO4J_USER", "neo4j"))
    parser.add_argument("--neo4j-password", default=os.environ.get("NEO4J_PASSWORD", "password123"))
    parser.add_argument("--clear", action="store_true", help="Clear graph before loading")
    args = parser.parse_args()

    driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_user, args.neo4j_password))

    try:
        driver.verify_connectivity()
        logger.info("Connected to Neo4j at %s", args.neo4j_uri)

        if args.clear:
            clear_graph(driver)

        rows = load_csv(args.csv)
        create_nodes_and_edges(driver, rows)
        create_similar_edges(driver)

        # Summary
        with driver.session() as session:
            stats = session.run("""
            MATCH (u:User) WITH count(u) AS users
            MATCH (p:Product) WITH users, count(p) AS products
            OPTIONAL MATCH ()-[b:BUY]->() WITH users, products, count(b) AS buys
            OPTIONAL MATCH ()-[v:VIEW]->() WITH users, products, buys, count(v) AS views
            OPTIONAL MATCH ()-[s:SIMILAR]->() WITH users, products, buys, views, count(s) AS similars
            RETURN users, products, buys, views, similars
            """).single()
            logger.info("Graph Summary: %d Users, %d Products, %d BUY, %d VIEW, %d SIMILAR",
                        stats["users"], stats["products"], stats["buys"], stats["views"], stats["similars"])
    finally:
        driver.close()


if __name__ == "__main__":
    main()
