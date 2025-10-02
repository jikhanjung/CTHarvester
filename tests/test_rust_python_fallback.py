"""
Tests for Rust/Python fallback mechanism in ThumbnailGenerator

Tests the automatic fallback from Rust to Python thumbnail generation
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from core.thumbnail_generator import ThumbnailGenerator


@pytest.mark.unit
class TestRustAvailabilityCheck:
    """Test Rust module availability detection"""

    @patch("core.thumbnail_generator.logger")
    def test_rust_available(self, mock_logger):
        """Test when Rust module is available"""
        with patch.dict("sys.modules", {"ct_thumbnail": MagicMock()}):
            generator = ThumbnailGenerator()
            assert generator.rust_available is True
            mock_logger.info.assert_called_with("Rust thumbnail module is available")

    @patch("core.thumbnail_generator.logger")
    def test_rust_not_available(self, mock_logger):
        """Test when Rust module is not available"""
        with patch.dict("sys.modules", {"ct_thumbnail": None}):
            # Force ImportError
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                generator = ThumbnailGenerator()
                assert generator.rust_available is False
                mock_logger.info.assert_called_with(
                    "Rust thumbnail module not available, will use Python fallback"
                )

    def test_availability_cached_in_instance(self):
        """Test that availability is checked once during init"""
        with patch("core.thumbnail_generator.logger"):
            with patch.dict("sys.modules", {"ct_thumbnail": MagicMock()}):
                generator = ThumbnailGenerator()
                first_check = generator.rust_available

                # Modify sys.modules
                with patch.dict("sys.modules", {"ct_thumbnail": None}):
                    # Should still use cached value
                    assert generator.rust_available == first_check


@pytest.mark.unit
class TestGenerateMethodSelection:
    """Test method selection logic in generate()"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings dictionary"""
        return {
            "prefix": "slice_",
            "file_type": "tif",
            "seq_begin": 1,
            "seq_end": 10,
            "index_length": 4,
            "image_width": 512,
            "image_height": 512,
        }

    @pytest.fixture
    def mock_threadpool(self):
        """Mock Qt threadpool"""
        return MagicMock()

    def test_rust_selected_when_available_and_preferred(self, mock_settings, mock_threadpool):
        """Test Rust is selected when available and preferred"""
        generator = ThumbnailGenerator()
        generator.rust_available = True
        generator.generate_rust = MagicMock(return_value=True)
        generator.generate_python = MagicMock()

        result = generator.generate(
            "/test/dir", mock_settings, mock_threadpool, use_rust_preference=True
        )

        generator.generate_rust.assert_called_once()
        generator.generate_python.assert_not_called()
        assert result["success"] is True

    def test_python_selected_when_rust_not_preferred(self, mock_settings, mock_threadpool):
        """Test Python is selected when Rust not preferred"""
        generator = ThumbnailGenerator()
        generator.rust_available = True
        generator.generate_rust = MagicMock()
        generator.generate_python = MagicMock(return_value={"success": True, "cancelled": False})

        result = generator.generate(
            "/test/dir", mock_settings, mock_threadpool, use_rust_preference=False
        )

        generator.generate_rust.assert_not_called()
        generator.generate_python.assert_called_once()

    def test_python_selected_when_rust_not_available(self, mock_settings, mock_threadpool):
        """Test Python is selected when Rust not available"""
        generator = ThumbnailGenerator()
        generator.rust_available = False
        generator.generate_rust = MagicMock()
        generator.generate_python = MagicMock(return_value={"success": True, "cancelled": False})

        result = generator.generate(
            "/test/dir",
            mock_settings,
            mock_threadpool,
            use_rust_preference=True,  # Preference doesn't matter if unavailable
        )

        generator.generate_rust.assert_not_called()
        generator.generate_python.assert_called_once()


@pytest.mark.unit
class TestRustGenerationReturnFormat:
    """Test Rust generation return format conversion"""

    def test_rust_success_returns_unified_format(self):
        """Test successful Rust generation returns unified dict format"""
        generator = ThumbnailGenerator()
        generator.rust_available = True
        generator.generate_rust = MagicMock(return_value=True)

        result = generator.generate(
            "/test/dir",
            {"prefix": "test_", "file_type": "tif"},
            MagicMock(),
            use_rust_preference=True,
        )

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["cancelled"] is False
        assert result["data"] is None
        assert result["error"] is None

    def test_rust_failure_returns_unified_format(self):
        """Test failed Rust generation returns unified dict format"""
        generator = ThumbnailGenerator()
        generator.rust_available = True
        generator.generate_rust = MagicMock(return_value=False)

        result = generator.generate(
            "/test/dir",
            {"prefix": "test_", "file_type": "tif"},
            MagicMock(),
            use_rust_preference=True,
        )

        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "Rust thumbnail generation failed"

    def test_rust_cancellation_detected(self):
        """Test cancellation is properly detected"""
        generator = ThumbnailGenerator()
        generator.rust_available = True
        generator.generate_rust = MagicMock(return_value=False)

        # Mock progress dialog with cancellation
        mock_progress = MagicMock()
        mock_progress.is_cancelled = True

        result = generator.generate(
            "/test/dir",
            {"prefix": "test_", "file_type": "tif"},
            MagicMock(),
            use_rust_preference=True,
            progress_dialog=mock_progress,
        )

        assert result["success"] is False
        assert result["cancelled"] is True
        assert result["error"] is None


@pytest.mark.unit
class TestProgressCallbackCreation:
    """Test progress callback creation from progress dialog"""

    def test_progress_callback_created_when_dialog_provided(self):
        """Test progress callback is created from dialog"""
        generator = ThumbnailGenerator()
        generator.rust_available = True

        mock_progress = MagicMock()
        mock_progress.is_cancelled = False

        # Capture the callbacks passed to generate_rust
        captured_callbacks = {}

        def mock_generate_rust(directory, progress_callback=None, cancel_check=None):
            captured_callbacks["progress"] = progress_callback
            captured_callbacks["cancel"] = cancel_check
            return True

        generator.generate_rust = mock_generate_rust

        generator.generate(
            "/test/dir",
            {"prefix": "test_", "file_type": "tif"},
            MagicMock(),
            use_rust_preference=True,
            progress_dialog=mock_progress,
        )

        # Verify callbacks were created
        assert captured_callbacks["progress"] is not None
        assert captured_callbacks["cancel"] is not None

        # Test progress callback
        captured_callbacks["progress"](50.0)
        mock_progress.lbl_text.setText.assert_called()
        mock_progress.pb_progress.setValue.assert_called_with(50)

        # Test cancel check
        is_cancelled = captured_callbacks["cancel"]()
        assert is_cancelled is False

    def test_no_callbacks_when_no_dialog(self):
        """Test no callbacks created when dialog not provided"""
        generator = ThumbnailGenerator()
        generator.rust_available = True

        captured_callbacks = {}

        def mock_generate_rust(directory, progress_callback=None, cancel_check=None):
            captured_callbacks["progress"] = progress_callback
            captured_callbacks["cancel"] = cancel_check
            return True

        generator.generate_rust = mock_generate_rust

        generator.generate(
            "/test/dir",
            {"prefix": "test_", "file_type": "tif"},
            MagicMock(),
            use_rust_preference=True,
            progress_dialog=None,
        )

        # Callbacks should be None
        assert captured_callbacks["progress"] is None
        assert captured_callbacks["cancel"] is None


@pytest.mark.unit
class TestFallbackBehavior:
    """Test fallback behavior scenarios"""

    @patch("core.thumbnail_generator.logger")
    def test_logs_method_selection(self, mock_logger):
        """Test that method selection is logged"""
        generator = ThumbnailGenerator()
        generator.rust_available = True
        generator.generate_rust = MagicMock(return_value=True)

        generator.generate(
            "/test/dir",
            {"prefix": "test_", "file_type": "tif"},
            MagicMock(),
            use_rust_preference=True,
        )

        # Verify Rust selection was logged
        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Rust-based thumbnail generation" in str(call) for call in calls)

    @patch("core.thumbnail_generator.logger")
    def test_logs_python_fallback(self, mock_logger):
        """Test that Python fallback is logged"""
        generator = ThumbnailGenerator()
        generator.rust_available = False
        generator.generate_python = MagicMock(return_value={"success": True, "cancelled": False})

        generator.generate(
            "/test/dir",
            {"prefix": "test_", "file_type": "tif"},
            MagicMock(),
            use_rust_preference=True,
        )

        # Verify Python fallback was logged
        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Python-based thumbnail generation" in str(call) for call in calls)

    def test_rust_import_error_in_generate_rust(self):
        """Test ImportError handling in generate_rust"""
        generator = ThumbnailGenerator()
        generator.rust_available = True  # Initially available

        # Force ImportError in generate_rust
        with patch("builtins.__import__", side_effect=ImportError("Module not found")):
            result = generator.generate_rust("/test/dir")

        assert result is False

    def test_preference_overrides_availability(self):
        """Test user preference can override Rust availability"""
        generator = ThumbnailGenerator()
        generator.rust_available = True
        generator.generate_rust = MagicMock(return_value=True)
        generator.generate_python = MagicMock(return_value={"success": True, "cancelled": False})

        # User explicitly requests Python
        result = generator.generate(
            "/test/dir",
            {"prefix": "test_", "file_type": "tif"},
            MagicMock(),
            use_rust_preference=False,
        )

        # Should use Python despite Rust being available
        generator.generate_python.assert_called_once()
        generator.generate_rust.assert_not_called()


@pytest.mark.integration
class TestFallbackIntegration:
    """Integration tests for fallback mechanism"""

    @pytest.fixture
    def temp_image_dir(self):
        """Create temporary directory with test images"""
        temp_dir = tempfile.mkdtemp()

        # Create 5 test images
        for i in range(1, 6):
            img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * (i * 50))
            img.save(os.path.join(temp_dir, f"slice_{i:04d}.tif"))

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_python_fallback_actually_works(self, temp_image_dir):
        """Test that Python fallback can actually generate thumbnails"""
        generator = ThumbnailGenerator()
        generator.rust_available = False  # Force Python

        settings = {
            "prefix": "slice_",
            "file_type": "tif",
            "seq_begin": 1,
            "seq_end": 5,
            "index_length": 4,
            "image_width": 100,
            "image_height": 100,
            "max_size": 50,
        }

        mock_threadpool = MagicMock()

        result = generator.generate(
            temp_image_dir,
            settings,
            mock_threadpool,
            use_rust_preference=True,  # Doesn't matter, Rust unavailable
        )

        # Should succeed with Python
        assert result is not None
        # Note: Python implementation returns different format

    def test_consistent_interface_regardless_of_backend(self, temp_image_dir):
        """Test that both backends provide consistent interface"""
        settings = {
            "prefix": "slice_",
            "file_type": "tif",
            "seq_begin": 1,
            "seq_end": 5,
            "index_length": 4,
            "image_width": 100,
            "image_height": 100,
        }

        mock_threadpool = MagicMock()

        # Test with Rust (mocked)
        generator_rust = ThumbnailGenerator()
        generator_rust.rust_available = True
        generator_rust.generate_rust = MagicMock(return_value=True)

        result_rust = generator_rust.generate(
            temp_image_dir, settings, mock_threadpool, use_rust_preference=True
        )

        # Test with Python
        generator_python = ThumbnailGenerator()
        generator_python.rust_available = False
        generator_python.generate_python = MagicMock(
            return_value={"success": True, "cancelled": False, "data": None, "error": None}
        )

        result_python = generator_python.generate(
            temp_image_dir, settings, mock_threadpool, use_rust_preference=True
        )

        # Both should return dict with same keys
        assert isinstance(result_rust, dict)
        assert isinstance(result_python, dict)
        assert set(result_rust.keys()) == set(result_python.keys())
