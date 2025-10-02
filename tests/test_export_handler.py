"""
Tests for ExportHandler class

Tests the export operations logic extracted from main_window.py
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

from ui.handlers.export_handler import ExportHandler


@pytest.mark.integration
class TestExportHandler:
    """Test suite for ExportHandler"""

    @pytest.fixture
    def mock_main_window(self):
        """Create a mock main window with required attributes"""
        window = MagicMock()

        # Basic attributes
        window.edtDirname.text.return_value = "/test/path"
        window.cbxOpenDirAfter.isChecked.return_value = False
        window.progress_text_1_1 = "Processing..."
        window.progress_text_1_2 = "Processing {}/{}"

        # Image label attributes for cropping
        window.image_label.crop_from_x = -1
        window.image_label.crop_from_y = -1
        window.image_label.crop_to_x = -1
        window.image_label.crop_to_y = -1
        window.image_label.top_idx = 9
        window.image_label.bottom_idx = 0
        window.image_label.isovalue = 127.5

        # Settings
        window.settings_hash = {
            "prefix": "slice_",
            "file_type": "tif",
            "index_length": 4,
        }

        # Level info
        window.level_info = [
            {"seq_begin": 1, "seq_end": 10},
            {"seq_begin": 1, "seq_end": 5},
        ]
        window.comboLevel.currentIndex.return_value = 0

        # Mock get_cropped_volume
        volume = np.random.randint(0, 255, (10, 100, 100), dtype=np.uint8)
        window.get_cropped_volume.return_value = (volume, {})

        return window

    @pytest.fixture
    def handler(self, mock_main_window):
        """Create an ExportHandler instance with mock window"""
        return ExportHandler(mock_main_window)

    @pytest.fixture
    def temp_image_stack(self):
        """Create temporary image stack for testing"""
        temp_dir = tempfile.mkdtemp()

        # Create 10 test images
        for i in range(1, 11):
            img = Image.fromarray(
                np.ones((100, 100), dtype=np.uint8) * (i * 25)
            )
            img.save(os.path.join(temp_dir, f"slice_{i:04d}.tif"))

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_initialization(self, handler, mock_main_window):
        """Test handler initializes correctly"""
        assert handler is not None
        assert handler.window == mock_main_window

    @patch('ui.handlers.export_handler.QFileDialog.getSaveFileName')
    @patch('ui.handlers.export_handler.mcubes.marching_cubes')
    @patch('ui.handlers.export_handler.SecureFileValidator')
    def test_export_obj_basic(self, mock_validator_cls, mock_mcubes, mock_dialog, handler, tmp_path):
        """Test basic OBJ export functionality"""
        # Setup
        obj_file = str(tmp_path / "test.obj")
        mock_dialog.return_value = (obj_file, "OBJ format (*.obj)")

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.validate_path.return_value = obj_file
        mock_validator_cls.return_value = mock_validator

        # Create simple mesh
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        triangles = np.array([[0, 1, 2]], dtype=int)
        mock_mcubes.return_value = (vertices, triangles)

        # Execute
        handler.export_3d_model_to_obj()

        # Verify
        assert os.path.exists(obj_file)
        with open(obj_file, 'r') as f:
            content = f.read()
            assert "v " in content  # Vertex lines
            assert "f " in content  # Face lines

    @patch('ui.handlers.export_handler.QFileDialog.getSaveFileName')
    def test_export_obj_cancelled(self, mock_dialog, handler):
        """Test OBJ export when user cancels"""
        # User cancels dialog
        mock_dialog.return_value = ("", "")

        # Should return early without error
        handler.export_3d_model_to_obj()

        # Verify dialog was called
        mock_dialog.assert_called_once()

    @patch('ui.handlers.export_handler.QFileDialog.getSaveFileName')
    @patch('ui.handlers.export_handler.mcubes.marching_cubes')
    @patch('ui.handlers.export_handler.QMessageBox.critical')
    def test_export_obj_mesh_generation_failure(self, mock_msg, mock_mcubes, mock_dialog, handler, tmp_path):
        """Test OBJ export when mesh generation fails"""
        # Setup
        obj_file = str(tmp_path / "test.obj")
        mock_dialog.return_value = (obj_file, "OBJ format (*.obj)")
        mock_mcubes.side_effect = Exception("Mesh generation failed")

        # Mock tr() to return the actual string
        handler.window.tr = lambda x: x

        # Execute
        handler.export_3d_model_to_obj()

        # Verify error dialog shown
        mock_msg.assert_called_once()
        # Check the message text (third argument)
        call_args = mock_msg.call_args[0]
        assert "Failed to generate 3D mesh" in call_args[2]

    @patch('ui.handlers.export_handler.QFileDialog.getSaveFileName')
    @patch('ui.handlers.export_handler.mcubes.marching_cubes')
    @patch('ui.handlers.export_handler.SecureFileValidator')
    def test_export_obj_vertex_transformation(self, mock_validator_cls, mock_mcubes, mock_dialog, handler, tmp_path):
        """Test that vertices are properly transformed (axis swap)"""
        # Setup
        obj_file = str(tmp_path / "test.obj")
        mock_dialog.return_value = (obj_file, "OBJ format (*.obj)")

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.validate_path.return_value = obj_file
        mock_validator_cls.return_value = mock_validator

        # Create vertices with known values
        vertices = np.array([[1, 2, 3], [4, 5, 6]], dtype=float)
        triangles = np.array([[0, 1, 0]], dtype=int)
        mock_mcubes.return_value = (vertices, triangles)

        # Execute
        handler.export_3d_model_to_obj()

        # Verify transformation (should swap to [z, x, y])
        with open(obj_file, 'r') as f:
            content = f.read()
            assert "v 3.0 1.0 2.0" in content  # First vertex transformed
            assert "v 6.0 4.0 5.0" in content  # Second vertex transformed

    @patch('ui.handlers.export_handler.QFileDialog.getSaveFileName')
    @patch('ui.handlers.export_handler.mcubes.marching_cubes')
    @patch('ui.handlers.export_handler.SecureFileValidator')
    def test_export_obj_face_indexing(self, mock_validator_cls, mock_mcubes, mock_dialog, handler, tmp_path):
        """Test that faces use 1-based indexing in OBJ format"""
        # Setup
        obj_file = str(tmp_path / "test.obj")
        mock_dialog.return_value = (obj_file, "OBJ format (*.obj)")

        # Mock validator
        mock_validator = MagicMock()
        mock_validator.validate_path.return_value = obj_file
        mock_validator_cls.return_value = mock_validator

        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        triangles = np.array([[0, 1, 2]], dtype=int)  # 0-based
        mock_mcubes.return_value = (vertices, triangles)

        # Execute
        handler.export_3d_model_to_obj()

        # Verify 1-based indexing in output
        with open(obj_file, 'r') as f:
            content = f.read()
            assert "f 1 2 3" in content  # Should be 1-based

    @patch('ui.handlers.export_handler.QFileDialog.getExistingDirectory')
    @patch('ui.handlers.export_handler.QApplication.setOverrideCursor')
    @patch('ui.handlers.export_handler.QApplication.restoreOverrideCursor')
    def test_save_image_stack_cancelled(self, mock_restore, mock_cursor, mock_dialog, handler):
        """Test save operation when user cancels directory selection"""
        # User cancels
        mock_dialog.return_value = ""

        # Execute
        handler.save_cropped_image_stack()

        # Verify no cursor changes happened
        mock_cursor.assert_not_called()
        mock_restore.assert_not_called()

    @patch('ui.handlers.export_handler.QFileDialog.getExistingDirectory')
    @patch('ui.handlers.export_handler.ProgressDialog')
    @patch('ui.handlers.export_handler.QApplication')
    def test_save_image_stack_no_crop(self, mock_app, mock_progress_cls, mock_dialog, handler, temp_image_stack, tmp_path):
        """Test saving images without cropping"""
        # Setup
        target_dir = str(tmp_path / "output")
        os.makedirs(target_dir)
        mock_dialog.return_value = target_dir

        # Mock progress dialog
        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress

        # Point to actual test images
        handler.window.edtDirname.text.return_value = temp_image_stack
        handler.window.image_label.top_idx = 9
        handler.window.image_label.bottom_idx = 0

        # Execute
        handler.save_cropped_image_stack()

        # Verify output files created
        output_files = os.listdir(target_dir)
        assert len(output_files) == 10
        assert "slice_0001.tif" in output_files
        assert "slice_0010.tif" in output_files

    @patch('ui.handlers.export_handler.QFileDialog.getExistingDirectory')
    @patch('ui.handlers.export_handler.ProgressDialog')
    @patch('ui.handlers.export_handler.QApplication')
    def test_save_image_stack_with_crop(self, mock_app, mock_progress_cls, mock_dialog, handler, temp_image_stack, tmp_path):
        """Test saving images with cropping applied"""
        # Setup
        target_dir = str(tmp_path / "output")
        os.makedirs(target_dir)
        mock_dialog.return_value = target_dir

        # Mock progress dialog
        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress

        # Configure cropping
        handler.window.edtDirname.text.return_value = temp_image_stack
        handler.window.image_label.crop_from_x = 10
        handler.window.image_label.crop_from_y = 10
        handler.window.image_label.crop_to_x = 50
        handler.window.image_label.crop_to_y = 50
        handler.window.image_label.top_idx = 2
        handler.window.image_label.bottom_idx = 0

        # Execute
        handler.save_cropped_image_stack()

        # Verify cropped images
        output_file = os.path.join(target_dir, "slice_0001.tif")
        assert os.path.exists(output_file)

        with Image.open(output_file) as img:
            # Should be cropped to 40x40 (from 10,10 to 50,50)
            assert img.size == (40, 40)

    @patch('ui.handlers.export_handler.QFileDialog.getExistingDirectory')
    @patch('ui.handlers.export_handler.ProgressDialog')
    @patch('ui.handlers.export_handler.QApplication')
    def test_save_image_stack_progress_updates(self, mock_app, mock_progress_cls, mock_dialog, handler, temp_image_stack, tmp_path):
        """Test that progress dialog is updated correctly"""
        # Setup
        target_dir = str(tmp_path / "output")
        os.makedirs(target_dir)
        mock_dialog.return_value = target_dir

        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress

        handler.window.edtDirname.text.return_value = temp_image_stack
        handler.window.image_label.top_idx = 4
        handler.window.image_label.bottom_idx = 0

        # Execute
        handler.save_cropped_image_stack()

        # Verify progress updates (5 images = at least 5 updates, initial setup might add one)
        assert mock_progress.pb_progress.setValue.call_count >= 5
        assert mock_progress.lbl_text.setText.call_count >= 5

    @patch('ui.handlers.export_handler.QFileDialog.getExistingDirectory')
    @patch('ui.handlers.export_handler.ProgressDialog')
    @patch('ui.handlers.export_handler.QApplication')
    def test_save_image_stack_open_after(self, mock_app, mock_progress_cls, mock_dialog, handler, temp_image_stack, tmp_path):
        """Test opening directory after save when checkbox is enabled"""
        import sys

        # Only test os.startfile on Windows
        if sys.platform != 'win32':
            pytest.skip("os.startfile only available on Windows")

        # Setup
        target_dir = str(tmp_path / "output")
        os.makedirs(target_dir)
        mock_dialog.return_value = target_dir

        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress

        handler.window.edtDirname.text.return_value = temp_image_stack
        handler.window.cbxOpenDirAfter.isChecked.return_value = True
        handler.window.image_label.top_idx = 2
        handler.window.image_label.bottom_idx = 0

        with patch('os.startfile') as mock_startfile:
            # Execute
            handler.save_cropped_image_stack()

            # Verify directory opened
            mock_startfile.assert_called_once_with(target_dir)

    def test_build_filename(self, handler):
        """Test filename building logic"""
        filename = handler._build_filename(0, 0)
        assert filename == "slice_0001.tif"

        filename = handler._build_filename(9, 0)
        assert filename == "slice_0010.tif"

    def test_get_crop_info(self, handler):
        """Test crop information collection"""
        crop_info = handler._get_crop_info()

        assert crop_info["from_x"] == -1
        assert crop_info["from_y"] == -1
        assert crop_info["to_x"] == -1
        assert crop_info["to_y"] == -1
        assert crop_info["size_idx"] == 0
        assert crop_info["top_idx"] == 9
        assert crop_info["bottom_idx"] == 0

    @patch('ui.handlers.export_handler.QFileDialog.getExistingDirectory')
    @patch('ui.handlers.export_handler.ProgressDialog')
    @patch('ui.handlers.export_handler.QApplication')
    def test_save_handles_missing_images(self, mock_app, mock_progress_cls, mock_dialog, handler, temp_image_stack, tmp_path, caplog):
        """Test that missing images are handled gracefully"""
        import logging

        # Setup
        target_dir = str(tmp_path / "output")
        os.makedirs(target_dir)
        mock_dialog.return_value = target_dir

        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress

        # Point to temp dir but delete some images
        handler.window.edtDirname.text.return_value = temp_image_stack
        os.remove(os.path.join(temp_image_stack, "slice_0005.tif"))

        # Execute with logging
        with caplog.at_level(logging.ERROR):
            handler.save_cropped_image_stack()

        # Verify error was logged for missing file
        assert any("Error opening/saving image" in record.message for record in caplog.records)

        # Other images should still be saved
        output_files = os.listdir(target_dir)
        assert len(output_files) == 9  # 10 - 1 missing

    def test_get_source_path_original(self, handler):
        """Test source path for original images (level 0)"""
        with patch('ui.handlers.export_handler.SecureFileValidator') as mock_validator_cls:
            mock_validator = MagicMock()
            mock_validator.safe_join.return_value = "/test/path/image.tif"
            mock_validator_cls.return_value = mock_validator

            path = handler._get_source_path("image.tif", 0)

            # Should join directly with base directory
            mock_validator.safe_join.assert_called_once_with("/test/path", "image.tif")
            assert path == "/test/path/image.tif"

    def test_get_source_path_thumbnail(self, handler):
        """Test source path for thumbnail images (level > 0)"""
        with patch('ui.handlers.export_handler.SecureFileValidator') as mock_validator_cls:
            mock_validator = MagicMock()
            # Two calls: one for directory, one for filename
            mock_validator.safe_join.side_effect = ["/test/path/.thumbnail/1", "/test/path/.thumbnail/1/image.tif"]
            mock_validator_cls.return_value = mock_validator

            path = handler._get_source_path("image.tif", 1)

            # Should join with thumbnail directory
            assert mock_validator.safe_join.call_count == 2
            assert path == "/test/path/.thumbnail/1/image.tif"

    @patch('ui.handlers.export_handler.QFileDialog.getExistingDirectory')
    @patch('ui.handlers.export_handler.ProgressDialog')
    @patch('ui.handlers.export_handler.QApplication')
    def test_save_image_stack_cursor_restoration(self, mock_app, mock_progress_cls, mock_dialog, handler, temp_image_stack, tmp_path):
        """Test that cursor is restored even if save fails"""
        # Setup
        target_dir = str(tmp_path / "output")
        os.makedirs(target_dir)
        mock_dialog.return_value = target_dir

        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress

        # Simulate failure by using invalid directory
        handler.window.edtDirname.text.return_value = "/nonexistent/path"

        # Execute (should not crash)
        handler.save_cropped_image_stack()

        # Verify cursor was restored
        mock_app.restoreOverrideCursor.assert_called_once()
        mock_progress.close.assert_called_once()


@pytest.mark.unit
class TestExportHelperMethods:
    """Test suite for ExportHandler helper methods"""

    @pytest.fixture
    def handler_with_window(self):
        """Create handler with minimal mock window"""
        window = MagicMock()
        return ExportHandler(window)

    @patch('ui.handlers.export_handler.QMessageBox.critical')
    def test_show_error(self, mock_msg, handler_with_window):
        """Test error message display"""
        # Mock tr() to return the actual string
        handler_with_window.window.tr = lambda x: x

        handler_with_window._show_error("Test error message")

        mock_msg.assert_called_once()
        # Check the message text (third argument)
        call_args = mock_msg.call_args[0]
        assert "Test error message" in call_args[2]

    def test_update_progress(self, handler_with_window):
        """Test progress update calculations"""
        mock_dialog = MagicMock()
        handler_with_window.window.progress_text_1_2 = "Processing {}/{}"

        handler_with_window._update_progress(mock_dialog, 5, 10)

        # Verify progress bar set to 50%
        mock_dialog.pb_progress.setValue.assert_called_once_with(50)

        # Verify text updated
        mock_dialog.lbl_text.setText.assert_called_once_with("Processing 5/10")
