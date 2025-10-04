"""Tests for ui/widgets/roi_manager.py - ROI management.

Part of Phase 4 refactoring (devlog 076)
"""

import pytest
from PyQt5.QtCore import QRect

from ui.widgets.roi_manager import ROIManager


class TestROIManager:
    """Test suite for ROIManager class"""

    @pytest.fixture
    def roi(self):
        """Create a basic ROI manager"""
        return ROIManager()

    @pytest.fixture
    def roi_with_image(self):
        """Create ROI manager with image size set"""
        roi = ROIManager()
        roi.set_image_size(1024, 768)
        return roi

    def test_initialization(self):
        """Test basic initialization"""
        roi = ROIManager()

        assert roi.crop_from_x == -1
        assert roi.crop_from_y == -1
        assert roi.crop_to_x == -1
        assert roi.crop_to_y == -1
        assert roi.temp_x1 == -1
        assert roi.temp_y1 == -1
        assert roi.temp_x2 == -1
        assert roi.temp_y2 == -1
        assert roi.edit_x1 is False
        assert roi.edit_x2 is False
        assert roi.edit_y1 is False
        assert roi.edit_y2 is False
        assert roi.canvas_box is None
        assert roi.image_width == 0
        assert roi.image_height == 0

    def test_set_image_size(self, roi):
        """Test setting image dimensions"""
        roi.set_image_size(1920, 1080)

        assert roi.image_width == 1920
        assert roi.image_height == 1080

    def test_reset(self, roi_with_image):
        """Test resetting ROI to empty state"""
        # Set some values
        roi_with_image.set_full_roi()
        assert roi_with_image.crop_from_x != -1

        # Reset
        roi_with_image.reset()

        assert roi_with_image.crop_from_x == -1
        assert roi_with_image.crop_from_y == -1
        assert roi_with_image.crop_to_x == -1
        assert roi_with_image.crop_to_y == -1
        assert roi_with_image.canvas_box is None

    def test_set_full_roi(self, roi_with_image):
        """Test setting ROI to full image"""
        roi_with_image.set_full_roi()

        assert roi_with_image.crop_from_x == 0
        assert roi_with_image.crop_from_y == 0
        assert roi_with_image.crop_to_x == 1024
        assert roi_with_image.crop_to_y == 768

    def test_set_full_roi_without_image_size(self, roi):
        """Test set_full_roi fails gracefully without image size"""
        roi.set_full_roi()

        # Should remain unset
        assert roi.crop_from_x == -1

    def test_is_full_or_empty_when_unset(self, roi):
        """Test is_full_or_empty returns True for unset ROI"""
        assert roi.is_full_or_empty() is True

    def test_is_full_or_empty_when_full(self, roi_with_image):
        """Test is_full_or_empty returns True for full ROI"""
        roi_with_image.set_full_roi()

        assert roi_with_image.is_full_or_empty() is True

    def test_is_full_or_empty_when_partial(self, roi_with_image):
        """Test is_full_or_empty returns False for partial ROI"""
        roi_with_image.set_roi_bounds(100, 100, 500, 500)

        assert roi_with_image.is_full_or_empty() is False

    def test_get_roi_bounds_when_unset(self, roi):
        """Test get_roi_bounds returns -1 values when unset"""
        bounds = roi.get_roi_bounds()

        assert bounds == (-1, -1, -1, -1)

    def test_get_roi_bounds_when_set(self, roi):
        """Test get_roi_bounds returns correct values"""
        roi.set_roi_bounds(100, 200, 300, 400)
        bounds = roi.get_roi_bounds()

        assert bounds == (100, 200, 300, 400)

    def test_set_roi_bounds_normal_order(self, roi):
        """Test set_roi_bounds with normal coordinates"""
        roi.set_roi_bounds(100, 200, 300, 400)

        assert roi.crop_from_x == 100
        assert roi.crop_from_y == 200
        assert roi.crop_to_x == 300
        assert roi.crop_to_y == 400

    def test_set_roi_bounds_reversed_order(self, roi):
        """Test set_roi_bounds auto-corrects reversed coordinates"""
        # x2 < x1, y2 < y1
        roi.set_roi_bounds(300, 400, 100, 200)

        # Should be auto-corrected to min/max
        assert roi.crop_from_x == 100
        assert roi.crop_from_y == 200
        assert roi.crop_to_x == 300
        assert roi.crop_to_y == 400

    def test_start_roi_creation(self, roi):
        """Test starting ROI creation"""
        roi.start_roi_creation(150, 250)

        assert roi.temp_x1 == 150
        assert roi.temp_y1 == 250
        assert roi.temp_x2 == 150
        assert roi.temp_y2 == 250

    def test_update_roi_creation(self, roi):
        """Test updating ROI during creation"""
        roi.start_roi_creation(100, 100)
        roi.update_roi_creation(200, 300)

        assert roi.temp_x1 == 100
        assert roi.temp_y1 == 100
        assert roi.temp_x2 == 200
        assert roi.temp_y2 == 300

    def test_finish_roi_creation(self, roi):
        """Test finishing ROI creation"""
        roi.start_roi_creation(100, 100)
        roi.update_roi_creation(200, 300)
        roi.finish_roi_creation()

        assert roi.crop_from_x == 100
        assert roi.crop_from_y == 100
        assert roi.crop_to_x == 200
        assert roi.crop_to_y == 300
        # Temp values should be cleared
        assert roi.temp_x1 == -1
        assert roi.temp_y1 == -1

    def test_finish_roi_creation_with_reversed_coords(self, roi):
        """Test finish_roi_creation auto-corrects reversed coordinates"""
        roi.start_roi_creation(200, 300)
        roi.update_roi_creation(100, 100)
        roi.finish_roi_creation()

        # Should be auto-corrected to min/max
        assert roi.crop_from_x == 100
        assert roi.crop_from_y == 100
        assert roi.crop_to_x == 200
        assert roi.crop_to_y == 300

    def test_finish_roi_creation_not_started(self, roi):
        """Test finish_roi_creation handles not-started case"""
        # Should not crash
        roi.finish_roi_creation()

        # ROI should remain unset
        assert roi.crop_from_x == -1

    def test_cancel_roi_creation(self, roi):
        """Test cancelling ROI creation"""
        roi.start_roi_creation(100, 100)
        roi.update_roi_creation(200, 300)
        roi.cancel_roi_creation()

        assert roi.temp_x1 == -1
        assert roi.temp_y1 == -1
        assert roi.temp_x2 == -1
        assert roi.temp_y2 == -1
        # Actual ROI should remain unset
        assert roi.crop_from_x == -1

    def test_is_creating_roi_false(self, roi):
        """Test is_creating_roi returns False initially"""
        assert roi.is_creating_roi() is False

    def test_is_creating_roi_true(self, roi):
        """Test is_creating_roi returns True during creation"""
        roi.start_roi_creation(100, 100)

        assert roi.is_creating_roi() is True

    def test_is_creating_roi_false_after_finish(self, roi):
        """Test is_creating_roi returns False after finishing"""
        roi.start_roi_creation(100, 100)
        roi.finish_roi_creation()

        assert roi.is_creating_roi() is False

    def test_get_temp_bounds_when_not_creating(self, roi):
        """Test get_temp_bounds returns -1 values when not creating"""
        bounds = roi.get_temp_bounds()

        assert bounds == (-1, -1, -1, -1)

    def test_get_temp_bounds_when_creating(self, roi):
        """Test get_temp_bounds returns correct values during creation"""
        roi.start_roi_creation(100, 100)
        roi.update_roi_creation(200, 300)

        bounds = roi.get_temp_bounds()

        assert bounds == (100, 100, 200, 300)

    def test_get_temp_bounds_with_reversed_coords(self, roi):
        """Test get_temp_bounds auto-corrects reversed coordinates"""
        roi.start_roi_creation(200, 300)
        roi.update_roi_creation(100, 100)

        bounds = roi.get_temp_bounds()

        # Should be auto-corrected to min/max
        assert bounds == (100, 100, 200, 300)

    def test_get_roi_dimensions_when_unset(self, roi):
        """Test get_roi_dimensions returns (0, 0) when unset"""
        dims = roi.get_roi_dimensions()

        assert dims == (0, 0)

    def test_get_roi_dimensions_when_set(self, roi):
        """Test get_roi_dimensions returns correct dimensions"""
        roi.set_roi_bounds(100, 200, 300, 500)

        dims = roi.get_roi_dimensions()

        assert dims == (200, 300)  # width=300-100, height=500-200

    def test_contains_point_when_unset(self, roi):
        """Test contains_point returns False when ROI unset"""
        assert roi.contains_point(150, 250) is False

    def test_contains_point_inside(self, roi):
        """Test contains_point returns True for point inside ROI"""
        roi.set_roi_bounds(100, 100, 300, 300)

        assert roi.contains_point(150, 150) is True
        assert roi.contains_point(200, 200) is True

    def test_contains_point_outside(self, roi):
        """Test contains_point returns False for point outside ROI"""
        roi.set_roi_bounds(100, 100, 300, 300)

        assert roi.contains_point(50, 50) is False
        assert roi.contains_point(350, 350) is False

    def test_contains_point_on_edge(self, roi):
        """Test contains_point returns True for point on ROI edge"""
        roi.set_roi_bounds(100, 100, 300, 300)

        assert roi.contains_point(100, 100) is True  # Top-left corner
        assert roi.contains_point(300, 300) is True  # Bottom-right corner
        assert roi.contains_point(100, 200) is True  # Left edge
        assert roi.contains_point(200, 300) is True  # Bottom edge

    def test_repr_when_unset(self, roi):
        """Test __repr__ for unset ROI"""
        assert repr(roi) == "ROIManager(unset)"

    def test_repr_when_set(self, roi):
        """Test __repr__ for set ROI"""
        roi.set_roi_bounds(100, 200, 300, 400)

        assert repr(roi) == "ROIManager((100, 200) -> (300, 400))"

    @pytest.mark.parametrize(
        "x1,y1,x2,y2,expected",
        [
            (100, 100, 200, 200, (100, 100, 200, 200)),
            (200, 200, 100, 100, (100, 100, 200, 200)),  # Reversed
            (0, 0, 1024, 768, (0, 0, 1024, 768)),  # Full
        ],
    )
    def test_set_roi_bounds_parametrized(self, roi, x1, y1, x2, y2, expected):
        """Parametrized test for set_roi_bounds"""
        roi.set_roi_bounds(x1, y1, x2, y2)

        assert roi.get_roi_bounds() == expected

    def test_workflow_complete_roi_creation(self, roi_with_image):
        """Test complete ROI creation workflow"""
        # Start with full image
        roi_with_image.set_full_roi()
        assert roi_with_image.is_full_or_empty() is True

        # Start drawing new ROI
        roi_with_image.start_roi_creation(100, 100)
        assert roi_with_image.is_creating_roi() is True

        # Update during drag
        roi_with_image.update_roi_creation(200, 200)
        temp = roi_with_image.get_temp_bounds()
        assert temp == (100, 100, 200, 200)

        # Finish
        roi_with_image.finish_roi_creation()
        assert roi_with_image.is_creating_roi() is False
        assert roi_with_image.get_roi_bounds() == (100, 100, 200, 200)
        assert roi_with_image.is_full_or_empty() is False

    def test_workflow_cancelled_roi_creation(self, roi_with_image):
        """Test cancelled ROI creation workflow"""
        # Set initial ROI
        roi_with_image.set_roi_bounds(50, 50, 150, 150)

        # Start drawing new ROI
        roi_with_image.start_roi_creation(200, 200)
        roi_with_image.update_roi_creation(300, 300)

        # Cancel
        roi_with_image.cancel_roi_creation()

        # Should revert to original ROI
        assert roi_with_image.get_roi_bounds() == (50, 50, 150, 150)

    def test_reset_preserves_image_size(self, roi_with_image):
        """Test that reset() preserves image size"""
        original_width = roi_with_image.image_width
        original_height = roi_with_image.image_height

        roi_with_image.set_full_roi()
        roi_with_image.reset()

        # Image size should be preserved
        assert roi_with_image.image_width == original_width
        assert roi_with_image.image_height == original_height
