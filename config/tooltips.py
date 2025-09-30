"""
Tooltip definitions for UI elements

Centralized tooltip and status tip definitions.
Created during Phase 1.6 UI/UX improvements.
"""

from typing import Dict


class TooltipManager:
    """
    Centralized tooltip manager

    Provides rich tooltips with descriptions and keyboard shortcuts.
    """

    # Tooltip format: HTML for rich formatting
    TOOLTIPS: Dict[str, Dict[str, str]] = {
        # File operations
        "open_directory": {
            "tooltip": (
                "<b>Open Directory</b><br>"
                "Select a directory containing CT image files.<br>"
                "Supported formats: BMP, JPG, PNG, TIF<br>"
                "<i>Shortcut: Ctrl+O</i>"
            ),
            "status": "Open a directory containing CT images",
        },
        "reload_directory": {
            "tooltip": (
                "<b>Reload Directory</b><br>"
                "Reload the current directory and refresh thumbnails.<br>"
                "<i>Shortcut: F5</i>"
            ),
            "status": "Reload current directory",
        },
        "save_cropped": {
            "tooltip": (
                "<b>Save Cropped Images</b><br>"
                "Save the cropped image stack to disk.<br>"
                "<i>Shortcut: Ctrl+S</i>"
            ),
            "status": "Save cropped images",
        },
        "export_mesh": {
            "tooltip": (
                "<b>Export 3D Mesh</b><br>"
                "Export the 3D mesh to STL, PLY, or OBJ format.<br>"
                "<i>Shortcut: Ctrl+E</i>"
            ),
            "status": "Export 3D mesh to file",
        },
        # Thumbnail operations
        "generate_thumbnails": {
            "tooltip": (
                "<b>Generate Thumbnails</b><br>"
                "Create pyramid thumbnails for efficient navigation.<br>"
                "This may take several minutes depending on image count.<br>"
                "<i>Shortcut: Ctrl+T</i>"
            ),
            "status": "Generate multi-level thumbnails for fast preview",
        },
        # View controls
        "zoom_in": {
            "tooltip": ("<b>Zoom In</b><br>" "Increase zoom level.<br>" "<i>Shortcut: Ctrl++</i>"),
            "status": "Zoom in",
        },
        "zoom_out": {
            "tooltip": ("<b>Zoom Out</b><br>" "Decrease zoom level.<br>" "<i>Shortcut: Ctrl+-</i>"),
            "status": "Zoom out",
        },
        "zoom_fit": {
            "tooltip": (
                "<b>Fit to Window</b><br>"
                "Adjust zoom to fit image in window.<br>"
                "<i>Shortcut: Ctrl+0</i>"
            ),
            "status": "Fit image to window",
        },
        "toggle_3d_view": {
            "tooltip": (
                "<b>Toggle 3D View</b><br>"
                "Show or hide 3D visualization panel.<br>"
                "<i>Shortcut: F3</i>"
            ),
            "status": "Toggle 3D view",
        },
        # Navigation
        "next_slice": {
            "tooltip": (
                "<b>Next Slice</b><br>"
                "Navigate to next slice in stack.<br>"
                "<i>Shortcut: Right Arrow</i>"
            ),
            "status": "Go to next slice",
        },
        "prev_slice": {
            "tooltip": (
                "<b>Previous Slice</b><br>"
                "Navigate to previous slice in stack.<br>"
                "<i>Shortcut: Left Arrow</i>"
            ),
            "status": "Go to previous slice",
        },
        # Crop region
        "set_bottom": {
            "tooltip": (
                "<b>Set Bottom Boundary</b><br>"
                "Set the bottom boundary of crop region at current slice.<br>"
                "<i>Shortcut: B</i>"
            ),
            "status": "Set bottom boundary for crop",
        },
        "set_top": {
            "tooltip": (
                "<b>Set Top Boundary</b><br>"
                "Set the top boundary of crop region at current slice.<br>"
                "<i>Shortcut: T</i>"
            ),
            "status": "Set top boundary for crop",
        },
        "reset_crop": {
            "tooltip": (
                "<b>Reset Crop Region</b><br>"
                "Reset crop region to full image stack.<br>"
                "<i>Shortcut: Ctrl+R</i>"
            ),
            "status": "Reset crop region",
        },
        # Threshold
        "threshold_slider": {
            "tooltip": (
                "<b>Threshold</b><br>"
                "Adjust the threshold for 3D mesh generation.<br>"
                "Higher values show only denser structures.<br>"
                "<i>Shortcuts: Up/Down arrows</i>"
            ),
            "status": "Adjust threshold for 3D visualization",
        },
        # Preferences
        "use_rust_thumbnail": {
            "tooltip": (
                "<b>Thumbnail Generation Method</b><br>"
                "<b>Rust (Fast):</b> High-performance native implementation<br>"
                "<b>Python (Fallback):</b> Slower but always available<br>"
                "Change requires restart to take effect."
            ),
            "status": "Choose thumbnail generation method",
        },
        # Help
        "show_shortcuts": {
            "tooltip": (
                "<b>Keyboard Shortcuts</b><br>"
                "Show all available keyboard shortcuts.<br>"
                "<i>Shortcut: F1</i>"
            ),
            "status": "Show keyboard shortcuts help",
        },
        "show_about": {
            "tooltip": (
                "<b>About CTHarvester</b><br>"
                "Show version and license information.<br>"
                "<i>Shortcut: Ctrl+I</i>"
            ),
            "status": "About CTHarvester",
        },
    }

    @classmethod
    def get_tooltip(cls, action: str) -> str:
        """
        Get tooltip text for action

        Args:
            action: Action name

        Returns:
            HTML tooltip text
        """
        info = cls.TOOLTIPS.get(action, {})
        return info.get("tooltip", "")

    @classmethod
    def get_status_tip(cls, action: str) -> str:
        """
        Get status tip text for action

        Args:
            action: Action name

        Returns:
            Status bar text
        """
        info = cls.TOOLTIPS.get(action, {})
        return info.get("status", "")

    @classmethod
    def set_action_tooltips(cls, action, action_name: str):
        """
        Set both tooltip and status tip for a QAction

        Args:
            action: QAction object
            action_name: Action name key
        """
        tooltip = cls.get_tooltip(action_name)
        status = cls.get_status_tip(action_name)

        if tooltip:
            action.setToolTip(tooltip)
        if status:
            action.setStatusTip(status)
