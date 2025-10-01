"""
Utility functions for UI testing

Helper functions to simplify common Qt testing patterns.
"""

from PyQt5.QtCore import QPoint, Qt


def simulate_mouse_drag(qtbot, widget, start_pos, end_pos, button=Qt.LeftButton):
    """
    Simulate mouse drag from start to end position.

    Args:
        qtbot: pytest-qt fixture
        widget: QWidget to interact with
        start_pos: QPoint or tuple (x, y) for start position
        end_pos: QPoint or tuple (x, y) for end position
        button: Mouse button to use (default: Qt.LeftButton)
    """
    if isinstance(start_pos, tuple):
        start_pos = QPoint(*start_pos)
    if isinstance(end_pos, tuple):
        end_pos = QPoint(*end_pos)

    qtbot.mousePress(widget, button, pos=start_pos)
    qtbot.mouseMove(widget, pos=end_pos)
    qtbot.mouseRelease(widget, button, pos=end_pos)


def wait_for_signal_or_timeout(qtbot, signal, timeout=1000):
    """
    Wait for signal with timeout, return whether it was emitted.

    Args:
        qtbot: pytest-qt fixture
        signal: Qt signal to wait for
        timeout: Timeout in milliseconds (default: 1000)

    Returns:
        bool: True if signal was emitted, False if timeout
    """
    try:
        with qtbot.waitSignal(signal, timeout=timeout):
            pass
        return True
    except Exception:
        return False


def get_widget_center(widget):
    """
    Get center point of widget.

    Args:
        widget: QWidget

    Returns:
        QPoint: Center point of the widget
    """
    rect = widget.rect()
    return QPoint(rect.width() // 2, rect.height() // 2)


def get_widget_position(widget, x_frac=0.5, y_frac=0.5):
    """
    Get position within widget based on fractional coordinates.

    Args:
        widget: QWidget
        x_frac: X position as fraction of width (0.0 to 1.0)
        y_frac: Y position as fraction of height (0.0 to 1.0)

    Returns:
        QPoint: Position within the widget

    Example:
        >>> pos = get_widget_position(widget, 0.25, 0.75)  # 25% from left, 75% from top
    """
    rect = widget.rect()
    x = int(rect.width() * x_frac)
    y = int(rect.height() * y_frac)
    return QPoint(x, y)


def simulate_key_sequence(qtbot, widget, keys):
    """
    Simulate sequence of key presses.

    Args:
        qtbot: pytest-qt fixture
        widget: QWidget to send keys to
        keys: List of Qt.Key_* constants or single key

    Example:
        >>> simulate_key_sequence(qtbot, widget, [Qt.Key_Down, Qt.Key_Down, Qt.Key_Enter])
    """
    if not isinstance(keys, list):
        keys = [keys]

    for key in keys:
        qtbot.keyClick(widget, key)


def wait_for_widget_painted(qtbot, widget, timeout=1000):
    """
    Wait for widget to be painted (visible and ready).

    Args:
        qtbot: pytest-qt fixture
        widget: QWidget
        timeout: Timeout in milliseconds

    Returns:
        bool: True if widget was painted, False if timeout
    """
    import time

    start_time = time.time()
    while not widget.isVisible() or widget.visibleRegion().isEmpty():
        qtbot.wait(10)
        if (time.time() - start_time) * 1000 > timeout:
            return False
    return True


def get_signal_blocker(widget):
    """
    Context manager to temporarily block signals from widget.

    Args:
        widget: QWidget or QObject

    Returns:
        Context manager that blocks signals

    Example:
        >>> with get_signal_blocker(widget):
        ...     widget.setValue(100)  # No signals emitted
    """
    from PyQt5.QtCore import QSignalBlocker

    return QSignalBlocker(widget)


def compare_colors(color1, color2, tolerance=5):
    """
    Compare two QColor objects with tolerance.

    Args:
        color1: QColor
        color2: QColor
        tolerance: Maximum difference per channel (default: 5)

    Returns:
        bool: True if colors are similar within tolerance
    """
    return (
        abs(color1.red() - color2.red()) <= tolerance
        and abs(color1.green() - color2.green()) <= tolerance
        and abs(color1.blue() - color2.blue()) <= tolerance
    )


def find_child_widget(parent, widget_type, object_name=None):
    """
    Find child widget by type and optional object name.

    Args:
        parent: Parent QWidget
        widget_type: Widget class type
        object_name: Optional object name to match

    Returns:
        QWidget or None: Found widget or None
    """
    children = parent.findChildren(widget_type)

    if object_name is None:
        return children[0] if children else None

    for child in children:
        if child.objectName() == object_name:
            return child

    return None


def simulate_wheel_scroll(qtbot, widget, delta, modifiers=Qt.NoModifier, pos=None):
    """
    Simulate mouse wheel scroll.

    Args:
        qtbot: pytest-qt fixture
        widget: QWidget
        delta: Scroll delta (positive = up, negative = down)
        modifiers: Keyboard modifiers (default: Qt.NoModifier)
        pos: Position to scroll at (default: widget center)
    """
    from PyQt5.QtCore import QCoreApplication, QPoint
    from PyQt5.QtGui import QWheelEvent

    if pos is None:
        pos = get_widget_center(widget)

    # Create wheel event
    event = QWheelEvent(
        pos,  # pos
        widget.mapToGlobal(pos),  # globalPos
        QPoint(0, 0),  # pixelDelta
        QPoint(0, delta),  # angleDelta
        delta,  # delta (deprecated but still used)
        Qt.Vertical,  # orientation
        Qt.LeftButton,  # buttons
        modifiers,  # modifiers
    )

    # Send event directly to widget
    QCoreApplication.sendEvent(widget, event)
