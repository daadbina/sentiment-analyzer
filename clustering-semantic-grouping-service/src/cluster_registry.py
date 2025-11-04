"""PostgreSQL cluster registry with audit trail."""

import logging
from datetime import datetime
from typing import List, Optional, Dict
import asyncpg
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class ClusterRecord(Base):
    """SQLAlchemy model for cluster records."""
    __tablename__ = "semantic_groups"

    group_id = Column(String, primary_key=True)
    article_count = Column(Integer)
    similarity_avg = Column(Float)
    topic_label = Column(String)
    centroid_vector = Column(JSON)
    cluster_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClusterRegistry:
    """PostgreSQL registry for cluster metadata."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "postgres",
        password: str = "password",
        database: str = "sentiment",
        min_pool_size: int = 5,
        max_pool_size: int = 20,
    ):
        """
        Initialize cluster registry.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: Database user
            password: Database password
            database: Database name
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
        """
        self.dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.engine = create_engine(
            self.dsn,
            pool_size=min_pool_size,
            max_overflow=max_pool_size - min_pool_size,
        )
        self.Session = sessionmaker(bind=self.engine)

        # Create tables
        Base.metadata.create_all(self.engine)
        logger.info(f"Initialized ClusterRegistry: {host}:{port}/{database}")

    def register_cluster(self, cluster: Dict) -> bool:
        """
        Register a cluster in the registry.

        Args:
            cluster: Cluster dictionary

        Returns:
            True if successful
        """
        try:
            session = self.Session()
            record = ClusterRecord(
                group_id=cluster.get("group_id"),
                article_count=cluster.get("article_count"),
                similarity_avg=cluster.get("similarity_avg"),
                topic_label=cluster.get("topic_label"),
                centroid_vector=cluster.get("centroid_vector"),
                cluster_metadata=cluster,
            )
            session.add(record)
            session.commit()
            session.close()

            logger.info(f"Registered cluster: {cluster.get('group_id')}")
            return True

        except Exception as e:
            logger.error(f"Error registering cluster: {e}", exc_info=True)
            return False

    def get_cluster(self, group_id: str) -> Optional[Dict]:
        """
        Get cluster from registry.

        Args:
            group_id: Cluster ID

        Returns:
            Cluster dictionary or None
        """
        try:
            session = self.Session()
            record = session.query(ClusterRecord).filter_by(group_id=group_id).first()
            session.close()

            if record:
                return {
                    "group_id": record.group_id,
                    "article_count": record.article_count,
                    "similarity_avg": record.similarity_avg,
                    "topic_label": record.topic_label,
                    "centroid_vector": record.centroid_vector,
                    "cluster_metadata": record.cluster_metadata,
                    "created_at": record.created_at.isoformat(),
                }

            return None

        except Exception as e:
            logger.error(f"Error getting cluster: {e}", exc_info=True)
            return None

    def list_clusters(self, limit: int = 100) -> List[Dict]:
        """
        List clusters from registry.

        Args:
            limit: Maximum number of clusters

        Returns:
            List of cluster dictionaries
        """
        try:
            session = self.Session()
            records = session.query(ClusterRecord).limit(limit).all()
            session.close()

            clusters = []
            for record in records:
                clusters.append({
                    "group_id": record.group_id,
                    "article_count": record.article_count,
                    "similarity_avg": record.similarity_avg,
                    "topic_label": record.topic_label,
                    "created_at": record.created_at.isoformat(),
                })

            return clusters

        except Exception as e:
            logger.error(f"Error listing clusters: {e}", exc_info=True)
            return []

    def delete_cluster(self, group_id: str) -> bool:
        """
        Delete cluster from registry.

        Args:
            group_id: Cluster ID

        Returns:
            True if successful
        """
        try:
            session = self.Session()
            session.query(ClusterRecord).filter_by(group_id=group_id).delete()
            session.commit()
            session.close()

            logger.info(f"Deleted cluster: {group_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting cluster: {e}", exc_info=True)
            return False

