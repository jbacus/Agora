#!/usr/bin/env python3
"""
Initialize the vector database and create collections.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from config.settings import settings
from src.data import get_embedding_provider, get_vector_db


def init_database():
    """Initialize vector database and create necessary collections."""
    logger.info("Initializing vector database...")
    logger.info(f"Database type: {settings.vector_db}")

    try:
        # Initialize vector database
        vector_db = get_vector_db(**settings.get_vector_db_config())
        vector_db.initialize()

        logger.info("✓ Vector database initialized successfully")

        # Initialize embedding provider
        logger.info(f"Initializing embedding provider: {settings.llm_provider}")
        embedding_provider = get_embedding_provider(**settings.get_embedding_config())

        logger.info(f"✓ Embedding provider initialized (dimension={embedding_provider.dimension})")

        logger.info("\n" + "=" * 60)
        logger.info("Database initialization complete!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Place source texts in data/raw/<author>/")
        logger.info("2. Run: python scripts/ingest_author.py --author marx")
        logger.info("3. Create expertise profiles: python scripts/create_expertise_profiles.py")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


if __name__ == "__main__":
    init_database()
