"""Tests for ViewManager (Phase 4.4).

This module tests the 3D view management handler which coordinates
3D mesh viewer updates and level synchronization.
"""

import logging
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from PyQt5.QtCore import QRect

from ui.handlers.view_manager import ViewManager


# Mock wait_cursor to avoid Qt GUI interactions in tests
@contextmanager
def mock_wait_cursor():
    """Mock wait_cursor context manager that does nothing."""
    yield


class TestViewManagerInitialization:
    """Tests for ViewManager initialization."""

    def test_initialization_with_main_window(self):
        """Test manager initialization with main window reference."""
        mock_window = MagicMock()

        manager = ViewManager(mock_window)

        assert manager.window is mock_window

    def test_initialization_stores_window_reference(self):
        """Test that window reference is properly stored."""
        mock_window = MagicMock()
        mock_window.mcube_widget = MagicMock()
        mock_window.minimum_volume = np.zeros((10, 20, 30))

        manager = ViewManager(mock_window)

        # Should be able to access window attributes
        assert manager.window.mcube_widget is not None
        assert manager.window.minimum_volume is not None


@patch("ui.handlers.view_manager.wait_cursor", mock_wait_cursor)
class TestViewManagerUpdate3DView:
    """Tests for update_3d_view method."""

    @pytest.fixture
    def mock_window(self):
        """Create mock main window with all necessary attributes."""
        window = MagicMock()
        window.minimum_volume = np.zeros((10, 20, 30))
        window.mcube_widget = MagicMock()
        window.timeline = MagicMock()
        window.timeline.values.return_value = (0, 50, 100)
        window.timeline.maximum.return_value = 100
        window.curr_level_idx = 0
        window.level_info = [
            {"size": (800, 600)},
            {"size": (400, 300)},
            {"size": (200, 150)},
        ]
        window.get_cropped_volume = Mock(return_value=(np.ones((5, 10, 15)), [0, 4, 0, 9, 0, 14]))
        return window

    @pytest.fixture
    def manager(self, mock_window):
        """Create ViewManager instance."""
        return ViewManager(mock_window)

    def test_update_3d_view_basic(self, manager, mock_window):
        """Test basic 3D view update."""
        manager.update_3d_view(update_volume=True)

        # Should call mcube_widget methods
        mock_window.mcube_widget.update_boxes.assert_called_once()
        mock_window.mcube_widget.adjust_boxes.assert_called_once()
        mock_window.mcube_widget.update_volume.assert_called_once()
        mock_window.mcube_widget.generate_mesh_multithread.assert_called_once()
        mock_window.mcube_widget.adjust_volume.assert_called_once()

    def test_update_3d_view_with_volume_update(self, manager, mock_window):
        """Test update with volume recalculation."""
        manager.update_3d_view(update_volume=True)

        # Should update volume and generate mesh
        mock_window.mcube_widget.update_volume.assert_called_once()
        mock_window.mcube_widget.generate_mesh_multithread.assert_called_once()

    def test_update_3d_view_without_volume_update(self, manager, mock_window):
        """Test update without volume recalculation."""
        manager.update_3d_view(update_volume=False)

        # Should NOT update volume or generate mesh
        mock_window.mcube_widget.update_volume.assert_not_called()
        mock_window.mcube_widget.generate_mesh_multithread.assert_not_called()
        # But should still adjust volume
        mock_window.mcube_widget.adjust_volume.assert_called_once()

    def test_update_3d_view_missing_minimum_volume(self, manager, mock_window):
        """Test that update is skipped when minimum_volume is None."""
        mock_window.minimum_volume = None

        manager.update_3d_view()

        # Should not call any mcube_widget methods
        mock_window.mcube_widget.update_boxes.assert_not_called()

    def test_update_3d_view_empty_volume(self, manager, mock_window):
        """Test handling of empty volume from get_cropped_volume."""
        mock_window.get_cropped_volume = Mock(return_value=(np.array([]), [0, 0, 0, 0, 0, 0]))

        manager.update_3d_view()

        # Should log warning and skip update
        mock_window.mcube_widget.update_boxes.assert_not_called()

    def test_update_3d_view_level_scaling_calculation(self, manager, mock_window):
        """Test that level scaling is calculated correctly."""
        # Current level is 0, smallest is 2, so scale_factor should be 2^2 = 4
        mock_window.curr_level_idx = 0
        mock_window.level_info = [{"size": (800, 600)}, {"size": (400, 300)}, {"size": (200, 150)}]

        manager.update_3d_view()

        # Check bounding box calculation
        call_args = mock_window.mcube_widget.update_boxes.call_args
        bounding_box = call_args[0][0]

        # Expected: base_shape (10, 20, 30) * scale_factor (4) = (40, 80, 120)
        expected_bbox = [0, 40 - 1, 0, 80 - 1, 0, 120 - 1]
        assert bounding_box == expected_bbox

    def test_update_3d_view_level_scaling_single_level(self, manager, mock_window):
        """Test level scaling with single level (no scaling)."""
        mock_window.curr_level_idx = 0
        mock_window.level_info = [{"size": (800, 600)}]  # Only one level

        manager.update_3d_view()

        call_args = mock_window.mcube_widget.update_boxes.call_args
        bounding_box = call_args[0][0]

        # scale_factor should be 1 (0 - 0 = 0, 2^0 = 1)
        expected_bbox = [0, 10 - 1, 0, 20 - 1, 0, 30 - 1]
        assert bounding_box == expected_bbox

    def test_update_3d_view_bounding_box_calculation(self, manager, mock_window):
        """Test bounding box dimensions are correctly scaled."""
        mock_window.curr_level_idx = 1
        mock_window.level_info = [{"size": (800, 600)}, {"size": (400, 300)}, {"size": (200, 150)}]
        mock_window.minimum_volume = np.zeros((5, 10, 15))

        manager.update_3d_view()

        call_args = mock_window.mcube_widget.update_boxes.call_args
        bounding_box = call_args[0][0]

        # level_diff = 2 - 1 = 1, scale_factor = 2^1 = 2
        # Expected: (5*2, 10*2, 15*2) = (10, 20, 30)
        expected_bbox = [0, 10 - 1, 0, 20 - 1, 0, 30 - 1]
        assert bounding_box == expected_bbox

    def test_update_3d_view_timeline_synchronization(self, manager, mock_window):
        """Test that timeline slice value is synchronized."""
        mock_window.timeline.values.return_value = (0, 75, 100)  # 75% through
        mock_window.timeline.maximum.return_value = 100
        mock_window.curr_level_idx = 0
        mock_window.level_info = [{"size": (800, 600)}, {"size": (400, 300)}]
        mock_window.minimum_volume = np.zeros((10, 20, 30))

        manager.update_3d_view()

        call_args = mock_window.mcube_widget.update_boxes.call_args
        curr_slice_val = call_args[0][2]

        # scale_factor = 2^1 = 2, scaled_depth = 10 * 2 = 20
        # curr_slice_val = 75/100 * 20 = 15
        assert curr_slice_val == 15.0

    def test_update_3d_view_timeline_zero_maximum(self, manager, mock_window):
        """Test timeline synchronization with zero maximum."""
        mock_window.timeline.values.return_value = (0, 50, 100)
        mock_window.timeline.maximum.return_value = 0

        manager.update_3d_view()

        # When maximum is 0, denom becomes 1.0
        # curr_slice_val = curr / denom * scaled_depth
        # scaled_depth = 10 * 4 = 40 (since level_diff = 2-0 = 2, scale_factor = 4)
        # curr_slice_val = 50 / 1.0 * 40 = 2000.0
        call_args = mock_window.mcube_widget.update_boxes.call_args
        curr_slice_val = call_args[0][2]
        assert curr_slice_val == 2000.0

    def test_update_3d_view_no_level_info(self, manager, mock_window):
        """Test update when level_info is not available."""
        mock_window.level_info = None

        manager.update_3d_view()

        # Should use scale_factor = 1 (no scaling)
        call_args = mock_window.mcube_widget.update_boxes.call_args
        bounding_box = call_args[0][0]
        expected_bbox = [0, 10 - 1, 0, 20 - 1, 0, 30 - 1]
        assert bounding_box == expected_bbox


@patch("ui.handlers.view_manager.wait_cursor", mock_wait_cursor)
class TestViewManagerUpdate3DViewWithThumbnails:
    """Tests for update_3d_view_with_thumbnails method."""

    @pytest.fixture
    def mock_window(self):
        """Create mock main window for thumbnail tests."""
        window = MagicMock()
        window.minimum_volume = np.zeros((10, 20, 30))
        window.mcube_widget = MagicMock()
        window.timeline = MagicMock()
        window.timeline.values.return_value = (0, 50, 100)
        window.timeline.maximum.return_value = 100
        return window

    @pytest.fixture
    def manager(self, mock_window):
        """Create ViewManager instance."""
        return ViewManager(mock_window)

    def test_update_3d_view_with_thumbnails_basic(self, manager, mock_window):
        """Test basic thumbnail 3D view update."""
        manager.update_3d_view_with_thumbnails()

        # Should call all necessary methods
        mock_window.mcube_widget.update_boxes.assert_called_once()
        mock_window.mcube_widget.adjust_boxes.assert_called_once()
        mock_window.mcube_widget.update_volume.assert_called_once()
        mock_window.mcube_widget.generate_mesh.assert_called_once()
        mock_window.mcube_widget.adjust_volume.assert_called_once()
        mock_window.mcube_widget.show_buttons.assert_called_once()
        mock_window.mcube_widget.setGeometry.assert_called_once()
        mock_window.mcube_widget.recalculate_geometry.assert_called_once()

    def test_update_3d_view_with_thumbnails_missing_volume(self, manager, mock_window):
        """Test that update is skipped when minimum_volume is None."""
        mock_window.minimum_volume = None

        manager.update_3d_view_with_thumbnails()

        # Should not call mcube_widget methods
        mock_window.mcube_widget.update_boxes.assert_not_called()

    def test_update_3d_view_with_thumbnails_invalid_dimensions(self, manager, mock_window):
        """Test handling of invalid volume dimensions."""
        mock_window.minimum_volume = np.zeros((10, 20))  # Only 2D

        manager.update_3d_view_with_thumbnails()

        # Should return early without updating
        mock_window.mcube_widget.update_boxes.assert_not_called()

    def test_update_3d_view_with_thumbnails_bounding_box(self, manager, mock_window):
        """Test that bounding box is calculated correctly."""
        mock_window.minimum_volume = np.zeros((8, 16, 24))

        manager.update_3d_view_with_thumbnails()

        call_args = mock_window.mcube_widget.update_boxes.call_args
        scaled_bounding_box = call_args[0][0]

        # Expected bounding box
        expected = np.array([0, 8 - 1, 0, 16 - 1, 0, 24 - 1])
        np.testing.assert_array_equal(scaled_bounding_box, expected)

    def test_update_3d_view_with_thumbnails_mesh_generation(self, manager, mock_window):
        """Test that mesh is generated (not multithread version)."""
        manager.update_3d_view_with_thumbnails()

        # Should use generate_mesh(), not generate_mesh_multithread()
        mock_window.mcube_widget.generate_mesh.assert_called_once()

    def test_update_3d_view_with_thumbnails_geometry_adjustment(self, manager, mock_window):
        """Test that geometry is properly set."""
        manager.update_3d_view_with_thumbnails()

        # Should set specific geometry
        mock_window.mcube_widget.setGeometry.assert_called_once_with(QRect(0, 0, 150, 150))
        mock_window.mcube_widget.recalculate_geometry.assert_called_once()

    def test_update_3d_view_with_thumbnails_volume_update(self, manager, mock_window):
        """Test that volume is passed to mcube_widget."""
        test_volume = np.ones((5, 10, 15))
        mock_window.minimum_volume = test_volume

        manager.update_3d_view_with_thumbnails()

        # Should pass the exact volume
        call_args = mock_window.mcube_widget.update_volume.call_args
        passed_volume = call_args[0][0]
        np.testing.assert_array_equal(passed_volume, test_volume)

    def test_update_3d_view_with_thumbnails_missing_mcube_widget(self, manager, mock_window):
        """Test handling when mcube_widget is not initialized."""
        delattr(mock_window, "mcube_widget")

        # Should not crash, just log error
        manager.update_3d_view_with_thumbnails()

        # No assertions needed - just verify no crash


@patch("ui.handlers.view_manager.wait_cursor", mock_wait_cursor)
class TestViewManagerEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.fixture
    def manager(self):
        """Create manager with minimal mock."""
        mock_window = MagicMock()
        return ViewManager(mock_window)

    def test_curr_slice_value_attribute_error(self, manager):
        """Test handling of AttributeError in timeline access."""
        manager.window.minimum_volume = np.zeros((10, 20, 30))
        manager.window.mcube_widget = MagicMock()
        manager.window.timeline = None  # Will cause AttributeError
        manager.window.curr_level_idx = 0
        manager.window.level_info = [{"size": (800, 600)}]
        manager.window.get_cropped_volume = Mock(
            return_value=(np.ones((5, 10, 15)), [0, 4, 0, 9, 0, 14])
        )

        # Should not crash
        manager.update_3d_view()

        # curr_slice_val should default to 0
        call_args = manager.window.mcube_widget.update_boxes.call_args
        curr_slice_val = call_args[0][2]
        assert curr_slice_val == 0

    def test_curr_slice_value_zero_division_error(self, manager):
        """Test handling of division by zero in slice calculation."""
        manager.window.minimum_volume = np.zeros((10, 20, 30))
        manager.window.mcube_widget = MagicMock()
        manager.window.timeline = MagicMock()
        manager.window.timeline.values.side_effect = ZeroDivisionError()
        manager.window.curr_level_idx = 0
        manager.window.level_info = [{"size": (800, 600)}]
        manager.window.get_cropped_volume = Mock(
            return_value=(np.ones((5, 10, 15)), [0, 4, 0, 9, 0, 14])
        )

        # Should not crash
        manager.update_3d_view()

        # Should still complete update with curr_slice_val = 0
        manager.window.mcube_widget.update_boxes.assert_called_once()


@patch("ui.handlers.view_manager.wait_cursor", mock_wait_cursor)
class TestViewManagerLogging:
    """Tests for logging behavior."""

    @pytest.fixture
    def manager(self):
        """Create manager for logging tests."""
        mock_window = MagicMock()
        return ViewManager(mock_window)

    def test_logs_warning_on_missing_minimum_volume(self, manager, caplog):
        """Test that warning is logged when minimum_volume is None."""
        manager.window.minimum_volume = None

        with caplog.at_level(logging.WARNING):
            manager.update_3d_view()

        assert "minimum_volume not initialized" in caplog.text

    def test_logs_warning_on_empty_volume(self, manager, caplog):
        """Test that warning is logged for empty volume."""
        manager.window.minimum_volume = np.zeros((10, 20, 30))
        manager.window.get_cropped_volume = Mock(return_value=(np.array([]), [0, 0, 0, 0, 0, 0]))

        with caplog.at_level(logging.WARNING):
            manager.update_3d_view()

        assert "Empty volume" in caplog.text

    def test_logs_info_on_thumbnail_update(self, manager, caplog):
        """Test that info is logged during thumbnail update."""
        manager.window.minimum_volume = np.zeros((10, 20, 30))
        manager.window.mcube_widget = MagicMock()
        manager.window.timeline = MagicMock()
        manager.window.timeline.values.return_value = (0, 50, 100)
        manager.window.timeline.maximum.return_value = 100

        with caplog.at_level(logging.INFO):
            manager.update_3d_view_with_thumbnails()

        assert "Updating 3D view after loading thumbnails" in caplog.text
        assert "3D view update complete" in caplog.text

    def test_logs_error_on_missing_mcube_widget(self, manager, caplog):
        """Test that error is logged when mcube_widget is missing."""
        manager.window.minimum_volume = np.zeros((10, 20, 30))
        delattr(manager.window, "mcube_widget")

        with caplog.at_level(logging.ERROR):
            manager.update_3d_view_with_thumbnails()

        assert "mcube_widget not initialized" in caplog.text
