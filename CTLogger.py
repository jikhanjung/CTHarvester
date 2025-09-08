"""
CTHarvester Logger Module
Provides centralized logging functionality for the CTHarvester application
"""

import logging
import os
from datetime import datetime


def setup_logger(name, log_dir=None, level=logging.INFO):
    """
    Set up a logger with file handler for CTHarvester
    
    Args:
        name: Logger name (typically PROGRAM_NAME)
        log_dir: Directory for log files (optional, uses DEFAULT_LOG_DIRECTORY if None)
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    # Default log directory if not provided
    if log_dir is None:
        user_profile = os.path.expanduser('~')
        # Use the name parameter to create log directory
        log_dir = os.path.join(user_profile, "PaleoBytes", name.replace(' ', '_'), "logs")
    
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
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create file handler
    try:
        handler = logging.FileHandler(logfile_path, encoding='utf-8')
        handler.setFormatter(formatter)
    except Exception as e:
        print(f"Warning: Could not create log file {logfile_path}: {e}")
        # Fall back to console handler
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
    
    # Get or create logger
    logger = logging.getLogger(name)
    
    # Clear any existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    logger.setLevel(level)
    logger.addHandler(handler)
    
    # Also add console handler for errors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger