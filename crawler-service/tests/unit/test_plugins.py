"""
Tests for plugin system.

Tests plugin registration, loading, and lifecycle management.
"""

import pytest
from src.plugins.base import (
    Plugin,
    PluginMetadata,
    PluginType,
    SourcePlugin,
    FetcherPlugin,
)
from src.plugins.registry import PluginRegistry
from src.plugins.manager import PluginManager
from src.plugins.examples import (
    ProxyRotationFetcher,
    LLMSummarizerProcessor,
    WebSocketSourcePlugin,
)


class TestPluginMetadata:
    """Test plugin metadata."""

    def test_create_metadata(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test plugin",
            author="Test Author",
        )
        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.plugin_type == PluginType.SOURCE

    def test_metadata_requires_name_and_version(self):
        """Test that metadata requires name and version."""
        with pytest.raises(ValueError):
            PluginMetadata(
                name="",
                version="1.0.0",
                plugin_type=PluginType.SOURCE,
                description="Test",
                author="Test",
            )

    def test_metadata_default_dependencies(self):
        """Test metadata default dependencies."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        assert metadata.dependencies == []
        assert metadata.config_schema == {}


class TestPluginRegistry:
    """Test plugin registry."""

    def test_register_plugin(self):
        """Test registering a plugin."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        assert registry.is_registered("test-plugin")

    def test_register_duplicate_plugin(self):
        """Test registering duplicate plugin raises error."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        with pytest.raises(ValueError):
            registry.register(ProxyRotationFetcher, metadata)

    def test_get_plugin(self):
        """Test getting plugin from registry."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        plugin_class = registry.get("test-plugin")
        assert plugin_class == ProxyRotationFetcher

    def test_list_plugins(self):
        """Test listing plugins."""
        registry = PluginRegistry()
        metadata1 = PluginMetadata(
            name="plugin1",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        metadata2 = PluginMetadata(
            name="plugin2",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata1)
        registry.register(WebSocketSourcePlugin, metadata2)
        plugins = registry.list_plugins()
        assert len(plugins) == 2
        assert "plugin1" in plugins
        assert "plugin2" in plugins

    def test_list_plugins_by_type(self):
        """Test listing plugins by type."""
        registry = PluginRegistry()
        metadata1 = PluginMetadata(
            name="plugin1",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        metadata2 = PluginMetadata(
            name="plugin2",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata1)
        registry.register(WebSocketSourcePlugin, metadata2)
        fetchers = registry.list_plugins(PluginType.FETCHER)
        assert len(fetchers) == 1
        assert "plugin1" in fetchers


@pytest.mark.asyncio
class TestPluginManager:
    """Test plugin manager."""

    async def test_load_plugin(self):
        """Test loading a plugin."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        manager = PluginManager(registry)

        config = {"proxies": ["http://proxy1:8080", "http://proxy2:8080"]}
        plugin = await manager.load_plugin("proxy-fetcher", config)
        assert plugin is not None
        assert "proxy-fetcher" in manager.list_loaded_plugins()

    async def test_load_nonexistent_plugin(self):
        """Test loading nonexistent plugin raises error."""
        registry = PluginRegistry()
        manager = PluginManager(registry)
        with pytest.raises(ValueError):
            await manager.load_plugin("nonexistent", {})

    async def test_unload_plugin(self):
        """Test unloading a plugin."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        manager = PluginManager(registry)

        config = {"proxies": ["http://proxy1:8080"]}
        await manager.load_plugin("proxy-fetcher", config)
        await manager.unload_plugin("proxy-fetcher")
        assert "proxy-fetcher" not in manager.list_loaded_plugins()

    async def test_health_check(self):
        """Test plugin health check."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        manager = PluginManager(registry)

        config = {"proxies": ["http://proxy1:8080"]}
        await manager.load_plugin("proxy-fetcher", config)
        health = await manager.health_check()
        assert health["proxy-fetcher"] is True

    async def test_shutdown_all(self):
        """Test shutting down all plugins."""
        registry = PluginRegistry()
        metadata1 = PluginMetadata(
            name="plugin1",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        metadata2 = PluginMetadata(
            name="plugin2",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata1)
        registry.register(WebSocketSourcePlugin, metadata2)
        manager = PluginManager(registry)

        await manager.load_plugin("plugin1", {"proxies": ["http://proxy:8080"]})
        await manager.load_plugin("plugin2", {"websocket_urls": ["ws://localhost"]})
        await manager.shutdown_all()
        assert len(manager.list_loaded_plugins()) == 0


@pytest.mark.asyncio
class TestProxyRotationFetcher:
    """Test proxy rotation fetcher plugin."""

    async def test_initialize(self):
        """Test initializing proxy fetcher."""
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        fetcher = ProxyRotationFetcher(metadata)
        config = {"proxies": ["http://proxy1:8080", "http://proxy2:8080"]}
        await fetcher.initialize(config)
        assert fetcher._initialized is True
        assert len(fetcher.proxies) == 2

    async def test_validate_config(self):
        """Test validating proxy fetcher config."""
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        fetcher = ProxyRotationFetcher(metadata)
        config = {"proxies": ["http://proxy1:8080"]}
        assert await fetcher.validate_config(config) is True

    async def test_validate_config_missing_proxies(self):
        """Test validating config without proxies raises error."""
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        fetcher = ProxyRotationFetcher(metadata)
        with pytest.raises(ValueError):
            await fetcher.validate_config({})

    async def test_supports_url(self):
        """Test URL support check."""
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        fetcher = ProxyRotationFetcher(metadata)
        assert await fetcher.supports_url("http://example.com") is True
        assert await fetcher.supports_url("https://example.com") is True
        assert await fetcher.supports_url("ftp://example.com") is False


@pytest.mark.asyncio
class TestWebSocketSourcePlugin:
    """Test WebSocket source plugin."""

    async def test_initialize(self):
        """Test initializing WebSocket source."""
        metadata = PluginMetadata(
            name="ws-source",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        source = WebSocketSourcePlugin(metadata)
        config = {"websocket_urls": ["ws://localhost:8000"]}
        await source.initialize(config)
        assert source._initialized is True

    async def test_get_feeds(self):
        """Test getting feeds from WebSocket source."""
        metadata = PluginMetadata(
            name="ws-source",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        source = WebSocketSourcePlugin(metadata)
        config = {"websocket_urls": ["ws://localhost:8000"]}
        await source.initialize(config)
        feeds = await source.get_feeds()
        assert len(feeds) == 1
        assert feeds[0]["feed_type"] == "websocket"

    async def test_validate_feed(self):
        """Test validating WebSocket feed."""
        metadata = PluginMetadata(
            name="ws-source",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        source = WebSocketSourcePlugin(metadata)
        feed = {"feed_type": "websocket"}
        assert await source.validate_feed(feed) is True

    async def test_validate_feed_invalid(self):
        """Test validating invalid feed."""
        metadata = PluginMetadata(
            name="ws-source",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        source = WebSocketSourcePlugin(metadata)
        feed = {"feed_type": "rss"}
        assert await source.validate_feed(feed) is False

    async def test_shutdown(self):
        """Test shutting down WebSocket source."""
        metadata = PluginMetadata(
            name="ws-source",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        source = WebSocketSourcePlugin(metadata)
        config = {"websocket_urls": ["ws://localhost:8000"]}
        await source.initialize(config)
        await source.shutdown()
        assert source._initialized is False


@pytest.mark.asyncio
class TestLLMSummarizerProcessor:
    """Test LLM summarizer processor plugin."""

    async def test_initialize(self):
        """Test initializing LLM summarizer."""
        metadata = PluginMetadata(
            name="llm-summarizer",
            version="1.0.0",
            plugin_type=PluginType.PROCESSOR,
            description="Test",
            author="Test",
        )
        from src.plugins.examples import LLMSummarizerProcessor

        processor = LLMSummarizerProcessor(metadata)
        config = {"llm_endpoint": "http://localhost:8000"}
        await processor.initialize(config)
        assert processor._initialized is True

    async def test_process_article(self):
        """Test processing article with LLM."""
        metadata = PluginMetadata(
            name="llm-summarizer",
            version="1.0.0",
            plugin_type=PluginType.PROCESSOR,
            description="Test",
            author="Test",
        )
        from src.plugins.examples import LLMSummarizerProcessor

        processor = LLMSummarizerProcessor(metadata)
        config = {"llm_endpoint": "http://localhost:8000", "model": "gpt-4"}
        await processor.initialize(config)
        article = {"title": "Test Article", "content": "Test content"}
        result = await processor.process(article)
        assert "ai_summary" in result
        assert result["ai_summary_model"] == "gpt-4"

    async def test_can_process(self):
        """Test checking if article can be processed."""
        metadata = PluginMetadata(
            name="llm-summarizer",
            version="1.0.0",
            plugin_type=PluginType.PROCESSOR,
            description="Test",
            author="Test",
        )
        from src.plugins.examples import LLMSummarizerProcessor

        processor = LLMSummarizerProcessor(metadata)
        config = {"llm_endpoint": "http://localhost:8000"}
        await processor.initialize(config)
        article_with_content = {"content": "Test"}
        article_without_content = {}
        assert await processor.can_process(article_with_content) is True
        assert await processor.can_process(article_without_content) is False

    async def test_validate_config(self):
        """Test validating LLM config."""
        metadata = PluginMetadata(
            name="llm-summarizer",
            version="1.0.0",
            plugin_type=PluginType.PROCESSOR,
            description="Test",
            author="Test",
        )
        from src.plugins.examples import LLMSummarizerProcessor

        processor = LLMSummarizerProcessor(metadata)
        config = {"llm_endpoint": "http://localhost:8000"}
        assert await processor.validate_config(config) is True

    async def test_validate_config_missing_endpoint(self):
        """Test validating config without endpoint."""
        metadata = PluginMetadata(
            name="llm-summarizer",
            version="1.0.0",
            plugin_type=PluginType.PROCESSOR,
            description="Test",
            author="Test",
        )
        from src.plugins.examples import LLMSummarizerProcessor

        processor = LLMSummarizerProcessor(metadata)
        with pytest.raises(ValueError):
            await processor.validate_config({})


class TestPluginRegistryAdvanced:
    """Advanced tests for plugin registry."""

    def test_unregister_plugin(self):
        """Test unregistering a plugin."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        registry.unregister("test-plugin")
        assert not registry.is_registered("test-plugin")

    def test_unregister_nonexistent_plugin(self):
        """Test unregistering nonexistent plugin raises error."""
        registry = PluginRegistry()
        with pytest.raises(ValueError):
            registry.unregister("nonexistent")

    def test_get_by_type(self):
        """Test getting plugins by type."""
        registry = PluginRegistry()
        metadata1 = PluginMetadata(
            name="fetcher1",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        metadata2 = PluginMetadata(
            name="fetcher2",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata1)
        registry.register(ProxyRotationFetcher, metadata2)
        fetchers = registry.get_by_type(PluginType.FETCHER)
        assert len(fetchers) == 2

    def test_clear_registry(self):
        """Test clearing registry."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        registry.clear()
        assert len(registry.list_plugins()) == 0

    def test_get_nonexistent_plugin(self):
        """Test getting nonexistent plugin returns None."""
        registry = PluginRegistry()
        assert registry.get("nonexistent") is None

    def test_get_nonexistent_metadata(self):
        """Test getting nonexistent metadata returns None."""
        registry = PluginRegistry()
        assert registry.get_metadata("nonexistent") is None

    def test_list_metadata(self):
        """Test listing metadata."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        metadata_list = registry.list_metadata()
        assert len(metadata_list) == 1
        assert metadata_list[0].name == "test-plugin"

    def test_list_metadata_by_type(self):
        """Test listing metadata by type."""
        registry = PluginRegistry()
        metadata1 = PluginMetadata(
            name="fetcher1",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        metadata2 = PluginMetadata(
            name="source1",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata1)
        registry.register(WebSocketSourcePlugin, metadata2)
        fetcher_metadata = registry.list_metadata(PluginType.FETCHER)
        assert len(fetcher_metadata) == 1
        assert fetcher_metadata[0].plugin_type == PluginType.FETCHER


@pytest.mark.asyncio
class TestPluginManagerAdvanced:
    """Advanced tests for plugin manager."""

    async def test_load_already_loaded_plugin(self):
        """Test loading already loaded plugin returns existing instance."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        manager = PluginManager(registry)

        config = {"proxies": ["http://proxy1:8080"]}
        plugin1 = await manager.load_plugin("proxy-fetcher", config)
        plugin2 = await manager.load_plugin("proxy-fetcher", config)
        assert plugin1 is plugin2

    async def test_unload_nonexistent_plugin(self):
        """Test unloading nonexistent plugin raises error."""
        registry = PluginRegistry()
        manager = PluginManager(registry)
        with pytest.raises(ValueError):
            await manager.unload_plugin("nonexistent")

    async def test_get_nonexistent_plugin(self):
        """Test getting nonexistent plugin returns None."""
        registry = PluginRegistry()
        manager = PluginManager(registry)
        assert manager.get_plugin("nonexistent") is None

    async def test_get_plugins_by_type(self):
        """Test getting plugins by type."""
        registry = PluginRegistry()
        metadata1 = PluginMetadata(
            name="fetcher1",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        metadata2 = PluginMetadata(
            name="source1",
            version="1.0.0",
            plugin_type=PluginType.SOURCE,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata1)
        registry.register(WebSocketSourcePlugin, metadata2)
        manager = PluginManager(registry)

        await manager.load_plugin("fetcher1", {"proxies": ["http://proxy:8080"]})
        await manager.load_plugin("source1", {"websocket_urls": ["ws://localhost"]})

        fetchers = manager.get_plugins_by_type(PluginType.FETCHER)
        assert len(fetchers) == 1
        assert isinstance(fetchers[0], ProxyRotationFetcher)

    async def test_reload_plugin(self):
        """Test reloading plugin with new config."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        manager = PluginManager(registry)

        config1 = {"proxies": ["http://proxy1:8080"]}
        await manager.load_plugin("proxy-fetcher", config1)
        config2 = {"proxies": ["http://proxy2:8080", "http://proxy3:8080"]}
        manager.reload_plugin("proxy-fetcher", config2)
        assert manager.configs["proxy-fetcher"] == config2

    async def test_reload_nonexistent_plugin(self):
        """Test reloading nonexistent plugin raises error."""
        registry = PluginRegistry()
        manager = PluginManager(registry)
        with pytest.raises(ValueError):
            manager.reload_plugin("nonexistent", {})

    async def test_load_plugin_with_invalid_config(self):
        """Test loading plugin with invalid config raises error."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        manager = PluginManager(registry)

        with pytest.raises(ValueError):
            await manager.load_plugin("proxy-fetcher", {})

    async def test_health_check_with_error(self):
        """Test health check handles plugin errors gracefully."""
        registry = PluginRegistry()
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        registry.register(ProxyRotationFetcher, metadata)
        manager = PluginManager(registry)

        config = {"proxies": ["http://proxy1:8080"]}
        await manager.load_plugin("proxy-fetcher", config)
        health = await manager.health_check()
        assert isinstance(health, dict)
        assert "proxy-fetcher" in health


@pytest.mark.asyncio
class TestProxyRotationFetcherAdvanced:
    """Advanced tests for proxy rotation fetcher."""

    async def test_fetch_without_proxies(self):
        """Test fetching without proxies raises error."""
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        fetcher = ProxyRotationFetcher(metadata)
        with pytest.raises(ValueError):
            await fetcher.fetch("http://example.com")

    async def test_proxy_rotation(self):
        """Test proxy rotation cycles through proxies."""
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        fetcher = ProxyRotationFetcher(metadata)
        config = {"proxies": ["http://proxy1:8080", "http://proxy2:8080"]}
        await fetcher.initialize(config)
        assert fetcher.current_proxy_index == 0
        # Simulate proxy selection
        proxy1 = fetcher.proxies[fetcher.current_proxy_index]
        fetcher.current_proxy_index = (fetcher.current_proxy_index + 1) % len(
            fetcher.proxies
        )
        proxy2 = fetcher.proxies[fetcher.current_proxy_index]
        assert proxy1 != proxy2

    async def test_shutdown(self):
        """Test shutting down proxy fetcher."""
        metadata = PluginMetadata(
            name="proxy-fetcher",
            version="1.0.0",
            plugin_type=PluginType.FETCHER,
            description="Test",
            author="Test",
        )
        fetcher = ProxyRotationFetcher(metadata)
        config = {"proxies": ["http://proxy1:8080"]}
        await fetcher.initialize(config)
        await fetcher.shutdown()
        assert fetcher._initialized is False


@pytest.mark.asyncio
class TestLLMSummarizerProcessorAdvanced:
    """Advanced tests for LLM summarizer processor."""

    async def test_process_without_endpoint(self):
        """Test processing without LLM endpoint."""
        metadata = PluginMetadata(
            name="llm-summarizer",
            version="1.0.0",
            plugin_type=PluginType.PROCESSOR,
            description="Test",
            author="Test",
        )
        from src.plugins.examples import LLMSummarizerProcessor

        processor = LLMSummarizerProcessor(metadata)
        config = {"llm_endpoint": ""}
        await processor.initialize(config)
        article = {"title": "Test", "content": "Test"}
        result = await processor.process(article)
        assert result == article

    async def test_shutdown(self):
        """Test shutting down LLM summarizer."""
        metadata = PluginMetadata(
            name="llm-summarizer",
            version="1.0.0",
            plugin_type=PluginType.PROCESSOR,
            description="Test",
            author="Test",
        )
        from src.plugins.examples import LLMSummarizerProcessor

        processor = LLMSummarizerProcessor(metadata)
        config = {"llm_endpoint": "http://localhost:8000"}
        await processor.initialize(config)
        await processor.shutdown()
        assert processor._initialized is False

