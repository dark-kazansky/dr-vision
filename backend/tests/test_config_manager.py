"""Tests for Config Manager singleton pattern fix (Task 1.3).

Validates Requirements 2.1, 2.2, 2.3:
- Config.load() returns cached instance on repeated calls
- Config.load(force_reload=True) reloads from YAML
- Instance state stored on instance, not as mutable class-level attribute
"""

import pytest
import yaml
from config.manager import Config


SAMPLE_CONFIG = {
    "api_providers": {
        "lm_studio": {"base_url": "http://localhost:1234/v1"}
    },
    "models": {
        "test-model": {
            "model_id": "test-model",
            "provider": "lm_studio",
            "name": "Test Model",
        }
    },
    "fastapi": {"host": "0.0.0.0", "port": 8000, "debug": False},
    "upload": {
        "folder": "uploads",
        "max_size_mb": 10,
        "allowed_extensions": [".pdf", ".png"],
    },
}


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the Config singleton before each test."""
    Config._instance = None
    yield
    Config._instance = None


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary YAML config file."""
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.dump(SAMPLE_CONFIG))
    return str(path)


class TestSingletonCaching:
    """Requirement 2.1: Config.load() returns same cached instance."""

    def test_load_returns_same_instance(self, config_file):
        first = Config.load(config_path=config_file)
        second = Config.load(config_path=config_file)
        assert first is second

    def test_cached_instance_preserves_data(self, config_file):
        first = Config.load(config_path=config_file)
        second = Config.load(config_path=config_file)
        assert first.default_model == second.default_model
        assert first.models == second.models


class TestForceReload:
    """Requirement 2.2: force_reload=True reloads from YAML."""

    def test_force_reload_creates_new_instance(self, config_file, tmp_path):
        first = Config.load(config_path=config_file)

        # Modify the YAML file
        updated = SAMPLE_CONFIG.copy()
        updated["default_model"] = "new-default"
        path = tmp_path / "settings.yaml"
        path.write_text(yaml.dump(updated))

        second = Config.load(config_path=config_file, force_reload=True)
        assert second is not first
        assert second.default_model == "new-default"

    def test_force_reload_updates_cached_instance(self, config_file, tmp_path):
        Config.load(config_path=config_file)

        updated = SAMPLE_CONFIG.copy()
        updated["default_model"] = "reloaded-model"
        path = tmp_path / "settings.yaml"
        path.write_text(yaml.dump(updated))

        Config.load(config_path=config_file, force_reload=True)
        # Subsequent call without force_reload should return the reloaded instance
        third = Config.load(config_path=config_file)
        assert third.default_model == "reloaded-model"


class TestInstanceState:
    """Requirement 2.3: _config_data stored on instance, not class."""

    def test_no_class_level_config_data(self):
        # The class itself should not have _config_data as a class attribute
        assert "_config_data" not in Config.__dict__

    def test_config_data_is_instance_attribute(self, config_file):
        instance = Config.load(config_path=config_file)
        assert "_config_data" in instance.__dict__
        assert isinstance(instance._config_data, dict)

    def test_separate_instances_have_independent_data(self, config_file, tmp_path):
        first = Config.load(config_path=config_file)
        first_models = first.models

        updated = SAMPLE_CONFIG.copy()
        updated["models"] = {}
        path = tmp_path / "settings.yaml"
        path.write_text(yaml.dump(updated))

        second = Config.load(config_path=config_file, force_reload=True)
        # first instance data should be unchanged
        assert first_models == SAMPLE_CONFIG["models"]
        assert second.models == {}
