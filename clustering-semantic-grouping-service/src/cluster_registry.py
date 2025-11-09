"""PostgreSQL cluster registry with audit trail."""

import logging
from datetime import datetime
from typing import List, Optional, Dict
import asyncpg
import numpy as np
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import uuid

logger = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj

Base = declarative_base()


class ClusterRecord(Base):
    """SQLAlchemy model for cluster records matching clustering.clusters schema."""
    __tablename__ = "clusters"
    __table_args__ = {'schema': 'clustering'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(UUID(as_uuid=False), unique=True, nullable=False)  # Store as string UUID
    article_ids = Column(ARRAY(String), nullable=False)
    article_count = Column(Integer, nullable=False)
    similarity_avg = Column(Float, nullable=False)
    topic_label = Column(String(255))
    centroid_vector = Column(ARRAY(Float), nullable=False)
    cluster_metadata = Column('metadata', JSONB)  # Use 'metadata' as column name, cluster_metadata as attribute
    stability_score = Column(Float, default=0.5)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    created_by = Column(String(100), default='clustering-service')


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
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=3600,  # Recycle connections after 1 hour
        )
        self.Session = sessionmaker(bind=self.engine)

        # Note: Tables are created by migrations, not here
        logger.info(f"Initialized ClusterRegistry: {host}:{port}/{database}")

    def register_cluster(self, cluster: Dict) -> bool:
        """
        Register a cluster in the registry.

        Writes to both:
        1. clustering.clusters table (for clustering service internal use)
        2. public.semantic_groups table (for labeler and other services)

        Args:
            cluster: Cluster dictionary with keys:
                - group_id: str
                - article_ids: List[str]
                - article_count: int
                - similarity_avg: float
                - topic_label: str
                - centroid_vector: List[float]
                - stability_score: float (optional, defaults to 0.5)
                - plus other metadata fields

        Returns:
            True if successful
        """
        session = None
        try:
            # Convert numpy types to Python native types
            cluster_converted = convert_numpy_types(cluster)

            # Extract required fields
            group_id = cluster_converted.get("group_id")
            article_ids = cluster_converted.get("article_ids", [])
            article_count = cluster_converted.get("article_count", len(article_ids))
            similarity_avg = float(cluster_converted.get("similarity_avg", 0.0))
            topic_label = cluster_converted.get("topic_label", "")
            centroid_vector = cluster_converted.get("centroid_vector", [])
            stability_score = float(cluster_converted.get("stability_score", 0.5))

            # Validate required fields
            if not group_id:
                logger.error("Missing required field: group_id")
                return False
            if not article_ids:
                logger.error(f"Missing required field: article_ids for cluster {group_id}")
                return False
            if not centroid_vector:
                logger.error(f"Missing required field: centroid_vector for cluster {group_id}")
                return False

            # Prepare metadata (exclude fields that have dedicated columns)
            cluster_meta = {k: v for k, v in cluster_converted.items()
                           if k not in ['group_id', 'article_ids', 'article_count',
                                       'similarity_avg', 'topic_label', 'centroid_vector',
                                       'stability_score', 'created_at', 'updated_at']}

            # Create timestamp
            created_at = datetime.utcnow()

            logger.debug(
                f"Registering cluster {group_id}: "
                f"articles={len(article_ids)}, "
                f"vector_dim={len(centroid_vector)}, "
                f"similarity={similarity_avg:.4f}, "
                f"stability={stability_score:.4f}"
            )

            session = self.Session()

            # 1. Write to clustering.clusters table (internal registry)
            record = ClusterRecord(
                group_id=group_id,
                article_ids=article_ids,
                article_count=article_count,
                similarity_avg=similarity_avg,
                topic_label=topic_label[:255] if topic_label else "",  # Truncate to 255 chars
                centroid_vector=centroid_vector,
                cluster_metadata=cluster_meta,
                stability_score=stability_score,
                created_at=created_at,
                created_by='clustering-service',
            )
            session.add(record)

            # 2. Write to public.semantic_groups table (for labeler and other services)
            # Convert centroid_vector to JSON string format for semantic_groups table
            centroid_json = "[" + ",".join([str(float(v)) for v in centroid_vector]) + "]"

            # Convert cluster_metadata to JSON string
            import json
            metadata_json = json.dumps(cluster_meta)

            # Check if group_id already exists in semantic_groups
            existing = session.execute(
                text("SELECT group_id FROM semantic_groups WHERE group_id = :group_id"),
                {"group_id": group_id}
            ).fetchone()

            if existing:
                # Update existing record
                session.execute(text("""
                    UPDATE semantic_groups
                    SET article_count = :article_count,
                        similarity_avg = :similarity_avg,
                        topic_label = :topic_label,
                        centroid_vector = :centroid_vector,
                        cluster_metadata = :cluster_metadata,
                        updated_at = :updated_at
                    WHERE group_id = :group_id
                """), {
                    "group_id": group_id,
                    "article_count": article_count,
                    "similarity_avg": similarity_avg,
                    "topic_label": topic_label[:255] if topic_label else "",
                    "centroid_vector": centroid_json,
                    "cluster_metadata": metadata_json,
                    "updated_at": datetime.utcnow()
                })
                logger.debug(f"Updated existing semantic group: {group_id}")
            else:
                # Insert new record
                session.execute(text("""
                    INSERT INTO semantic_groups (
                        group_id, article_count, similarity_avg, topic_label,
                        centroid_vector, cluster_metadata, created_at, updated_at
                    ) VALUES (
                        :group_id, :article_count, :similarity_avg, :topic_label,
                        :centroid_vector, :cluster_metadata, :created_at, :updated_at
                    )
                """), {
                    "group_id": group_id,
                    "article_count": article_count,
                    "similarity_avg": similarity_avg,
                    "topic_label": topic_label[:255] if topic_label else "",
                    "centroid_vector": centroid_json,
                    "cluster_metadata": metadata_json,
                    "created_at": created_at,
                    "updated_at": created_at
                })
                logger.debug(f"Inserted new semantic group: {group_id}")

            session.commit()

            logger.info(
                f"Registered cluster: {group_id} "
                f"({article_count} articles, similarity={similarity_avg:.4f})"
            )
            return True

        except Exception as e:
            logger.error(f"Error registering cluster: {e}", exc_info=True)
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()

    def get_cluster(self, group_id: str) -> Optional[Dict]:
        """
        Get cluster from registry.

        Args:
            group_id: Cluster ID

        Returns:
            Cluster dictionary or None
        """
        session = None
        try:
            session = self.Session()
            record = session.query(ClusterRecord).filter_by(group_id=group_id).first()

            if record:
                result = {
                    "group_id": record.group_id,
                    "article_ids": record.article_ids,
                    "article_count": record.article_count,
                    "similarity_avg": record.similarity_avg,
                    "topic_label": record.topic_label,
                    "centroid_vector": record.centroid_vector,
                    "metadata": record.cluster_metadata,
                    "stability_score": record.stability_score,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                    "created_by": record.created_by,
                }
                return result

            return None

        except Exception as e:
            logger.error(f"Error getting cluster: {e}", exc_info=True)
            return None
        finally:
            if session:
                session.close()

    def list_clusters(self, limit: int = 100) -> List[Dict]:
        """
        List clusters from registry.

        Args:
            limit: Maximum number of clusters

        Returns:
            List of cluster dictionaries
        """
        session = None
        try:
            session = self.Session()
            records = session.query(ClusterRecord).order_by(
                ClusterRecord.created_at.desc()
            ).limit(limit).all()

            clusters = []
            for record in records:
                clusters.append({
                    "group_id": record.group_id,
                    "article_count": record.article_count,
                    "similarity_avg": record.similarity_avg,
                    "topic_label": record.topic_label,
                    "stability_score": record.stability_score,
                    "created_at": record.created_at.isoformat(),
                })

            return clusters

        except Exception as e:
            logger.error(f"Error listing clusters: {e}", exc_info=True)
            return []
        finally:
            if session:
                session.close()

    def delete_cluster(self, group_id: str) -> bool:
        """
        Delete cluster from registry.

        Args:
            group_id: Cluster ID

        Returns:
            True if successful
        """
        session = None
        try:
            session = self.Session()
            deleted_count = session.query(ClusterRecord).filter_by(group_id=group_id).delete()
            session.commit()

            if deleted_count > 0:
                logger.info(f"Deleted cluster: {group_id}")
                return True
            else:
                logger.warning(f"Cluster not found for deletion: {group_id}")
                return False

        except Exception as e:
            logger.error(f"Error deleting cluster: {e}", exc_info=True)
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()

