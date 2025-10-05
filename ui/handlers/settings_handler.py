"""Settings management handler for CTHarvester main window.

This module handles reading and saving window-specific settings including
geometry, directory preferences, language, and processing options.

Extracted from main_window.py during Phase 2 refactoring to separate
settings management logic from the main window class.

Classes:
    WindowSettingsHandler: Manages window settings persistence

Example:
    >>> handler = WindowSettingsHandler(main_window, settings_manager)
    >>> handler.read_all_settings()  # Load from YAML
    >>> handler.save_all_settings()  # Save to YAML

Note:
    Uses YAML-based SettingsManager for persistent storage.
    Gracefully handles missing or corrupted settings with defaults.

See Also:
    utils.settings_manager: YAML settings persistence
    ui.ctharvester_app: Application singleton
"""

import logging
from typing import TYPE_CHECKING, Optional

from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication

from ui.ctharvester_app import CTHarvesterApp

if TYPE_CHECKING:
    from ui.main_window import CTHarvesterMainWindow
    from utils.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class WindowSettingsHandler:
    """Handles window settings persistence for CTHarvester main window.

    Manages reading and saving of window-specific settings including
    geometry, directory preferences, language, and processing options.

    Args:
        main_window: The CTHarvester main window instance
        settings_manager: YAML settings manager for persistence

    Attributes:
        window: Reference to main window
        settings: Settings manager instance
        app: Application singleton instance (may be None)

    Example:
        >>> handler = WindowSettingsHandler(window, settings_mgr)
        >>> handler.read_all_settings()
        >>> # ... user makes changes ...
        >>> handler.save_all_settings()

    Note:
        Handles missing or corrupted settings gracefully by applying defaults.
    """

    def __init__(
        self, main_window: "CTHarvesterMainWindow", settings_manager: "SettingsManager"
    ) -> None:
        """Initialize settings handler with main window and settings manager.

        Args:
            main_window: The CTHarvester main window instance
            settings_manager: YAML settings manager for persistent storage
        """
        self.window: "CTHarvesterMainWindow" = main_window
        self.settings: "SettingsManager" = settings_manager
        self.app: Optional[CTHarvesterApp] = QApplication.instance()  # type: ignore[assignment]

    def read_all_settings(self) -> None:
        """Read all settings from YAML storage and apply to application.

        Loads and applies:
        - Directory settings (remember_directory, default_directory)
        - Geometry settings (window position/size, mcube geometry)
        - Language settings
        - Processing settings (Rust module preference)

        Note:
            If reading fails, applies default values via _apply_defaults().
            Logs success/failure for debugging.
        """
        try:
            self._read_directory_settings()
            self._read_geometry_settings()
            self._read_language_settings()
            self._read_processing_settings()
            logger.info("Settings loaded successfully")
        except Exception as e:
            logger.error(f"Error reading main window settings: {e}")
            self._apply_defaults()

    def _read_directory_settings(self) -> None:
        """Read directory-related settings from YAML.

        Loads remember_directory flag and default_directory path.
        If remember_directory is False, uses current directory.
        """
        if not self.app:
            return

        self.app.remember_directory = self.settings.get("window.remember_position", True)

        if self.app.remember_directory:
            self.app.default_directory = self.settings.get("application.default_directory", ".")
        else:
            self.app.default_directory = "."

    def _read_geometry_settings(self) -> None:
        """Read window geometry settings (position and size).

        Loads both main window geometry and MCube widget geometry.
        Uses defaults if settings are missing or invalid.
        """
        if not self.app:
            return

        self.app.remember_geometry = self.settings.get("window.remember_size", True)

        if self.app.remember_geometry:
            # Main window geometry
            saved_geom = self.settings.get("window.main_geometry", None)
            if saved_geom and isinstance(saved_geom, dict):
                self.window.setGeometry(
                    QRect(
                        saved_geom.get("x", 100),
                        saved_geom.get("y", 100),
                        saved_geom.get("width", 600),
                        saved_geom.get("height", 550),
                    )
                )
            else:
                self.window.setGeometry(QRect(100, 100, 600, 550))

            # MCube widget geometry
            mcube_geom = self.settings.get("window.mcube_geometry", None)
            if mcube_geom and isinstance(mcube_geom, dict):
                self.window.mcube_geometry = QRect(
                    mcube_geom.get("x", 0),
                    mcube_geom.get("y", 0),
                    mcube_geom.get("width", 150),
                    mcube_geom.get("height", 150),
                )
            else:
                self.window.mcube_geometry = QRect(0, 0, 150, 150)
        else:
            # Use defaults if not remembering geometry
            self.window.setGeometry(QRect(100, 100, 600, 550))
            self.window.mcube_geometry = QRect(0, 0, 150, 150)

    def _read_language_settings(self) -> None:
        """Read language preference from settings.

        Maps language code to supported values: auto->en, en->en, ko->ko.
        Defaults to English if code is invalid.
        """
        if not self.app:
            return

        lang_code = self.settings.get("application.language", "auto")
        lang_map = {"auto": "en", "en": "en", "ko": "ko"}
        self.app.language = lang_map.get(lang_code, "en")

    def _read_processing_settings(self) -> None:
        """Read processing-related settings (Rust module preference).

        Loads use_rust_module flag and updates UI checkbox if present.
        """
        if not self.app:
            return

        use_rust_default = self.settings.get("processing.use_rust_module", True)
        self.app.use_rust_thumbnail = use_rust_default

        # Update UI checkbox if it exists
        if hasattr(self.window, "cbxUseRust"):
            self.window.cbxUseRust.setChecked(use_rust_default)

    def _apply_defaults(self) -> None:
        """Apply default settings when reading fails.

        Sets sensible defaults for all settings categories.
        Logs that defaults were applied.
        """
        if not self.app:
            return

        self.app.remember_directory = True
        self.app.default_directory = "."
        self.app.remember_geometry = True
        self.window.setGeometry(QRect(100, 100, 600, 550))
        self.window.mcube_geometry = QRect(0, 0, 150, 150)
        self.app.language = "en"
        self.app.use_rust_thumbnail = True

        if hasattr(self.window, "cbxUseRust"):
            self.window.cbxUseRust.setChecked(True)

        logger.info("Applied default settings")

    def save_all_settings(self) -> None:
        """Save all current settings to YAML storage and persist to disk.

        Saves (conditionally based on flags):
        - Default directory (if remember_directory is enabled)
        - Window geometries (if remember_geometry is enabled)
        - Rust module preference (always)

        Note:
            Calls settings.save() to persist changes to disk.
            Logs errors if saving fails.
        """
        try:
            if not self.app:
                logger.warning("Application instance not available, cannot save settings")
                return

            if self.app.remember_directory:
                self._save_directory_settings()

            if self.app.remember_geometry:
                self._save_geometry_settings()

            self._save_processing_settings()

            # Persist to disk
            self.settings.save()
            logger.info("Settings saved successfully")

        except Exception as e:
            logger.error(f"Error saving main window settings: {e}")

    def _save_directory_settings(self) -> None:
        """Save default directory setting to YAML."""
        if self.app:
            self.settings.set("application.default_directory", self.app.default_directory)

    def _save_geometry_settings(self) -> None:
        """Save window geometry settings to YAML.

        Saves both main window and MCube widget geometries.
        """
        # Save main window geometry
        geom = self.window.geometry()
        self.settings.set(
            "window.main_geometry",
            {"x": geom.x(), "y": geom.y(), "width": geom.width(), "height": geom.height()},
        )

        # Save mcube widget geometry
        mcube_geom = self.window.mcube_widget.geometry()
        self.settings.set(
            "window.mcube_geometry",
            {
                "x": mcube_geom.x(),
                "y": mcube_geom.y(),
                "width": mcube_geom.width(),
                "height": mcube_geom.height(),
            },
        )

    def _save_processing_settings(self) -> None:
        """Save processing-related settings (Rust module preference).

        Note:
            cbxUseRust checkbox doesn't exist in main_window.
            Settings are managed through SettingsDialog instead.
            Saves the current app state (updated by SettingsDialog).
        """
        current_value = getattr(self.app, "use_rust_thumbnail", True)
        self.settings.set("processing.use_rust_module", current_value)
        logger.info(f"Settings handler: saving processing.use_rust_module = {current_value}")
