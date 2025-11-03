"""
Plugin system for Crawler Service.

Provides extensible architecture for custom sources, fetchers, and processors.
"""

from .base import (
    Plugin,
    SourcePlugin,
    FetcherPlugin,
    ProcessorPlugin,
    PluginMetadata,
)
from .manager import PluginManager
from .registry import PluginRegistry

__all__ = [
    "Plugin",
    "SourcePlugin",
    "FetcherPlugin",
    "ProcessorPlugin",
    "PluginMetadata",
    "PluginManager",
    "PluginRegistry",
]

