"""
Plugin manager for lifecycle management.

Handles plugin initialization, shutdown, and health checks.
"""

import logging
from typing import Dict, Any, Optional, List
from .base import Plugin, PluginType
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manager for plugin lifecycle.

    Handles initialization, shutdown, and health monitoring of plugins.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        """
        Initialize plugin manager.

        Args:
            registry: Plugin registry.
        """
        self.registry = registry
        self.instances: Dict[str, Plugin] = {}
        self.configs: Dict[str, Dict[str, Any]] = {}

    async def load_plugin(
        self, plugin_name: str, config: Dict[str, Any]
    ) -> Plugin:
        """
        Load and initialize plugin.

        Args:
            plugin_name: Name of plugin to load.
            config: Plugin configuration.

        Returns:
            Initialized plugin instance.

        Raises:
            ValueError: If plugin not found or initialization fails.
        """
        if plugin_name in self.instances:
            logger.warning(f"Plugin {plugin_name} already loaded")
            return self.instances[plugin_name]

        plugin_class = self.registry.get(plugin_name)
        if plugin_class is None:
            raise ValueError(f"Plugin {plugin_name} not found in registry")

        metadata = self.registry.get_metadata(plugin_name)
        if metadata is None:
            raise ValueError(f"Metadata for plugin {plugin_name} not found")

        try:
            instance = plugin_class(metadata)
            await instance.validate_config(config)
            await instance.initialize(config)
            self.instances[plugin_name] = instance
            self.configs[plugin_name] = config
            logger.info(f"Loaded plugin: {plugin_name}")
            return instance
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            raise

    async def unload_plugin(self, plugin_name: str) -> None:
        """
        Unload and shutdown plugin.

        Args:
            plugin_name: Name of plugin to unload.

        Raises:
            ValueError: If plugin not loaded.
        """
        if plugin_name not in self.instances:
            raise ValueError(f"Plugin {plugin_name} not loaded")

        try:
            instance = self.instances[plugin_name]
            await instance.shutdown()
            del self.instances[plugin_name]
            del self.configs[plugin_name]
            logger.info(f"Unloaded plugin: {plugin_name}")
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            raise

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get loaded plugin instance.

        Args:
            plugin_name: Name of plugin.

        Returns:
            Plugin instance or None if not loaded.
        """
        return self.instances.get(plugin_name)

    def list_loaded_plugins(self) -> List[str]:
        """
        List loaded plugins.

        Returns:
            List of loaded plugin names.
        """
        return list(self.instances.keys())

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all loaded plugins.

        Returns:
            Dictionary of plugin name to health status.
        """
        health_status = {}
        for plugin_name, instance in self.instances.items():
            try:
                health_status[plugin_name] = await instance.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {plugin_name}: {e}")
                health_status[plugin_name] = False
        return health_status

    async def shutdown_all(self) -> None:
        """Shutdown all loaded plugins."""
        plugin_names = list(self.instances.keys())
        for plugin_name in plugin_names:
            try:
                await self.unload_plugin(plugin_name)
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin_name}: {e}")

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """
        Get all loaded plugins of a specific type.

        Args:
            plugin_type: Plugin type to filter by.

        Returns:
            List of plugin instances.
        """
        plugins = []
        for plugin_name, instance in self.instances.items():
            metadata = self.registry.get_metadata(plugin_name)
            if metadata and metadata.plugin_type == plugin_type:
                plugins.append(instance)
        return plugins

    def reload_plugin(
        self, plugin_name: str, config: Dict[str, Any]
    ) -> None:
        """
        Reload plugin with new configuration.

        Args:
            plugin_name: Name of plugin to reload.
            config: New plugin configuration.

        Raises:
            ValueError: If plugin not loaded.
        """
        if plugin_name not in self.instances:
            raise ValueError(f"Plugin {plugin_name} not loaded")

        self.configs[plugin_name] = config
        logger.info(f"Reloaded configuration for plugin: {plugin_name}")

