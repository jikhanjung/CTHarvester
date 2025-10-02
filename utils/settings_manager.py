"""YAML-based settings manager for application configuration.

This module provides a unified settings management system using YAML for human-readable
configuration storage. It replaces the previous QSettings-based approach with a more
portable and version-control friendly solution.

The module was created during Phase 2.1 settings management improvements as part of
the transition from platform-specific QSettings to platform-independent YAML files.

Key features:
    - Platform-independent configuration storage
    - Human-readable YAML format
    - Default settings with validation
    - Import/Export functionality
    - Dot notation for nested settings access (e.g., 'application.language')

Typical usage example:

    from utils.settings_manager import SettingsManager

    # Initialize (uses default location)
    settings = SettingsManager()

    # Get settings with dot notation
    language = settings.get('application.language', 'en')
    max_size = settings.get('thumbnails.max_size', 500)

    # Set settings
    settings.set('application.language', 'ko')
    settings.set('thumbnails.max_size', 1000)

    # Save to disk
    settings.save()

    # Export/Import
    settings.export('backup.yaml')
    settings.import_settings('backup.yaml')
"""

import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class SettingsManager:
    """YAML-based settings manager for application configuration.

    This class manages application settings using YAML files stored in platform-specific
    configuration directories. It provides a simple key-value interface with dot notation
    support for nested settings.

    Settings are organized hierarchically and accessed using dot notation (e.g.,
    'application.language'). The manager automatically creates configuration directories
    and files as needed.

    Attributes:
        config_dir: Path object pointing to configuration directory.
        config_file: Path object pointing to settings YAML file.
        settings: Dictionary containing current settings.
        default_settings: Dictionary containing default settings from config/settings.yaml.

    Class Attributes:
        DEFAULT_CONFIG_FILE: Default filename for settings (settings.yaml).

    Example:
        >>> mgr = SettingsManager()
        >>> mgr.set('application.language', 'ko')
        >>> lang = mgr.get('application.language')
        >>> print(lang)  # 'ko'
        >>> mgr.save()
    """

    DEFAULT_CONFIG_FILE = "settings.yaml"

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize the settings manager.

        Creates the configuration directory if it doesn't exist and loads settings
        from disk. If no settings file exists, uses default settings.

        Args:
            config_dir: Path to configuration directory. If None, uses platform-specific
                default location:
                - Windows: %APPDATA%/CTHarvester
                - Linux/Mac: ~/.config/CTHarvester

        Note:
            The configuration directory and file are created automatically if they
            don't exist.
        """
        if config_dir is None:
            # Default location: ~/.config/CTHarvester (Linux/Mac) or %APPDATA%/CTHarvester (Windows)
            if os.name == "nt":
                config_dir = os.path.join(os.environ.get("APPDATA", ""), "CTHarvester")
            else:
                config_dir = os.path.join(os.path.expanduser("~"), ".config", "CTHarvester")

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILE

        # Create directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load settings
        self.settings: Dict[str, Any] = {}
        self.default_settings = self._load_default_settings()
        self.load()

    def _load_default_settings(self) -> Dict:
        """Load default settings from config/settings.yaml"""
        # Look for default settings in config directory
        default_file = Path(__file__).parent.parent / "config" / "settings.yaml"

        if default_file.exists():
            try:
                with open(default_file, encoding="utf-8") as f:
                    settings = yaml.safe_load(f)
                    logger.info(f"Default settings loaded from {default_file}")
                    return settings or {}
            except Exception as e:
                logger.error(f"Failed to load default settings: {e}")

        logger.warning("Default settings file not found, using empty defaults")
        return self._get_hardcoded_defaults()

    def _get_hardcoded_defaults(self) -> Dict:
        """Hardcoded default settings as fallback"""
        return {
            "application": {"language": "auto", "theme": "light", "auto_save_settings": True},
            "window": {
                "width": 1200,
                "height": 800,
                "remember_position": True,
                "remember_size": True,
            },
            "thumbnails": {
                "max_size": 500,
                "sample_size": 20,
                "max_level": 10,
                "compression": True,
                "format": "tif",
            },
            "processing": {"threads": "auto", "memory_limit_gb": 4, "use_rust_module": True},
            "rendering": {
                "background_color": [0.2, 0.2, 0.2],
                "default_threshold": 128,
                "anti_aliasing": True,
                "show_fps": False,
            },
            "export": {"mesh_format": "stl", "image_format": "tif", "compression_level": 6},
            "logging": {
                "level": "INFO",
                "max_file_size_mb": 10,
                "backup_count": 5,
                "console_output": True,
            },
            "paths": {"last_directory": "", "export_directory": ""},
        }

    def load(self) -> None:
        """Load settings from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    self.settings = yaml.safe_load(f) or {}
                logger.info(f"Settings loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self.settings = deepcopy(self.default_settings)
        else:
            # Use default settings
            self.settings = deepcopy(self.default_settings)
            self.save()

    def save(self) -> None:
        """Save settings to file"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Settings saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value (supports dot notation)

        Args:
            key: Setting key (e.g., 'thumbnails.max_size')
            default: Default value

        Returns:
            Setting value
        """
        keys = key.split(".")
        value = self.settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set setting value (supports dot notation)

        Args:
            key: Setting key (e.g., 'thumbnails.max_size')
            value: Setting value
        """
        keys = key.split(".")
        settings = self.settings

        # Create nested dictionaries
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]

        # Set value
        settings[keys[-1]] = value

    def reset(self) -> None:
        """Reset to default settings"""
        self.settings = deepcopy(self.default_settings)
        self.save()
        logger.info("Settings reset to defaults")

    def export(self, file_path: str) -> None:
        """
        Export settings to file

        Args:
            file_path: Export file path
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Settings exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            raise

    def import_settings(self, file_path: str) -> None:
        """
        Import settings from file

        Args:
            file_path: Import file path
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                imported = yaml.safe_load(f)

            # Validate and apply
            if self._validate_settings(imported):
                self.settings = imported
                self.save()
                logger.info(f"Settings imported from {file_path}")
            else:
                raise ValueError("Invalid settings file")

        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            raise

    def _validate_settings(self, settings: Dict) -> bool:
        """
        Validate settings structure

        Args:
            settings: Settings dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic structure validation
        required_keys = ["application", "thumbnails", "processing"]

        for key in required_keys:
            if key not in settings:
                logger.error(f"Missing required key: {key}")
                return False

        return True

    def get_all(self) -> Dict:
        """
        Get all settings

        Returns:
            Copy of all settings
        """
        return deepcopy(self.settings)

    def get_config_file_path(self) -> str:
        """
        Get configuration file path

        Returns:
            Path to config file
        """
        return str(self.config_file)
