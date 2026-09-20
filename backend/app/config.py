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
class AIConfig:
    """AI service configuration.

    ``think`` controls the reasoning effort of thinking models
    (Qwen3, DeepSeek-R1); non-thinking models ignore it. ``max_tokens``
    is the total generation budget: thinking models consume part of it
    with internal reasoning, so the default is generous.
    """

    model: str = "qwen2.5:3b"
    url: str = "http://localhost:11434/api/generate"
    timeout: int = 120
    temperature: float = 0.5
    max_tokens: int = 1024
    think: str = "low"


@dataclass
class AppConfig:
    """Application configuration."""

    ai: AIConfig = field(default_factory=AIConfig)
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
        ai_data = data.get("ai", {})
        defaults = AIConfig()
        ai_config = AIConfig(
            model=ai_data.get("model", defaults.model),
            url=ai_data.get("url", defaults.url),
            timeout=ai_data.get("timeout", defaults.timeout),
            temperature=ai_data.get("temperature", defaults.temperature),
            max_tokens=ai_data.get("max_tokens", defaults.max_tokens),
            think=ai_data.get("think", defaults.think),
        )
        return AppConfig(
            ai=ai_config,
            theme=data.get("theme", "dark"),
            language=data.get("language", "es"),
        )

    def save_config(self) -> None:
        """Persist the current configuration to disk."""
        data = {
            "ai": asdict(self.config.ai),
            "theme": self.config.theme,
            "language": self.config.language,
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError:
            logger.exception("Failed to save config to %s", self.config_file)

    def get_ai_config(self) -> AIConfig:
        """Return the AI configuration."""
        return self.config.ai

    def set_ai_config(self, ai_config: AIConfig) -> None:
        """Replace the AI configuration and persist it."""
        self.config.ai = ai_config
        self.save_config()

    def get_theme(self) -> str:
        """Return the theme preference."""
        return self.config.theme

    def set_theme(self, theme: str) -> None:
        """Set the theme preference and persist it."""
        self.config.theme = theme
        self.save_config()


config_manager = ConfigManager()
