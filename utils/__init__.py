"""Utility modules for common operations across CTHarvester.

This package provides reusable utility functions and classes for file operations,
image processing, worker threads, progress tracking, and application settings.

Created during Phase 4 refactoring to consolidate common functionality.

Modules:
    common: General utility functions (resource paths, directory creation)
    file_utils: File system operations (finding images, parsing filenames)
    image_utils: Image processing utilities (loading, resizing, thumbnail generation)
    worker: Generic worker thread base class for background operations
    settings_manager: YAML-based settings management

Key Features:
    - Cross-platform resource path resolution
    - Natural sorting for image sequences
    - Memory-efficient image loading
    - Background worker thread execution
    - Persistent YAML-based configuration

Example:
    >>> from utils.common import resource_path, ensure_directories
    >>> from utils.file_utils import find_image_files, parse_filename
    >>> from utils.image_utils import load_image_safe, resize_image
    >>> from utils.worker import Worker
    >>> from utils.settings_manager import SettingsManager
    >>>
    >>> # Find images in directory
    >>> images = find_image_files("/path/to/images")
    >>>
    >>> # Load and process image
    >>> img = load_image_safe(images[0])
    >>> resized = resize_image(img, (256, 256))
    >>>
    >>> # Manage settings
    >>> settings = SettingsManager()
    >>> value = settings.get('key', default='default_value')

Note:
    Many utilities handle edge cases and errors gracefully, logging issues
    rather than raising exceptions to allow the application to continue.

See Also:
    utils.common: Core utility functions
    utils.file_utils: File system operations
    utils.image_utils: Image processing
    utils.worker: Background thread execution
    utils.settings_manager: Configuration management
"""
