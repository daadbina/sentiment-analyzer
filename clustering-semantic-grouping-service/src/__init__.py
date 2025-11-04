"""
Clustering-Semantic-Grouping-Service

Phase 2 microservice for semantic grouping of multilingual news articles.
Consumes embeddings from Qdrant, performs density-based clustering,
and publishes semantic groups to Kafka and Delta Lake.
"""

__version__ = "0.1.0"
__author__ = "Sentiment Analyzer Team"
__description__ = "Semantic clustering and grouping service for multilingual news"

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info(f"Initializing clustering-semantic-grouping-service v{__version__}")

