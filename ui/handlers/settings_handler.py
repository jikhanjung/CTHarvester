"""
WindowSettingsHandler - Settings management for CTHarvesterMainWindow

Separates settings read/write logic from main window class.
Extracted from main_window.py read_settings() and save_settings() methods
(Phase 2: Settings Management Separation)
"""

import logging

from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class WindowSettingsHandler:
    """
    Handles reading and saving window-specific settings for CTHarvesterMainWindow.

    This class manages:
    - Window geometry (position and size)
    - MCube widget geometry
    - Directory preferences
    - Language settings
    - Processing preferences (Rust module usage)
    """

    def __init__(self, main_window, settings_manager):
        """
        Initialize settings handler.

        Args:
            main_window (CTHarvesterMainWindow): The main window instance
            settings_manager (SettingsManager): The YAML settings manager
        """
        self.window = main_window
        self.settings = settings_manager
        self.app = QApplication.instance()

    def read_all_settings(self):
        """
        Read all settings from YAML and apply to application.

        Reads:
        - Directory settings (remember_directory, default_directory)
        - Geometry settings (window position/size, mcube geometry)
        - Language settings
        - Processing settings (Rust module preference)

        If reading fails, applies default values.
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

    def _read_directory_settings(self):
        """Read directory-related settings."""
        self.app.remember_directory = self.settings.get("window.remember_position", True)

        if self.app.remember_directory:
            self.app.default_directory = self.settings.get(
                "application.default_directory", "."
            )
        else:
            self.app.default_directory = "."

    def _read_geometry_settings(self):
        """Read window geometry settings (position and size)."""
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

    def _read_language_settings(self):
        """Read language preference."""
        lang_code = self.settings.get("application.language", "auto")
        lang_map = {"auto": "en", "en": "en", "ko": "ko"}
        self.app.language = lang_map.get(lang_code, "en")

    def _read_processing_settings(self):
        """Read processing-related settings (Rust module preference)."""
        use_rust_default = self.settings.get("processing.use_rust_module", True)
        self.app.use_rust_thumbnail = use_rust_default

        # Update UI checkbox if it exists
        if hasattr(self.window, "cbxUseRust"):
            self.window.cbxUseRust.setChecked(use_rust_default)

    def _apply_defaults(self):
        """Apply default settings when reading fails."""
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

    def save_all_settings(self):
        """
        Save all current settings to YAML storage.

        Saves:
        - Default directory (if remember_directory is enabled)
        - Window geometries (if remember_geometry is enabled)
        - Rust module preference

        Persists changes to disk.
        """
        try:
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

    def _save_directory_settings(self):
        """Save default directory setting."""
        self.settings.set(
            "application.default_directory",
            self.app.default_directory
        )

    def _save_geometry_settings(self):
        """Save window geometry settings."""
        # Save main window geometry
        geom = self.window.geometry()
        self.settings.set(
            "window.main_geometry",
            {
                "x": geom.x(),
                "y": geom.y(),
                "width": geom.width(),
                "height": geom.height()
            },
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

    def _save_processing_settings(self):
        """Save processing-related settings (Rust module preference)."""
        # Note: cbxUseRust checkbox doesn't exist in main_window
        # Settings are managed through SettingsDialog instead
        # Only save the current app state (which should be updated by SettingsDialog)
        current_value = getattr(self.app, 'use_rust_thumbnail', True)
        self.settings.set("processing.use_rust_module", current_value)
        logger.info(f"Settings handler: saving processing.use_rust_module = {current_value}")
