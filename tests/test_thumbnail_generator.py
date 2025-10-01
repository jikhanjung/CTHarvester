"""
Tests for ThumbnailGenerator class

Tests the thumbnail generation logic extracted from main_window.py
"""

import os
import shutil
import tempfile

import numpy as np
import pytest
from PIL import Image

from core.thumbnail_generator import ThumbnailGenerator


class TestThumbnailGenerator:
    """Test suite for ThumbnailGenerator"""

    @pytest.fixture
    def generator(self):
        """Create a ThumbnailGenerator instance"""
        return ThumbnailGenerator()

    @pytest.fixture
    def temp_image_dir(self):
        """Create a temporary directory with test images"""
        temp_dir = tempfile.mkdtemp()

        # Create 10 test images (100x100, grayscale)
        for i in range(10):
            img = Image.fromarray(
                np.ones((100, 100), dtype=np.uint8) * (i * 25)  # Different intensities
            )
            img.save(os.path.join(temp_dir, f"test_{i:04d}.tif"))

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_initialization(self, generator):
        """Test generator initializes correctly"""
        assert generator.level_sizes == []
        assert generator.level_work_distribution == []
        assert generator.total_levels == 0
        assert generator.weighted_total_work == 0
        assert isinstance(generator.rust_available, bool)

    def test_calculate_total_thumbnail_work_single_level(self, generator):
        """Test work calculation for single LoD level"""
        # Small images, only 1 level needed
        total_work = generator.calculate_total_thumbnail_work(
            seq_begin=0,
            seq_end=99,  # 100 images
            size=256,  # Small enough for 1 level
            max_size=256,
        )

        # Should have 1 level
        assert generator.total_levels == 1
        assert len(generator.level_sizes) == 1
        assert len(generator.level_work_distribution) == 1

        # First level should process ~50 images (half of 100)
        assert generator.level_sizes[0][2] == 51  # (100 // 2) + 1

    def test_calculate_total_thumbnail_work_multiple_levels(self, generator):
        """Test work calculation for multiple LoD levels"""
        # Large images, multiple levels needed
        total_work = generator.calculate_total_thumbnail_work(
            seq_begin=0, seq_end=99, size=2048, max_size=256  # 100 images  # Large image
        )

        # Should have multiple levels (2048 -> 1024 -> 512 -> 256)
        assert generator.total_levels >= 3
        assert len(generator.level_sizes) >= 3

        # First level should have higher weight due to I/O
        first_level_weight = generator.level_work_distribution[0]["weight"]
        assert first_level_weight > 0

        # Weighted work should be calculated
        assert generator.weighted_total_work > 0

    def test_calculate_total_thumbnail_work_first_level_weight(self, generator):
        """Test that level weights follow image size ratio (64:8:1)"""
        generator.calculate_total_thumbnail_work(seq_begin=0, seq_end=99, size=2048, max_size=256)

        # Weights should follow (temp_size/size)² ratio
        first_level = generator.level_work_distribution[0]
        base_size_factor = (first_level["size"] / 2048) ** 2

        # Weight should match the base size factor (no additional multiplier)
        expected_weight = base_size_factor
        assert abs(first_level["weight"] - expected_weight) < 0.01

    def test_calculate_total_thumbnail_work_zero_images(self, generator):
        """Test work calculation with zero images (edge case)"""
        total_work = generator.calculate_total_thumbnail_work(
            seq_begin=0, seq_end=0, size=512, max_size=256  # Single image
        )

        assert generator.total_levels >= 1
        # Should still create at least one level
        assert len(generator.level_sizes) >= 1

    def test_rust_availability_check(self, generator):
        """Test Rust module availability detection"""
        # rust_available should be bool
        assert isinstance(generator.rust_available, bool)

        # If available, should not raise error
        if generator.rust_available:
            try:
                from ct_thumbnail import build_thumbnails

                # Should succeed
            except ImportError:
                pytest.fail("rust_available is True but ct_thumbnail cannot be imported")

    def test_load_thumbnail_data_no_directory(self, generator):
        """Test loading thumbnails from non-existent directory"""
        result, info = generator.load_thumbnail_data("/nonexistent/path")

        assert result is None
        assert info == {}

    def test_load_thumbnail_data_empty_directory(self, generator, temp_image_dir):
        """Test loading thumbnails from directory without .thumbnail folder"""
        result, info = generator.load_thumbnail_data(temp_image_dir)

        assert result is None
        assert info == {}

    def test_load_thumbnail_data_with_thumbnails(self, generator, temp_image_dir):
        """Test loading thumbnails from directory with generated thumbnails"""
        # Create .thumbnail/1 directory with test thumbnails
        thumbnail_dir = os.path.join(temp_image_dir, ".thumbnail", "1")
        os.makedirs(thumbnail_dir, exist_ok=True)

        # Create 5 small thumbnail images (50x50)
        for i in range(5):
            img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * (i * 50))
            img.save(os.path.join(thumbnail_dir, f"thumb_{i:04d}.tif"))

        # Load thumbnails
        result, info = generator.load_thumbnail_data(temp_image_dir, max_thumbnail_size=512)

        # Should successfully load
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape == (5, 50, 50)  # 5 images, 50x50

        # Check info structure
        assert "levels" in info
        assert "current_level" in info
        assert info["current_level"] == 1

    def test_load_thumbnail_data_16bit_conversion(self, generator, temp_image_dir):
        """Test loading 16-bit thumbnails converts to 8-bit"""
        # Create .thumbnail/1 directory
        thumbnail_dir = os.path.join(temp_image_dir, ".thumbnail", "1")
        os.makedirs(thumbnail_dir, exist_ok=True)

        # Create 16-bit image
        img_16bit = np.ones((50, 50), dtype=np.uint16) * 25600  # High value
        img = Image.fromarray(img_16bit)
        img.save(os.path.join(thumbnail_dir, "thumb_0000.tif"))

        # Load thumbnails
        result, info = generator.load_thumbnail_data(temp_image_dir)

        # Should convert to 8-bit
        assert result is not None
        assert result.dtype == np.uint8

        # Value should be converted (25600 / 256 = 100)
        assert result[0, 0, 0] == 100

    def test_load_thumbnail_data_multiple_levels(self, generator, temp_image_dir):
        """Test loading thumbnails with multiple levels chooses appropriate one"""
        # Create multiple levels
        for level in [1, 2, 3]:
            level_dir = os.path.join(temp_image_dir, ".thumbnail", str(level))
            os.makedirs(level_dir, exist_ok=True)

            # Each level has smaller images
            size = 200 // level  # Level 1: 200, Level 2: 100, Level 3: 66

            for i in range(5):
                img = Image.fromarray(np.ones((size, size), dtype=np.uint8) * 100)
                img.save(os.path.join(level_dir, f"thumb_{i:04d}.tif"))

        # Load with max_thumbnail_size=150
        result, info = generator.load_thumbnail_data(temp_image_dir, max_thumbnail_size=150)

        # Should choose level 2 (size 100 < 150)
        assert result is not None
        assert info["current_level"] == 2
        assert result.shape[1] == 100  # Height
        assert result.shape[2] == 100  # Width

    @pytest.mark.parametrize(
        "seq_begin,seq_end,size,max_size",
        [
            (0, 99, 512, 256),  # Normal case
            (0, 0, 1024, 256),  # Single image
            (10, 110, 2048, 256),  # Different start
            (0, 999, 4096, 256),  # Large dataset
        ],
    )
    def test_calculate_work_parametrized(self, generator, seq_begin, seq_end, size, max_size):
        """Test work calculation with various parameters"""
        total_work = generator.calculate_total_thumbnail_work(seq_begin, seq_end, size, max_size)

        # Should always calculate some work
        assert total_work > 0
        assert generator.total_levels > 0
        assert len(generator.level_sizes) > 0
        assert generator.weighted_total_work > 0

    def test_generate_method_routing(self, generator, temp_image_dir, qtbot):
        """Test that generate() routes to correct implementation"""
        from PyQt5.QtCore import QThreadPool

        # Mock progress dialog
        class MockProgressDialog:
            def __init__(self):
                self.is_cancelled = False
                self.percentage_updates = []

                class MockLabel:
                    def __init__(self):
                        self.text = ""
                    def setText(self, text):
                        self.text = text

                class MockProgressBar:
                    def __init__(self):
                        self.value = 0
                    def setValue(self, value):
                        self.value = value

                self.lbl_text = MockLabel()
                self.lbl_detail = MockLabel()
                self.pb_progress = MockProgressBar()

        progress_dialog = MockProgressDialog()

        # Create mock settings
        settings = {
            "image_width": "512",
            "image_height": "512",
            "seq_begin": 0,
            "seq_end": 9,
            "prefix": "test_",
            "index_length": 4,
            "file_type": "tif"
        }

        # Create thread pool
        threadpool = QThreadPool()

        # Test generate() method with new API
        result = generator.generate(
            directory=temp_image_dir,
            settings=settings,
            threadpool=threadpool,
            use_rust_preference=False,  # Force Python path for testing
            progress_dialog=progress_dialog
        )

        # Python returns a result dictionary
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'cancelled' in result
        assert 'minimum_volume' in result
        assert 'level_info' in result

        # Test direct Python call still works
        result_python = generator.generate_python(
            directory=temp_image_dir,
            settings=settings,
            threadpool=threadpool,
            progress_dialog=progress_dialog
        )
        assert isinstance(result_python, dict)
        assert 'success' in result_python


class TestThumbnailGeneratorIntegration:
    """Integration tests for thumbnail generation workflow"""

    @pytest.mark.slow
    def test_full_workflow_python(self):
        """Test complete thumbnail generation workflow (Python)"""
        # This test would require full Python implementation
        # Placeholder for future implementation
        pass

    @pytest.mark.slow
    def test_full_workflow_rust(self):
        """Test complete thumbnail generation workflow (Rust)"""
        # This test would require Rust module
        # Placeholder for future implementation
        pass
