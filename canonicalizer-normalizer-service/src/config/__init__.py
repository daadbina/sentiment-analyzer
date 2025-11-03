"""Configuration management module."""

from src.config.config_manager import ConfigManager, FeatureFlag, ABTestConfig
import sys
from pathlib import Path

# Import settings from config.py at the src level
# We need to import from the parent directory's config.py file
parent_dir = Path(__file__).parent.parent
config_py_path = parent_dir / "config.py"

# Import get_settings from the config.py file
if config_py_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_config_settings", config_py_path)
    if spec and spec.loader:
        _config_settings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_config_settings)
        get_settings = _config_settings.get_settings
        Settings = _config_settings.Settings
        KafkaSettings = _config_settings.KafkaSettings
        PostgresSettings = _config_settings.PostgresSettings
        RedisSettings = _config_settings.RedisSettings
        NormalizationSettings = _config_settings.NormalizationSettings
        ServiceSettings = _config_settings.ServiceSettings
    else:
        raise ImportError("Could not load config.py")
else:
    raise ImportError("config.py not found")

__all__ = [
    "ConfigManager",
    "FeatureFlag",
    "ABTestConfig",
    "get_settings",
    "Settings",
    "KafkaSettings",
    "PostgresSettings",
    "RedisSettings",
    "NormalizationSettings",
    "ServiceSettings",
]

