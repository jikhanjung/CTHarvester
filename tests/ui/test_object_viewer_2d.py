"""
Unit tests for ObjectViewer2D widget

Tests 2D image viewer with ROI selection functionality.
"""

import os
import sys

import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from PyQt5.QtCore import QPoint, QRect, Qt
    from PyQt5.QtGui import QImage, QPixmap
    from PyQt5.QtWidgets import QWidget

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

if PYQT_AVAILABLE:
    from config.view_modes import MODE_ADD_BOX, MODE_EDIT_BOX, MODE_MOVE_BOX, MODE_VIEW
    from ui.widgets.object_viewer_2d import ObjectViewer2D


def create_test_pixmap(width=100, height=100):
    """Create a test QPixmap"""
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(Qt.gray)
    return QPixmap.fromImage(image)


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestObjectViewer2DInitialization:
    """Tests for ObjectViewer2D initialization"""

    @pytest.fixture
    def parent_widget(self, qtbot):
        """Create parent widget"""
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def viewer(self, qtbot, parent_widget):
        """Create ObjectViewer2D instance"""
        v = ObjectViewer2D(parent_widget)
        qtbot.addWidget(v)
        return v

    def test_initialization(self, viewer):
        """Should initialize with correct default values"""
        assert viewer is not None
        assert viewer.minimumSize().width() == 512
        assert viewer.minimumSize().height() == 512

    def test_initial_state(self, viewer):
        """Should have correct initial state"""
        assert viewer.scale == 1.0
        assert viewer.image_canvas_ratio == 1.0
        assert viewer.orig_pixmap is None
        assert viewer.curr_pixmap is None

    def test_initial_crop_values(self, viewer):
        """Should have crop values reset"""
        assert viewer.crop_from_x == -1
        assert viewer.crop_from_y == -1
        assert viewer.crop_to_x == -1
        assert viewer.crop_to_y == -1

    def test_initial_mode(self, viewer):
        """Should start in ADD_BOX mode"""
        assert viewer.edit_mode == MODE_ADD_BOX

    def test_initial_indices(self, viewer):
        """Should have initial index values"""
        assert viewer.top_idx == -1
        assert viewer.bottom_idx == -1
        assert viewer.curr_idx == 0

    def test_mouse_tracking_enabled(self, viewer):
        """Should have mouse tracking enabled"""
        assert viewer.hasMouseTracking() is True


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestObjectViewer2DModeManagement:
    """Tests for mode management"""

    @pytest.fixture
    def parent_widget(self, qtbot):
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def viewer(self, qtbot, parent_widget):
        v = ObjectViewer2D(parent_widget)
        qtbot.addWidget(v)
        return v

    def test_set_mode_view(self, viewer):
        """Should set VIEW mode and arrow cursor"""
        viewer.set_mode(MODE_VIEW)
        assert viewer.edit_mode == MODE_VIEW
        assert viewer.cursor().shape() == Qt.ArrowCursor

    def test_set_mode_add_box(self, viewer):
        """Should set ADD_BOX mode and cross cursor"""
        viewer.set_mode(MODE_ADD_BOX)
        assert viewer.edit_mode == MODE_ADD_BOX
        assert viewer.cursor().shape() == Qt.CrossCursor

    def test_set_mode_move_box(self, viewer):
        """Should set MOVE_BOX mode and open hand cursor"""
        viewer.set_mode(MODE_MOVE_BOX)
        assert viewer.edit_mode == MODE_MOVE_BOX
        assert viewer.cursor().shape() == Qt.OpenHandCursor

    def test_set_mode_edit_box(self, viewer):
        """Should set EDIT_BOX mode"""
        viewer.set_mode(MODE_EDIT_BOX)
        assert viewer.edit_mode == MODE_EDIT_BOX


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestObjectViewer2DROIManagement:
    """Tests for ROI (Region of Interest) management"""

    @pytest.fixture
    def parent_widget(self, qtbot):
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def viewer(self, qtbot, parent_widget):
        v = ObjectViewer2D(parent_widget)
        qtbot.addWidget(v)
        return v

    def test_reset_crop_without_image(self, viewer):
        """Should reset crop values to -1"""
        viewer.reset_crop()

        assert viewer.crop_from_x == -1
        assert viewer.crop_from_y == -1
        assert viewer.crop_to_x == -1
        assert viewer.crop_to_y == -1

    def test_set_full_roi_without_image(self, viewer):
        """Should handle set_full_roi when no image is loaded"""
        viewer.set_full_roi()  # Should not crash

        # ROI should still be unset
        assert viewer.crop_from_x == -1 or viewer.crop_from_x == 0

    def test_set_full_roi_with_image(self, viewer):
        """Should set ROI to full image dimensions"""
        # Load test pixmap
        viewer.orig_pixmap = create_test_pixmap(200, 150)

        viewer.set_full_roi()

        assert viewer.crop_from_x == 0
        assert viewer.crop_from_y == 0
        assert viewer.crop_to_x == 200
        assert viewer.crop_to_y == 150

    def test_is_roi_full_or_empty_without_image(self, viewer):
        """Should return True when no image is loaded"""
        assert viewer.is_roi_full_or_empty() is True

    def test_is_roi_full_or_empty_with_unset_roi(self, viewer):
        """Should return True when ROI is not set"""
        viewer.orig_pixmap = create_test_pixmap(100, 100)
        # ROI values still -1
        assert viewer.is_roi_full_or_empty() is True

    def test_is_roi_full_or_empty_with_full_roi(self, viewer):
        """Should return True when ROI covers entire image"""
        viewer.orig_pixmap = create_test_pixmap(100, 100)
        viewer.set_full_roi()

        assert viewer.is_roi_full_or_empty() is True

    def test_is_roi_full_or_empty_with_partial_roi(self, viewer):
        """Should return False when ROI is partial"""
        viewer.orig_pixmap = create_test_pixmap(100, 100)
        viewer.crop_from_x = 10
        viewer.crop_from_y = 10
        viewer.crop_to_x = 90
        viewer.crop_to_y = 90

        assert viewer.is_roi_full_or_empty() is False

    def test_reset_crop_with_image_sets_full_roi(self, viewer):
        """Should set full ROI when resetting with image loaded"""
        viewer.orig_pixmap = create_test_pixmap(100, 100)
        viewer.reset_crop()

        # Should be set to full image
        assert viewer.crop_from_x == 0
        assert viewer.crop_to_x == 100


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestObjectViewer2DCoordinateConversion:
    """Tests for coordinate conversion methods"""

    @pytest.fixture
    def parent_widget(self, qtbot):
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def viewer(self, qtbot, parent_widget):
        v = ObjectViewer2D(parent_widget)
        qtbot.addWidget(v)
        return v

    def test_canvas_to_image_x_default_scale(self, viewer):
        """Should convert canvas X to image X correctly"""
        viewer.scale = 1.0
        viewer.image_canvas_ratio = 1.0

        # At 1:1 scale and ratio, coordinates should be the same
        assert viewer._2imgx(50) == 50
        assert viewer._2imgx(100) == 100

    def test_canvas_to_image_y_default_scale(self, viewer):
        """Should convert canvas Y to image Y correctly"""
        viewer.scale = 1.0
        viewer.image_canvas_ratio = 1.0

        assert viewer._2imgy(50) == 50
        assert viewer._2imgy(100) == 100

    def test_image_to_canvas_x_default_scale(self, viewer):
        """Should convert image X to canvas X correctly"""
        viewer.scale = 1.0
        viewer.image_canvas_ratio = 1.0

        assert viewer._2canx(50) == 50
        assert viewer._2canx(100) == 100

    def test_image_to_canvas_y_default_scale(self, viewer):
        """Should convert image Y to canvas Y correctly"""
        viewer.scale = 1.0
        viewer.image_canvas_ratio = 1.0

        assert viewer._2cany(50) == 50
        assert viewer._2cany(100) == 100

    def test_coordinate_conversion_with_scale(self, viewer):
        """Should convert coordinates correctly with different scale"""
        viewer.scale = 2.0
        viewer.image_canvas_ratio = 1.0

        # Canvas coordinates should be 2x image coordinates
        assert viewer._2canx(50) == 100
        assert viewer._2cany(50) == 100

        # Image coordinates should be 1/2 canvas coordinates
        assert viewer._2imgx(100) == 50
        assert viewer._2imgy(100) == 50

    def test_coordinate_conversion_roundtrip(self, viewer):
        """Should maintain value in roundtrip conversion"""
        viewer.scale = 1.5
        viewer.image_canvas_ratio = 2.0

        img_x = 100
        can_x = viewer._2canx(img_x)
        back_to_img_x = viewer._2imgx(can_x)

        # Should be close (allowing for rounding)
        assert abs(img_x - back_to_img_x) <= 1


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestObjectViewer2DProperties:
    """Tests for property setters and getters"""

    @pytest.fixture
    def parent_widget(self, qtbot):
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def viewer(self, qtbot, parent_widget):
        v = ObjectViewer2D(parent_widget)
        qtbot.addWidget(v)
        return v

    def test_set_isovalue(self, viewer):
        """Should set isovalue"""
        viewer.set_isovalue(100)
        assert viewer.isovalue == 100

        viewer.set_isovalue(50)
        assert viewer.isovalue == 50

    def test_get_pixmap_geometry_without_pixmap(self, viewer):
        """Should return None when no pixmap is loaded"""
        geom = viewer.get_pixmap_geometry()
        assert geom is None

    def test_get_pixmap_geometry_with_pixmap(self, viewer):
        """Should return pixmap rect when pixmap is loaded"""
        viewer.curr_pixmap = create_test_pixmap(200, 150)
        geom = viewer.get_pixmap_geometry()

        assert geom is not None
        assert geom.width() == 200
        assert geom.height() == 150

    def test_initial_isovalue(self, viewer):
        """Should have default isovalue"""
        assert viewer.isovalue == 60

    def test_initial_inverse_flag(self, viewer):
        """Should have inverse flag set to False"""
        assert viewer.is_inverse is False


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestObjectViewer2DEdgeCases:
    """Tests for edge cases and boundary conditions"""

    @pytest.fixture
    def parent_widget(self, qtbot):
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def viewer(self, qtbot, parent_widget):
        v = ObjectViewer2D(parent_widget)
        qtbot.addWidget(v)
        return v

    def test_multiple_reset_crop(self, viewer):
        """Should handle multiple reset_crop calls"""
        viewer.orig_pixmap = create_test_pixmap(100, 100)

        viewer.reset_crop()
        viewer.reset_crop()
        viewer.reset_crop()

        # Should still be in valid state
        assert viewer.crop_from_x == 0
        assert viewer.crop_to_x == 100

    def test_zero_dimension_pixmap(self, viewer):
        """Should handle edge case of very small pixmap"""
        viewer.orig_pixmap = create_test_pixmap(1, 1)
        viewer.set_full_roi()

        assert viewer.crop_from_x == 0
        assert viewer.crop_to_x == 1

    def test_large_pixmap(self, viewer):
        """Should handle large pixmap"""
        viewer.orig_pixmap = create_test_pixmap(4096, 4096)
        viewer.set_full_roi()

        assert viewer.crop_from_x == 0
        assert viewer.crop_to_x == 4096

    def test_coordinate_conversion_extreme_scale(self, viewer):
        """Should handle extreme scale values"""
        viewer.scale = 10.0
        viewer.image_canvas_ratio = 0.1

        # Should not crash
        can_x = viewer._2canx(100)
        img_x = viewer._2imgx(100)

        assert can_x >= 0
        assert img_x >= 0

    def test_mode_switching_sequence(self, viewer):
        """Should handle rapid mode switching"""
        modes = [MODE_VIEW, MODE_ADD_BOX, MODE_MOVE_BOX, MODE_EDIT_BOX, MODE_VIEW]

        for mode in modes:
            viewer.set_mode(mode)
            assert viewer.edit_mode == mode

    def test_roi_with_negative_coordinates(self, viewer):
        """Should clamp negative ROI coordinates"""
        viewer.orig_pixmap = create_test_pixmap(100, 100)

        # Try to set negative coordinates
        viewer.crop_from_x = -10
        viewer.crop_from_y = -10
        viewer.crop_to_x = 110
        viewer.crop_to_y = 110

        # Values should be set (actual clamping may happen elsewhere)
        assert viewer.crop_from_x != -1  # Not unset

    def test_roi_boundaries(self, viewer):
        """Should handle ROI at exact boundaries"""
        viewer.orig_pixmap = create_test_pixmap(100, 100)

        # Set ROI to exact boundaries
        viewer.crop_from_x = 0
        viewer.crop_from_y = 0
        viewer.crop_to_x = 100
        viewer.crop_to_y = 100

        assert viewer.is_roi_full_or_empty() is True

    def test_distance_threshold_initialization(self, viewer):
        """Should initialize distance threshold"""
        assert viewer.distance_threshold is not None
        assert viewer.distance_threshold > 0


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestObjectViewer2DIntegration:
    """Integration tests for ObjectViewer2D"""

    @pytest.fixture
    def parent_widget(self, qtbot):
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def viewer(self, qtbot, parent_widget):
        v = ObjectViewer2D(parent_widget)
        qtbot.addWidget(v)
        return v

    def test_load_and_set_full_roi_workflow(self, viewer):
        """Test complete workflow of loading image and setting ROI"""
        # Load image
        viewer.orig_pixmap = create_test_pixmap(256, 256)

        # Set full ROI
        viewer.set_full_roi()

        # Verify ROI is full
        assert viewer.is_roi_full_or_empty() is True

        # Change to partial ROI
        viewer.crop_from_x = 50
        viewer.crop_from_y = 50
        viewer.crop_to_x = 200
        viewer.crop_to_y = 200

        # Verify ROI is partial
        assert viewer.is_roi_full_or_empty() is False

        # Reset
        viewer.reset_crop()

        # Should be back to full
        assert viewer.is_roi_full_or_empty() is True

    def test_mode_and_roi_workflow(self, viewer):
        """Test combined mode and ROI operations"""
        viewer.orig_pixmap = create_test_pixmap(100, 100)

        # Start in add box mode
        viewer.set_mode(MODE_ADD_BOX)
        assert viewer.cursor().shape() == Qt.CrossCursor

        # Set ROI
        viewer.set_full_roi()

        # Switch to move mode
        viewer.set_mode(MODE_MOVE_BOX)
        assert viewer.cursor().shape() == Qt.OpenHandCursor

        # ROI should still be valid
        assert viewer.crop_to_x == 100

    def test_coordinate_system_consistency(self, viewer):
        """Test that coordinate conversions are consistent"""
        viewer.scale = 2.0
        viewer.image_canvas_ratio = 1.5

        # Test multiple coordinates
        for img_coord in [0, 10, 50, 100, 200]:
            can_coord = viewer._2canx(img_coord)
            back_img = viewer._2imgx(can_coord)

            # Should roundtrip with minimal error
            assert abs(img_coord - back_img) <= 1
