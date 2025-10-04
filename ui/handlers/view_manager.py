"""View management handler for 3D visualization updates.

This module handles 3D view updates and synchronization between 2D/3D views.
Extracted from CTHarvesterMainWindow during Phase 4.4 refactoring to reduce main_window.py size.

The handler coordinates:
- 3D mesh viewer updates
- Bounding box calculations
- Volume data synchronization
- Level scaling and transformations
"""

import logging
from typing import TYPE_CHECKING

import numpy as np
from PyQt5.QtCore import QRect

from utils.ui_utils import wait_cursor

if TYPE_CHECKING:
    from ui.main_window import CTHarvesterMainWindow

logger = logging.getLogger(__name__)


class ViewManager:
    """Manages 3D view updates and level synchronization.

    Extracted from CTHarvesterMainWindow during Phase 4.4 refactoring
    to reduce file size and improve separation of concerns.

    The handler manages:
    - 3D mesh viewer (mcube_widget) updates
    - Bounding box scaling across pyramid levels
    - Volume data updates
    - Timeline synchronization
    """

    def __init__(self, main_window: "CTHarvesterMainWindow"):
        """Initialize the view manager.

        Args:
            main_window: Reference to main window for UI access
        """
        self.window = main_window

    def update_3d_view(self, update_volume: bool = True) -> None:
        """Update 3D mesh viewer with current crop region and bounding box.

        Args:
            update_volume: If True, recalculates volume from current settings.
                          If False, only updates display.

        The method scales bounding box dimensions based on current pyramid level
        to ensure proper visualization across different resolution levels.
        """
        # Check if minimum_volume is initialized
        if self.window.minimum_volume is None:
            logger.warning("minimum_volume not initialized in update_3D_view, skipping update")
            return

        volume, roi_box = self.window.get_cropped_volume()

        # Check if volume is empty
        if volume.size == 0:
            logger.warning("Empty volume in update_3D_view, skipping update")
            return

        # Calculate bounding box based on current level
        # The minimum_volume is always the smallest level, but we need to scale it
        # based on the current viewing level
        if hasattr(self.window, "level_info") and self.window.level_info:
            smallest_level_idx = len(self.window.level_info) - 1
            level_diff = smallest_level_idx - self.window.curr_level_idx
            scale_factor = 2**level_diff  # Each level is 2x the size of the next
        else:
            # Default to no scaling if level_info is not available
            scale_factor = 1

        # Get the base dimensions from minimum_volume
        base_shape = self.window.minimum_volume.shape

        # Scale the dimensions according to current level
        scaled_depth = base_shape[0] * scale_factor
        scaled_height = base_shape[1] * scale_factor
        scaled_width = base_shape[2] * scale_factor

        bounding_box = [0, scaled_depth - 1, 0, scaled_height - 1, 0, scaled_width - 1]

        # Scale the current slice value as well
        try:
            _, curr, _ = self.window.timeline.values()
            denom = (
                float(self.window.timeline.maximum()) if self.window.timeline.maximum() > 0 else 1.0
            )
            curr_slice_val = curr / denom * scaled_depth
        except (AttributeError, ValueError, ZeroDivisionError):
            curr_slice_val = 0

        self.window.mcube_widget.update_boxes(bounding_box, roi_box, curr_slice_val)
        self.window.mcube_widget.adjust_boxes()

        if update_volume:
            with wait_cursor():
                self.window.mcube_widget.update_volume(volume)
                self.window.mcube_widget.generate_mesh_multithread()
        self.window.mcube_widget.adjust_volume()

    def update_3d_view_with_thumbnails(self) -> None:
        """Update 3D view after loading thumbnails.

        This method is called after thumbnail generation to initialize
        the 3D visualization with the loaded thumbnail data.
        """
        logger.info("Updating 3D view after loading thumbnails")
        if self.window.minimum_volume is None:
            logger.warning("Cannot update 3D view: minimum_volume is None")
            return

        bounding_box = self.window.minimum_volume.shape
        logger.info(f"Bounding box shape: {bounding_box}")

        if len(bounding_box) < 3:
            return

        # Calculate proper bounding box
        scaled_depth = bounding_box[0]
        scaled_height = bounding_box[1]
        scaled_width = bounding_box[2]

        scaled_bounding_box = np.array(
            [0, scaled_depth - 1, 0, scaled_height - 1, 0, scaled_width - 1]
        )

        try:
            _, curr, _ = self.window.timeline.values()
            denom = (
                float(self.window.timeline.maximum()) if self.window.timeline.maximum() > 0 else 1.0
            )
            curr_slice_val = curr / denom * scaled_depth
        except (AttributeError, ValueError, ZeroDivisionError):
            curr_slice_val = 0

        logger.info(f"Updating mcube_widget with scaled_bounding_box: {scaled_bounding_box}")

        if not hasattr(self.window, "mcube_widget"):
            logger.error("mcube_widget not initialized!")
            return

        # Show wait cursor during 3D model generation
        with wait_cursor():
            self.window.mcube_widget.update_boxes(
                scaled_bounding_box, scaled_bounding_box, curr_slice_val
            )
            self.window.mcube_widget.adjust_boxes()
            self.window.mcube_widget.update_volume(self.window.minimum_volume)
            self.window.mcube_widget.generate_mesh()
            self.window.mcube_widget.adjust_volume()
            self.window.mcube_widget.show_buttons()
            logger.info("3D view update complete")

        # Ensure the 3D widget doesn't cover the main image
        self.window.mcube_widget.setGeometry(QRect(0, 0, 150, 150))
        self.window.mcube_widget.recalculate_geometry()
