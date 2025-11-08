"""
Snapshot manager for graph metadata.
Creates daily snapshots of graph state in PostgreSQL.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from ..postgres.client import postgres_client
from ..analytics.graph_metrics import graph_metrics_calculator
from ..analytics.centrality import centrality_computer
from ..analytics.clustering import clustering_detector
from ..exceptions import SnapshotError

logger = structlog.get_logger(__name__)


class SnapshotManager:
    """
    Manager for creating and managing graph metadata snapshots.
    """

    def __init__(self):
        """Initialize snapshot manager."""
        self.postgres_client = postgres_client

    async def create_snapshot(
        self,
        include_centrality: bool = True,
        include_clustering: bool = True,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Create a snapshot of current graph state.
        
        Args:
            include_centrality: Include centrality statistics
            include_clustering: Include clustering statistics
            trace_id: Trace ID for correlation
            
        Returns:
            Snapshot ID
            
        Raises:
            SnapshotError: If snapshot creation fails
        """
        try:
            logger.info(
                "snapshot_creation_started",
                include_centrality=include_centrality,
                include_clustering=include_clustering,
                trace_id=trace_id,
            )
            
            # Compute graph metrics
            graph_metrics = graph_metrics_calculator.compute_all_metrics(
                node_label=None,
                trace_id=trace_id,
            )
            
            node_counts = graph_metrics.get("node_counts", {})
            relationship_counts = graph_metrics.get("relationship_counts", {})
            
            # Compute centrality stats if requested
            centrality_stats = None
            if include_centrality:
                try:
                    centrality_stats = centrality_computer.compute_all_centralities(
                        trace_id=trace_id,
                    )
                except Exception as e:
                    logger.warning(
                        "centrality_computation_failed_during_snapshot",
                        error=str(e),
                        trace_id=trace_id,
                    )
            
            # Compute clustering stats if requested
            clustering_stats = None
            if include_clustering:
                try:
                    clustering_stats = clustering_detector.detect_communities(
                        trace_id=trace_id,
                    )
                except Exception as e:
                    logger.warning(
                        "clustering_detection_failed_during_snapshot",
                        error=str(e),
                        trace_id=trace_id,
                    )
            
            # Save snapshot to PostgreSQL
            snapshot_id = await self.postgres_client.save_graph_metadata(
                node_counts=node_counts,
                relationship_counts=relationship_counts,
                centrality_stats=centrality_stats,
                clustering_stats=clustering_stats,
                graph_metrics=graph_metrics,
                trace_id=trace_id,
            )
            
            logger.info(
                "snapshot_created",
                snapshot_id=snapshot_id,
                total_nodes=node_counts.get("_total", 0),
                total_relationships=relationship_counts.get("_total", 0),
                trace_id=trace_id,
            )
            
            return snapshot_id
            
        except Exception as e:
            logger.error(
                "snapshot_creation_failed",
                error=str(e),
                trace_id=trace_id,
            )
            raise SnapshotError(
                message=f"Failed to create snapshot: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def get_latest_snapshot(
        self,
        trace_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent snapshot.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Snapshot data or None if no snapshots exist
        """
        try:
            query = """
            SELECT *
            FROM graph_metadata
            ORDER BY snapshot_timestamp DESC
            LIMIT 1
            """
            
            result = await self.postgres_client.execute_query(
                query,
                None,
                trace_id=trace_id,
            )
            
            if not result:
                logger.info("no_snapshots_found", trace_id=trace_id)
                return None
            
            snapshot = result[0]
            
            logger.debug(
                "latest_snapshot_retrieved",
                snapshot_id=snapshot.get("id"),
                snapshot_timestamp=snapshot.get("snapshot_timestamp"),
                trace_id=trace_id,
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(
                "snapshot_retrieval_failed",
                error=str(e),
                trace_id=trace_id,
            )
            return None

    async def get_snapshot_by_id(
        self,
        snapshot_id: int,
        trace_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific snapshot by ID.
        
        Args:
            snapshot_id: Snapshot ID
            trace_id: Trace ID for correlation
            
        Returns:
            Snapshot data or None if not found
        """
        try:
            query = """
            SELECT *
            FROM graph_metadata
            WHERE id = $1
            """
            
            result = await self.postgres_client.execute_query(
                query,
                [snapshot_id],
                trace_id=trace_id,
            )
            
            if not result:
                logger.warning(
                    "snapshot_not_found",
                    snapshot_id=snapshot_id,
                    trace_id=trace_id,
                )
                return None
            
            return result[0]
            
        except Exception as e:
            logger.error(
                "snapshot_retrieval_by_id_failed",
                snapshot_id=snapshot_id,
                error=str(e),
                trace_id=trace_id,
            )
            return None

    async def get_snapshots_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        trace_id: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """
        Get snapshots within a time range.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            trace_id: Trace ID for correlation
            
        Returns:
            List of snapshots
        """
        try:
            query = """
            SELECT *
            FROM graph_metadata
            WHERE snapshot_timestamp >= $1
              AND snapshot_timestamp <= $2
            ORDER BY snapshot_timestamp DESC
            """
            
            result = await self.postgres_client.execute_query(
                query,
                [start_time, end_time],
                trace_id=trace_id,
            )
            
            logger.debug(
                "snapshots_retrieved_in_range",
                start_time=start_time,
                end_time=end_time,
                snapshot_count=len(result),
                trace_id=trace_id,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "snapshot_range_retrieval_failed",
                start_time=start_time,
                end_time=end_time,
                error=str(e),
                trace_id=trace_id,
            )
            return []

    async def delete_old_snapshots(
        self,
        retention_days: int = 30,
        trace_id: Optional[str] = None,
    ) -> int:
        """
        Delete snapshots older than retention period.
        
        Args:
            retention_days: Number of days to retain snapshots
            trace_id: Trace ID for correlation
            
        Returns:
            Number of snapshots deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            query = """
            DELETE FROM graph_metadata
            WHERE snapshot_timestamp < $1
            """
            
            # Execute delete
            result = await self.postgres_client.execute_query(
                query + " RETURNING id",
                [cutoff_date],
                trace_id=trace_id,
            )
            
            deleted_count = len(result)
            
            logger.info(
                "old_snapshots_deleted",
                retention_days=retention_days,
                cutoff_date=cutoff_date,
                deleted_count=deleted_count,
                trace_id=trace_id,
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "snapshot_deletion_failed",
                retention_days=retention_days,
                error=str(e),
                trace_id=trace_id,
            )
            return 0

    async def compare_snapshots(
        self,
        snapshot_id_1: int,
        snapshot_id_2: int,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare two snapshots.
        
        Args:
            snapshot_id_1: First snapshot ID
            snapshot_id_2: Second snapshot ID
            trace_id: Trace ID for correlation
            
        Returns:
            Comparison results
        """
        try:
            snapshot_1 = await self.get_snapshot_by_id(snapshot_id_1, trace_id)
            snapshot_2 = await self.get_snapshot_by_id(snapshot_id_2, trace_id)
            
            if not snapshot_1 or not snapshot_2:
                raise SnapshotError(
                    message="One or both snapshots not found",
                    details={
                        "snapshot_id_1": snapshot_id_1,
                        "snapshot_id_2": snapshot_id_2,
                    },
                )
            
            # Compare node counts
            node_counts_1 = snapshot_1.get("node_counts", {})
            node_counts_2 = snapshot_2.get("node_counts", {})
            
            node_diff = {
                label: node_counts_2.get(label, 0) - node_counts_1.get(label, 0)
                for label in set(list(node_counts_1.keys()) + list(node_counts_2.keys()))
            }
            
            # Compare relationship counts
            rel_counts_1 = snapshot_1.get("relationship_counts", {})
            rel_counts_2 = snapshot_2.get("relationship_counts", {})
            
            rel_diff = {
                rel_type: rel_counts_2.get(rel_type, 0) - rel_counts_1.get(rel_type, 0)
                for rel_type in set(list(rel_counts_1.keys()) + list(rel_counts_2.keys()))
            }
            
            comparison = {
                "snapshot_1": {
                    "id": snapshot_id_1,
                    "timestamp": snapshot_1.get("snapshot_timestamp"),
                },
                "snapshot_2": {
                    "id": snapshot_id_2,
                    "timestamp": snapshot_2.get("snapshot_timestamp"),
                },
                "node_count_diff": node_diff,
                "relationship_count_diff": rel_diff,
            }
            
            logger.info(
                "snapshots_compared",
                snapshot_id_1=snapshot_id_1,
                snapshot_id_2=snapshot_id_2,
                trace_id=trace_id,
            )
            
            return comparison
            
        except Exception as e:
            logger.error(
                "snapshot_comparison_failed",
                snapshot_id_1=snapshot_id_1,
                snapshot_id_2=snapshot_id_2,
                error=str(e),
                trace_id=trace_id,
            )
            raise SnapshotError(
                message=f"Failed to compare snapshots: {str(e)}",
                details={"error": str(e)},
            ) from e


# Global snapshot manager instance
snapshot_manager = SnapshotManager()

