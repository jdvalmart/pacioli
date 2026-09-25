"""Tests for configuration management."""

from pathlib import Path

import pytest

from app.config import AppConfig, ConfigManager


class TestConfigManager:
    """Test suite for configuration management."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path: Path) -> Path:
        """Provide a temporary config directory."""
        return tmp_path

    @pytest.fixture
    def config_manager(
        self, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> ConfigManager:
        """Create a ConfigManager isolated in a temp directory."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_dir))
        return ConfigManager()

    def test_default_config_creation(self, config_manager: ConfigManager) -> None:
        config = config_manager.config
        assert isinstance(config, AppConfig)
        assert config.theme == "dark"

    def test_save_and_load_config(self, config_manager: ConfigManager) -> None:
        config_manager.config.theme = "light"

        config_manager.save_config()

        new_manager = ConfigManager()
        assert new_manager.config.theme == "light"

    def test_set_theme(self, config_manager: ConfigManager) -> None:
        config_manager.set_theme("light")
        assert config_manager.get_theme() == "light"

        config_manager.set_theme("dark")
        assert config_manager.get_theme() == "dark"

    def test_config_file_location(
        self, config_manager: ConfigManager, temp_config_dir: Path
    ) -> None:
        expected_path = temp_config_dir / "pacioli" / "config.json"
        assert config_manager.config_file == expected_path

    def test_load_invalid_json(self, config_manager: ConfigManager) -> None:
        config_manager.config_file.parent.mkdir(parents=True, exist_ok=True)
        config_manager.config_file.write_text("invalid json{{{")

        new_manager = ConfigManager()
        assert new_manager.config.theme == "dark"

    def test_app_config_defaults(self) -> None:
        config = AppConfig()
        assert config.theme == "dark"
        assert config.language == "es"

    def test_config_persistence_across_instances(
        self, temp_config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_dir))

        manager1 = ConfigManager()
        manager1.config.theme = "light"
        manager1.save_config()

        manager2 = ConfigManager()
        assert manager2.config.theme == "light"
