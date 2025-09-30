"""
CTHarvester Global Constants
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
USER_PROFILE_DIRECTORY = os.path.expanduser('~')
DEFAULT_DB_DIRECTORY = os.path.join(USER_PROFILE_DIRECTORY, COMPANY_NAME, PROGRAM_NAME)
DEFAULT_STORAGE_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "data/")
DEFAULT_LOG_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "logs/")
DB_BACKUP_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "backups/")

# File Extensions
SUPPORTED_IMAGE_EXTENSIONS = ('.bmp', '.jpg', '.jpeg', '.png', '.tif', '.tiff')
SUPPORTED_EXPORT_FORMATS = ('.stl', '.ply', '.obj')
THUMBNAIL_DIR_NAME = ".thumbnail"
THUMBNAIL_EXTENSION = ".tif"

# Thumbnail Generation Parameters
DEFAULT_THUMBNAIL_MAX_SIZE = 500
DEFAULT_SAMPLE_SIZE = 20
DEFAULT_MAX_LEVEL = 10

# Thread Settings
MIN_THREADS = 1
MAX_THREADS = 8
DEFAULT_THREADS = 1  # Single thread optimal for Python fallback

# Memory Settings
MEMORY_THRESHOLD_MB = 4096
IMAGE_MEMORY_ESTIMATE_MB = 50  # Estimated memory per image

# UI Settings
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
PROGRESS_UPDATE_INTERVAL_MS = 100

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