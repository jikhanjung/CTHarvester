"""Tests for DirectoryOpenHandler (Phase 4.3).

This module tests the directory opening handler which manages
directory selection dialogs and CT image stack initialization.
"""

import logging
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from ui.handlers.directory_open_handler import DirectoryOpenHandler


# Mock wait_cursor to avoid Qt GUI interactions in tests
@contextmanager
def mock_wait_cursor():
    """Mock wait_cursor context manager that does nothing."""
    yield


@patch("ui.handlers.directory_open_handler.wait_cursor", mock_wait_cursor)
class TestDirectoryOpenHandlerInitialization:
    """Tests for DirectoryOpenHandler initialization."""

    def test_initialization_with_main_window(self):
        """Test handler initialization with main window reference."""
        mock_window = MagicMock()

        handler = DirectoryOpenHandler(mock_window)

        assert handler.window is mock_window

    def test_initialization_stores_window_reference(self):
        """Test that window reference is properly stored."""
        mock_window = MagicMock()
        mock_window.file_handler = MagicMock()
        mock_window.m_app = MagicMock()

        handler = DirectoryOpenHandler(mock_window)

        # Should be able to access window attributes
        assert handler.window.file_handler is not None
        assert handler.window.m_app is not None


@patch("ui.handlers.directory_open_handler.wait_cursor", mock_wait_cursor)
@patch("ui.errors.QMessageBox")  # QMessageBox now imported in ui.errors
@patch("ui.handlers.directory_open_handler.QFileDialog")
class TestDirectoryOpenHandlerDialogHandling:
    """Tests for directory dialog handling."""

    @pytest.fixture
    def mock_window(self):
        """Create mock main window with necessary attributes."""
        window = MagicMock()
        window.m_app = MagicMock()
        window.m_app.default_directory = "/default/path"
        window.file_handler = MagicMock()
        window.edtDirname = MagicMock()
        window.edtNumImages = MagicMock()
        window.edtImageDimension = MagicMock()
        window.tr = lambda x: x
        return window

    @pytest.fixture
    def handler(self, mock_window):
        """Create DirectoryOpenHandler instance."""
        return DirectoryOpenHandler(mock_window)

    def test_open_directory_shows_dialog(
        self, MockFileDialog, MockMessageBox, handler, mock_window
    ):
        """Test that directory dialog is shown."""
        MockFileDialog.getExistingDirectory.return_value = ""

        handler.open_directory()

        # Should show dialog with default directory
        MockFileDialog.getExistingDirectory.assert_called_once()
        call_args = MockFileDialog.getExistingDirectory.call_args
        assert call_args[0][2] == "/default/path"

    def test_open_directory_cancellation(
        self, MockFileDialog, MockMessageBox, handler, mock_window
    ):
        """Test that cancelling dialog returns early."""
        MockFileDialog.getExistingDirectory.return_value = ""

        handler.open_directory()

        # Should return early without calling file_handler
        mock_window.file_handler.open_directory.assert_not_called()

    def test_open_directory_updates_path(
        self, MockFileDialog, MockMessageBox, handler, mock_window
    ):
        """Test that selected path updates UI."""
        MockFileDialog.getExistingDirectory.return_value = "/test/path"
        mock_window.file_handler.open_directory.return_value = None

        handler.open_directory()

        # Should set directory in UI
        mock_window.edtDirname.setText.assert_called_once_with("/test/path")

    def test_open_directory_updates_default_directory(
        self, MockFileDialog, MockMessageBox, handler, mock_window
    ):
        """Test that default directory is updated."""
        MockFileDialog.getExistingDirectory.return_value = "/test/subdir"
        mock_window.file_handler.open_directory.return_value = None

        handler.open_directory()

        # Should update app's default directory to parent
        assert mock_window.m_app.default_directory == "/test"


@patch("ui.handlers.directory_open_handler.wait_cursor", mock_wait_cursor)
@patch("ui.handlers.directory_open_handler.QFileDialog")
@patch("ui.errors.QMessageBox")
class TestDirectoryOpenHandlerValidation:
    """Tests for directory validation logic."""

    @pytest.fixture
    def mock_window(self):
        """Create mock main window."""
        window = MagicMock()
        window.m_app = MagicMock()
        window.m_app.default_directory = "/default"
        window.file_handler = MagicMock()
        window.edtDirname = MagicMock()
        window.edtNumImages = MagicMock()
        window.edtImageDimension = MagicMock()
        window.tr = lambda x: x
        window._reset_ui_state = MagicMock()
        window._load_first_image = MagicMock()
        window._load_existing_thumbnail_levels = MagicMock()
        window.create_thumbnail = MagicMock()
        return window

    @pytest.fixture
    def handler(self, mock_window):
        """Create handler."""
        return DirectoryOpenHandler(mock_window)

    def test_open_directory_valid_ct_stack(
        self, MockMessageBox, MockFileDialog, handler, mock_window
    ):
        """Test opening directory with valid CT image stack."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"
        mock_window.file_handler.open_directory.return_value = {
            "prefix": "img_",
            "file_type": "tif",
            "seq_begin": 0,
            "seq_end": 99,
            "image_width": 512,
            "image_height": 512,
            "index_length": 4,
        }
        mock_window.file_handler.get_file_list.return_value = [
            f"img_{i:04d}.tif" for i in range(100)
        ]

        handler.open_directory()

        # Should analyze directory
        mock_window.file_handler.open_directory.assert_called_once_with("/test/dir")
        # Should not show warning
        MockMessageBox.warning.assert_not_called()
        # Should trigger thumbnail generation
        mock_window.create_thumbnail.assert_called_once()

    def test_open_directory_no_images_warning(
        self, MockMessageBox, MockFileDialog, handler, mock_window
    ):
        """Test that warning is shown when no valid images found."""
        MockFileDialog.getExistingDirectory.return_value = "/empty/dir"
        mock_window.file_handler.open_directory.return_value = None

        handler.open_directory()

        # Should show warning via show_error
        MockMessageBox.assert_called_once()  # Now calls show_error
        # Should not trigger thumbnail generation
        mock_window.create_thumbnail.assert_not_called()

    def test_open_directory_invalid_path(
        self, MockMessageBox, MockFileDialog, handler, mock_window
    ):
        """Test handling of invalid directory path."""
        MockFileDialog.getExistingDirectory.return_value = "/nonexistent/dir"
        mock_window.file_handler.open_directory.return_value = None

        handler.open_directory()

        # Should return without crashing
        MockMessageBox.assert_called_once()  # Now calls show_error


@patch("ui.handlers.directory_open_handler.wait_cursor", mock_wait_cursor)
@patch("ui.handlers.directory_open_handler.QFileDialog")
class TestDirectoryOpenHandlerUIUpdates:
    """Tests for UI state updates."""

    @pytest.fixture
    def mock_window(self):
        """Create mock window for UI tests."""
        window = MagicMock()
        window.m_app = MagicMock()
        window.m_app.default_directory = "/default"
        window.file_handler = MagicMock()
        window.file_handler.open_directory.return_value = {
            "prefix": "slice_",
            "file_type": "tif",
            "seq_begin": 10,
            "seq_end": 109,
            "image_width": 1024,
            "image_height": 768,
            "index_length": 4,
        }
        window.file_handler.get_file_list.return_value = [
            f"slice_{i:04d}.tif" for i in range(10, 110)
        ]
        window.edtDirname = MagicMock()
        window.edtNumImages = MagicMock()
        window.edtImageDimension = MagicMock()
        window.tr = lambda x: x
        window._reset_ui_state = MagicMock()
        window._load_first_image = MagicMock()
        window._load_existing_thumbnail_levels = MagicMock()
        window.create_thumbnail = MagicMock()
        return window

    @pytest.fixture
    def handler(self, mock_window):
        """Create handler."""
        return DirectoryOpenHandler(mock_window)

    def test_ui_state_reset(self, MockFileDialog, handler, mock_window):
        """Test that UI state is reset before loading."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # Should reset UI state
        mock_window._reset_ui_state.assert_called_once()
        # initialized should be set to False during reset
        # settings_hash gets populated after reset, so it will have values at the end
        assert mock_window.initialized is False

    def test_ui_updates_image_info(self, MockFileDialog, handler, mock_window):
        """Test that image info is updated in UI."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # Should update number of images (seq_end - seq_begin + 1)
        mock_window.edtNumImages.setText.assert_called_once_with("100")
        # Should update image dimensions
        mock_window.edtImageDimension.setText.assert_called_once_with("1024 x 768")

    def test_ui_updates_level_info(self, MockFileDialog, handler, mock_window):
        """Test that level_info is initialized."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # Should initialize level_info with original level
        assert mock_window.level_info == [
            {
                "name": "Original",
                "width": 1024,
                "height": 768,
                "seq_begin": 10,
                "seq_end": 109,
            }
        ]

    def test_original_indices_set(self, MockFileDialog, handler, mock_window):
        """Test that original indices are set correctly."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # 100 images (0-99 indices)
        assert mock_window.original_from_idx == 0
        assert mock_window.original_to_idx == 99


@patch("ui.handlers.directory_open_handler.wait_cursor", mock_wait_cursor)
@patch("ui.handlers.directory_open_handler.QFileDialog")
class TestDirectoryOpenHandlerIntegration:
    """Tests for integration with other components."""

    @pytest.fixture
    def mock_window(self):
        """Create fully mocked window."""
        window = MagicMock()
        window.m_app = MagicMock()
        window.m_app.default_directory = "/default"
        window.file_handler = MagicMock()
        window.file_handler.open_directory.return_value = {
            "prefix": "img_",
            "file_type": "tif",
            "seq_begin": 0,
            "seq_end": 49,
            "image_width": 512,
            "image_height": 512,
            "index_length": 4,
        }
        window.file_handler.get_file_list.return_value = [f"img_{i:04d}.tif" for i in range(50)]
        window.edtDirname = MagicMock()
        window.edtNumImages = MagicMock()
        window.edtImageDimension = MagicMock()
        window.tr = lambda x: x
        window._reset_ui_state = MagicMock()
        window._load_first_image = MagicMock()
        window._load_existing_thumbnail_levels = MagicMock()
        window.create_thumbnail = MagicMock()
        return window

    @pytest.fixture
    def handler(self, mock_window):
        """Create handler."""
        return DirectoryOpenHandler(mock_window)

    def test_thumbnail_generation_triggered(self, MockFileDialog, handler, mock_window):
        """Test that thumbnail generation is initiated."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # Should call create_thumbnail at the end
        mock_window.create_thumbnail.assert_called_once()

    def test_settings_persistence(self, MockFileDialog, handler, mock_window):
        """Test that settings are stored in window."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # settings_hash should be populated
        assert mock_window.settings_hash == {
            "prefix": "img_",
            "file_type": "tif",
            "seq_begin": 0,
            "seq_end": 49,
            "image_width": 512,
            "image_height": 512,
            "index_length": 4,
        }

    def test_existing_thumbnails_loaded(self, MockFileDialog, handler, mock_window):
        """Test that existing thumbnail levels are detected."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # Should check for existing thumbnails
        mock_window._load_existing_thumbnail_levels.assert_called_once_with("/test/dir")

    def test_first_image_preview_loaded(self, MockFileDialog, handler, mock_window):
        """Test that first image is loaded for preview."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # Should load first image
        mock_window._load_first_image.assert_called_once()
        call_args = mock_window._load_first_image.call_args
        assert call_args[0][0] == "/test/dir"
        # Second arg should be file list
        assert len(call_args[0][1]) == 50

    def test_file_handler_integration(self, MockFileDialog, handler, mock_window):
        """Test integration with FileHandler."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"

        handler.open_directory()

        # Should call file_handler methods
        mock_window.file_handler.open_directory.assert_called_once_with("/test/dir")
        mock_window.file_handler.get_file_list.assert_called_once()


@patch("ui.handlers.directory_open_handler.wait_cursor", mock_wait_cursor)
class TestDirectoryOpenHandlerLogging:
    """Tests for logging behavior."""

    @pytest.fixture
    def handler(self):
        """Create handler for logging tests."""
        mock_window = MagicMock()
        return DirectoryOpenHandler(mock_window)

    @patch("ui.handlers.directory_open_handler.QFileDialog")
    def test_logs_directory_selection_start(self, MockFileDialog, handler, caplog):
        """Test that directory selection start is logged."""
        MockFileDialog.getExistingDirectory.return_value = ""

        with caplog.at_level(logging.INFO):
            handler.open_directory()

        assert "open_dir method called - START" in caplog.text

    @patch("ui.handlers.directory_open_handler.QFileDialog")
    def test_logs_cancellation(self, MockFileDialog, handler, caplog):
        """Test that cancellation is logged."""
        MockFileDialog.getExistingDirectory.return_value = ""

        with caplog.at_level(logging.INFO):
            handler.open_directory()

        assert "Directory selection cancelled" in caplog.text

    @patch("ui.handlers.directory_open_handler.QFileDialog")
    @patch("ui.errors.QMessageBox")
    def test_logs_no_valid_images(self, MockMessageBox, MockFileDialog, handler, caplog):
        """Test that no valid images warning is logged."""
        from core.file_handler import NoImagesFoundError

        MockFileDialog.getExistingDirectory.return_value = "/empty/dir"
        handler.window.m_app = MagicMock()
        handler.window.m_app.default_directory = "/default"
        handler.window.file_handler = MagicMock()
        handler.window.file_handler.open_directory.side_effect = NoImagesFoundError(
            "No files found"
        )
        handler.window.edtDirname = MagicMock()
        handler.window.tr = lambda x: x
        handler.window._reset_ui_state = MagicMock()

        with caplog.at_level(logging.WARNING):
            handler.open_directory()

        assert "No valid image files found" in caplog.text

    @patch("ui.handlers.directory_open_handler.QFileDialog")
    def test_logs_successful_load(self, MockFileDialog, handler, caplog):
        """Test that successful directory load is logged."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"
        handler.window.m_app = MagicMock()
        handler.window.m_app.default_directory = "/default"
        handler.window.file_handler = MagicMock()
        handler.window.file_handler.open_directory.return_value = {
            "prefix": "img_",
            "seq_begin": 0,
            "seq_end": 49,
            "image_width": 512,
            "image_height": 512,
        }
        handler.window.file_handler.get_file_list.return_value = [
            f"img_{i:04d}.tif" for i in range(50)
        ]
        handler.window.edtDirname = MagicMock()
        handler.window.edtNumImages = MagicMock()
        handler.window.edtImageDimension = MagicMock()
        handler.window.tr = lambda x: x
        handler.window._reset_ui_state = MagicMock()
        handler.window._load_first_image = MagicMock()
        handler.window._load_existing_thumbnail_levels = MagicMock()
        handler.window.create_thumbnail = MagicMock()

        with caplog.at_level(logging.INFO):
            handler.open_directory()

        assert "Successfully loaded directory with 50 images" in caplog.text
        assert "Selected directory: /test/dir" in caplog.text
        assert "prefix=img_" in caplog.text
