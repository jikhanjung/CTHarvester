"""
Keyboard shortcuts configuration

Centralized keyboard shortcut definitions for the application.
Created during Phase 1.5 UI/UX improvements.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Shortcut:
    """Keyboard shortcut definition"""

    key: str  # Qt key sequence (e.g., 'Ctrl+O')
    description: str  # User-visible description
    action: str  # Action name (method name)


class ShortcutManager:
    """Centralized keyboard shortcut manager"""

    SHORTCUTS: Dict[str, Shortcut] = {
        # File operations
        "open_directory": Shortcut(
            key="Ctrl+O", description="Open directory", action="open_directory"
        ),
        "reload_directory": Shortcut(
            key="F5", description="Reload current directory", action="reload_directory"
        ),
        "save_cropped": Shortcut(
            key="Ctrl+S", description="Save cropped images", action="save_cropped"
        ),
        "export_mesh": Shortcut(key="Ctrl+E", description="Export 3D mesh", action="export_mesh"),
        "quit": Shortcut(key="Ctrl+Q", description="Quit application", action="quit"),
        # Thumbnail generation
        "generate_thumbnails": Shortcut(
            key="Ctrl+T", description="Generate thumbnails", action="generate_thumbnails"
        ),
        # View controls
        "zoom_in": Shortcut(key="Ctrl++", description="Zoom in", action="zoom_in"),
        "zoom_out": Shortcut(key="Ctrl+-", description="Zoom out", action="zoom_out"),
        "zoom_fit": Shortcut(key="Ctrl+0", description="Fit to window", action="zoom_fit"),
        "toggle_3d_view": Shortcut(key="F3", description="Toggle 3D view", action="toggle_3d_view"),
        # Navigation
        "next_slice": Shortcut(key="Right", description="Next slice", action="next_slice"),
        "prev_slice": Shortcut(key="Left", description="Previous slice", action="prev_slice"),
        "first_slice": Shortcut(key="Home", description="First slice", action="first_slice"),
        "last_slice": Shortcut(key="End", description="Last slice", action="last_slice"),
        "jump_forward_10": Shortcut(
            key="Ctrl+Right", description="Jump forward 10 slices", action="jump_forward_10"
        ),
        "jump_backward_10": Shortcut(
            key="Ctrl+Left", description="Jump backward 10 slices", action="jump_backward_10"
        ),
        # Crop region
        "set_bottom": Shortcut(key="B", description="Set bottom boundary", action="set_bottom"),
        "set_top": Shortcut(key="T", description="Set top boundary", action="set_top"),
        "reset_crop": Shortcut(key="Ctrl+R", description="Reset crop region", action="reset_crop"),
        # Threshold adjustment
        "increase_threshold": Shortcut(
            key="Up", description="Increase threshold", action="increase_threshold"
        ),
        "decrease_threshold": Shortcut(
            key="Down", description="Decrease threshold", action="decrease_threshold"
        ),
        # Help
        "show_shortcuts": Shortcut(
            key="F1", description="Show keyboard shortcuts", action="show_shortcuts"
        ),
        "show_about": Shortcut(key="Ctrl+I", description="About CTHarvester", action="show_about"),
        # Preferences
        "show_preferences": Shortcut(
            key="Ctrl+,", description="Open preferences", action="show_preferences"
        ),
    }

    @classmethod
    def get_shortcut(cls, action: str) -> Shortcut:
        """
        Get shortcut for action

        Args:
            action: Action name

        Returns:
            Shortcut object or None
        """
        return cls.SHORTCUTS.get(action)

    @classmethod
    def get_all_shortcuts(cls) -> Dict[str, Shortcut]:
        """
        Get all shortcuts

        Returns:
            Dictionary of all shortcuts
        """
        return cls.SHORTCUTS.copy()

    @classmethod
    def get_shortcuts_by_category(cls) -> Dict[str, list]:
        """
        Get shortcuts organized by category

        Returns:
            Dictionary with category names as keys and lists of action names as values
        """
        return {
            "File": ["open_directory", "reload_directory", "save_cropped", "export_mesh", "quit"],
            "Thumbnails": ["generate_thumbnails"],
            "View": ["zoom_in", "zoom_out", "zoom_fit", "toggle_3d_view"],
            "Navigation": [
                "next_slice",
                "prev_slice",
                "first_slice",
                "last_slice",
                "jump_forward_10",
                "jump_backward_10",
            ],
            "Crop": ["set_bottom", "set_top", "reset_crop"],
            "Threshold": ["increase_threshold", "decrease_threshold"],
            "Help": ["show_shortcuts", "show_about"],
            "Settings": ["show_preferences"],
        }
