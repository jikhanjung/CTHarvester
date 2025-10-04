"""UI utility functions for CTHarvester.

This module provides common UI-related helper functions and context managers
for PyQt5-based applications.

Created during Phase 1 of quality improvement plan (devlog 072).
"""

import logging
from contextlib import contextmanager
from typing import Callable, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)


@contextmanager
def wait_cursor():
    """Context manager for safe cursor override to wait cursor.

    This ensures the cursor is always restored even if an exception occurs
    during the operation. This prevents the common bug where the wait cursor
    gets stuck if an exception is raised.

    Usage:
        >>> from utils.ui_utils import wait_cursor
        >>> with wait_cursor():
        ...     # Long-running operation
        ...     process_large_dataset()

    Example with exception handling:
        >>> try:
        ...     with wait_cursor():
        ...         risky_operation()
        ... except Exception as e:
        ...     logger.error(f"Operation failed: {e}")
        ...     # Cursor is automatically restored even on error

    Yields:
        None

    Note:
        The cursor will be restored in the finally block, guaranteeing
        cleanup even if the code block raises an exception.
    """
    QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore[attr-defined]
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


@contextmanager
def override_cursor(cursor=Qt.WaitCursor):  # type: ignore[attr-defined]
    """Context manager for safe cursor override to any cursor shape.

    More flexible version of wait_cursor() that allows specifying
    any cursor shape.

    Args:
        cursor: Qt cursor shape (default: Qt.WaitCursor)

    Usage:
        >>> from utils.ui_utils import override_cursor
        >>> from PyQt5.QtCore import Qt
        >>> with override_cursor(Qt.CrossCursor):
        ...     # Operation with cross cursor
        ...     select_region()

    Yields:
        None
    """
    QApplication.setOverrideCursor(cursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def safe_disconnect(signal, slot: Optional[Callable] = None):
    """Safely disconnect a signal from a slot.

    Handles the case where the signal might not be connected,
    preventing exceptions.

    Args:
        signal: PyQt signal to disconnect
        slot: Slot to disconnect (if None, disconnects all)

    Example:
        >>> safe_disconnect(button.clicked, on_button_clicked)
        >>> safe_disconnect(button.clicked)  # Disconnect all
    """
    try:
        if slot is None:
            signal.disconnect()
        else:
            signal.disconnect(slot)
    except (TypeError, RuntimeError) as e:
        # Signal was not connected, which is fine
        logger.debug(f"Signal disconnect: {e}")
        pass
