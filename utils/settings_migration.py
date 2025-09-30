"""
Settings migration utility

Migrates settings from QSettings to YAML-based SettingsManager.
One-time migration for backward compatibility.

Created during Phase 2 settings management improvements.
"""
import logging
from PyQt5.QtCore import QSettings

from utils.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


def migrate_qsettings_to_yaml(qsettings: QSettings, settings_manager: SettingsManager) -> bool:
    """
    Migrate settings from QSettings to YAML

    Args:
        qsettings: QSettings instance
        settings_manager: SettingsManager instance

    Returns:
        True if migration was performed, False if skipped
    """
    # Check if migration already done
    if settings_manager.get('_migration.qsettings_migrated', False):
        logger.debug("QSettings migration already completed, skipping")
        return False

    logger.info("Starting QSettings to YAML migration")
    migrated_count = 0

    # Map QSettings keys to YAML paths
    migration_map = {
        # Old QSettings key -> New YAML path
        'Remember geometry': 'window.remember_position',
        'Remember directory': 'window.remember_size',  # Note: slightly different meaning
        'Language': 'application.language',
        'Log Level': 'logging.level',
        'Use Rust Thumbnail': 'processing.use_rust_module',
    }

    for qsettings_key, yaml_path in migration_map.items():
        if qsettings.contains(qsettings_key):
            value = qsettings.value(qsettings_key)

            # Type conversion
            if qsettings_key in ['Remember geometry', 'Remember directory', 'Use Rust Thumbnail']:
                # Convert to boolean
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes')
                else:
                    value = bool(value)

            settings_manager.set(yaml_path, value)
            migrated_count += 1
            logger.info(f"Migrated: {qsettings_key} -> {yaml_path} = {value}")

    if migrated_count > 0:
        # Mark migration as complete
        settings_manager.set('_migration.qsettings_migrated', True)
        settings_manager.set('_migration.migrated_at', __import__('datetime').datetime.now().isoformat())
        settings_manager.save()
        logger.info(f"Migration complete: {migrated_count} settings migrated")
        return True
    else:
        logger.info("No QSettings found to migrate")
        # Still mark as migrated to avoid checking again
        settings_manager.set('_migration.qsettings_migrated', True)
        settings_manager.save()
        return False


def should_use_yaml_settings() -> bool:
    """
    Check if we should use YAML settings

    Returns:
        True if YAML settings file exists or migration is complete
    """
    from pathlib import Path
    import os

    # Determine config directory
    if os.name == 'nt':
        config_dir = Path(os.environ.get('APPDATA', '')) / 'CTHarvester'
    else:
        config_dir = Path.home() / '.config' / 'CTHarvester'

    settings_file = config_dir / 'settings.yaml'
    return settings_file.exists()