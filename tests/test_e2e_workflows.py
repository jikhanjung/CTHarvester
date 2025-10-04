"""
End-to-end integration tests with real file I/O.

Tests complete workflows using temporary directories and actual image files:
- Full directory loading pipeline
- Real thumbnail generation (Python implementation)
- Actual file system operations
- Complete error recovery scenarios

These tests are more expensive but verify real-world behavior.
"""

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from core.file_handler import FileHandler
from core.thumbnail_generator import ThumbnailGenerator
from ui.handlers.directory_open_handler import DirectoryOpenHandler
from ui.handlers.thumbnail_creation_handler import ThumbnailCreationHandler


@pytest.fixture
def realistic_ct_stack():
    """Create realistic CT scan directory structure for testing."""
    temp_dir = tempfile.mkdtemp(prefix="ct_e2e_")

    # Create more realistic CT stack (100 slices, 256x256, 8-bit)
    num_slices = 100
    img_size = 256

    for i in range(num_slices):
        # Create gradient pattern with some noise (more realistic)
        base_pattern = np.linspace(0, 255, img_size * img_size).reshape(img_size, img_size)
        noise = np.random.randint(-20, 20, (img_size, img_size))
        img_array = np.clip(base_pattern + noise + i, 0, 255).astype(np.uint8)

        img = Image.fromarray(img_array)
        filename = f"slice_{i:04d}.tif"
        img.save(os.path.join(temp_dir, filename))

    yield temp_dir

    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def realistic_16bit_ct_stack():
    """Create realistic 16-bit CT scan for testing."""
    temp_dir = tempfile.mkdtemp(prefix="ct_16bit_")

    num_slices = 50
    img_size = 128

    for i in range(num_slices):
        # 16-bit gradient with noise
        base_pattern = np.linspace(0, 65535, img_size * img_size).reshape(img_size, img_size)
        noise = np.random.randint(-500, 500, (img_size, img_size))
        img_array = np.clip(base_pattern + noise + i * 100, 0, 65535).astype(np.uint16)

        img = Image.fromarray(img_array)
        filename = f"scan_{i:04d}.tif"
        img.save(os.path.join(temp_dir, filename))

    yield temp_dir

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.mark.integration
@pytest.mark.slow
class TestE2EDirectoryLoading:
    """End-to-end tests for directory loading workflow."""

    def test_complete_directory_analysis(self, realistic_ct_stack):
        """Should analyze directory and extract all metadata."""
        file_handler = FileHandler()

        result = file_handler.open_directory(realistic_ct_stack)

        # Verify complete metadata
        assert result is not None
        assert result["prefix"] == "slice_"
        assert result["file_type"] == "tif"
        assert result["seq_begin"] == 0
        assert result["seq_end"] == 99
        assert result["image_width"] == 256
        assert result["image_height"] == 256
        assert result["index_length"] == 4

        # Verify file list
        file_list = file_handler.get_file_list()
        assert len(file_list) == 100
        assert file_list[0] == "slice_0000.tif"
        assert file_list[99] == "slice_0099.tif"

    def test_directory_with_mixed_files(self, realistic_ct_stack):
        """Should ignore non-image files in directory."""
        # Add some non-image files
        with open(os.path.join(realistic_ct_stack, "README.txt"), "w") as f:
            f.write("Test readme")
        with open(os.path.join(realistic_ct_stack, "metadata.json"), "w") as f:
            f.write('{"test": true}')

        file_handler = FileHandler()
        result = file_handler.open_directory(realistic_ct_stack)

        # Should still work, ignoring non-images
        assert result is not None
        file_list = file_handler.get_file_list()
        assert len(file_list) == 100  # Only .tif files

    def test_16bit_image_detection(self, realistic_16bit_ct_stack):
        """Should correctly detect and handle 16-bit images."""
        file_handler = FileHandler()
        result = file_handler.open_directory(realistic_16bit_ct_stack)

        assert result is not None
        assert result["image_width"] == 128
        assert result["image_height"] == 128

        # Verify first image is actually 16-bit
        from utils.image_utils import detect_bit_depth

        first_file = os.path.join(realistic_16bit_ct_stack, "scan_0000.tif")
        bit_depth = detect_bit_depth(first_file)
        assert bit_depth == 16


@pytest.mark.integration
@pytest.mark.slow
class TestE2EThumbnailGeneration:
    """End-to-end tests for thumbnail generation workflow."""

    def test_python_thumbnail_generation_single_level(self, realistic_ct_stack):
        """Should generate level 1 thumbnails using Python implementation."""
        generator = ThumbnailGenerator(
            source_dir=realistic_ct_stack,
            prefix="slice_",
            file_type="tif",
            seq_begin=0,
            seq_end=99,
            index_length=4,
            use_rust=False,
        )

        # Generate level 1
        result = generator.generate_level(
            level=1, start_idx=0, end_idx=99, image_width=256, image_height=256
        )

        assert result is True

        # Verify thumbnails created
        thumb_dir = os.path.join(realistic_ct_stack, ".thumbnail", "1")
        assert os.path.exists(thumb_dir)

        thumb_files = [f for f in os.listdir(thumb_dir) if f.endswith(".tif")]
        assert len(thumb_files) == 50  # 100 images -> 50 thumbnails (2:1 averaging)

        # Verify thumbnail size
        from utils.image_utils import get_image_dimensions

        first_thumb = os.path.join(thumb_dir, thumb_files[0])
        width, height = get_image_dimensions(first_thumb)
        assert width == 128  # 256 / 2
        assert height == 128

    def test_multi_level_pyramid_generation(self, realistic_ct_stack):
        """Should generate complete thumbnail pyramid (3 levels)."""
        generator = ThumbnailGenerator(
            source_dir=realistic_ct_stack,
            prefix="slice_",
            file_type="tif",
            seq_begin=0,
            seq_end=99,
            index_length=4,
            use_rust=False,
        )

        # Generate pyramid: Level 1, 2, 3
        levels_info = []

        # Level 1: 100 -> 50 images, 256x256 -> 128x128
        result1 = generator.generate_level(1, 0, 99, 256, 256)
        assert result1 is True
        levels_info.append((1, 50, 128))

        # Level 2: 50 -> 25 images, 128x128 -> 64x64
        result2 = generator.generate_level(2, 0, 49, 128, 128)
        assert result2 is True
        levels_info.append((2, 25, 64))

        # Level 3: 25 -> 12 images, 64x64 -> 32x32
        result3 = generator.generate_level(3, 0, 24, 64, 64)
        assert result3 is True
        levels_info.append((3, 12, 32))

        # Verify all levels
        from utils.image_utils import get_image_dimensions

        for level, expected_count, expected_size in levels_info:
            thumb_dir = os.path.join(realistic_ct_stack, ".thumbnail", str(level))
            assert os.path.exists(thumb_dir)

            thumb_files = [f for f in os.listdir(thumb_dir) if f.endswith(".tif")]
            assert len(thumb_files) == expected_count

            # Check first thumbnail size
            first_thumb = os.path.join(thumb_dir, thumb_files[0])
            width, height = get_image_dimensions(first_thumb)
            assert width == expected_size
            assert height == expected_size

    def test_thumbnail_cleanup_and_regeneration(self, realistic_ct_stack):
        """Should clean up old thumbnails before regenerating."""
        from utils.file_utils import clean_old_thumbnails

        generator = ThumbnailGenerator(
            source_dir=realistic_ct_stack,
            prefix="slice_",
            file_type="tif",
            seq_begin=0,
            seq_end=99,
            index_length=4,
            use_rust=False,
        )

        # Generate initial thumbnails
        generator.generate_level(1, 0, 99, 256, 256)
        thumb_dir = os.path.join(realistic_ct_stack, ".thumbnail", "1")
        assert os.path.exists(thumb_dir)

        # Clean up
        result = clean_old_thumbnails(realistic_ct_stack)
        assert result is True
        assert not os.path.exists(os.path.join(realistic_ct_stack, ".thumbnail"))

        # Regenerate
        generator.generate_level(1, 0, 99, 256, 256)
        assert os.path.exists(thumb_dir)

    def test_16bit_thumbnail_preservation(self, realistic_16bit_ct_stack):
        """Should preserve 16-bit depth in thumbnails."""
        from utils.image_utils import detect_bit_depth

        generator = ThumbnailGenerator(
            source_dir=realistic_16bit_ct_stack,
            prefix="scan_",
            file_type="tif",
            seq_begin=0,
            seq_end=49,
            index_length=4,
            use_rust=False,
        )

        # Generate level 1 (should preserve 16-bit)
        result = generator.generate_level(1, 0, 49, 128, 128)
        assert result is True

        # Verify bit depth preserved
        thumb_dir = os.path.join(realistic_16bit_ct_stack, ".thumbnail", "1")
        thumb_files = [f for f in os.listdir(thumb_dir) if f.endswith(".tif")]

        first_thumb = os.path.join(thumb_dir, thumb_files[0])
        thumb_depth = detect_bit_depth(first_thumb)
        assert thumb_depth == 16


@pytest.mark.integration
@pytest.mark.slow
class TestE2ECompleteWorkflow:
    """End-to-end tests for complete application workflows."""

    @patch("ui.handlers.directory_open_handler.QFileDialog")
    @patch("ui.handlers.directory_open_handler.wait_cursor")
    def test_directory_open_to_thumbnail_complete(
        self, mock_wait_cursor, MockFileDialog, realistic_ct_stack
    ):
        """Should complete full workflow from directory open to thumbnails."""
        # Create mock main window
        mock_window = MagicMock()
        mock_window.edtDirname = MagicMock()
        mock_window.edtNumImages = MagicMock()
        mock_window.edtImageDimension = MagicMock()
        mock_window.m_app = MagicMock()
        mock_window.m_app.default_directory = "/tmp"
        mock_window.settings_hash = {}
        mock_window.level_info = []
        mock_window.tr = lambda x: x
        mock_window._reset_ui_state = MagicMock()
        mock_window._load_first_image = MagicMock()
        mock_window._load_existing_thumbnail_levels = MagicMock()

        # Real file handler
        mock_window.file_handler = FileHandler()

        # Initialize directory open handler
        dir_handler = DirectoryOpenHandler(mock_window)

        # Mock file dialog to return our test directory
        MockFileDialog.getExistingDirectory.return_value = realistic_ct_stack

        # Step 1: Open directory
        dir_handler.open_directory()

        # Verify directory was analyzed
        assert mock_window.settings_hash["prefix"] == "slice_"
        assert mock_window.settings_hash["seq_end"] == 99

        # Step 2: Generate thumbnails (using real ThumbnailGenerator)
        generator = ThumbnailGenerator(
            source_dir=realistic_ct_stack,
            prefix=mock_window.settings_hash["prefix"],
            file_type=mock_window.settings_hash["file_type"],
            seq_begin=mock_window.settings_hash["seq_begin"],
            seq_end=mock_window.settings_hash["seq_end"],
            index_length=mock_window.settings_hash["index_length"],
            use_rust=False,
        )

        result = generator.generate_level(1, 0, 99, 256, 256)
        assert result is True

        # Verify complete workflow
        thumb_dir = os.path.join(realistic_ct_stack, ".thumbnail", "1")
        assert os.path.exists(thumb_dir)
        thumb_files = [f for f in os.listdir(thumb_dir) if f.endswith(".tif")]
        assert len(thumb_files) == 50

    def test_error_recovery_invalid_directory(self):
        """Should recover from invalid directory selection."""
        file_handler = FileHandler()

        # Try to open non-existent directory
        result = file_handler.open_directory("/non/existent/path")

        # Should return None, not crash
        assert result is None

    def test_error_recovery_corrupted_image(self, realistic_ct_stack):
        """Should handle corrupted image files gracefully."""
        # Create a corrupted "image" file
        corrupted_file = os.path.join(realistic_ct_stack, "slice_0050.tif")
        with open(corrupted_file, "w") as f:
            f.write("This is not a valid image file")

        file_handler = FileHandler()

        # Should still open directory (may skip corrupted file)
        result = file_handler.open_directory(realistic_ct_stack)

        # Should not crash entire process
        assert result is not None or result is None  # Either way, no exception


@pytest.mark.integration
@pytest.mark.slow
class TestE2EPerformance:
    """End-to-end performance and resource tests."""

    def test_memory_efficiency_large_stack(self, realistic_ct_stack):
        """Should handle large image stacks without excessive memory usage."""
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate thumbnails for 100 images
        generator = ThumbnailGenerator(
            source_dir=realistic_ct_stack,
            prefix="slice_",
            file_type="tif",
            seq_begin=0,
            seq_end=99,
            index_length=4,
            use_rust=False,
        )

        result = generator.generate_level(1, 0, 99, 256, 256)
        assert result is True

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Should not use excessive memory (< 500MB for this test)
        # Note: This is a rough check, actual usage depends on system
        assert memory_increase < 500, f"Memory usage too high: {memory_increase:.2f} MB"

    def test_thumbnail_generation_reasonable_time(self, realistic_ct_stack):
        """Should generate thumbnails in reasonable time."""
        generator = ThumbnailGenerator(
            source_dir=realistic_ct_stack,
            prefix="slice_",
            file_type="tif",
            seq_begin=0,
            seq_end=99,
            index_length=4,
            use_rust=False,
        )

        start_time = time.time()
        result = generator.generate_level(1, 0, 99, 256, 256)
        elapsed_time = time.time() - start_time

        assert result is True

        # Should complete in reasonable time (< 30 seconds for 100 images)
        # This is generous; typically should be much faster
        assert elapsed_time < 30, f"Thumbnail generation too slow: {elapsed_time:.2f} seconds"

    def test_disk_space_efficiency(self, realistic_ct_stack):
        """Should create thumbnails that are smaller than originals."""
        from utils.file_utils import get_directory_size

        # Get original stack size
        original_size = get_directory_size(realistic_ct_stack)

        # Generate thumbnails
        generator = ThumbnailGenerator(
            source_dir=realistic_ct_stack,
            prefix="slice_",
            file_type="tif",
            seq_begin=0,
            seq_end=99,
            index_length=4,
            use_rust=False,
        )
        generator.generate_level(1, 0, 99, 256, 256)

        # Get thumbnail directory size
        thumb_dir = os.path.join(realistic_ct_stack, ".thumbnail", "1")
        thumb_size = get_directory_size(thumb_dir)

        # Thumbnails should be significantly smaller
        # (128x128 vs 256x256 = 1/4 area, roughly 1/4 size)
        assert thumb_size < original_size / 2


@pytest.mark.integration
class TestE2EEdgeCases:
    """End-to-end tests for edge cases and boundary conditions."""

    def test_single_image_directory(self):
        """Should handle directory with only one image."""
        temp_dir = tempfile.mkdtemp(prefix="single_img_")

        # Create single image
        img_array = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
        img = Image.fromarray(img_array)
        img.save(os.path.join(temp_dir, "scan_0000.tif"))

        try:
            file_handler = FileHandler()
            result = file_handler.open_directory(temp_dir)

            # Should handle single image
            assert result is not None
            assert result["seq_begin"] == 0
            assert result["seq_end"] == 0

            file_list = file_handler.get_file_list()
            assert len(file_list) == 1
        finally:
            shutil.rmtree(temp_dir)

    def test_very_small_images(self):
        """Should handle very small images (16x16)."""
        temp_dir = tempfile.mkdtemp(prefix="tiny_img_")

        # Create tiny images
        for i in range(10):
            img_array = np.random.randint(0, 256, (16, 16), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(os.path.join(temp_dir, f"tiny_{i:04d}.tif"))

        try:
            generator = ThumbnailGenerator(
                source_dir=temp_dir,
                prefix="tiny_",
                file_type="tif",
                seq_begin=0,
                seq_end=9,
                index_length=4,
                use_rust=False,
            )

            # Should handle downsampling tiny images
            result = generator.generate_level(1, 0, 9, 16, 16)

            # May succeed or fail gracefully depending on min size constraints
            # Either way, should not crash
            assert isinstance(result, bool)
        finally:
            shutil.rmtree(temp_dir)

    def test_non_sequential_filenames(self):
        """Should handle non-sequential image indices."""
        temp_dir = tempfile.mkdtemp(prefix="nonseq_")

        # Create images with gaps in sequence
        indices = [0, 1, 2, 5, 6, 10, 15, 20]
        for idx in indices:
            img_array = np.random.randint(0, 256, (128, 128), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(os.path.join(temp_dir, f"scan_{idx:04d}.tif"))

        try:
            file_handler = FileHandler()
            result = file_handler.open_directory(temp_dir)

            # Should detect the range (0 to 20) even with gaps
            assert result is not None
            # File handler should find the files that exist
            file_list = file_handler.get_file_list()
            assert len(file_list) == len(indices)
        finally:
            shutil.rmtree(temp_dir)
