"""Theme manager for Pacioli.

Handles theme switching between light and dark modes, persistence,
and dynamic updates across the application.
"""

import json
from pathlib import Path
from typing import Literal, Optional
import customtkinter as ctk

from pacioli.ui.tokens import theme, DarkColors, LightColors


ThemeMode = Literal["dark", "light", "system"]


# Config file location
CONFIG_DIR = Path.home() / ".local" / "share" / "pacioli"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ThemeManager:
    """Manages application theme with persistence.

    Handles theme mode switching, persistence to config file,
    and notifies listeners of theme changes.
    """

    _instance: Optional["ThemeManager"] = None
    _listeners: list[callable] = []

    def __new__(cls) -> "ThemeManager":
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize theme manager."""
        if self._initialized:
            return

        self._initialized = True
        self._mode: ThemeMode = "dark"
        self._load_config()

    @property
    def mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self._mode

    @property
    def is_dark(self) -> bool:
        """Check if current theme is dark."""
        if self._mode == "system":
            return ctk.get_appearance_mode() == "Dark"
        return self._mode == "dark"

    @property
    def colors(self) -> type[DarkColors] | type[LightColors]:
        """Get current color palette."""
        return DarkColors if self.is_dark else LightColors

    def set_mode(self, mode: ThemeMode) -> None:
        """Set theme mode.

        Args:
            mode: Theme mode ("dark", "light", or "system")
        """
        self._mode = mode

        # Apply to CustomTkinter
        if mode == "system":
            ctk.set_appearance_mode("system")
        else:
            ctk.set_appearance_mode(mode)

        # Update global theme
        theme.set_mode("dark" if self.is_dark else "light")

        # Save config
        self._save_config()

        # Notify listeners
        self._notify_listeners()

    def toggle(self) -> None:
        """Toggle between dark and light mode."""
        new_mode = "light" if self.is_dark else "dark"
        self.set_mode(new_mode)

    def add_listener(self, callback: callable) -> None:
        """Add a theme change listener.

        Args:
            callback: Function to call when theme changes
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: callable) -> None:
        """Remove a theme change listener.

        Args:
            callback: Function to remove
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all listeners of theme change."""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                # Log error but don't crash
                print(f"Theme listener error: {e}")

    def _load_config(self) -> None:
        """Load theme config from file."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self._mode = config.get("theme", "dark")
        except Exception:
            # Use default on error
            self._mode = "dark"

    def _save_config(self) -> None:
        """Save theme config to file."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Load existing config or create new
            config = {}
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)

            # Update theme
            config["theme"] = self._mode

            # Save
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            # Log error but don't crash
            print(f"Failed to save theme config: {e}")


# Global theme manager instance
theme_manager = ThemeManager()


# ── Convenience Functions ─────────────────────────────────────


def get_theme_mode() -> ThemeMode:
    """Get current theme mode.

    Returns:
        Current theme mode
    """
    return theme_manager.mode


def set_theme_mode(mode: ThemeMode) -> None:
    """Set theme mode.

    Args:
        mode: Theme mode to set
    """
    theme_manager.set_mode(mode)


def toggle_theme() -> None:
    """Toggle between dark and light mode."""
    theme_manager.toggle()


def is_dark_mode() -> bool:
    """Check if dark mode is active.

    Returns:
        True if dark mode, False otherwise
    """
    return theme_manager.is_dark
