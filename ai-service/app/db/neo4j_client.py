"""
Neo4j Client — Chapter 3.5

Singleton driver for Knowledge Graph operations.
Nodes: User, Product
Edges: BUY, VIEW, SIMILAR (PDF 3.5.1)
"""

import logging
from neo4j import GraphDatabase
from app.config import get_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Singleton Neo4j driver wrapper."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "driver"):
            self.driver = None

    def connect(self):
        """Lazy connect to Neo4j."""
        if self.driver is None:
            settings = get_settings()
            try:
                self.driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                )
                self.driver.verify_connectivity()
                logger.info("Connected to Neo4j at %s", settings.NEO4J_URI)
            except Exception as e:
                logger.error("Failed to connect to Neo4j: %s", e)
                self.driver = None

    def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Neo4j connection closed.")

    def execute_read(self, query: str, parameters: dict = None) -> list:
        """Execute a read query and return results as list of dicts."""
        self.connect()
        if self.driver is None:
            return []
        try:
            with self.driver.session() as session:
                result = session.execute_read(
                    lambda tx: tx.run(query, parameters or {}).data()
                )
                return result
        except Exception as e:
            logger.error("Neo4j read query failed: %s", e)
            return []

    def execute_write(self, query: str, parameters: dict = None) -> list:
        """Execute a write query and return results."""
        self.connect()
        if self.driver is None:
            return []
        try:
            with self.driver.session() as session:
                result = session.execute_write(
                    lambda tx: tx.run(query, parameters or {}).data()
                )
                return result
        except Exception as e:
            logger.error("Neo4j write query failed: %s", e)
            return []


# Singleton instance
neo4j_client = Neo4jClient()
