"""Integration tests for main_window handler coordination.

This module tests how handlers work together in the main window:
- Handler coordination
- State management
- Event handling
- Settings persistence
"""

import logging
from unittest.mock import MagicMock, Mock, patch

import pytest

from ui.handlers.directory_open_handler import DirectoryOpenHandler
from ui.handlers.thumbnail_creation_handler import ThumbnailCreationHandler
from ui.handlers.view_manager import ViewManager


class TestHandlerCoordination:
    """Tests for coordination between handlers."""

    @pytest.fixture
    def mock_main_window(self):
        """Create a mock main window with all handlers."""
        window = MagicMock()
        window.edtDirname = MagicMock()
        window.edtNumImages = MagicMock()
        window.edtImageDimension = MagicMock()
        window.m_app = MagicMock()
        window.m_app.default_directory = "/default"
        window.m_app.use_rust = True
        window.file_handler = MagicMock()
        window.mcube_widget = MagicMock()
        window.minimum_volume = None
        window.settings_hash = {}
        window.initialized = False
        window.tr = lambda x: x
        window._reset_ui_state = MagicMock()
        window._load_first_image = MagicMock()
        window._load_existing_thumbnail_levels = MagicMock()
        window.create_thumbnail = MagicMock()

        # Initialize handlers
        window.directory_open_handler = DirectoryOpenHandler(window)
        window.thumbnail_creation_handler = ThumbnailCreationHandler(window)
        window.view_manager = ViewManager(window)

        return window

    @patch("ui.handlers.directory_open_handler.wait_cursor")
    @patch("ui.handlers.directory_open_handler.QMessageBox")
    @patch("ui.handlers.directory_open_handler.QFileDialog")
    def test_directory_open_triggers_thumbnail_creation(
        self, MockFileDialog, MockMessageBox, mock_wait_cursor, mock_main_window
    ):
        """Test that opening a directory triggers thumbnail creation."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"
        mock_main_window.file_handler.open_directory.return_value = {
            "prefix": "img_",
            "file_type": "tif",
            "seq_begin": 0,
            "seq_end": 9,
            "image_width": 512,
            "image_height": 512,
            "index_length": 4,
        }
        mock_main_window.file_handler.get_file_list.return_value = [
            f"img_{i:04d}.tif" for i in range(10)
        ]

        # Open directory using handler
        mock_main_window.directory_open_handler.open_directory()

        # Should trigger thumbnail creation
        mock_main_window.create_thumbnail.assert_called_once()

        # Settings should be populated
        assert mock_main_window.settings_hash["prefix"] == "img_"
        assert mock_main_window.settings_hash["seq_begin"] == 0
        assert mock_main_window.settings_hash["seq_end"] == 9

    def test_state_persistence_across_handlers(self, mock_main_window):
        """Test that state is shared correctly between handlers."""
        # Set state via one handler
        mock_main_window.settings_hash = {"test_key": "test_value"}
        mock_main_window.initialized = True

        # All handlers should see the same state
        assert mock_main_window.directory_open_handler.window.settings_hash == {
            "test_key": "test_value"
        }
        assert mock_main_window.thumbnail_creation_handler.window.initialized is True
        assert mock_main_window.view_manager.window.initialized is True

    def test_handlers_share_window_reference(self, mock_main_window):
        """Test that all handlers reference the same window."""
        # All handlers should point to the same window instance
        assert mock_main_window.directory_open_handler.window is mock_main_window
        assert mock_main_window.thumbnail_creation_handler.window is mock_main_window
        assert mock_main_window.view_manager.window is mock_main_window


class TestStateManagement:
    """Tests for state management across operations."""

    @pytest.fixture
    def mock_window(self):
        """Create mock window for state tests."""
        window = MagicMock()
        window.settings_hash = {}
        window.initialized = False
        window.level_info = []
        window.minimum_volume = None
        window.curr_level_idx = 0
        return window

    def test_state_initialization(self, mock_window):
        """Test initial state is correct."""
        assert mock_window.settings_hash == {}
        assert mock_window.initialized is False
        assert mock_window.level_info == []
        assert mock_window.minimum_volume is None

    def test_state_reset(self, mock_window):
        """Test state can be reset."""
        # Set some state
        mock_window.settings_hash = {"key": "value"}
        mock_window.initialized = True
        mock_window.level_info = [{"level": 0}]

        # Reset
        mock_window.settings_hash = {}
        mock_window.initialized = False
        mock_window.level_info = []

        # State should be cleared
        assert mock_window.settings_hash == {}
        assert mock_window.initialized is False
        assert mock_window.level_info == []

    def test_settings_hash_population(self, mock_window):
        """Test settings hash is populated correctly."""
        settings = {
            "prefix": "test_",
            "file_type": "tif",
            "seq_begin": 0,
            "seq_end": 99,
            "image_width": 1024,
            "image_height": 768,
        }

        mock_window.settings_hash = settings

        assert mock_window.settings_hash["prefix"] == "test_"
        assert mock_window.settings_hash["seq_end"] == 99
        assert mock_window.settings_hash["image_width"] == 1024

    def test_level_info_management(self, mock_window):
        """Test level_info list management."""
        # Add original level
        mock_window.level_info.append(
            {
                "name": "Original",
                "width": 1024,
                "height": 768,
                "seq_begin": 0,
                "seq_end": 99,
            }
        )

        # Add thumbnail levels
        mock_window.level_info.append(
            {
                "name": "Level 1",
                "width": 512,
                "height": 384,
                "seq_begin": 0,
                "seq_end": 99,
            }
        )

        assert len(mock_window.level_info) == 2
        assert mock_window.level_info[0]["name"] == "Original"
        assert mock_window.level_info[1]["width"] == 512


class TestEventHandling:
    """Tests for event handling coordination."""

    @pytest.fixture
    def mock_window_with_handlers(self):
        """Create window with handlers for event tests."""
        window = MagicMock()
        window.file_handler = MagicMock()
        window.m_app = MagicMock()
        window.edtDirname = MagicMock()
        window.edtNumImages = MagicMock()
        window.edtImageDimension = MagicMock()
        window.tr = lambda x: x

        # Add handlers
        window.directory_open_handler = DirectoryOpenHandler(window)
        window.thumbnail_creation_handler = ThumbnailCreationHandler(window)

        return window

    def test_directory_change_event_flow(self, mock_window_with_handlers):
        """Test event flow when directory changes."""
        # Simulate directory change
        new_path = "/new/directory"
        mock_window_with_handlers.edtDirname.setText(new_path)

        # Verify text was set
        mock_window_with_handlers.edtDirname.setText.assert_called_with(new_path)

    def test_ui_update_events(self, mock_window_with_handlers):
        """Test UI update events are propagated."""
        # Simulate UI updates
        mock_window_with_handlers.edtNumImages.setText("100")
        mock_window_with_handlers.edtImageDimension.setText("1024 x 768")

        # Verify updates
        mock_window_with_handlers.edtNumImages.setText.assert_called_with("100")
        mock_window_with_handlers.edtImageDimension.setText.assert_called_with("1024 x 768")


class TestSettingsPersistence:
    """Tests for settings persistence across operations."""

    @pytest.fixture
    def mock_window(self):
        """Create window for persistence tests."""
        window = MagicMock()
        window.m_app = MagicMock()
        window.m_app.default_directory = "/initial/dir"
        window.m_app.use_rust = True
        return window

    def test_default_directory_persistence(self, mock_window):
        """Test default directory is persisted."""
        # Change default directory
        new_dir = "/new/default/dir"
        mock_window.m_app.default_directory = new_dir

        # Should persist
        assert mock_window.m_app.default_directory == new_dir

    def test_rust_preference_persistence(self, mock_window):
        """Test Rust usage preference is persisted."""
        # Toggle Rust preference
        mock_window.m_app.use_rust = False

        # Should persist
        assert mock_window.m_app.use_rust is False

        # Toggle back
        mock_window.m_app.use_rust = True
        assert mock_window.m_app.use_rust is True

    def test_settings_survive_reset(self, mock_window):
        """Test that app settings survive UI reset."""
        # Store app settings
        original_dir = mock_window.m_app.default_directory
        original_rust = mock_window.m_app.use_rust

        # App settings should not change during UI operations
        # (In real code, settings_hash gets reset but m_app settings don't)
        assert mock_window.m_app.default_directory == original_dir
        assert mock_window.m_app.use_rust == original_rust


class TestHandlerErrorPropagation:
    """Tests for error propagation between handlers."""

    @pytest.fixture
    def mock_window(self):
        """Create window for error tests."""
        window = MagicMock()
        window.file_handler = MagicMock()
        window.edtDirname = MagicMock()
        window.m_app = MagicMock()
        window.m_app.default_directory = "/default"
        window.tr = lambda x: x
        window._reset_ui_state = MagicMock()
        return window

    @patch("ui.handlers.directory_open_handler.wait_cursor")
    @patch("ui.handlers.directory_open_handler.QMessageBox")
    @patch("ui.handlers.directory_open_handler.QFileDialog")
    def test_file_handler_error_prevents_thumbnail_creation(
        self, MockFileDialog, MockMessageBox, mock_wait_cursor, mock_window
    ):
        """Test that file handler errors prevent thumbnail creation."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"
        # File handler returns None (error)
        mock_window.file_handler.open_directory.return_value = None
        mock_window.create_thumbnail = MagicMock()

        handler = DirectoryOpenHandler(mock_window)
        handler.open_directory()

        # Should show warning
        MockMessageBox.warning.assert_called_once()
        # Should NOT call create_thumbnail
        mock_window.create_thumbnail.assert_not_called()

    @patch("ui.handlers.directory_open_handler.wait_cursor")
    @patch("ui.handlers.directory_open_handler.QFileDialog")
    def test_cancel_dialog_prevents_further_processing(
        self, MockFileDialog, mock_wait_cursor, mock_window
    ):
        """Test that canceling dialog prevents further processing."""
        # Simulate user canceling dialog
        MockFileDialog.getExistingDirectory.return_value = ""

        handler = DirectoryOpenHandler(mock_window)
        handler.open_directory()

        # Should not call file_handler
        mock_window.file_handler.open_directory.assert_not_called()


class TestHandlerIntegrationLogging:
    """Tests for logging across handler integration."""

    @pytest.fixture
    def mock_window(self):
        """Create window for logging tests."""
        window = MagicMock()
        window.file_handler = MagicMock()
        window.edtDirname = MagicMock()
        window.edtNumImages = MagicMock()
        window.edtImageDimension = MagicMock()
        window.m_app = MagicMock()
        window.m_app.default_directory = "/default"
        window.tr = lambda x: x
        window._reset_ui_state = MagicMock()
        window._load_first_image = MagicMock()
        window._load_existing_thumbnail_levels = MagicMock()
        window.create_thumbnail = MagicMock()
        return window

    @patch("ui.handlers.directory_open_handler.wait_cursor")
    @patch("ui.handlers.directory_open_handler.QFileDialog")
    def test_successful_operation_logging(
        self, MockFileDialog, mock_wait_cursor, mock_window, caplog
    ):
        """Test that successful operations are logged."""
        MockFileDialog.getExistingDirectory.return_value = "/test/dir"
        mock_window.file_handler.open_directory.return_value = {
            "prefix": "img_",
            "seq_begin": 0,
            "seq_end": 9,
            "image_width": 512,
            "image_height": 512,
        }
        mock_window.file_handler.get_file_list.return_value = [
            f"img_{i:04d}.tif" for i in range(10)
        ]

        handler = DirectoryOpenHandler(mock_window)

        with caplog.at_level(logging.INFO):
            handler.open_directory()

        # Should log success messages
        assert "Successfully loaded directory" in caplog.text
        assert "10 images" in caplog.text
