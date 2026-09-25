"""Configuration management for Pacioli.

Persistent configuration stored under the XDG config directory
(``~/.config/pacioli/config.json`` by default).
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.logging_config import logger


@dataclass
class AppConfig:
    """Application configuration."""

    theme: str = "dark"
    language: str = "es"


class ConfigManager:
    """Manages application configuration with persistence."""

    def __init__(self) -> None:
        """Initialize the manager, loading the configuration from disk."""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()

    def _get_config_dir(self) -> Path:
        """Return the configuration directory following the XDG spec."""
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        config_dir = (
            Path(xdg_config) / "pacioli" if xdg_config else Path.home() / ".config" / "pacioli"
        )
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _load_config(self) -> AppConfig:
        """Load configuration from file or return defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    return self._parse_config(json.load(f))
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupt config file at %s, using defaults", self.config_file)
        return AppConfig()

    def _parse_config(self, data: dict[str, Any]) -> AppConfig:
        """Build an AppConfig from a raw JSON dict, tolerating missing keys."""
        return AppConfig(
            theme=data.get("theme", "dark"),
            language=data.get("language", "es"),
        )

    def save_config(self) -> None:
        """Persist the current configuration to disk."""
        data = {
            "theme": self.config.theme,
            "language": self.config.language,
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError:
            logger.exception("Failed to save config to %s", self.config_file)

    def get_theme(self) -> str:
        """Return the theme preference."""
        return self.config.theme

    def set_theme(self, theme: str) -> None:
        """Set the theme preference and persist it."""
        self.config.theme = theme
        self.save_config()


config_manager = ConfigManager()
