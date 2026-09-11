"""Configuration management for Pacioli.

Handles persistent configuration storage and retrieval.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class AIConfig:
    """AI service configuration."""
    model: str = "qwen2.5:3b"
    url: str = "http://localhost:11434/api/generate"
    timeout: int = 30
    temperature: float = 0.7
    max_tokens: int = 400


@dataclass
class AppConfig:
    """Application configuration."""
    ai: AIConfig = field(default_factory=AIConfig)
    theme: str = "dark"
    language: str = "es"


class ConfigManager:
    """Manages application configuration with persistence."""

    def __init__(self):
        """Initialize configuration manager."""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()

    def _get_config_dir(self) -> Path:
        """Get configuration directory following XDG spec."""
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / "pacioli"
        else:
            config_dir = Path.home() / ".config" / "pacioli"

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _load_config(self) -> AppConfig:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self._parse_config(data)
            except (json.JSONDecodeError, IOError):
                pass

        # Return default config
        return AppConfig()

    def _parse_config(self, data: dict[str, Any]) -> AppConfig:
        """Parse configuration data into AppConfig object."""
        ai_data = data.get("ai", {})
        ai_config = AIConfig(
            model=ai_data.get("model", "qwen2.5:3b"),
            url=ai_data.get("url", "http://localhost:11434/api/generate"),
            timeout=ai_data.get("timeout", 30),
            temperature=ai_data.get("temperature", 0.7),
            max_tokens=ai_data.get("max_tokens", 400),
        )

        return AppConfig(
            ai=ai_config,
            theme=data.get("theme", "dark"),
            language=data.get("language", "es"),
        )

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            data = {
                "ai": asdict(self.config.ai),
                "theme": self.config.theme,
                "language": self.config.language,
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get_ai_config(self) -> AIConfig:
        """Get AI configuration."""
        return self.config.ai

    def set_ai_config(self, ai_config: AIConfig) -> None:
        """Set AI configuration and save."""
        self.config.ai = ai_config
        self.save_config()

    def get_theme(self) -> str:
        """Get theme preference."""
        return self.config.theme

    def set_theme(self, theme: str) -> None:
        """Set theme preference and save."""
        self.config.theme = theme
        self.save_config()


# Global configuration manager instance
config_manager = ConfigManager()
