"""
Common utility functions

Centralized helper functions used across the application.
"""
import sys
import os


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def value_to_bool(value):
    """Convert string or any value to boolean."""
    return value.lower() == 'true' if isinstance(value, str) else bool(value)


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
            # Use print here since logger might not be initialized yet
            print(f"Warning: Could not create directory {directory}: {e}")
            # Don't fail completely, let the application try to continue