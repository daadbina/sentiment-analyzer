"""Graph API endpoints."""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
import logging

from src.api.schemas import (
    NeighborsResponse,
    PathResponse,
    CentralityResponse,
    GraphNode,
    GraphPath,
)
from src.clients import Neo4jClient
from src.queries import CypherBuilder, PathFinder, CentralityCalculator
from src.exceptions import QueryError
from src.utils.logging import get_logger
from src.metrics import metrics_recorder

logger = get_logger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


async def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client dependency."""
    from src.clients import neo4j_client

    return neo4j_client


@router.get("/neighbors/{node_id}", response_model=NeighborsResponse)
async def get_neighbors(
    node_id: str,
    relationship_type: Optional[str] = None,
    depth: int = Query(1, ge=1, le=5),
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
) -> NeighborsResponse:
    """Get neighboring nodes in graph.

    Args:
        node_id: Node ID
        relationship_type: Optional relationship type filter
        depth: Traversal depth
        neo4j_client: Neo4j client

    Returns:
        Neighboring nodes
    """
    try:
        metrics_recorder.record_request(f"GET /graph/neighbors/{node_id}")

        neighbors = await neo4j_client.get_neighbors(
            node_id,
            relationship_type,
            depth,
        )

        neighbor_nodes = [
            GraphNode(
                id=neighbor.get("id"),
                label=neighbor.get("label"),
                properties=neighbor,
            )
            for neighbor in neighbors
        ]

        logger.info(
            "Graph neighbors retrieved",
            extra={
                "extra_fields": {
                    "node_id": node_id,
                    "neighbor_count": len(neighbor_nodes),
                    "depth": depth,
                }
            },
        )

        metrics_recorder.record_success(f"GET /graph/neighbors/{node_id}")

        return NeighborsResponse(
            node_id=node_id,
            neighbors=neighbor_nodes,
            relationship_count=len(neighbor_nodes),
        )

    except QueryError as e:
        logger.error(f"Failed to get neighbors: {str(e)}")
        metrics_recorder.record_error(f"GET /graph/neighbors/{node_id}", str(e))
        raise HTTPException(status_code=500, detail="Failed to get neighbors")


@router.get("/paths/{from_id}/{to_id}", response_model=PathResponse)
async def find_paths(
    from_id: str,
    to_id: str,
    max_length: int = Query(5, ge=1, le=10),
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
) -> PathResponse:
    """Find paths between nodes.

    Args:
        from_id: Source node ID
        to_id: Target node ID
        max_length: Maximum path length
        neo4j_client: Neo4j client

    Returns:
        Paths between nodes
    """
    try:
        metrics_recorder.record_request(f"GET /graph/paths/{from_id}/{to_id}")

        paths = await neo4j_client.find_paths(from_id, to_id, max_length)

        graph_paths = [
            GraphPath(
                nodes=[
                    GraphNode(
                        id=node.get("id"),
                        label=node.get("label"),
                        properties=node,
                    )
                    for node in path.get("nodes", [])
                ],
                relationships=[],
            )
            for path in paths
        ]

        logger.info(
            "Graph paths found",
            extra={
                "extra_fields": {
                    "from_id": from_id,
                    "to_id": to_id,
                    "path_count": len(graph_paths),
                }
            },
        )

        metrics_recorder.record_success(f"GET /graph/paths/{from_id}/{to_id}")

        return PathResponse(
            from_id=from_id,
            to_id=to_id,
            paths=graph_paths,
            path_count=len(graph_paths),
        )

    except QueryError as e:
        logger.error(f"Failed to find paths: {str(e)}")
        metrics_recorder.record_error(f"GET /graph/paths/{from_id}/{to_id}", str(e))
        raise HTTPException(status_code=500, detail="Failed to find paths")


@router.get("/centrality", response_model=CentralityResponse)
async def get_centrality(
    metric_type: str = Query("degree", regex="^(degree|betweenness|closeness)$"),
    node_label: str = Query("Entity"),
    limit: int = Query(10, ge=1, le=100),
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
) -> CentralityResponse:
    """Get centrality metrics for nodes.

    Args:
        metric_type: Type of centrality metric
        node_label: Node label to analyze
        limit: Number of top nodes to return
        neo4j_client: Neo4j client

    Returns:
        Centrality metrics
    """
    try:
        metrics_recorder.record_request("GET /graph/centrality")

        if metric_type == "degree":
            query, params = CentralityCalculator.degree_centrality(node_label)
        elif metric_type == "betweenness":
            query, params = CentralityCalculator.betweenness_centrality(
                node_label,
                limit,
            )
        elif metric_type == "closeness":
            query, params = CentralityCalculator.closeness_centrality(
                node_label,
                limit,
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid metric type")

        results = await neo4j_client.execute(query, params)

        from src.api.schemas import CentralityMetric

        metrics = [
            CentralityMetric(
                node_id=result.get("id") or result.get(list(result.keys())[0]),
                value=float(result.get("degree") or result.get("connections") or 0),
            )
            for result in results
        ]

        logger.info(
            "Centrality metrics retrieved",
            extra={
                "extra_fields": {
                    "metric_type": metric_type,
                    "node_label": node_label,
                    "metric_count": len(metrics),
                }
            },
        )

        metrics_recorder.record_success("GET /graph/centrality")

        return CentralityResponse(
            metric_type=metric_type,
            metrics=metrics,
        )

    except QueryError as e:
        logger.error(f"Failed to get centrality: {str(e)}")
        metrics_recorder.record_error("GET /graph/centrality", str(e))
        raise HTTPException(status_code=500, detail="Failed to get centrality")

