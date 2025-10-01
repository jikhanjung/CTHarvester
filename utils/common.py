"""Common utility functions used across CTHarvester.

This module provides general-purpose utility functions for resource path resolution,
directory creation, and type conversions used throughout the application.

Created during Phase 4 refactoring to centralize common helper functions.

Functions:
    resource_path: Get absolute path to resource (works with PyInstaller)
    value_to_bool: Convert various types to boolean
    ensure_directories: Create multiple directories if they don't exist

Example:
    >>> from utils.common import resource_path, value_to_bool, ensure_directories
    >>> icon_path = resource_path("icons/app_icon.png")
    >>> is_enabled = value_to_bool("True")  # Returns True
    >>> ensure_directories(["/tmp/output", "/tmp/cache"])

Note:
    resource_path() handles both development and PyInstaller frozen environments
    by checking for sys._MEIPASS to support bundled applications.

See Also:
    utils.file_utils: File-specific operations
    utils.settings_manager: Settings persistence
"""

import os
import sys
import warnings


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def value_to_bool(value):
    """Convert string or any value to boolean."""
    return value.lower() == "true" if isinstance(value, str) else bool(value)


def ensure_directories(directories):
    """
    Safely create necessary directories with error handling.

    Args:
        directories: List of directory paths to create
    """
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Use warnings here since logger might not be initialized yet
            warnings.warn(f"Could not create directory {directory}: {e}", RuntimeWarning)
            # Don't fail completely, let the application try to continue
