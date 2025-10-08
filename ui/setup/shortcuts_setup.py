"""
Keyboard shortcuts setup for main window

Wires up keyboard shortcuts from config.shortcuts to main window actions.
Created during Phase 2.2 (UI Polish & Accessibility).
"""

import logging
from typing import TYPE_CHECKING

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut

from config.shortcuts import ShortcutManager

if TYPE_CHECKING:
    from ui.main_window import CTHarvesterMainWindow

logger = logging.getLogger(__name__)


def setup_shortcuts(window: "CTHarvesterMainWindow") -> None:
    """
    Setup all keyboard shortcuts for the main window.

    Args:
        window: Main window instance

    This function connects keyboard shortcuts defined in config.shortcuts
    to their corresponding action methods in the main window.
    """
    shortcuts = ShortcutManager.get_all_shortcuts()
    shortcuts_created = 0

    # Map of shortcut action names to actual window methods
    action_map = {
        # File operations
        "open_directory": window.open_dir,
        "reload_directory": lambda: window.open_dir() if hasattr(window, "ddir") else None,
        "save_cropped": window.save_result,
        "export_mesh": window.export_3d_model,
        "quit": window.close,
        # Thumbnail generation
        "generate_thumbnails": window.create_thumbnail,
        # View controls
        "zoom_in": lambda: _handle_zoom(window, "in"),
        "zoom_out": lambda: _handle_zoom(window, "out"),
        "zoom_fit": lambda: _handle_zoom(window, "fit"),
        "toggle_3d_view": lambda: _toggle_3d_view(window),
        # Navigation
        "next_slice": lambda: _navigate_slice(window, 1),
        "prev_slice": lambda: _navigate_slice(window, -1),
        "first_slice": lambda: _jump_to_slice(window, "first"),
        "last_slice": lambda: _jump_to_slice(window, "last"),
        "jump_forward_10": lambda: _navigate_slice(window, 10),
        "jump_backward_10": lambda: _navigate_slice(window, -10),
        # Crop region
        "set_bottom": window.set_bottom,
        "set_top": window.set_top,
        "reset_crop": window.reset_crop,
        # Threshold adjustment
        "increase_threshold": lambda: _adjust_threshold(window, 1),
        "decrease_threshold": lambda: _adjust_threshold(window, -1),
        # Help
        "show_shortcuts": lambda: _show_shortcuts_dialog(window),
        "show_about": window.show_info,
        # Preferences
        "show_preferences": window.show_advanced_settings,
    }

    for action_name, shortcut in shortcuts.items():
        if action_name not in action_map:
            logger.warning(f"Shortcut action '{action_name}' not found in action_map")
            continue

        action_method = action_map[action_name]
        if action_method is None:
            logger.warning(f"Shortcut action '{action_name}' has no method assigned")
            continue

        try:
            # Create QShortcut
            qs = QShortcut(QKeySequence(shortcut.key), window)
            qs.activated.connect(action_method)
            shortcuts_created += 1
            logger.debug(f"Created shortcut: {shortcut.key} -> {action_name}")
        except Exception as e:
            logger.error(f"Failed to create shortcut for {action_name}: {e}")

    logger.info(f"Setup {shortcuts_created}/{len(shortcuts)} keyboard shortcuts")


# Helper functions for shortcuts


def _handle_zoom(window: "CTHarvesterMainWindow", direction: str) -> None:
    """Handle zoom shortcuts."""
    if not hasattr(window, "objViewer2D"):
        return

    viewer = window.objViewer2D
    # Note: Zoom methods not yet implemented in ObjectViewer2D
    # TODO: Implement zoom_in(), zoom_out(), fit_to_window() in ObjectViewer2D
    if hasattr(viewer, "zoom_in") and direction == "in":
        viewer.zoom_in()
    elif hasattr(viewer, "zoom_out") and direction == "out":
        viewer.zoom_out()
    elif hasattr(viewer, "fit_to_window") and direction == "fit":
        viewer.fit_to_window()
    else:
        logger.debug(f"Zoom {direction} not implemented yet")


def _toggle_3d_view(window: "CTHarvesterMainWindow") -> None:
    """Toggle 3D view visibility."""
    if not hasattr(window, "mcubeWidget"):
        return

    widget = window.mcubeWidget
    widget.setVisible(not widget.isVisible())


def _navigate_slice(window: "CTHarvesterMainWindow", delta: int) -> None:
    """Navigate slices by delta."""
    if not hasattr(window, "slider2"):
        return

    slider = window.slider2
    new_value = slider.value() + delta
    # Clamp to valid range
    new_value = max(slider.minimum(), min(slider.maximum(), new_value))
    slider.setValue(new_value)


def _jump_to_slice(window: "CTHarvesterMainWindow", position: str) -> None:
    """Jump to first or last slice."""
    if not hasattr(window, "slider2"):
        return

    slider = window.slider2
    if position == "first":
        slider.setValue(slider.minimum())
    elif position == "last":
        slider.setValue(slider.maximum())


def _adjust_threshold(window: "CTHarvesterMainWindow", delta: int) -> None:
    """Adjust threshold by delta."""
    if not hasattr(window, "slider"):
        return

    slider = window.slider
    new_value = slider.value() + delta
    # Clamp to valid range
    new_value = max(slider.minimum(), min(slider.maximum(), new_value))
    slider.setValue(new_value)


def _show_shortcuts_dialog(window: "CTHarvesterMainWindow") -> None:
    """Show keyboard shortcuts help dialog."""
    try:
        from ui.dialogs.shortcut_dialog import ShortcutDialog

        dialog = ShortcutDialog(window)
        dialog.exec_()
    except Exception as e:
        logger.error(f"Failed to show shortcuts dialog: {e}")
