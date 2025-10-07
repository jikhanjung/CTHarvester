"""Log helper utilities for CTHarvester.

Provides functions to access and manage log files from the application.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional


def get_log_directory() -> Path:
    """Get the log directory path for CTHarvester.

    Returns:
        Path: Path to the log directory

    The log directory location depends on the platform:
    - Windows: ~/PaleoBytes/CTHarvester/logs
    - Linux/Mac: ~/PaleoBytes/CTHarvester/logs
    """
    user_profile = os.path.expanduser("~")
    log_dir = Path(user_profile) / "PaleoBytes" / "CTHarvester" / "logs"
    return log_dir


def get_log_file_path() -> Optional[Path]:
    """Get the path to the main log file.

    Returns:
        Optional[Path]: Path to the log file, or None if it doesn't exist
    """
    log_dir = get_log_directory()
    log_file = log_dir / "CTHarvester.log"

    if log_file.exists():
        return log_file
    return None


def open_log_directory():
    """Open the log directory in the system file explorer.

    Opens the directory using the platform's default file manager:
    - Windows: Explorer
    - macOS: Finder
    - Linux: xdg-open
    """
    log_dir = get_log_directory()

    # Create directory if it doesn't exist
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    system = platform.system()

    try:
        if system == "Windows":
            os.startfile(str(log_dir))  # type: ignore[attr-defined]
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(log_dir)], check=True)
        else:  # Linux and other Unix-like
            subprocess.run(["xdg-open", str(log_dir)], check=True)
    except Exception as e:
        raise RuntimeError(f"Failed to open log directory: {e}")


def get_recent_log_lines(num_lines: int = 100) -> list[str]:
    """Get the most recent lines from the log file.

    Args:
        num_lines: Number of lines to retrieve (default: 100)

    Returns:
        list[str]: List of log lines, or empty list if log doesn't exist
    """
    log_file = get_log_file_path()

    if not log_file or not log_file.exists():
        return []

    try:
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
            return lines[-num_lines:]
    except Exception:
        return []


def get_log_file_size() -> int:
    """Get the size of the main log file in bytes.

    Returns:
        int: Size in bytes, or 0 if log doesn't exist
    """
    log_file = get_log_file_path()

    if not log_file or not log_file.exists():
        return 0

    return log_file.stat().st_size


def get_all_log_files() -> list[Path]:
    """Get all log files (including rotated backups).

    Returns:
        list[Path]: List of log file paths, sorted by modification time (newest first)
    """
    log_dir = get_log_directory()

    if not log_dir.exists():
        return []

    log_files = list(log_dir.glob("CTHarvester.log*"))
    log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return log_files
