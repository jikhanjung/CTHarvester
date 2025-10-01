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
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def find_image_files(
    directory: str, extensions: Optional[tuple] = None, recursive: bool = False
) -> List[str]:
    """
    Find image files in directory

    Args:
        directory: Search directory
        extensions: Allowed extensions (None for default)
        recursive: Include subdirectories

    Returns:
        List of filenames (sorted)
    """
    from config.constants import SUPPORTED_IMAGE_EXTENSIONS

    if extensions is None:
        extensions = SUPPORTED_IMAGE_EXTENSIONS

    try:
        # Use secure file validator if available
        try:
            from security.file_validator import FileSecurityError, SecureFileValidator

            file_list = SecureFileValidator.secure_listdir(directory, extensions=set(extensions))
            return sorted(file_list)
        except ImportError:
            # Fallback to os.listdir
            files = []
            for filename in os.listdir(directory):
                if os.path.splitext(filename)[1].lower() in extensions:
                    files.append(filename)
            return sorted(files)

    except Exception as e:
        logger.error(f"Failed to list directory {directory}: {e}")
        return []


def parse_filename(filename: str, pattern: Optional[str] = None) -> Optional[Tuple[str, int, str]]:
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
            return (prefix, number, ext)
        except ValueError:
            logger.warning(f"Cannot parse number in filename: {filename}")
            return None
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

    if level == 1:
        thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME)
    else:
        thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME, str(level))

    try:
        os.makedirs(thumb_dir, exist_ok=True)
        logger.info(f"Created thumbnail directory: {thumb_dir}")
        return thumb_dir
    except OSError as e:
        logger.error(f"Failed to create thumbnail directory: {e}")
        raise


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

    if level == 1:
        thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME)
    else:
        thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME, str(level))

    filename = f"{index:06d}{THUMBNAIL_EXTENSION}"
    return os.path.join(thumb_dir, filename)


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

    thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME)

    if os.path.exists(thumb_dir):
        try:
            shutil.rmtree(thumb_dir)
            logger.info(f"Removed old thumbnail directory: {thumb_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove thumbnail directory: {e}")
            return False
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
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"Failed to calculate directory size: {e}")

    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size to human-readable string

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
