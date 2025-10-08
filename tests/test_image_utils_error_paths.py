"""
Error path tests for image_utils module

Tests error handling scenarios including corrupted images, OOM conditions,
and edge cases for image processing functions using actual API.
"""

import os
import shutil
import tempfile
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from utils.image_utils import (
    ImageLoadError,
    downsample_image,
    load_image_as_array,
    safe_load_image,
    save_image_from_array,
)


@pytest.mark.unit
class TestImageUtilsErrorPaths:
    """Error path test suite for image_utils"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    # ===== Corrupted Image Handling =====

    def test_load_corrupted_image(self, temp_dir):
        """Test loading a corrupted image file"""
        corrupted_path = os.path.join(temp_dir, "corrupted.tif")
        with open(corrupted_path, "wb") as f:
            f.write(b"Not a valid image\x00\x00\xff")

        with pytest.raises(ImageLoadError):
            safe_load_image(corrupted_path)

    def test_load_truncated_image(self, temp_dir):
        """Test loading a truncated image file"""
        truncated_path = os.path.join(temp_dir, "truncated.png")

        # Create valid image then truncate
        img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * 128)
        img.save(truncated_path)

        # Truncate to 50% of original size
        file_size = os.path.getsize(truncated_path)
        with open(truncated_path, "r+b") as f:
            f.truncate(file_size // 2)

        with pytest.raises(ImageLoadError):
            safe_load_image(truncated_path)

    # ===== Memory Error Simulation =====

    def test_load_image_memory_error(self, temp_dir):
        """Test handling MemoryError during image loading"""
        img_path = os.path.join(temp_dir, "test.tif")
        img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
        img.save(img_path)

        with patch("PIL.Image.open", side_effect=MemoryError("Out of memory")):
            with pytest.raises(ImageLoadError):
                safe_load_image(img_path)

    # ===== File I/O Errors =====

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file"""
        result = safe_load_image("/nonexistent/path/image.tif")
        # Should return None or empty array for nonexistent files
        assert result is None or len(result) == 0

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_load_image_permission_denied(self, temp_dir):
        """Test loading image without read permission"""
        img_path = os.path.join(temp_dir, "noperm.tif")
        img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
        img.save(img_path)

        os.chmod(img_path, 0o000)

        try:
            with pytest.raises(ImageLoadError):
                safe_load_image(img_path)
        finally:
            os.chmod(img_path, 0o644)

    # ===== Downsampling Edge Cases =====

    def test_downsample_by_zero(self):
        """Test downsampling by factor of zero"""
        test_img = np.ones((100, 100), dtype=np.uint8) * 128

        with pytest.raises((ValueError, ZeroDivisionError)):
            downsample_image(test_img, factor=0)

    def test_downsample_larger_than_image(self):
        """Test downsampling by factor larger than image size"""
        test_img = np.ones((10, 10), dtype=np.uint8) * 128

        # Downsample by 100x (larger than image)
        result = downsample_image(test_img, factor=100)

        # Should return minimal image or handle gracefully
        assert result is None or (result.shape[0] > 0 and result.shape[1] > 0)

    # ===== Disk Space Errors =====

    def test_save_image_disk_full(self, temp_dir):
        """Test saving image when disk is full"""
        test_img = np.ones((50, 50), dtype=np.uint8) * 100
        output_path = os.path.join(temp_dir, "full_disk.tif")

        with patch("PIL.Image.Image.save", side_effect=OSError(28, "No space left on device")):
            result = save_image_from_array(test_img, output_path)
            assert result is False

    # ===== Concurrent Access =====

    def test_simultaneous_image_loads(self, temp_dir):
        """Test loading same image from multiple threads"""
        from concurrent.futures import ThreadPoolExecutor

        img_path = os.path.join(temp_dir, "concurrent.tif")
        img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * 128)
        img.save(img_path)

        def load_image():
            return safe_load_image(img_path)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(load_image) for _ in range(50)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r is not None and len(r) > 0 for r in results)
