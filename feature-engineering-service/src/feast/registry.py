"""Feast feature registry management."""

from typing import List, Dict, Any, Optional
from feast import FeatureStore, FeatureView, Entity
from ..utils import StructuredLogger
from ..exceptions import FeastWriteError
from ..config import FeastConfig

logger = StructuredLogger(__name__)


class FeastRegistry:
    """Manage Feast feature registry and feature view registration."""

    def __init__(self, config: FeastConfig):
        """Initialize registry manager.
        
        Args:
            config: Feast configuration
        """
        self.config = config
        self.fs: Optional[FeatureStore] = None

    def connect(self) -> bool:
        """Connect to Feast registry.
        
        Returns:
            True if connection successful
        """
        try:
            self.fs = FeatureStore(repo_path=self.config.repo_path)
            logger.info(
                "Feast registry connected",
                repo_path=self.config.repo_path,
                registry_path=self.config.registry_path,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to connect to Feast registry",
                error=str(e),
                repo_path=self.config.repo_path,
            )
            raise FeastWriteError(f"Failed to connect to Feast registry: {str(e)}")

    def register_feature_view(self, feature_view: FeatureView) -> bool:
        """Register a feature view in Feast.

        Args:
            feature_view: Feature view to register

        Returns:
            True if registration successful
        """
        if not self.fs:
            raise FeastWriteError("Not connected to Feast registry")

        try:
            logger.debug(
                "Registering feature view",
                feature_view_name=feature_view.name,
                num_features=len(feature_view.schema) if hasattr(feature_view, 'schema') else 0,
                entities=str(feature_view.entities),
            )

            # Apply feature view to registry
            logger.debug("Calling fs.apply() with feature view")
            self.fs.apply([feature_view])
            logger.debug("fs.apply() completed successfully")

            logger.info(
                "Feature view registered",
                feature_view_name=feature_view.name,
                num_features=len(feature_view.features),
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to register feature view",
                feature_view_name=feature_view.name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise FeastWriteError(f"Failed to register feature view: {str(e)}")

    def list_feature_views(self) -> List[str]:
        """List all registered feature views.
        
        Returns:
            List of feature view names
        """
        if not self.fs:
            raise FeastWriteError("Not connected to Feast registry")

        try:
            feature_views = self.fs.list_feature_views()
            names = [fv.name for fv in feature_views]
            
            logger.info(
                "Listed feature views",
                count=len(names),
                names=names,
            )
            return names
        except Exception as e:
            logger.error("Failed to list feature views", error=str(e))
            raise FeastWriteError(f"Failed to list feature views: {str(e)}")

    def get_feature_view(self, name: str) -> Optional[FeatureView]:
        """Get feature view by name.
        
        Args:
            name: Feature view name
            
        Returns:
            Feature view or None if not found
        """
        if not self.fs:
            raise FeastWriteError("Not connected to Feast registry")

        try:
            feature_view = self.fs.get_feature_view(name)
            logger.info(
                "Retrieved feature view",
                feature_view_name=name,
                num_features=len(feature_view.features) if feature_view else 0,
            )
            return feature_view
        except Exception as e:
            logger.warning(
                "Feature view not found",
                feature_view_name=name,
                error=str(e),
            )
            return None

    def list_entities(self) -> List[str]:
        """List all registered entities.
        
        Returns:
            List of entity names
        """
        if not self.fs:
            raise FeastWriteError("Not connected to Feast registry")

        try:
            entities = self.fs.list_entities()
            names = [e.name for e in entities]
            
            logger.info(
                "Listed entities",
                count=len(names),
                names=names,
            )
            return names
        except Exception as e:
            logger.error("Failed to list entities", error=str(e))
            raise FeastWriteError(f"Failed to list entities: {str(e)}")

    def get_entity(self, name: str) -> Optional[Entity]:
        """Get entity by name.
        
        Args:
            name: Entity name
            
        Returns:
            Entity or None if not found
        """
        if not self.fs:
            raise FeastWriteError("Not connected to Feast registry")

        try:
            entity = self.fs.get_entity(name)
            logger.info("Retrieved entity", entity_name=name)
            return entity
        except Exception as e:
            logger.warning(
                "Entity not found",
                entity_name=name,
                error=str(e),
            )
            return None

    def close(self):
        """Close registry connection."""
        if self.fs:
            self.fs = None
            logger.info("Feast registry connection closed")

