"""Version management for Qdrant collections."""

import logging
from typing import Dict, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages versions of Qdrant collections."""

    def __init__(self, postgres_client=None):
        """
        Initialize version manager.

        Args:
            postgres_client: PostgreSQL client for persistence
        """
        self.postgres_client = postgres_client
        self.versions = {}

    async def create_version(
        self,
        collection_name: str,
        model_name: str,
        model_version: str,
        metadata: Dict = None,
    ) -> str:
        """
        Create a new collection version.

        Args:
            collection_name: Name of collection
            model_name: Name of embedding model
            model_version: Version of embedding model
            metadata: Optional metadata

        Returns:
            Version ID
        """
        version_id = f"{collection_name}_{model_version}_{datetime.now().timestamp()}"

        version_info = {
            "version_id": version_id,
            "collection_name": collection_name,
            "model_name": model_name,
            "model_version": model_version,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "point_count": 0,
            "status": "active",
        }

        self.versions[version_id] = version_info

        # Persist to database if available
        if self.postgres_client:
            try:
                await self.postgres_client.execute(
                    """
                    INSERT INTO collection_versions 
                    (version_id, collection_name, model_name, model_version, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        version_id,
                        collection_name,
                        model_name,
                        model_version,
                        json.dumps(metadata or {}),
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to persist version: {e}")

        logger.info(f"Created version: {version_id}")

        return version_id

    async def get_version(self, version_id: str) -> Optional[Dict]:
        """
        Get version information.

        Args:
            version_id: Version ID

        Returns:
            Version information dictionary
        """
        return self.versions.get(version_id)

    async def list_versions(
        self,
        collection_name: str = None,
    ) -> List[Dict]:
        """
        List versions.

        Args:
            collection_name: Optional filter by collection name

        Returns:
            List of version information dictionaries
        """
        versions = list(self.versions.values())

        if collection_name:
            versions = [v for v in versions if v["collection_name"] == collection_name]

        return versions

    async def update_version_status(
        self,
        version_id: str,
        status: str,
    ) -> None:
        """
        Update version status.

        Args:
            version_id: Version ID
            status: New status (active, deprecated, archived)
        """
        if version_id not in self.versions:
            raise ValueError(f"Version not found: {version_id}")

        self.versions[version_id]["status"] = status
        self.versions[version_id]["updated_at"] = datetime.now().isoformat()

        logger.info(f"Updated version {version_id} status to {status}")

    async def increment_point_count(
        self,
        version_id: str,
        count: int = 1,
    ) -> None:
        """
        Increment point count for version.

        Args:
            version_id: Version ID
            count: Number of points to add
        """
        if version_id not in self.versions:
            raise ValueError(f"Version not found: {version_id}")

        self.versions[version_id]["point_count"] += count

    async def get_active_version(
        self,
        collection_name: str,
    ) -> Optional[Dict]:
        """
        Get active version for collection.

        Args:
            collection_name: Collection name

        Returns:
            Active version information
        """
        versions = await self.list_versions(collection_name)
        active_versions = [v for v in versions if v["status"] == "active"]

        if not active_versions:
            return None

        # Return most recent active version
        return max(active_versions, key=lambda v: v["created_at"])

    async def deprecate_version(
        self,
        version_id: str,
    ) -> None:
        """
        Deprecate a version.

        Args:
            version_id: Version ID
        """
        await self.update_version_status(version_id, "deprecated")

    async def archive_version(
        self,
        version_id: str,
    ) -> None:
        """
        Archive a version.

        Args:
            version_id: Version ID
        """
        await self.update_version_status(version_id, "archived")

    async def get_version_statistics(
        self,
        version_id: str,
    ) -> Optional[Dict]:
        """
        Get statistics for version.

        Args:
            version_id: Version ID

        Returns:
            Statistics dictionary
        """
        version = await self.get_version(version_id)

        if not version:
            return None

        return {
            "version_id": version_id,
            "collection_name": version["collection_name"],
            "model_name": version["model_name"],
            "model_version": version["model_version"],
            "created_at": version["created_at"],
            "point_count": version["point_count"],
            "status": version["status"],
        }

    async def cleanup_old_versions(
        self,
        collection_name: str,
        keep_count: int = 3,
    ) -> List[str]:
        """
        Clean up old versions, keeping only recent ones.

        Args:
            collection_name: Collection name
            keep_count: Number of versions to keep

        Returns:
            List of archived version IDs
        """
        versions = await self.list_versions(collection_name)

        # Sort by creation date (newest first)
        versions.sort(key=lambda v: v["created_at"], reverse=True)

        archived = []

        # Archive old versions
        for version in versions[keep_count:]:
            await self.archive_version(version["version_id"])
            archived.append(version["version_id"])

        logger.info(
            f"Archived {len(archived)} old versions for {collection_name}, "
            f"keeping {keep_count} recent versions"
        )

        return archived

