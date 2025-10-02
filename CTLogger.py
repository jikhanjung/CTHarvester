"""
CTHarvester Logger Module
Provides centralized logging functionality for the CTHarvester application
"""

import logging
import os
from datetime import datetime


def setup_logger(name, log_dir=None, level=logging.INFO, console_level=None):
    """
    Set up a logger with file handler for CTHarvester

    Supports environment variables for dynamic configuration:
    - CTHARVESTER_LOG_LEVEL: File log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - CTHARVESTER_CONSOLE_LEVEL: Console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - CTHARVESTER_LOG_DIR: Custom log directory path

    Args:
        name: Logger name (typically PROGRAM_NAME)
        log_dir: Directory for log files (optional, uses environment or default)
        level: File logging level (default: INFO, can be overridden by env var)
        console_level: Console logging level (default: same as level, can be overridden by env var)

    Returns:
        Configured logger instance

    Example:
        # Default usage
        logger = setup_logger('CTHarvester')

        # With environment variables
        # export CTHARVESTER_LOG_LEVEL=DEBUG
        # export CTHARVESTER_CONSOLE_LEVEL=WARNING
        logger = setup_logger('CTHarvester')
    """
    # Read log level from environment variable
    env_level = os.getenv("CTHARVESTER_LOG_LEVEL")
    if env_level:
        try:
            level = getattr(logging, env_level.upper())
        except AttributeError:
            print(f"Warning: Invalid log level '{env_level}', using default")

    # Read console level from environment variable
    env_console_level = os.getenv("CTHARVESTER_CONSOLE_LEVEL")
    if env_console_level:
        try:
            console_level = getattr(logging, env_console_level.upper())
        except AttributeError:
            print(f"Warning: Invalid console level '{env_console_level}', using default")
    elif console_level is None:
        console_level = level

    # Read log directory from environment variable
    env_log_dir = os.getenv("CTHARVESTER_LOG_DIR")
    if env_log_dir:
        log_dir = env_log_dir
    elif log_dir is None:
        user_profile = os.path.expanduser("~")
        log_dir = os.path.join(user_profile, "PaleoBytes", name.replace(" ", "_"), "logs")

    # Ensure log directory exists
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create log directory {log_dir}: {e}")
            # Fall back to current directory
            log_dir = "."

    # Create log filename with date
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    logfile_path = os.path.join(log_dir, f"{name.replace(' ', '_')}.{date_str}.log")

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create file handler
    try:
        handler = logging.FileHandler(logfile_path, encoding="utf-8")
        handler.setFormatter(formatter)
        handler.setLevel(level)
    except Exception as e:
        print(f"Warning: Could not create log file {logfile_path}: {e}")
        # Fall back to console handler
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.setLevel(level)

    # Get or create logger
    logger = logging.getLogger(name)

    # Clear any existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(min(level, console_level))  # Set to the lower level
    logger.addHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
