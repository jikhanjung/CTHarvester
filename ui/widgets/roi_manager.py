"""ROI (Region of Interest) management for 2D image viewers.

This module was extracted from ObjectViewer2D during Phase 4 refactoring
to reduce complexity and improve maintainability. It handles all aspects
of ROI state management, coordinate transformations, and interaction logic.

Typical usage:

    roi_manager = ROIManager()

    # Set image dimensions
    roi_manager.set_image_size(1024, 1024)

    # Set full ROI
    roi_manager.set_full_roi()

    # Start drawing ROI
    roi_manager.start_roi_creation(100, 100)
    roi_manager.update_roi_creation(200, 200)
    roi_manager.finish_roi_creation()

    # Get ROI bounds
    bounds = roi_manager.get_roi_bounds()  # (x1, y1, x2, y2)
"""

import logging
from typing import Optional, Tuple

from PyQt5.QtCore import QRect

logger = logging.getLogger(__name__)


class ROIManager:
    """Manages Region of Interest (ROI) selection and manipulation.

    This class handles the state and logic for ROI (crop box) selection
    in a 2D image viewer. It manages:
    - ROI bounds (crop_from_x/y, crop_to_x/y)
    - Temporary drawing state (temp_x1/y1, temp_x2/y2)
    - Edge editing state (edit_x1/2, edit_y1/2)
    - Canvas coordinate transformations

    The ROI can be in several states:
    - Unset: All coordinates are -1
    - Full image: Coordinates match image dimensions
    - Custom: User-defined region

    Attributes:
        crop_from_x: Left edge of ROI (image coordinates)
        crop_from_y: Top edge of ROI (image coordinates)
        crop_to_x: Right edge of ROI (image coordinates)
        crop_to_y: Bottom edge of ROI (image coordinates)
        temp_x1, temp_y1: Temporary coordinates during drawing
        temp_x2, temp_y2: Temporary coordinates during drawing
        edit_x1, edit_x2: Flags for edge editing state
        edit_y1, edit_y2: Flags for edge editing state
        canvas_box: QRect representing ROI in canvas coordinates
        image_width: Width of the source image
        image_height: Height of the source image

    Example:
        >>> roi = ROIManager()
        >>> roi.set_image_size(1024, 768)
        >>> roi.set_full_roi()
        >>> roi.is_full_or_empty()
        True
        >>> roi.start_roi_creation(100, 100)
        >>> roi.update_roi_creation(200, 200)
        >>> roi.finish_roi_creation()
        >>> roi.get_roi_bounds()
        (100, 100, 200, 200)
    """

    def __init__(self):
        """Initialize ROI manager with default empty state."""
        # ROI bounds (image coordinates)
        self.crop_from_x = -1
        self.crop_from_y = -1
        self.crop_to_x = -1
        self.crop_to_y = -1

        # Temporary coordinates during drawing
        self.temp_x1 = -1
        self.temp_y1 = -1
        self.temp_x2 = -1
        self.temp_y2 = -1

        # Edge editing state
        self.edit_x1 = False
        self.edit_x2 = False
        self.edit_y1 = False
        self.edit_y2 = False

        # Canvas representation
        self.canvas_box: Optional[QRect] = None

        # Image dimensions
        self.image_width = 0
        self.image_height = 0

        logger.debug("ROIManager initialized")

    def set_image_size(self, width: int, height: int) -> None:
        """Set the size of the source image.

        Args:
            width: Image width in pixels
            height: Image height in pixels
        """
        self.image_width = width
        self.image_height = height
        logger.debug(f"Image size set: {width}x{height}")

    def reset(self) -> None:
        """Reset ROI to empty state (all coordinates = -1)."""
        self.crop_from_x = -1
        self.crop_from_y = -1
        self.crop_to_x = -1
        self.crop_to_y = -1
        self.temp_x1 = -1
        self.temp_y1 = -1
        self.temp_x2 = -1
        self.temp_y2 = -1
        self.edit_x1 = False
        self.edit_x2 = False
        self.edit_y1 = False
        self.edit_y2 = False
        self.canvas_box = None
        logger.debug("ROI reset to empty state")

    def set_full_roi(self) -> None:
        """Set ROI to cover the entire image.

        Requires image size to be set first via set_image_size().
        """
        if self.image_width == 0 or self.image_height == 0:
            logger.warning("Cannot set full ROI: image size not set")
            return

        self.crop_from_x = 0
        self.crop_from_y = 0
        self.crop_to_x = self.image_width
        self.crop_to_y = self.image_height
        logger.debug(
            f"ROI set to full image: ({self.crop_from_x}, {self.crop_from_y}) -> "
            f"({self.crop_to_x}, {self.crop_to_y})"
        )

    def is_full_or_empty(self) -> bool:
        """Check if ROI is not set or covers the entire image.

        Returns:
            True if ROI is unset or covers entire image, False otherwise
        """
        # Check if ROI is not set
        if (
            self.crop_from_x == -1
            or self.crop_from_y == -1
            or self.crop_to_x == -1
            or self.crop_to_y == -1
        ):
            return True

        # Check if ROI covers entire image
        if self.image_width == 0 or self.image_height == 0:
            return True

        return (
            self.crop_from_x == 0
            and self.crop_from_y == 0
            and self.crop_to_x == self.image_width
            and self.crop_to_y == self.image_height
        )

    def get_roi_bounds(self) -> Tuple[int, int, int, int]:
        """Get ROI bounds in image coordinates.

        Returns:
            Tuple of (x1, y1, x2, y2) where:
            - x1, y1: Top-left corner
            - x2, y2: Bottom-right corner
            Returns (-1, -1, -1, -1) if ROI not set
        """
        return (self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y)

    def set_roi_bounds(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Set ROI bounds directly.

        Args:
            x1: Left edge (image coordinates)
            y1: Top edge (image coordinates)
            x2: Right edge (image coordinates)
            y2: Bottom edge (image coordinates)
        """
        # Ensure x1 < x2 and y1 < y2
        self.crop_from_x = min(x1, x2)
        self.crop_from_y = min(y1, y2)
        self.crop_to_x = max(x1, x2)
        self.crop_to_y = max(y1, y2)

        logger.debug(
            f"ROI bounds set: ({self.crop_from_x}, {self.crop_from_y}) -> "
            f"({self.crop_to_x}, {self.crop_to_y})"
        )

    def start_roi_creation(self, x: int, y: int) -> None:
        """Start creating a new ROI.

        Args:
            x: Starting x coordinate (image coordinates)
            y: Starting y coordinate (image coordinates)
        """
        self.temp_x1 = x
        self.temp_y1 = y
        self.temp_x2 = x
        self.temp_y2 = y
        logger.debug(f"ROI creation started at ({x}, {y})")

    def update_roi_creation(self, x: int, y: int) -> None:
        """Update ROI during creation (mouse drag).

        Args:
            x: Current x coordinate (image coordinates)
            y: Current y coordinate (image coordinates)
        """
        self.temp_x2 = x
        self.temp_y2 = y

    def finish_roi_creation(self) -> None:
        """Finish creating ROI and commit temporary coordinates."""
        if self.temp_x1 == -1 or self.temp_y1 == -1:
            logger.warning("Cannot finish ROI creation: not started")
            return

        # Commit temporary coordinates to actual ROI
        self.crop_from_x = min(self.temp_x1, self.temp_x2)
        self.crop_from_y = min(self.temp_y1, self.temp_y2)
        self.crop_to_x = max(self.temp_x1, self.temp_x2)
        self.crop_to_y = max(self.temp_y1, self.temp_y2)

        # Clear temporary state
        self.temp_x1 = -1
        self.temp_y1 = -1
        self.temp_x2 = -1
        self.temp_y2 = -1

        logger.debug(
            f"ROI creation finished: ({self.crop_from_x}, {self.crop_from_y}) -> "
            f"({self.crop_to_x}, {self.crop_to_y})"
        )

    def cancel_roi_creation(self) -> None:
        """Cancel ROI creation and discard temporary coordinates."""
        self.temp_x1 = -1
        self.temp_y1 = -1
        self.temp_x2 = -1
        self.temp_y2 = -1
        logger.debug("ROI creation cancelled")

    def is_creating_roi(self) -> bool:
        """Check if currently in ROI creation mode.

        Returns:
            True if temp coordinates are set, False otherwise
        """
        return self.temp_x1 != -1 and self.temp_y1 != -1

    def get_temp_bounds(self) -> Tuple[int, int, int, int]:
        """Get temporary ROI bounds during creation.

        Returns:
            Tuple of (x1, y1, x2, y2) for temporary ROI,
            or (-1, -1, -1, -1) if not creating
        """
        if not self.is_creating_roi():
            return (-1, -1, -1, -1)

        return (
            min(self.temp_x1, self.temp_x2),
            min(self.temp_y1, self.temp_y2),
            max(self.temp_x1, self.temp_x2),
            max(self.temp_y1, self.temp_y2),
        )

    def update_canvas_box(
        self, image_canvas_ratio: float, scale: float, canvas_transform_func
    ) -> None:
        """Update canvas representation of ROI.

        Args:
            image_canvas_ratio: Ratio between image and canvas coordinates
            scale: Current zoom scale
            canvas_transform_func: Function to convert image coords to canvas coords
                Should accept (x, y) and return (canvas_x, canvas_y)
        """
        if self.crop_from_x == -1 or image_canvas_ratio == 0:
            self.canvas_box = None
            return

        # Convert image coordinates to canvas coordinates
        x1_canvas = canvas_transform_func(self.crop_from_x, self.crop_from_y)[0]
        y1_canvas = canvas_transform_func(self.crop_from_x, self.crop_from_y)[1]
        width_canvas = canvas_transform_func(
            self.crop_to_x - self.crop_from_x, self.crop_to_y - self.crop_from_y
        )[0]
        height_canvas = canvas_transform_func(
            self.crop_to_x - self.crop_from_x, self.crop_to_y - self.crop_from_y
        )[1]

        self.canvas_box = QRect(x1_canvas, y1_canvas, width_canvas, height_canvas)

    def get_roi_dimensions(self) -> Tuple[int, int]:
        """Get ROI width and height.

        Returns:
            Tuple of (width, height), or (0, 0) if ROI not set
        """
        if self.crop_from_x == -1:
            return (0, 0)

        width = self.crop_to_x - self.crop_from_x
        height = self.crop_to_y - self.crop_from_y
        return (width, height)

    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is inside the ROI.

        Args:
            x: X coordinate (image coordinates)
            y: Y coordinate (image coordinates)

        Returns:
            True if point is inside ROI, False otherwise
        """
        if self.crop_from_x == -1:
            return False

        return self.crop_from_x <= x <= self.crop_to_x and self.crop_from_y <= y <= self.crop_to_y

    def __repr__(self) -> str:
        """String representation for debugging."""
        if self.crop_from_x == -1:
            return "ROIManager(unset)"
        return (
            f"ROIManager(({self.crop_from_x}, {self.crop_from_y}) -> "
            f"({self.crop_to_x}, {self.crop_to_y}))"
        )
