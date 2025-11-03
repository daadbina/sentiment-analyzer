"""Tests for configuration manager."""

import pytest
import json
import tempfile
from pathlib import Path
from src.config.config_manager import ConfigManager, FeatureFlag, ABTestConfig


class TestFeatureFlag:
    """Test feature flag functionality."""

    def test_feature_flag_creation(self):
        """Test creating a feature flag."""
        flag = FeatureFlag(
            name="new_ui",
            enabled=True,
            description="New UI feature",
            rollout_percentage=50,
        )

        assert flag.name == "new_ui"
        assert flag.enabled is True
        assert flag.rollout_percentage == 50

    def test_feature_flag_enabled_for_all(self):
        """Test feature flag enabled for all users."""
        flag = FeatureFlag(name="feature", enabled=True, rollout_percentage=100)

        assert flag.is_enabled_for_user("user1") is True
        assert flag.is_enabled_for_user("user2") is True

    def test_feature_flag_disabled(self):
        """Test disabled feature flag."""
        flag = FeatureFlag(name="feature", enabled=False)

        assert flag.is_enabled_for_user("user1") is False

    def test_feature_flag_target_users(self):
        """Test feature flag with target users."""
        flag = FeatureFlag(
            name="feature",
            enabled=True,
            target_users=["user1", "user2"],
        )

        assert flag.is_enabled_for_user("user1") is True
        assert flag.is_enabled_for_user("user3") is False

    def test_feature_flag_rollout_percentage(self):
        """Test feature flag rollout percentage."""
        flag = FeatureFlag(
            name="feature",
            enabled=True,
            rollout_percentage=50,
        )

        # Test multiple users to verify rollout
        enabled_count = sum(
            1 for i in range(100) if flag.is_enabled_for_user(f"user{i}")
        )

        # Should be approximately 50% (allow 40-60% range)
        assert 40 <= enabled_count <= 60


class TestABTestConfig:
    """Test A/B test configuration."""

    def test_ab_test_creation(self):
        """Test creating an A/B test."""
        test = ABTestConfig(
            name="checkout_flow",
            enabled=True,
            variant_a={"flow": "old"},
            variant_b={"flow": "new"},
            split_percentage=50,
        )

        assert test.name == "checkout_flow"
        assert test.enabled is True
        assert test.split_percentage == 50

    def test_ab_test_variant_assignment(self):
        """Test A/B test variant assignment."""
        test = ABTestConfig(
            name="test",
            enabled=True,
            variant_a={"version": "a"},
            variant_b={"version": "b"},
            split_percentage=50,
        )

        # Test multiple users
        variants = [test.get_variant_for_user(f"user{i}") for i in range(100)]

        # Should have both variants
        assert "variant_a" in variants
        assert "variant_b" in variants

    def test_ab_test_config_for_user(self):
        """Test getting A/B test config for user."""
        test = ABTestConfig(
            name="test",
            enabled=True,
            variant_a={"color": "red"},
            variant_b={"color": "blue"},
        )

        config_a = test.get_config_for_user("user1")
        config_b = test.get_config_for_user("user2")

        assert config_a in [{"color": "red"}, {"color": "blue"}]
        assert config_b in [{"color": "red"}, {"color": "blue"}]

    def test_ab_test_disabled(self):
        """Test disabled A/B test."""
        test = ABTestConfig(
            name="test",
            enabled=False,
            variant_a={"version": "a"},
            variant_b={"version": "b"},
        )

        assert test.get_variant_for_user("user1") == "control"


class TestConfigManager:
    """Test configuration manager."""

    def test_config_manager_creation(self):
        """Test creating config manager."""
        manager = ConfigManager()

        assert manager.config == {}
        assert manager.feature_flags == {}
        assert manager.ab_tests == {}

    def test_load_json_config(self):
        """Test loading JSON configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_data = {"database": {"host": "localhost", "port": 5432}}

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            manager = ConfigManager(tmpdir)
            manager.load_config("config.json")

            assert manager.get("database.host") == "localhost"
            assert manager.get("database.port") == 5432

    def test_get_config_value(self):
        """Test getting configuration values."""
        manager = ConfigManager()
        manager.config = {
            "app": {"name": "test", "version": "1.0"},
            "db": {"host": "localhost"},
        }

        assert manager.get("app.name") == "test"
        assert manager.get("app.version") == "1.0"
        assert manager.get("db.host") == "localhost"
        assert manager.get("missing") is None
        assert manager.get("missing", "default") == "default"

    def test_set_config_value(self):
        """Test setting configuration values."""
        manager = ConfigManager()

        manager.set("app.name", "myapp")
        manager.set("app.version", "2.0")

        assert manager.get("app.name") == "myapp"
        assert manager.get("app.version") == "2.0"

    def test_load_feature_flags(self):
        """Test loading feature flags."""
        with tempfile.TemporaryDirectory() as tmpdir:
            flags_file = Path(tmpdir) / "flags.json"
            flags_data = {
                "flags": [
                    {
                        "name": "feature1",
                        "enabled": True,
                        "description": "Feature 1",
                        "rollout_percentage": 100,
                    },
                    {
                        "name": "feature2",
                        "enabled": False,
                        "description": "Feature 2",
                        "rollout_percentage": 50,
                    },
                ]
            }

            with open(flags_file, "w") as f:
                json.dump(flags_data, f)

            manager = ConfigManager(tmpdir)
            manager.load_feature_flags("flags.json")

            assert manager.is_feature_enabled("feature1") is True
            assert manager.is_feature_enabled("feature2") is False

    def test_is_feature_enabled_for_user(self):
        """Test checking if feature is enabled for user."""
        manager = ConfigManager()
        manager.feature_flags["feature1"] = FeatureFlag(
            name="feature1",
            enabled=True,
            rollout_percentage=100,
        )

        assert manager.is_feature_enabled("feature1", "user1") is True

    def test_load_ab_tests(self):
        """Test loading A/B tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tests_file = Path(tmpdir) / "tests.json"
            tests_data = {
                "tests": [
                    {
                        "name": "test1",
                        "enabled": True,
                        "variant_a": {"version": "a"},
                        "variant_b": {"version": "b"},
                        "split_percentage": 50,
                    }
                ]
            }

            with open(tests_file, "w") as f:
                json.dump(tests_data, f)

            manager = ConfigManager(tmpdir)
            manager.load_ab_tests("tests.json")

            assert "test1" in manager.ab_tests

    def test_get_ab_test_variant(self):
        """Test getting A/B test variant."""
        manager = ConfigManager()
        manager.ab_tests["test1"] = ABTestConfig(
            name="test1",
            enabled=True,
            variant_a={"version": "a"},
            variant_b={"version": "b"},
        )

        variant = manager.get_ab_test_variant("test1", "user1")
        assert variant in ["variant_a", "variant_b"]

    def test_get_ab_test_config(self):
        """Test getting A/B test configuration."""
        manager = ConfigManager()
        manager.ab_tests["test1"] = ABTestConfig(
            name="test1",
            enabled=True,
            variant_a={"color": "red"},
            variant_b={"color": "blue"},
        )

        config = manager.get_ab_test_config("test1", "user1")
        assert config in [{"color": "red"}, {"color": "blue"}]

    def test_config_watcher(self):
        """Test configuration watcher callback."""
        manager = ConfigManager()
        callback_called = False

        def on_config_change(mgr):
            nonlocal callback_called
            callback_called = True

        manager.watch(on_config_change)
        manager.set("key", "value")

        assert callback_called is True

    def test_to_dict(self):
        """Test exporting configuration as dictionary."""
        manager = ConfigManager()
        manager.config = {"app": {"name": "test"}}
        manager.feature_flags["feature1"] = FeatureFlag(
            name="feature1", enabled=True
        )

        config_dict = manager.to_dict()

        assert "config" in config_dict
        assert "feature_flags" in config_dict
        assert "ab_tests" in config_dict
        assert config_dict["config"]["app"]["name"] == "test"

