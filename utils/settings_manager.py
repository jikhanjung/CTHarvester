"""Settings manager for application configuration.

Provides a unified settings management system, replacing the platform-specific
QSettings approach it started from with a plain file the user can read, copy and
version-control.

There is one settings file: ``preferences.json`` in the OS configuration
directory under ``PaleoBytes/CTHarvester`` (see :mod:`utils.paths`), separate
from the data directory that holds the logs. The defaults are defined once, in
:meth:`SettingsManager._get_default_settings`.

Key features:
    - Platform-independent configuration storage
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
    settings.export('backup.json')
    settings.import_settings('backup.json')
"""

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from utils.paths import CONFIG_FILENAME, get_config_dir

logger = logging.getLogger(__name__)


class SettingsManager:
    """Settings manager for application configuration.

    This class manages application settings as a JSON file in the user's
    configuration directory. It provides a simple key-value interface with dot
    notation support for nested settings.

    Settings are organized hierarchically and accessed using dot notation (e.g.,
    'application.language'). The manager automatically creates configuration directories
    and files as needed.

    Attributes:
        config_dir: Path object pointing to configuration directory.
        config_file: Path object pointing to the preferences file.
        settings: Dictionary containing current settings.
        default_settings: Dictionary containing the default settings.

    Class Attributes:
        DEFAULT_CONFIG_FILE: Default filename for settings (preferences.json).

    Example:
        >>> mgr = SettingsManager()
        >>> mgr.set('application.language', 'ko')
        >>> lang = mgr.get('application.language')
        >>> print(lang)  # 'ko'
        >>> mgr.save()
    """

    DEFAULT_CONFIG_FILE = CONFIG_FILENAME

    def __init__(self, config_dir: str | None = None):
        """Initialize the settings manager.

        Creates the configuration directory if it doesn't exist and loads settings
        from disk. If no settings file exists, uses default settings.

        Args:
            config_dir: Path to configuration directory. If None, uses the
                configuration directory from :mod:`utils.paths` — the OS config
                location under ``PaleoBytes/CTHarvester``, deliberately separate
                from the data directory that holds the logs.

        Note:
            The configuration directory and file are created automatically if they
            don't exist.
        """
        self.config_dir = Path(config_dir) if config_dir is not None else get_config_dir()
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILE

        # Create directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load settings
        self.settings: dict[str, Any] = {}
        self.default_settings = self._get_default_settings()
        self.load()

    def _get_default_settings(self) -> dict:
        """Return the default settings.

        This is the only definition of them. It used to be a fallback behind
        ``config/settings.yaml``, and the two drifted exactly as a hand-kept
        second copy does: the YAML carried keys nothing reads
        (``rendering.background_color``, ``logging.backup_count``,
        ``paths.export_directory``) and lacked three the application writes
        (``application.default_directory``, ``window.main_geometry``,
        ``window.mcube_geometry``). Worse, the YAML was never bundled into the
        frozen build, so released versions always ran on this dict while the
        manual documented the file.
        """
        return {
            "application": {
                # auto, en, ko
                "language": "auto",
                # light, dark
                "theme": "light",
                "auto_save_settings": True,
            },
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
                # tif, png
                "format": "tif",
            },
            "processing": {
                # auto, or a specific number (1-16)
                "threads": "auto",
                "memory_limit_gb": 4,
                # True uses the compiled Rust thumbnail generator, which is what
                # the application ships with. If the module is missing or fails to
                # import, ThumbnailCreationHandler falls back to the Python
                # implementation on its own -- set this False only to force that
                # fallback for debugging.
                "use_rust_module": True,
            },
            "rendering": {
                "background_color": [0.2, 0.2, 0.2],
                "default_threshold": 128,
                "anti_aliasing": True,
                "show_fps": False,
            },
            "export": {
                # stl, ply, obj
                "mesh_format": "stl",
                # tif, png, jpg
                "image_format": "tif",
                # 0-9
                "compression_level": 6,
            },
            "logging": {
                # DEBUG, INFO, WARNING, ERROR
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
                with self.config_file.open(encoding="utf-8") as f:
                    self.settings = json.load(f) or {}
                logger.info(f"Settings loaded from {self.config_file}")
            except (OSError, ValueError):
                # Falling back to defaults means every preference the user set is
                # gone, so do not let the file that caused it disappear with
                # them: keep it as .bak for recovery, and say so loudly.
                logger.exception("Failed to load settings; falling back to defaults")
                self._back_up_unreadable_config()
                self.settings = deepcopy(self.default_settings)
        else:
            # Use default settings
            self.settings = deepcopy(self.default_settings)
            self.save()

    def _back_up_unreadable_config(self) -> None:
        """Move a config file that could not be read aside, as ``.bak``."""
        backup = self.config_file.with_suffix(self.config_file.suffix + ".bak")
        try:
            self.config_file.replace(backup)
        except OSError as err:
            logger.warning(f"Could not back up unreadable settings file: {err}")
        else:
            logger.error(f"Unreadable settings file backed up to {backup}")

    def save(self) -> None:
        """Save settings to file"""
        try:
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info(f"Settings saved to {self.config_file}")
        except Exception:
            logger.exception("Failed to save settings")

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
            with Path(file_path).open("w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info(f"Settings exported to {file_path}")
        except Exception:
            logger.exception("Failed to export settings")
            raise

    def import_settings(self, file_path: str) -> None:
        """
        Import settings from file

        Args:
            file_path: Import file path
        """
        try:
            with Path(file_path).open(encoding="utf-8") as f:
                imported = json.load(f)

            # Validate and apply
            if self._validate_settings(imported):
                self.settings = imported
                self.save()
                logger.info(f"Settings imported from {file_path}")
            else:
                raise ValueError("Invalid settings file")

        except Exception:
            logger.exception("Failed to import settings")
            raise

    def _validate_settings(self, settings: dict) -> bool:
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

    def get_all(self) -> dict:
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
