"""Global application constants for CTHarvester.

This module defines application-wide constants including metadata, default values,
paths, and configuration settings used throughout CTHarvester.

Created during Phase 4 refactoring to centralize constant definitions.

Constants:
    APP_NAME: Application name ("CTHarvester")
    APP_ORGANIZATION: Organization name ("PaleoBytes")
    PROGRAM_VERSION: Current version from version.py
    DEFAULT_THUMBNAIL_LEVELS: Number of thumbnail levels to generate
    MAX_IMAGE_DIMENSION: Maximum allowed image dimension
    SUPPORTED_IMAGE_FORMATS: List of supported image file extensions

Example:
    >>> from config.constants import APP_NAME, DEFAULT_THUMBNAIL_LEVELS
    >>> print(f"{APP_NAME} - Levels: {DEFAULT_THUMBNAIL_LEVELS}")

Note:
    These constants should be treated as read-only. Modifying them at runtime
    may lead to inconsistent application behavior.
"""

import logging
import os

# Application Information
APP_NAME = "CTHarvester"
APP_ORGANIZATION = "PaleoBytes"
COMPANY_NAME = "PaleoBytes"
PROGRAM_AUTHOR = "Jikhan Jung"

# Version (imported from version.py)
try:
    from version import __version__, __version_info__
except ImportError:
    __version__ = "0.2.3"
    __version_info__ = (0, 2, 3)

PROGRAM_NAME = APP_NAME
PROGRAM_VERSION = __version__

# Build-time year for copyright
BUILD_YEAR = 2025
PROGRAM_COPYRIGHT = f"© 2023-{BUILD_YEAR} Jikhan Jung"

# Directory setup
USER_PROFILE_DIRECTORY = os.path.expanduser("~")
DEFAULT_DB_DIRECTORY = os.path.join(USER_PROFILE_DIRECTORY, COMPANY_NAME, PROGRAM_NAME)
DEFAULT_STORAGE_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "data/")
DEFAULT_LOG_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "logs/")
DB_BACKUP_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "backups/")

# File Extensions
SUPPORTED_IMAGE_EXTENSIONS = (".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff")
SUPPORTED_EXPORT_FORMATS = (".stl", ".ply", ".obj")
THUMBNAIL_DIR_NAME = ".thumbnail"
THUMBNAIL_EXTENSION = ".tif"

# Thumbnail Generation Parameters
DEFAULT_THUMBNAIL_MAX_SIZE = 500
MAX_THUMBNAIL_SIZE = 512  # Maximum size for thumbnail in memory
DEFAULT_SAMPLE_SIZE = 20
MIN_SAMPLE_SIZE = 1
MAX_SAMPLE_SIZE = 100
DEFAULT_ADAPTIVE_SAMPLE_MIN = 20
DEFAULT_ADAPTIVE_SAMPLE_MAX = 30
ADAPTIVE_SAMPLE_RATIO = 0.02  # 2% of total work
DEFAULT_MAX_LEVEL = 10
MAX_THUMBNAIL_LEVELS = 20  # Maximum levels to check when loading
BIT_DEPTH_16_TO_8_DIVISOR = 256  # Division factor for 16-bit to 8-bit conversion

# Thread Settings
MIN_THREADS = 1
MAX_THREADS = 8
DEFAULT_THREADS = 1  # Single thread optimal for Python fallback
GARBAGE_COLLECTION_INTERVAL = 10  # Collect garbage every N items

# Performance Monitoring
STALL_DETECTION_THRESHOLD = 12  # Number of 5-second checks before stall warning (60 seconds)
STALL_CHECK_INTERVAL_MS = 5000  # Check for stalls every 5 seconds
SLOW_IMAGE_THRESHOLD_MS = 1000  # Warn if image load takes over 1 second
FAST_PROCESSING_THRESHOLD = 10  # Images per second threshold for "fast" processing

# Memory Settings
MEMORY_THRESHOLD_MB = 4096
IMAGE_MEMORY_ESTIMATE_MB = 50  # Estimated memory per image

# UI Settings
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
PREVIEW_WIDTH = 512  # Width for image preview scaling
THUMBNAIL_ICON_SIZE = 128  # Size for thumbnail icons
PROGRESS_UPDATE_INTERVAL_MS = 100
THREAD_SLEEP_MS = 10  # Sleep duration for worker threads
PROGRESS_UPDATE_STEP_INTERVAL = 10  # Update UI every N steps

# Progress Reporting
PROGRESS_LOG_INTERVAL = 10  # Log progress every N items
PROGRESS_LOG_INITIAL = 5  # Log first N items
PROGRESS_PERCENTAGE_MULTIPLIER = 100

# Time Display
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
MINUTES_PER_HOUR = 60

# 3D Rendering
DEFAULT_THRESHOLD = 128
DEFAULT_ISO_VALUE = 127.5
DEFAULT_BACKGROUND_COLOR = (0.2, 0.2, 0.2)

# Logging
LOG_DIR_NAME = "logs"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
DEFAULT_LOG_LEVEL = logging.INFO

# Environment Variables
ENV_LOG_LEVEL = "CTHARVESTER_LOG_LEVEL"
ENV_CONSOLE_LEVEL = "CTHARVESTER_CONSOLE_LEVEL"
ENV_LOG_DIR = "CTHARVESTER_LOG_DIR"
