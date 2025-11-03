"""
Plugin registry for managing installed plugins.

Maintains registry of available plugins and their metadata.
"""

import logging
from typing import Dict, List, Optional, Type
from .base import Plugin, PluginType, PluginMetadata

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Registry for managing plugins.

    Stores plugin classes and provides lookup operations.
    """

    def __init__(self) -> None:
        """Initialize plugin registry."""
        self.plugins: Dict[str, Type[Plugin]] = {}
        self.metadata: Dict[str, PluginMetadata] = {}

    def register(
        self, plugin_class: Type[Plugin], metadata: PluginMetadata
    ) -> None:
        """
        Register plugin.

        Args:
            plugin_class: Plugin class to register.
            metadata: Plugin metadata.

        Raises:
            ValueError: If plugin already registered.
        """
        if metadata.name in self.plugins:
            raise ValueError(f"Plugin {metadata.name} already registered")

        self.plugins[metadata.name] = plugin_class
        self.metadata[metadata.name] = metadata
        logger.info(
            f"Registered plugin: {metadata.name} v{metadata.version} "
            f"({metadata.plugin_type})"
        )

    def unregister(self, plugin_name: str) -> None:
        """
        Unregister plugin.

        Args:
            plugin_name: Name of plugin to unregister.

        Raises:
            ValueError: If plugin not found.
        """
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin {plugin_name} not found")

        del self.plugins[plugin_name]
        del self.metadata[plugin_name]
        logger.info(f"Unregistered plugin: {plugin_name}")

    def get(self, plugin_name: str) -> Optional[Type[Plugin]]:
        """
        Get plugin class by name.

        Args:
            plugin_name: Name of plugin.

        Returns:
            Plugin class or None if not found.
        """
        return self.plugins.get(plugin_name)

    def get_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata by name.

        Args:
            plugin_name: Name of plugin.

        Returns:
            Plugin metadata or None if not found.
        """
        return self.metadata.get(plugin_name)

    def list_plugins(
        self, plugin_type: Optional[PluginType] = None
    ) -> List[str]:
        """
        List registered plugins.

        Args:
            plugin_type: Filter by plugin type (optional).

        Returns:
            List of plugin names.
        """
        if plugin_type is None:
            return list(self.plugins.keys())

        return [
            name
            for name, metadata in self.metadata.items()
            if metadata.plugin_type == plugin_type
        ]

    def list_metadata(
        self, plugin_type: Optional[PluginType] = None
    ) -> List[PluginMetadata]:
        """
        List plugin metadata.

        Args:
            plugin_type: Filter by plugin type (optional).

        Returns:
            List of plugin metadata.
        """
        if plugin_type is None:
            return list(self.metadata.values())

        return [
            metadata
            for metadata in self.metadata.values()
            if metadata.plugin_type == plugin_type
        ]

    def get_by_type(self, plugin_type: PluginType) -> Dict[str, Type[Plugin]]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Plugin type to filter by.

        Returns:
            Dictionary of plugin name to class.
        """
        return {
            name: plugin_class
            for name, plugin_class in self.plugins.items()
            if self.metadata[name].plugin_type == plugin_type
        }

    def is_registered(self, plugin_name: str) -> bool:
        """
        Check if plugin is registered.

        Args:
            plugin_name: Name of plugin.

        Returns:
            True if plugin is registered.
        """
        return plugin_name in self.plugins

    def clear(self) -> None:
        """Clear all registered plugins."""
        self.plugins.clear()
        self.metadata.clear()
        logger.info("Cleared all registered plugins")

