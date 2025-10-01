"""
VolumeProcessor - Handles volume processing operations

Extracted from ui/main_window.py during Phase 1 refactoring.
Provides volume cropping, scaling, and ROI management for CT data.
"""

import logging
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class VolumeProcessor:
    """Manages volume processing operations for CT data

    This class provides geometric operations on 3D CT volumes, including
    cropping, coordinate transformations, and region-of-interest (ROI) management
    across multiple Level-of-Detail (LoD) representations.

    Features:
        - Volume cropping based on user-defined ROI
        - Coordinate scaling between different LoD levels
        - Boundary validation and automatic clamping
        - Coordinate normalization/denormalization
        - Volume statistics and validation

    Key Concepts:
        - LoD Levels: Lower levels = higher resolution, Level 0 = original
        - Coordinates: All operations support 3D (Z, Y, X) or 6D (Z_min, Z_max, Y_min, Y_max, X_min, X_max)
        - Scaling: Each LoD level is 2x smaller than the previous (power of 2)

    Example:
        >>> processor = VolumeProcessor()
        >>> # Crop a volume based on ROI
        >>> cropped, roi = processor.get_cropped_volume(
        ...     minimum_volume=volume_data,
        ...     level_info=level_info,
        ...     curr_level_idx=0,
        ...     top_idx=50,
        ...     bottom_idx=10,
        ...     crop_box=[100, 100, 500, 500]
        ... )
        >>> print(f"Cropped volume shape: {cropped.shape}")
        >>> # Scale coordinates between levels
        >>> coords_level0 = [100, 200, 300]
        >>> coords_level2 = processor.scale_coordinates_between_levels(coords_level0, 0, 2)
        >>> # coords_level2 = [25, 50, 75]  (scaled by 1/4)

    Thread Safety:
        This class is stateless and thread-safe. Multiple threads can
        use the same instance concurrently without synchronization.
    """

    def __init__(self):
        """Initialize volume processor"""
        pass

    def get_cropped_volume(
        self,
        minimum_volume: np.ndarray,
        level_info: List[dict],
        curr_level_idx: int,
        top_idx: int,
        bottom_idx: int,
        crop_box: List[int],
    ) -> Tuple[np.ndarray, List[int]]:
        """Get cropped volume based on current ROI selection

        This method takes the minimum (lowest resolution) volume and crops it
        based on the user's selection in the 2D viewer. It handles coordinate
        transformation between different LoD levels.

        Args:
            minimum_volume (np.ndarray): The lowest resolution volume data (Z, Y, X)
            level_info (List[dict]): Information about each LoD level
                Each dict contains: {'seq_begin', 'seq_end', 'width', 'height'}
            curr_level_idx (int): Current viewing level index
            top_idx (int): Top slice index in current level
            bottom_idx (int): Bottom slice index in current level
            crop_box (List[int]): Crop box in current level [x1, y1, x2, y2]

        Returns:
            Tuple[np.ndarray, List[int]]: (cropped_volume, scaled_roi)
                - cropped_volume: Cropped 3D numpy array
                - scaled_roi: ROI in current level coordinates [z_min, z_max, y_min, y_max, x_min, x_max]

        Algorithm:
            1. Normalize coordinates to [0, 1] range based on current level
            2. Transform to smallest level coordinates
            3. Crop minimum_volume
            4. Scale ROI back to current level for display
        """
        # Validate inputs
        if not level_info:
            logger.warning("level_info not initialized in get_cropped_volume")
            return np.array([]), [0, 0, 0, 0, 0, 0]

        if curr_level_idx >= len(level_info):
            logger.warning(f"curr_level_idx {curr_level_idx} out of bounds, using 0")
            curr_level_idx = 0

        # Get current level information
        level_info_curr = level_info[curr_level_idx]
        seq_begin = level_info_curr["seq_begin"]
        seq_end = level_info_curr["seq_end"]
        image_count = seq_end - seq_begin + 1

        curr_width = level_info_curr["width"]
        curr_height = level_info_curr["height"]

        # Validate and clamp top/bottom indices
        if top_idx < 0 or bottom_idx < 0 or bottom_idx > top_idx:
            logger.debug("Invalid top/bottom indices, using full range")
            bottom_idx = 0
            top_idx = image_count - 1

        # Normalize crop box coordinates to [0, 1] range
        from_x = crop_box[0] / float(curr_width)
        from_y = crop_box[1] / float(curr_height)
        to_x = crop_box[2] / float(curr_width)
        to_y = crop_box[3] / float(curr_height)

        # Normalize slice indices to [0, 1] range
        top_idx_norm = top_idx / float(image_count)
        bottom_idx_norm = bottom_idx / float(image_count)

        # Transform to smallest level coordinates
        smallest_level_info = level_info[-1]
        smallest_count = smallest_level_info["seq_end"] - smallest_level_info["seq_begin"] + 1
        smallest_width = smallest_level_info["width"]
        smallest_height = smallest_level_info["height"]

        # Convert normalized coordinates to smallest level pixel coordinates
        bottom_idx_small = int(bottom_idx_norm * smallest_count)
        top_idx_small = int(top_idx_norm * smallest_count)

        # Clamp indices
        bottom_idx_small = max(0, min(bottom_idx_small, smallest_count - 1))
        top_idx_small = max(0, min(top_idx_small, smallest_count))

        # Ensure valid range
        if top_idx_small <= bottom_idx_small:
            top_idx_small = min(bottom_idx_small + 1, smallest_count)

        # Convert spatial coordinates
        # Note: Python slicing uses half-open intervals [start:end), so we don't subtract 1
        # The slice arr[0:5] returns indices 0,1,2,3,4 (5 elements total)
        from_x_small = int(from_x * smallest_width)
        from_y_small = int(from_y * smallest_height)
        to_x_small = int(to_x * smallest_width)
        to_y_small = int(to_y * smallest_height)

        # Ensure minimum_volume is numpy array
        if isinstance(minimum_volume, list):
            if len(minimum_volume) > 0:
                minimum_volume = np.array(minimum_volume)
            else:
                logger.error("minimum_volume is empty list")
                return np.array([]), [0, 0, 0, 0, 0, 0]

        # Validate array
        if minimum_volume.size == 0:
            logger.error("minimum_volume is empty array")
            return np.array([]), [0, 0, 0, 0, 0, 0]

        # Crop volume
        try:
            volume = minimum_volume[
                bottom_idx_small:top_idx_small, from_y_small:to_y_small, from_x_small:to_x_small
            ]
        except Exception as e:
            logger.error(f"Error cropping volume: {e}")
            logger.error(f"minimum_volume shape: {minimum_volume.shape}")
            logger.error(
                f"Crop indices: Z[{bottom_idx_small}:{top_idx_small}], "
                f"Y[{from_y_small}:{to_y_small}], X[{from_x_small}:{to_x_small}]"
            )
            return np.array([]), [0, 0, 0, 0, 0, 0]

        # Scale ROI box to current level coordinates
        smallest_level_idx = len(level_info) - 1
        level_diff = smallest_level_idx - curr_level_idx
        scale_factor = 2**level_diff

        # Scale the ROI coordinates back to current level
        scaled_roi = [
            bottom_idx_small * scale_factor,  # z_min
            top_idx_small * scale_factor,  # z_max
            from_y_small * scale_factor,  # y_min
            to_y_small * scale_factor,  # y_max
            from_x_small * scale_factor,  # x_min
            to_x_small * scale_factor,  # x_max
        ]

        logger.debug(f"Cropped volume shape: {volume.shape}, ROI: {scaled_roi}")

        return volume, scaled_roi

    def scale_coordinates_between_levels(
        self, coords: List[float], from_level: int, to_level: int
    ) -> List[float]:
        """Scale coordinates from one LoD level to another

        Args:
            coords (List[float]): Coordinates to scale [z, y, x] or [z_min, z_max, y_min, y_max, x_min, x_max]
            from_level (int): Source level index
            to_level (int): Target level index

        Returns:
            List[float]: Scaled coordinates

        Example:
            # Scale from level 0 (full res) to level 2 (1/4 res)
            coords = [100, 200, 300]  # Z, Y, X at level 0
            scaled = scale_coordinates_between_levels(coords, 0, 2)
            # Result: [25, 50, 75] at level 2
        """
        level_diff = to_level - from_level
        scale_factor = 2 ** (-level_diff)  # Negative because higher level = smaller size

        return [c * scale_factor for c in coords]

    def normalize_coordinates(self, coords: List[int], dimensions: List[int]) -> List[float]:
        """Normalize coordinates to [0, 1] range

        Args:
            coords (List[int]): Coordinates to normalize
            dimensions (List[int]): Maximum dimensions for normalization

        Returns:
            List[float]: Normalized coordinates in [0, 1] range
        """
        if len(coords) != len(dimensions):
            raise ValueError("Coordinates and dimensions must have same length")

        return [c / float(d) if d > 0 else 0.0 for c, d in zip(coords, dimensions)]

    def denormalize_coordinates(self, norm_coords: List[float], dimensions: List[int]) -> List[int]:
        """Convert normalized coordinates back to pixel coordinates

        Args:
            norm_coords (List[float]): Normalized coordinates in [0, 1]
            dimensions (List[int]): Target dimensions

        Returns:
            List[int]: Pixel coordinates
        """
        if len(norm_coords) != len(dimensions):
            raise ValueError("Coordinates and dimensions must have same length")

        return [int(nc * d) for nc, d in zip(norm_coords, dimensions)]

    def clamp_indices(self, bottom_idx: int, top_idx: int, max_count: int) -> Tuple[int, int]:
        """Clamp and validate slice indices

        Ensures indices are within valid range and bottom < top.

        Args:
            bottom_idx (int): Bottom slice index
            top_idx (int): Top slice index
            max_count (int): Maximum number of slices

        Returns:
            Tuple[int, int]: (clamped_bottom, clamped_top)
        """
        # Clamp to valid range
        bottom_idx = max(0, min(bottom_idx, max_count - 1))
        top_idx = max(0, min(top_idx, max_count))

        # Ensure bottom < top
        if top_idx <= bottom_idx:
            top_idx = min(bottom_idx + 1, max_count)

        return bottom_idx, top_idx

    def clamp_crop_box(self, crop_box: List[int], width: int, height: int) -> List[int]:
        """Clamp crop box to image boundaries

        Args:
            crop_box (List[int]): Crop box [x1, y1, x2, y2]
            width (int): Image width
            height (int): Image height

        Returns:
            List[int]: Clamped crop box
        """
        x1, y1, x2, y2 = crop_box

        x1 = max(0, min(x1, width - 1))
        x2 = max(x1 + 1, min(x2, width))
        y1 = max(0, min(y1, height - 1))
        y2 = max(y1 + 1, min(y2, height))

        return [x1, y1, x2, y2]

    def calculate_cropped_dimensions(
        self,
        level_info: List[dict],
        curr_level_idx: int,
        top_idx: int,
        bottom_idx: int,
        crop_box: List[int],
    ) -> dict:
        """Calculate dimensions of cropped volume at current level

        Args:
            level_info (List[dict]): LoD level information
            curr_level_idx (int): Current level index
            top_idx (int): Top slice index
            bottom_idx (int): Bottom slice index
            crop_box (List[int]): Crop box [x1, y1, x2, y2]

        Returns:
            dict: Dimensions {'depth', 'height', 'width', 'voxels'}
        """
        if not level_info or curr_level_idx >= len(level_info):
            return {"depth": 0, "height": 0, "width": 0, "voxels": 0}

        level = level_info[curr_level_idx]

        depth = top_idx - bottom_idx + 1
        height = crop_box[3] - crop_box[1]
        width = crop_box[2] - crop_box[0]
        voxels = depth * height * width

        return {"depth": depth, "height": height, "width": width, "voxels": voxels}

    def validate_volume(self, volume: np.ndarray) -> bool:
        """Validate volume data

        Args:
            volume (np.ndarray): Volume to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if volume is None:
            logger.error("Volume is None")
            return False

        if not isinstance(volume, np.ndarray):
            logger.error(f"Volume is not numpy array, got {type(volume)}")
            return False

        if volume.size == 0:
            logger.error("Volume is empty")
            return False

        if volume.ndim != 3:
            logger.error(f"Volume must be 3D, got {volume.ndim}D")
            return False

        return True

    def get_volume_statistics(self, volume: np.ndarray) -> dict:
        """Calculate volume statistics

        Args:
            volume (np.ndarray): 3D volume data

        Returns:
            dict: Statistics {'min', 'max', 'mean', 'std', 'shape', 'dtype'}
        """
        if not self.validate_volume(volume):
            return {}

        return {
            "min": float(volume.min()),
            "max": float(volume.max()),
            "mean": float(volume.mean()),
            "std": float(volume.std()),
            "shape": volume.shape,
            "dtype": str(volume.dtype),
        }
