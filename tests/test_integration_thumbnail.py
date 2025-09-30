"""
Integration tests for thumbnail generation workflow

Tests the complete thumbnail generation process without GUI:
- File discovery
- Image loading
- Downsampling
- Thumbnail saving
- Directory management

These tests use real file I/O and image processing.
"""
import sys
import os
import tempfile
import shutil
import pytest
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

if PIL_AVAILABLE:
    from utils.file_utils import (
        find_image_files,
        parse_filename,
        create_thumbnail_directory,
        get_thumbnail_path,
        clean_old_thumbnails,
        format_file_size
    )
    from utils.image_utils import (
        detect_bit_depth,
        load_image_as_array,
        downsample_image,
        average_images,
        save_image_from_array,
        get_image_dimensions
    )


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
@pytest.mark.integration
class TestThumbnailGenerationWorkflow:
    """Integration tests for complete thumbnail generation workflow"""

    def setup_method(self):
        """Create temporary directory with test images"""
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.temp_dir, "source")
        self.output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(self.source_dir)
        os.makedirs(self.output_dir)

        # Create test images (8-bit grayscale)
        self.image_files = []
        for i in range(10):
            # Create gradient images
            img_array = np.linspace(0, 255, 10000, dtype=np.uint8).reshape(100, 100)
            img_array = img_array + (i * 10)  # Vary by index
            img_array = np.clip(img_array, 0, 255).astype(np.uint8)

            img = Image.fromarray(img_array)
            filename = f"scan_{i:04d}.tif"
            filepath = os.path.join(self.source_dir, filename)
            img.save(filepath)
            self.image_files.append(filename)

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_complete_single_level_workflow(self):
        """Should generate thumbnails for a complete level"""
        # 1. Discovery: Find source images
        found_images = find_image_files(self.source_dir)
        assert len(found_images) == 10
        assert all(img in found_images for img in self.image_files)

        # 2. Setup: Create thumbnail directory
        thumb_dir = create_thumbnail_directory(self.output_dir, level=1)
        assert os.path.exists(thumb_dir)
        assert ".thumbnail" in thumb_dir

        # 3. Process: Generate thumbnails by averaging pairs
        thumbnail_count = 0
        for i in range(0, len(found_images) - 1, 2):
            # Load pair of images
            img1_path = os.path.join(self.source_dir, found_images[i])
            img2_path = os.path.join(self.source_dir, found_images[i + 1])

            img1 = load_image_as_array(img1_path)
            img2 = load_image_as_array(img2_path)

            # Average the pair
            averaged = average_images(img1, img2)

            # Downsample by 2x
            downsampled = downsample_image(averaged, factor=2, method='subsample')

            # Save thumbnail
            thumb_path = get_thumbnail_path(self.output_dir, level=1, index=thumbnail_count)
            save_image_from_array(downsampled, thumb_path)

            thumbnail_count += 1

        # 4. Verify: Check results
        assert thumbnail_count == 5  # 10 images -> 5 thumbnails

        # Verify all thumbnails exist and have correct size
        for i in range(thumbnail_count):
            thumb_path = get_thumbnail_path(self.output_dir, level=1, index=i)
            assert os.path.exists(thumb_path)

            width, height = get_image_dimensions(thumb_path)
            assert width == 50  # 100 / 2
            assert height == 50

    def test_multi_level_pyramid_generation(self):
        """Should generate multiple levels of thumbnail pyramid"""
        levels_generated = []

        # Level 1: Process original images (100x100 -> 50x50)
        found_images = find_image_files(self.source_dir)

        # Generate level 1
        thumb_dir_1 = create_thumbnail_directory(self.output_dir, level=1)
        level1_count = 0

        for i in range(0, len(found_images) - 1, 2):
            img1_path = os.path.join(self.source_dir, found_images[i])
            img2_path = os.path.join(self.source_dir, found_images[i + 1])

            img1 = load_image_as_array(img1_path)
            img2 = load_image_as_array(img2_path)
            averaged = average_images(img1, img2)
            downsampled = downsample_image(averaged, factor=2)

            thumb_path = get_thumbnail_path(self.output_dir, level=1, index=level1_count)
            save_image_from_array(downsampled, thumb_path)
            level1_count += 1

        levels_generated.append((1, level1_count))

        # Level 2: Process level 1 thumbnails (50x50 -> 25x25)
        level1_images = find_image_files(thumb_dir_1)
        thumb_dir_2 = create_thumbnail_directory(self.output_dir, level=2)
        level2_count = 0

        for i in range(0, len(level1_images) - 1, 2):
            img1_path = os.path.join(thumb_dir_1, level1_images[i])
            img2_path = os.path.join(thumb_dir_1, level1_images[i + 1])

            img1 = load_image_as_array(img1_path)
            img2 = load_image_as_array(img2_path)
            averaged = average_images(img1, img2)
            downsampled = downsample_image(averaged, factor=2)

            thumb_path = get_thumbnail_path(self.output_dir, level=2, index=level2_count)
            save_image_from_array(downsampled, thumb_path)
            level2_count += 1

        levels_generated.append((2, level2_count))

        # Verify pyramid structure
        assert levels_generated[0] == (1, 5)  # 10 -> 5
        assert levels_generated[1] == (2, 2)  # 5 -> 2

        # Verify sizes
        for level, count in levels_generated:
            for i in range(count):
                thumb_path = get_thumbnail_path(self.output_dir, level=level, index=i)
                assert os.path.exists(thumb_path)

                width, height = get_image_dimensions(thumb_path)
                expected_size = 100 // (2 ** level)
                assert width == expected_size
                assert height == expected_size

    def test_16bit_image_workflow(self):
        """Should handle 16-bit images correctly"""
        # Create 16-bit test images
        source_16bit = os.path.join(self.temp_dir, "source_16bit")
        os.makedirs(source_16bit)

        for i in range(4):
            # Create 16-bit gradient
            img_array = np.linspace(0, 65535, 10000, dtype=np.uint16).reshape(100, 100)
            img_array = img_array + (i * 1000)
            img_array = np.clip(img_array, 0, 65535).astype(np.uint16)

            img = Image.fromarray(img_array)
            filename = f"scan_{i:04d}.tif"
            filepath = os.path.join(source_16bit, filename)
            img.save(filepath)

        # Detect bit depth
        test_file = os.path.join(source_16bit, "scan_0000.tif")
        bit_depth = detect_bit_depth(test_file)
        assert bit_depth == 16

        # Process with 16-bit preservation
        found_images = find_image_files(source_16bit)
        thumb_dir = create_thumbnail_directory(self.output_dir, level=1)

        for i in range(0, len(found_images) - 1, 2):
            img1_path = os.path.join(source_16bit, found_images[i])
            img2_path = os.path.join(source_16bit, found_images[i + 1])

            img1 = load_image_as_array(img1_path)
            img2 = load_image_as_array(img2_path)

            assert img1.dtype == np.uint16
            assert img2.dtype == np.uint16

            averaged = average_images(img1, img2)
            downsampled = downsample_image(averaged, factor=2)

            thumb_path = get_thumbnail_path(self.output_dir, level=1, index=i // 2)
            save_image_from_array(downsampled, thumb_path)

        # Verify output is 16-bit
        thumb_path = get_thumbnail_path(self.output_dir, level=1, index=0)
        output_depth = detect_bit_depth(thumb_path)
        assert output_depth == 16

    def test_cleanup_old_thumbnails(self):
        """Should clean up old thumbnails before regeneration"""
        # Generate initial thumbnails
        thumb_dir = create_thumbnail_directory(self.output_dir, level=1)
        for i in range(3):
            thumb_path = get_thumbnail_path(self.output_dir, level=1, index=i)
            img_array = np.ones((50, 50), dtype=np.uint8) * 128
            save_image_from_array(img_array, thumb_path)

        # Verify thumbnails exist
        assert len(find_image_files(thumb_dir)) == 3

        # Clean up
        result = clean_old_thumbnails(self.output_dir)
        assert result is True
        assert not os.path.exists(thumb_dir)

        # Recreate and verify clean state
        thumb_dir = create_thumbnail_directory(self.output_dir, level=1)
        assert len(find_image_files(thumb_dir)) == 0

    def test_filename_parsing_workflow(self):
        """Should correctly parse and handle different filename formats"""
        # Test various filename patterns
        test_patterns = [
            ("scan_0001.tif", ("scan_", 1, "tif")),
            ("image_00123.jpg", ("image_", 123, "jpg")),
            ("data_999999.png", ("data_", 999999, "png")),
        ]

        for filename, expected in test_patterns:
            result = parse_filename(filename)
            assert result == expected

    def test_error_handling_missing_images(self):
        """Should handle missing image files gracefully"""
        # Try to load non-existent image
        missing_path = os.path.join(self.source_dir, "missing.tif")

        with pytest.raises(Exception):
            load_image_as_array(missing_path)

    def test_downsampling_methods_comparison(self):
        """Should produce different results with different downsampling methods"""
        # Load a test image
        img_path = os.path.join(self.source_dir, self.image_files[0])
        img = load_image_as_array(img_path)

        # Downsample with both methods
        subsample = downsample_image(img, factor=2, method='subsample')
        average = downsample_image(img, factor=2, method='average')

        # Both should be same size
        assert subsample.shape == average.shape
        assert subsample.shape == (50, 50)

        # But different content (average is smoother)
        # They shouldn't be identical (unless image is uniform)
        if not np.all(img == img[0, 0]):
            # For non-uniform images, methods should differ
            assert not np.array_equal(subsample, average)

    def test_memory_efficient_processing(self):
        """Should process images without loading all into memory"""
        # This test verifies we can process images one pair at a time
        # without keeping all in memory

        found_images = find_image_files(self.source_dir)
        thumb_dir = create_thumbnail_directory(self.output_dir, level=1)

        # Process in small batches (simulating memory constraints)
        batch_size = 2
        thumb_index = 0

        for batch_start in range(0, len(found_images) - 1, batch_size):
            batch_end = min(batch_start + batch_size, len(found_images))

            for i in range(batch_start, batch_end - 1, 2):
                img1_path = os.path.join(self.source_dir, found_images[i])
                img2_path = os.path.join(self.source_dir, found_images[i + 1])

                img1 = load_image_as_array(img1_path)
                img2 = load_image_as_array(img2_path)
                averaged = average_images(img1, img2)
                downsampled = downsample_image(averaged, factor=2)

                thumb_path = get_thumbnail_path(self.output_dir, level=1, index=thumb_index)
                save_image_from_array(downsampled, thumb_path)
                thumb_index += 1

                # Explicitly delete to free memory (in real case, would be handled by GC)
                del img1, img2, averaged, downsampled

        # Verify all thumbnails generated
        assert thumb_index == 5

    def test_size_calculation(self):
        """Should calculate correct sizes throughout workflow"""
        # Original images
        original_path = os.path.join(self.source_dir, self.image_files[0])
        width, height = get_image_dimensions(original_path)
        assert width == 100
        assert height == 100

        # Generate level 1
        thumb_dir = create_thumbnail_directory(self.output_dir, level=1)
        found = find_image_files(self.source_dir)

        img1 = load_image_as_array(os.path.join(self.source_dir, found[0]))
        img2 = load_image_as_array(os.path.join(self.source_dir, found[1]))
        averaged = average_images(img1, img2)
        downsampled = downsample_image(averaged, factor=2)

        thumb_path = get_thumbnail_path(self.output_dir, level=1, index=0)
        save_image_from_array(downsampled, thumb_path)

        # Check level 1 size
        width_l1, height_l1 = get_image_dimensions(thumb_path)
        assert width_l1 == 50
        assert height_l1 == 50

        # Format file size for reporting
        original_size = os.path.getsize(original_path)
        thumb_size = os.path.getsize(thumb_path)

        original_fmt = format_file_size(original_size)
        thumb_fmt = format_file_size(thumb_size)

        assert "KB" in original_fmt or "B" in original_fmt
        assert "KB" in thumb_fmt or "B" in thumb_fmt

        # Thumbnail should be smaller (roughly 1/4 the size)
        assert thumb_size < original_size