"""Tests for configuration management."""

import pytest
import json
import tempfile
from pathlib import Path

from pacioli.core.config import ConfigManager, AppConfig, AIConfig


class TestConfigManager:
    """Test suite for configuration management."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_manager(self, temp_config_dir, monkeypatch):
        """Create config manager with temp directory."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_dir))
        return ConfigManager()

    def test_default_config_creation(self, config_manager):
        """Test that default config is created when no file exists."""
        config = config_manager.config
        assert isinstance(config, AppConfig)
        assert isinstance(config.ai, AIConfig)
        assert config.ai.model == "qwen2.5:3b"
        assert config.ai.timeout == 30
        assert config.theme == "dark"

    def test_save_and_load_config(self, config_manager):
        """Test saving and loading configuration."""
        # Modify config
        config_manager.config.ai.model = "test-model"
        config_manager.config.ai.timeout = 60
        config_manager.config.theme = "light"

        # Save
        config_manager.save_config()

        # Create new manager to load
        new_manager = ConfigManager()
        assert new_manager.config.ai.model == "test-model"
        assert new_manager.config.ai.timeout == 60
        assert new_manager.config.theme == "light"

    def test_set_ai_config(self, config_manager):
        """Test setting AI configuration."""
        new_ai_config = AIConfig(
            model="llama2",
            url="http://custom:11434/api/generate",
            timeout=45,
            temperature=0.5,
            max_tokens=500
        )

        config_manager.set_ai_config(new_ai_config)

        # Check it was saved
        loaded_config = config_manager.get_ai_config()
        assert loaded_config.model == "llama2"
        assert loaded_config.url == "http://custom:11434/api/generate"
        assert loaded_config.timeout == 45
        assert loaded_config.temperature == 0.5
        assert loaded_config.max_tokens == 500

    def test_set_theme(self, config_manager):
        """Test setting theme preference."""
        config_manager.set_theme("light")
        assert config_manager.get_theme() == "light"

        config_manager.set_theme("dark")
        assert config_manager.get_theme() == "dark"

    def test_config_file_location(self, config_manager, temp_config_dir):
        """Test that config file is in correct location."""
        expected_path = temp_config_dir / "pacioli" / "config.json"
        assert config_manager.config_file == expected_path

    def test_load_invalid_json(self, config_manager):
        """Test loading invalid JSON file."""
        # Create invalid JSON file
        config_manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        config_manager.config_file.write_text("invalid json{{{")

        # Should load defaults
        new_manager = ConfigManager()
        assert new_manager.config.ai.model == "qwen2.5:3b"

    def test_ai_config_defaults(self):
        """Test AIConfig default values."""
        config = AIConfig()
        assert config.model == "qwen2.5:3b"
        assert config.url == "http://localhost:11434/api/generate"
        assert config.timeout == 30
        assert config.temperature == 0.7
        assert config.max_tokens == 400

    def test_app_config_defaults(self):
        """Test AppConfig default values."""
        config = AppConfig()
        assert isinstance(config.ai, AIConfig)
        assert config.theme == "dark"
        assert config.language == "es"

    def test_config_persistence_across_instances(self, temp_config_dir, monkeypatch):
        """Test that config persists across different manager instances."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_dir))

        # First instance - modify and save
        manager1 = ConfigManager()
        manager1.config.ai.model = "persistent-model"
        manager1.save_config()

        # Second instance - should load saved config
        manager2 = ConfigManager()
        assert manager2.config.ai.model == "persistent-model"
