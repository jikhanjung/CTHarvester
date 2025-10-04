"""Tests for ThumbnailCreationHandler (Phase 4.2).

This module tests the thumbnail creation handler which orchestrates
Rust and Python thumbnail generation implementations.
"""

import sys
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from ui.handlers.thumbnail_creation_handler import ThumbnailCreationHandler


class TestThumbnailCreationHandlerInitialization:
    """Tests for ThumbnailCreationHandler initialization."""

    def test_initialization_with_main_window(self):
        """Test handler initialization with main window reference."""
        mock_window = MagicMock()
        handler = ThumbnailCreationHandler(mock_window)

        assert handler.window is mock_window

    def test_initialization_stores_window_reference(self):
        """Test that window reference is accessible after initialization."""
        mock_window = MagicMock()
        handler = ThumbnailCreationHandler(mock_window)

        assert hasattr(handler, "window")
        assert handler.window == mock_window


class TestThumbnailCreationHandlerRustPythonSelection:
    """Tests for Rust/Python implementation selection logic."""

    @pytest.fixture
    def mock_window(self):
        """Create mock main window."""
        window = MagicMock()
        window.m_app = MagicMock()
        window.m_app.use_rust_thumbnail = True
        return window

    @pytest.fixture
    def handler(self, mock_window):
        """Create handler instance."""
        return ThumbnailCreationHandler(mock_window)

    def test_create_thumbnail_uses_rust_when_available(self, handler, monkeypatch):
        """Test that Rust implementation is used when available and preferred."""
        # Mock Rust module
        mock_rust = MagicMock()
        monkeypatch.setitem(sys.modules, "ct_thumbnail", mock_rust)

        # Mock create_thumbnail_rust to avoid actual execution
        handler.create_thumbnail_rust = Mock(return_value=True)

        result = handler.create_thumbnail()

        handler.create_thumbnail_rust.assert_called_once()
        assert result is True

    def test_create_thumbnail_falls_back_to_python_when_rust_missing(self, handler, monkeypatch):
        """Test fallback to Python when Rust module unavailable."""
        # Ensure ct_thumbnail is not in sys.modules
        if "ct_thumbnail" in sys.modules:
            monkeypatch.delitem(sys.modules, "ct_thumbnail")

        # Mock import to raise ImportError
        def mock_import(name, *args):
            if name == "ct_thumbnail":
                raise ImportError("Module not found")
            return __import__(name, *args)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # Mock create_thumbnail_python
        handler.create_thumbnail_python = Mock(return_value=True)

        result = handler.create_thumbnail()

        handler.create_thumbnail_python.assert_called_once()
        assert result is True

    def test_create_thumbnail_respects_user_preference_false(self, handler):
        """Test that user preference to disable Rust is respected."""
        handler.window.m_app.use_rust_thumbnail = False
        handler.create_thumbnail_python = Mock(return_value=True)

        result = handler.create_thumbnail()

        handler.create_thumbnail_python.assert_called_once()
        assert result is True

    def test_create_thumbnail_respects_user_preference_true(self, handler, monkeypatch):
        """Test that user preference to enable Rust is respected."""
        handler.window.m_app.use_rust_thumbnail = True

        # Mock Rust module
        mock_rust = MagicMock()
        monkeypatch.setitem(sys.modules, "ct_thumbnail", mock_rust)

        handler.create_thumbnail_rust = Mock(return_value=True)

        result = handler.create_thumbnail()

        handler.create_thumbnail_rust.assert_called_once()
        assert result is True

    def test_create_thumbnail_handles_missing_m_app_attribute(self, handler, monkeypatch):
        """Test graceful handling when m_app doesn't have use_rust_thumbnail."""
        # Remove the attribute
        delattr(handler.window.m_app, "use_rust_thumbnail")

        # Mock import to fail
        def mock_import(name, *args):
            if name == "ct_thumbnail":
                raise ImportError("Module not found")
            return __import__(name, *args)

        monkeypatch.setattr("builtins.__import__", mock_import)
        handler.create_thumbnail_python = Mock(return_value=True)

        result = handler.create_thumbnail()

        # Should fall back to Python after Rust import fails
        handler.create_thumbnail_python.assert_called_once()


class TestThumbnailCreationHandlerRustImplementation:
    """Tests for Rust implementation."""

    @pytest.fixture
    def mock_window(self):
        """Create comprehensive mock main window."""
        window = MagicMock()
        window.edtDirname = MagicMock()
        window.edtDirname.text.return_value = "/fake/directory"
        window.settings_hash = {
            "prefix": "img_",
            "file_type": "tif",
            "seq_begin": 0,
            "seq_end": 99,
            "index_length": 4,
        }
        window.progress_dialog = None
        window.thumbnail_start_time = None
        window.rust_cancelled = False
        window.minimum_volume = None
        window.level_info = []
        window.comboLevel = MagicMock()
        window.comboLevel.count.return_value = 0
        window.initializeComboSize = MagicMock()
        window.reset_crop = MagicMock()
        window.load_thumbnail_data_from_disk = MagicMock()
        window.comboLevelIndexChanged = MagicMock()
        window.threadpool = MagicMock()
        return window

    @pytest.fixture
    def handler(self, mock_window):
        """Create handler instance."""
        return ThumbnailCreationHandler(mock_window)

    @pytest.fixture
    def mock_rust_module(self, monkeypatch):
        """Mock ct_thumbnail Rust module."""

        def mock_build_thumbnails(dir, callback, *args):
            """Simulate Rust thumbnail generation with progress callbacks."""
            # Simulate progress from 0 to 100
            for i in range(0, 101, 20):
                if not callback(i):
                    return  # Cancelled
            return True

        mock_module = MagicMock()
        mock_module.build_thumbnails = mock_build_thumbnails
        monkeypatch.setitem(sys.modules, "ct_thumbnail", mock_module)
        return mock_module

    def test_create_thumbnail_rust_success(self, handler, mock_rust_module, qtbot):
        """Test successful Rust thumbnail generation."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.is_cancelled = False  # Not cancelled
            MockDialog.return_value = mock_dialog

            result = handler.create_thumbnail_rust()

            assert result is True
            assert handler.window.thumbnail_start_time is not None
            handler.window.load_thumbnail_data_from_disk.assert_called_once()

    def test_create_thumbnail_rust_creates_progress_dialog(self, handler, mock_rust_module, qtbot):
        """Test that progress dialog is created."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog") as MockProgressDialog:
            mock_dialog = MagicMock()
            mock_dialog.is_cancelled = False
            MockProgressDialog.return_value = mock_dialog

            handler.create_thumbnail_rust()

            MockProgressDialog.assert_called_once_with(handler.window)
            mock_dialog.show.assert_called_once()

    def test_create_thumbnail_rust_progress_callbacks(self, handler, mock_rust_module, qtbot):
        """Test that progress callbacks are invoked correctly."""
        progress_values = []

        def mock_build_thumbnails(dir, callback, *args):
            """Track progress callback invocations."""
            for i in range(0, 101, 25):
                progress_values.append(i)
                if not callback(i):
                    return False
            return True

        mock_rust_module.build_thumbnails = mock_build_thumbnails

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.is_cancelled = False
            MockDialog.return_value = mock_dialog

            handler.create_thumbnail_rust()

            assert progress_values == [0, 25, 50, 75, 100]

    def test_create_thumbnail_rust_cancellation(self, handler, monkeypatch, qtbot):
        """Test cancellation during Rust generation."""

        # Mock Rust to check for cancellation
        def mock_build_thumbnails(dir, callback, *args):
            callback(10)
            callback(20)
            # Simulate user cancellation
            handler.window.rust_cancelled = True
            return callback(30)  # Should return False

        mock_module = MagicMock()
        mock_module.build_thumbnails = mock_build_thumbnails
        monkeypatch.setitem(sys.modules, "ct_thumbnail", mock_module)

        mock_progress = MagicMock()
        mock_progress.is_cancelled = True
        handler.window.progress_dialog = mock_progress

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            result = handler.create_thumbnail_rust()

            # Should return False on cancellation
            assert result is False
            # Should not load thumbnails
            handler.window.load_thumbnail_data_from_disk.assert_not_called()

    def test_create_thumbnail_rust_error_handling(self, handler, monkeypatch, qtbot):
        """Test error handling when Rust generation fails."""

        def mock_build_thumbnails(dir, callback, *args):
            raise RuntimeError("Rust module error")

        mock_module = MagicMock()
        mock_module.build_thumbnails = mock_build_thumbnails
        monkeypatch.setitem(sys.modules, "ct_thumbnail", mock_module)

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            with patch("ui.handlers.thumbnail_creation_handler.QMessageBox") as MockMessageBox:
                result = handler.create_thumbnail_rust()

                # Should handle error gracefully
                assert result is False
                # Should show warning
                MockMessageBox.warning.assert_called_once()

    def test_create_thumbnail_rust_initializes_combo_boxes(self, handler, mock_rust_module, qtbot):
        """Test that combo boxes are initialized after generation."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog") as MockDialog:
            mock_dialog = MagicMock()
            mock_dialog.is_cancelled = False
            MockDialog.return_value = mock_dialog

            handler.create_thumbnail_rust()

            handler.window.initializeComboSize.assert_called_once()
            handler.window.reset_crop.assert_called_once()

    def test_create_thumbnail_rust_closes_progress_dialog(self, handler, mock_rust_module, qtbot):
        """Test that progress dialog is closed after completion."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog") as MockProgressDialog:
            mock_dialog = MagicMock()
            mock_dialog.is_cancelled = False
            MockProgressDialog.return_value = mock_dialog

            handler.create_thumbnail_rust()

            mock_dialog.close.assert_called_once()


class TestThumbnailCreationHandlerPythonImplementation:
    """Tests for Python fallback implementation."""

    @pytest.fixture
    def mock_window(self):
        """Create mock main window for Python tests."""
        window = MagicMock()
        window.edtDirname = MagicMock()
        window.edtDirname.text.return_value = "/fake/directory"
        window.settings_hash = {
            "image_width": 1024,
            "image_height": 1024,
            "seq_begin": 0,
            "seq_end": 99,
        }
        window.progress_dialog = None
        window.thumbnail_generator = MagicMock()
        window.thumbnail_generator.calculate_total_thumbnail_work = MagicMock(return_value=1000)
        window.thumbnail_generator.weighted_total_work = 1000
        window.thumbnail_generator.generate_python = MagicMock(
            return_value={"success": True, "minimum_volume": [], "level_info": []}
        )
        window.threadpool = MagicMock()
        window.minimum_volume = []
        window.level_info = []
        window.comboLevel = MagicMock()
        window.comboLevel.count.return_value = 1
        window.initializeComboSize = MagicMock()
        window.reset_crop = MagicMock()
        window.load_thumbnail_data_from_disk = MagicMock()
        window.comboLevelIndexChanged = MagicMock()
        window.update_3D_view = MagicMock()
        window.initialized = False
        return window

    @pytest.fixture
    def handler(self, mock_window):
        """Create handler instance."""
        return ThumbnailCreationHandler(mock_window)

    def test_create_thumbnail_python_success(self, handler, qtbot):
        """Test successful Python thumbnail generation."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            result = handler.create_thumbnail_python()

            assert result is True
            handler.window.thumbnail_generator.generate_python.assert_called_once()

    def test_create_thumbnail_python_creates_progress_dialog(self, handler, qtbot):
        """Test that progress dialog is created for Python generation."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog") as MockProgressDialog:
            mock_dialog = MagicMock()
            MockProgressDialog.return_value = mock_dialog

            handler.create_thumbnail_python()

            MockProgressDialog.assert_called_once_with(handler.window)

    def test_create_thumbnail_python_calls_thumbnail_generator(self, handler, qtbot):
        """Test that ThumbnailGenerator.generate_python is called correctly."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            handler.create_thumbnail_python()

            handler.window.thumbnail_generator.generate_python.assert_called_once()
            call_kwargs = handler.window.thumbnail_generator.generate_python.call_args.kwargs

            assert call_kwargs["directory"] == "/fake/directory"
            assert call_kwargs["settings"] == handler.window.settings_hash
            assert call_kwargs["threadpool"] == handler.window.threadpool

    def test_create_thumbnail_python_handles_cancellation(self, handler, qtbot):
        """Test handling of user cancellation during Python generation."""
        handler.window.thumbnail_generator.generate_python.return_value = {
            "success": False,
            "cancelled": True,
        }

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            with patch("ui.handlers.thumbnail_creation_handler.QMessageBox") as MockMessageBox:
                result = handler.create_thumbnail_python()

                assert result is False
                MockMessageBox.information.assert_called_once()

    def test_create_thumbnail_python_handles_failure(self, handler, qtbot):
        """Test handling of generation failure."""
        handler.window.thumbnail_generator.generate_python.return_value = {
            "success": False,
            "cancelled": False,
            "error": "Test error message",
        }

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            with patch("ui.handlers.thumbnail_creation_handler.QMessageBox") as MockMessageBox:
                result = handler.create_thumbnail_python()

                assert result is False
                MockMessageBox.critical.assert_called_once()

    def test_create_thumbnail_python_handles_none_return(self, handler, qtbot):
        """Test handling when generate_python returns None."""
        handler.window.thumbnail_generator.generate_python.return_value = None

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            with patch("ui.handlers.thumbnail_creation_handler.QMessageBox") as MockMessageBox:
                result = handler.create_thumbnail_python()

                assert result is False
                MockMessageBox.critical.assert_called_once()

    def test_create_thumbnail_python_updates_state_on_success(self, handler, qtbot):
        """Test that instance state is updated on successful generation."""
        test_volume = [1, 2, 3]
        test_level_info = [{"name": "Level 0"}]

        handler.window.thumbnail_generator.generate_python.return_value = {
            "success": True,
            "minimum_volume": test_volume,
            "level_info": test_level_info,
        }

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            handler.create_thumbnail_python()

            assert handler.window.minimum_volume == test_volume
            assert handler.window.level_info == test_level_info

    def test_create_thumbnail_python_initializes_ui_components(self, handler, qtbot):
        """Test that UI components are initialized after generation."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            handler.create_thumbnail_python()

            handler.window.load_thumbnail_data_from_disk.assert_called_once()
            handler.window.initializeComboSize.assert_called_once()
            handler.window.reset_crop.assert_called_once()

    def test_create_thumbnail_python_triggers_initial_display(self, handler, qtbot):
        """Test that initial display is triggered after generation."""
        handler.window.comboLevel.count.return_value = 2

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            handler.create_thumbnail_python()

            handler.window.comboLevel.setCurrentIndex.assert_called_once_with(0)
            handler.window.comboLevelIndexChanged.assert_called_once()
            handler.window.update_3D_view.assert_called_once_with(False)

    def test_create_thumbnail_python_closes_progress_dialog(self, handler, qtbot):
        """Test that progress dialog is properly closed."""
        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog") as MockProgressDialog:
            mock_dialog = MagicMock()
            MockProgressDialog.return_value = mock_dialog

            handler.create_thumbnail_python()

            mock_dialog.close.assert_called()

    def test_create_thumbnail_python_handles_exception(self, handler, qtbot):
        """Test handling of unexpected exceptions."""
        handler.window.thumbnail_generator.generate_python.side_effect = RuntimeError(
            "Unexpected error"
        )

        with patch("ui.handlers.thumbnail_creation_handler.ProgressDialog"):
            result = handler.create_thumbnail_python()

            assert result is False


class TestThumbnailCreationHandlerEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.fixture
    def mock_window(self):
        """Create mock window."""
        window = MagicMock()
        window.m_app = MagicMock()
        window.m_app.use_rust_thumbnail = True
        return window

    @pytest.fixture
    def handler(self, mock_window):
        """Create handler instance."""
        return ThumbnailCreationHandler(mock_window)

    def test_handler_with_none_window(self):
        """Test that handler handles None window gracefully."""
        # This should not crash
        handler = ThumbnailCreationHandler(None)
        assert handler.window is None

    def test_create_thumbnail_without_m_app(self, handler, monkeypatch):
        """Test behavior when window.m_app is None."""
        handler.window.m_app = None

        # Mock import to fail
        def mock_import(name, *args):
            if name == "ct_thumbnail":
                raise ImportError("Module not found")
            return __import__(name, *args)

        monkeypatch.setattr("builtins.__import__", mock_import)
        handler.create_thumbnail_python = Mock(return_value=True)

        # Will try Rust first (default True), fail import, then Python
        result = handler.create_thumbnail()

        handler.create_thumbnail_python.assert_called_once()
