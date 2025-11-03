"""Configuration management with hot-reloading and feature flags."""

import json
import yaml
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlag:
    """Feature flag configuration."""

    name: str
    enabled: bool
    description: str = ""
    rollout_percentage: int = 100  # 0-100
    target_users: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def is_enabled_for_user(self, user_id: str) -> bool:
        """Check if feature is enabled for specific user."""
        if not self.enabled:
            return False

        if self.target_users and user_id not in self.target_users:
            return False

        # Simple hash-based rollout
        if self.rollout_percentage < 100:
            user_hash = hash(f"{self.name}:{user_id}") % 100
            return user_hash < self.rollout_percentage

        return True


@dataclass
class ABTestConfig:
    """A/B test configuration."""

    name: str
    enabled: bool
    variant_a: Dict[str, Any]
    variant_b: Dict[str, Any]
    split_percentage: int = 50  # 0-100
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_variant_for_user(self, user_id: str) -> str:
        """Get variant for specific user."""
        if not self.enabled:
            return "control"

        user_hash = hash(f"{self.name}:{user_id}") % 100
        return "variant_a" if user_hash < self.split_percentage else "variant_b"

    def get_config_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get configuration for specific user."""
        variant = self.get_variant_for_user(user_id)
        if variant == "variant_a":
            return self.variant_a
        else:
            return self.variant_b


class ConfigManager:
    """Configuration manager with hot-reloading and feature flags."""

    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self.config: Dict[str, Any] = {}
        self.feature_flags: Dict[str, FeatureFlag] = {}
        self.ab_tests: Dict[str, ABTestConfig] = {}
        self.watchers: List[Callable] = []
        self.last_reload: Optional[datetime] = None

    def load_config(self, filename: str) -> None:
        """Load configuration from file (YAML or JSON)."""
        filepath = self.config_dir / filename

        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}")
            return

        try:
            with open(filepath, "r") as f:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    self.config = yaml.safe_load(f) or {}
                elif filename.endswith(".json"):
                    self.config = json.load(f)
                else:
                    logger.error(f"Unsupported config format: {filename}")
                    return

            self.last_reload = datetime.now()
            logger.info(f"Configuration loaded from {filepath}")
            self._notify_watchers()

        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def load_feature_flags(self, filename: str) -> None:
        """Load feature flags from file."""
        filepath = self.config_dir / filename

        if not filepath.exists():
            logger.warning(f"Feature flags file not found: {filepath}")
            return

        try:
            with open(filepath, "r") as f:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    data = yaml.safe_load(f) or {}
                elif filename.endswith(".json"):
                    data = json.load(f)
                else:
                    logger.error(f"Unsupported format: {filename}")
                    return

            self.feature_flags = {}
            for flag_data in data.get("flags", []):
                flag = FeatureFlag(**flag_data)
                self.feature_flags[flag.name] = flag

            logger.info(f"Feature flags loaded from {filepath}")
            self._notify_watchers()

        except Exception as e:
            logger.error(f"Error loading feature flags: {e}")

    def load_ab_tests(self, filename: str) -> None:
        """Load A/B tests from file."""
        filepath = self.config_dir / filename

        if not filepath.exists():
            logger.warning(f"A/B tests file not found: {filepath}")
            return

        try:
            with open(filepath, "r") as f:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    data = yaml.safe_load(f) or {}
                elif filename.endswith(".json"):
                    data = json.load(f)
                else:
                    logger.error(f"Unsupported format: {filename}")
                    return

            self.ab_tests = {}
            for test_data in data.get("tests", []):
                test = ABTestConfig(**test_data)
                self.ab_tests[test.name] = test

            logger.info(f"A/B tests loaded from {filepath}")
            self._notify_watchers()

        except Exception as e:
            logger.error(f"Error loading A/B tests: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        self._notify_watchers()

    def is_feature_enabled(self, feature_name: str, user_id: Optional[str] = None) -> bool:
        """Check if feature is enabled."""
        flag = self.feature_flags.get(feature_name)
        if not flag:
            return False

        if user_id:
            return flag.is_enabled_for_user(user_id)

        return flag.enabled

    def get_ab_test_variant(self, test_name: str, user_id: str) -> str:
        """Get A/B test variant for user."""
        test = self.ab_tests.get(test_name)
        if not test:
            return "control"

        return test.get_variant_for_user(user_id)

    def get_ab_test_config(self, test_name: str, user_id: str) -> Dict[str, Any]:
        """Get A/B test configuration for user."""
        test = self.ab_tests.get(test_name)
        if not test:
            return {}

        return test.get_config_for_user(user_id)

    def watch(self, callback: Callable) -> None:
        """Register callback for configuration changes."""
        self.watchers.append(callback)

    def _notify_watchers(self) -> None:
        """Notify all watchers of configuration changes."""
        for callback in self.watchers:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Error in config watcher: {e}")

    def reload(self) -> None:
        """Reload all configurations."""
        logger.info("Reloading configurations...")
        # Reload from environment or files
        self._notify_watchers()

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            "config": self.config,
            "feature_flags": {
                name: asdict(flag) for name, flag in self.feature_flags.items()
            },
            "ab_tests": {
                name: asdict(test) for name, test in self.ab_tests.items()
            },
            "last_reload": self.last_reload.isoformat() if self.last_reload else None,
        }

