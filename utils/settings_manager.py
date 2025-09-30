"""
YAML-based settings manager

Provides configuration management with:
- Default settings support
- Validation
- Auto-save
- Import/Export functionality

Created during Phase 2.1 settings management improvements.
"""
import yaml
import os
from pathlib import Path
from typing import Any, Dict
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    YAML-based settings manager

    Features:
    - Default settings support
    - Settings validation
    - Auto-save
    - Import/Export
    """

    DEFAULT_CONFIG_FILE = "settings.yaml"

    def __init__(self, config_dir: str = None):
        """
        Initialize settings manager

        Args:
            config_dir: Configuration directory (None for default location)
        """
        if config_dir is None:
            # Default location: ~/.config/CTHarvester (Linux/Mac) or %APPDATA%/CTHarvester (Windows)
            if os.name == 'nt':
                config_dir = os.path.join(os.environ.get('APPDATA', ''), 'CTHarvester')
            else:
                config_dir = os.path.join(os.path.expanduser('~'), '.config', 'CTHarvester')

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILE

        # Create directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load settings
        self.settings = {}
        self.default_settings = self._load_default_settings()
        self.load()

    def _load_default_settings(self) -> Dict:
        """Load default settings from config/settings.yaml"""
        # Look for default settings in config directory
        default_file = Path(__file__).parent.parent / "config" / "settings.yaml"

        if default_file.exists():
            try:
                with open(default_file, 'r', encoding='utf-8') as f:
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
            'application': {
                'language': 'auto',
                'theme': 'light',
                'auto_save_settings': True
            },
            'window': {
                'width': 1200,
                'height': 800,
                'remember_position': True,
                'remember_size': True
            },
            'thumbnails': {
                'max_size': 500,
                'sample_size': 20,
                'max_level': 10,
                'compression': True,
                'format': 'tif'
            },
            'processing': {
                'threads': 'auto',
                'memory_limit_gb': 4,
                'use_rust_module': True
            },
            'rendering': {
                'background_color': [0.2, 0.2, 0.2],
                'default_threshold': 128,
                'anti_aliasing': True,
                'show_fps': False
            },
            'export': {
                'mesh_format': 'stl',
                'image_format': 'tif',
                'compression_level': 6
            },
            'logging': {
                'level': 'INFO',
                'max_file_size_mb': 10,
                'backup_count': 5,
                'console_output': True
            },
            'paths': {
                'last_directory': '',
                'export_directory': ''
            }
        }

    def load(self):
        """Load settings from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.settings = yaml.safe_load(f) or {}
                logger.info(f"Settings loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self.settings = deepcopy(self.default_settings)
        else:
            # Use default settings
            self.settings = deepcopy(self.default_settings)
            self.save()

    def save(self):
        """Save settings to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
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
        keys = key.split('.')
        value = self.settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set setting value (supports dot notation)

        Args:
            key: Setting key (e.g., 'thumbnails.max_size')
            value: Setting value
        """
        keys = key.split('.')
        settings = self.settings

        # Create nested dictionaries
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]

        # Set value
        settings[keys[-1]] = value

    def reset(self):
        """Reset to default settings"""
        self.settings = deepcopy(self.default_settings)
        self.save()
        logger.info("Settings reset to defaults")

    def export(self, file_path: str):
        """
        Export settings to file

        Args:
            file_path: Export file path
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Settings exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            raise

    def import_settings(self, file_path: str):
        """
        Import settings from file

        Args:
            file_path: Import file path
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
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
        required_keys = ['application', 'thumbnails', 'processing']

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