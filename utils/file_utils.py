"""File system utility functions for image file operations.

This module provides utilities for finding, parsing, and organizing image files
in CT scan directories. It handles file name parsing, natural sorting, thumbnail
directory management, and file size calculations.

Created during Phase 4 refactoring to consolidate file operation utilities.

Functions:
    find_image_files: Find image files in directory with extension filtering
    parse_filename: Extract prefix, number, and extension from filename
    create_thumbnail_directory: Create thumbnail subdirectories
    get_thumbnail_path: Generate thumbnail file path for given level
    clean_old_thumbnails: Remove old thumbnail directories
    get_directory_size: Calculate total size of directory

Example:
    >>> from utils.file_utils import find_image_files, parse_filename
    >>> images = find_image_files("/path/to/ct/scans", extensions=[".tif", ".tiff"])
    >>> for img in images:
    ...     prefix, num, ext = parse_filename(img)
    ...     print(f"Image {num}: {prefix}{num:06}{ext}")

Note:
    These utilities use SecureFileValidator for safe file operations and
    handle edge cases like missing directories or permission errors gracefully.

See Also:
    security.file_validator: Secure file validation and operations
    utils.image_utils: Image processing utilities
"""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def find_image_files(directory: str, extensions: tuple[str, ...] | None = None) -> list[str]:
    """
    Find image files in a directory (non-recursively)

    Args:
        directory: Search directory
        extensions: Allowed extensions (None for default)

    Returns:
        List of filenames (sorted)

    Note:
        There used to be a ``recursive`` parameter here, documented as "include
        subdirectories" and never implemented -- both code paths below list one
        directory. Passing ``recursive=True`` silently returned the same
        non-recursive result. Removed rather than implemented: no caller wanted
        it, and a TypeError is a better answer than a quietly wrong one. A CT
        image stack is a flat directory by construction.
    """
    from config.constants import SUPPORTED_IMAGE_EXTENSIONS

    if extensions is None:
        extensions = SUPPORTED_IMAGE_EXTENSIONS

    try:
        # Use secure file validator if available
        try:
            from security.file_validator import SecureFileValidator

            file_list = SecureFileValidator.secure_listdir(directory, extensions=set(extensions))
            return sorted(file_list)
        except ImportError:
            # Fallback to os.listdir
            files = []
            for entry in Path(directory).iterdir():
                if entry.suffix.lower() in extensions:
                    files.append(entry.name)
            return sorted(files)

    except Exception:
        logger.exception(f"Failed to list directory {directory}")
        return []


def parse_filename(filename: str, pattern: str | None = None) -> tuple[str, int, str] | None:
    """
    Parse filename (prefix, number, extension)

    Args:
        filename: Filename
        pattern: Regex pattern (None for default)

    Returns:
        (prefix, number, extension) or None

    Example:
        "scan_00123.tif" -> ("scan_", 123, "tif")
    """
    if pattern is None:
        # Default pattern: prefix + digits + extension
        pattern = r"^(.+?)(\d+)\.([a-zA-Z]+)$"

    match = re.match(pattern, filename)
    if match:
        prefix, number_str, ext = match.groups()
        try:
            number = int(number_str)
        except ValueError:
            logger.warning(f"Cannot parse number in filename: {filename}")
            return None
        else:
            return (prefix, number, ext)
    else:
        return None


def create_thumbnail_directory(base_dir: str, level: int = 1) -> str:
    """
    Create thumbnail directory

    Args:
        base_dir: Base directory
        level: Pyramid level

    Returns:
        Created directory path

    Raises:
        OSError: Directory creation failed
    """
    from config.constants import THUMBNAIL_DIR_NAME

    thumb_path = Path(base_dir) / THUMBNAIL_DIR_NAME
    if level != 1:
        thumb_path = thumb_path / str(level)
    thumb_dir = str(thumb_path)

    try:
        thumb_path.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("Failed to create thumbnail directory")
        raise
    else:
        logger.info(f"Created thumbnail directory: {thumb_dir}")
        return thumb_dir


def get_thumbnail_path(base_dir: str, level: int, index: int) -> str:
    """
    Generate thumbnail file path

    Args:
        base_dir: Base directory
        level: Pyramid level
        index: Index

    Returns:
        Thumbnail file path
    """
    from config.constants import THUMBNAIL_DIR_NAME, THUMBNAIL_EXTENSION

    thumb_dir = Path(base_dir) / THUMBNAIL_DIR_NAME
    if level != 1:
        thumb_dir = thumb_dir / str(level)

    filename = f"{index:06d}{THUMBNAIL_EXTENSION}"
    return str(thumb_dir / filename)


def clean_old_thumbnails(base_dir: str) -> bool:
    """
    Remove old thumbnail directory

    Args:
        base_dir: Base directory

    Returns:
        Success flag
    """
    import shutil

    from config.constants import THUMBNAIL_DIR_NAME

    thumb_dir = Path(base_dir) / THUMBNAIL_DIR_NAME

    if thumb_dir.exists():
        try:
            shutil.rmtree(thumb_dir)
        except Exception:
            logger.exception("Failed to remove thumbnail directory")
            return False
        else:
            logger.info(f"Removed old thumbnail directory: {thumb_dir}")
            return True
    return True


def get_directory_size(directory: str) -> int:
    """
    Calculate total directory size

    Args:
        directory: Directory path

    Returns:
        Size in bytes
    """
    total_size = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                if filepath.exists():
                    total_size += filepath.stat().st_size
    except Exception:
        logger.exception("Failed to calculate directory size")

    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size to human-readable string

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    size_value: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_value < 1024.0:
            return f"{size_value:.2f} {unit}"
        size_value /= 1024.0
    return f"{size_value:.2f} PB"
