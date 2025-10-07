"""
CTHarvester Logger Module
Provides centralized logging functionality for the CTHarvester application

Features:
- Automatic log file rotation (max 5 files, 10MB each)
- Configurable log levels via environment variables
- Session ID tracking for debugging
- Separate file and console log levels
"""

import logging
import os
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(name, log_dir=None, level=logging.INFO, console_level=None, session_id=None):
    """
    Set up a logger with rotating file handler for CTHarvester

    Features:
    - Automatic log rotation: max 5 files, 10MB each (50MB total)
    - Session ID tracking for debugging multi-session issues
    - Separate file and console log levels
    - Configurable via environment variables

    Supports environment variables for dynamic configuration:
    - CTHARVESTER_LOG_LEVEL: File log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - CTHARVESTER_CONSOLE_LEVEL: Console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - CTHARVESTER_LOG_DIR: Custom log directory path

    Args:
        name: Logger name (typically PROGRAM_NAME)
        log_dir: Directory for log files (optional, uses environment or default)
        level: File logging level (default: INFO, can be overridden by env var)
        console_level: Console logging level (default: same as level, can be overridden by env var)
        session_id: Unique session ID (auto-generated if not provided)

    Returns:
        tuple: (logger, session_id) - Configured logger instance and session ID

    Example:
        # Default usage
        logger, session_id = setup_logger('CTHarvester')
        logger.info(f"Session started: {session_id}")

        # With environment variables
        # export CTHARVESTER_LOG_LEVEL=DEBUG
        # export CTHARVESTER_CONSOLE_LEVEL=WARNING
        logger, session_id = setup_logger('CTHarvester')
    """
    # Generate or use provided session ID
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]  # Short session ID for readability

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

    # Create log filename (single rotating log file)
    logfile_path = os.path.join(log_dir, f"{name.replace(' ', '_')}.log")

    # Create formatter with session ID
    formatter = logging.Formatter(
        f"%(asctime)s - [%(name)s] - [Session:{session_id}] - %(levelname)s - %(message)s"
    )

    # Create rotating file handler (max 5 files, 10MB each = 50MB total)
    try:
        handler = RotatingFileHandler(
            logfile_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # Keep 5 backup files
            encoding="utf-8",
        )
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

    # Log startup information
    logger.info(f"=== CTHarvester Session Started ===")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Log directory: {log_dir}")
    logger.info(f"Log level: {logging.getLevelName(level)}")
    logger.info(f"Console level: {logging.getLevelName(console_level)}")

    return logger, session_id
