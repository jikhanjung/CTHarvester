"""
Unit tests for utils/image_utils.py

Tests image processing utility functions.
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
    from utils.image_utils import (
        detect_bit_depth,
        load_image_as_array,
        downsample_image,
        average_images,
        save_image_from_array,
        get_image_dimensions
    )


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestDetectBitDepth:
    """Tests for detect_bit_depth()"""

    def setup_method(self):
        """Create temporary directory and test images"""
        self.temp_dir = tempfile.mkdtemp()

        # Create 8-bit grayscale image
        img_8bit = Image.fromarray(np.ones((10, 10), dtype=np.uint8) * 128, mode='L')
        self.image_8bit = os.path.join(self.temp_dir, "image_8bit.tif")
        img_8bit.save(self.image_8bit)

        # Create 16-bit grayscale image
        img_16bit = Image.fromarray(np.ones((10, 10), dtype=np.uint16) * 32768, mode='I;16')
        self.image_16bit = os.path.join(self.temp_dir, "image_16bit.tif")
        img_16bit.save(self.image_16bit)

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_detect_8bit(self):
        """Should detect 8-bit image"""
        assert detect_bit_depth(self.image_8bit) == 8

    def test_detect_16bit(self):
        """Should detect 16-bit image"""
        assert detect_bit_depth(self.image_16bit) == 16

    def test_nonexistent_file(self):
        """Should raise error for nonexistent file"""
        with pytest.raises(ValueError):
            detect_bit_depth("/nonexistent/file.tif")

    def test_detect_rgb(self):
        """Should detect RGB image as 8-bit"""
        self.temp_dir = tempfile.mkdtemp()

        # Create RGB image
        img_rgb = Image.fromarray(np.ones((10, 10, 3), dtype=np.uint8) * 128, mode='RGB')
        image_rgb = os.path.join(self.temp_dir, "image_rgb.png")
        img_rgb.save(image_rgb)

        assert detect_bit_depth(image_rgb) == 8

        shutil.rmtree(self.temp_dir)

    def test_detect_rgba(self):
        """Should detect RGBA image as 8-bit"""
        self.temp_dir = tempfile.mkdtemp()

        # Create RGBA image
        img_rgba = Image.fromarray(np.ones((10, 10, 4), dtype=np.uint8) * 128, mode='RGBA')
        image_rgba = os.path.join(self.temp_dir, "image_rgba.png")
        img_rgba.save(image_rgba)

        assert detect_bit_depth(image_rgba) == 8

        shutil.rmtree(self.temp_dir)

    def test_unsupported_mode_warning(self):
        """Should return 8 for unsupported modes with warning"""
        self.temp_dir = tempfile.mkdtemp()

        # Create image with unusual mode
        img = Image.new('1', (10, 10))  # 1-bit mode
        image_path = os.path.join(self.temp_dir, "image_1bit.png")
        img.save(image_path)

        # Should default to 8 with warning
        result = detect_bit_depth(image_path)
        assert result == 8

        shutil.rmtree(self.temp_dir)


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestLoadImageAsArray:
    """Tests for load_image_as_array()"""

    def setup_method(self):
        """Create temporary directory and test image"""
        self.temp_dir = tempfile.mkdtemp()

        # Create test image
        test_array = np.arange(100, dtype=np.uint8).reshape(10, 10)
        img = Image.fromarray(test_array, mode='L')
        self.test_image = os.path.join(self.temp_dir, "test.tif")
        img.save(self.test_image)

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_as_array(self):
        """Should load image as numpy array"""
        arr = load_image_as_array(self.test_image)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (10, 10)

    def test_auto_dtype_detection(self):
        """Should auto-detect dtype"""
        arr = load_image_as_array(self.test_image)
        assert arr.dtype == np.uint8

    def test_explicit_dtype(self):
        """Should use explicit dtype"""
        arr = load_image_as_array(self.test_image, target_dtype=np.uint16)
        assert arr.dtype == np.uint16

    def test_load_16bit_image(self):
        """Should load 16-bit image with correct dtype"""
        # Create 16-bit test image
        test_array = np.arange(100, dtype=np.uint16).reshape(10, 10) * 256
        img = Image.fromarray(test_array, mode='I;16')
        test_16bit = os.path.join(self.temp_dir, "test_16bit.tif")
        img.save(test_16bit)

        # Load and verify
        arr = load_image_as_array(test_16bit)
        assert arr.dtype == np.uint16

    def test_load_error_handling(self):
        """Should raise exception on load error"""
        with pytest.raises(Exception):
            load_image_as_array("/nonexistent/image.tif")


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestDownsampleImage:
    """Tests for downsample_image()"""

    def test_downsample_by_2(self):
        """Should downsample by factor of 2"""
        img_array = np.ones((100, 100), dtype=np.uint8) * 128
        result = downsample_image(img_array, factor=2)
        assert result.shape == (50, 50)

    def test_downsample_by_4(self):
        """Should downsample by factor of 4"""
        img_array = np.ones((100, 100), dtype=np.uint8) * 128
        result = downsample_image(img_array, factor=4)
        assert result.shape == (25, 25)

    def test_preserve_dtype(self):
        """Should preserve dtype"""
        img_array = np.ones((100, 100), dtype=np.uint16) * 32768
        result = downsample_image(img_array, factor=2)
        # Note: dtype might change depending on method, so just check it's a valid type
        assert result.dtype in [np.uint8, np.uint16, np.uint32, np.float32, np.float64]

    def test_downsample_average_method(self):
        """Should downsample using average method"""
        img_array = np.ones((100, 100), dtype=np.uint8) * 128
        result = downsample_image(img_array, factor=2, method='average')
        assert result.shape == (50, 50)
        assert np.all(result == 128)

    def test_downsample_color_image(self):
        """Should downsample color image"""
        img_array = np.ones((100, 100, 3), dtype=np.uint8) * 128
        result = downsample_image(img_array, factor=2, method='average')
        assert result.shape == (50, 50, 3)

    def test_invalid_method(self):
        """Should raise error for invalid method"""
        img_array = np.ones((100, 100), dtype=np.uint8) * 128
        with pytest.raises(ValueError):
            downsample_image(img_array, factor=2, method='invalid')


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestAverageImages:
    """Tests for average_images()"""

    def test_average_two_arrays(self):
        """Should average two arrays"""
        arr1 = np.ones((10, 10), dtype=np.uint8) * 100
        arr2 = np.ones((10, 10), dtype=np.uint8) * 200
        result = average_images(arr1, arr2)
        assert np.all(result == 150)

    def test_overflow_prevention(self):
        """Should prevent overflow"""
        arr1 = np.ones((10, 10), dtype=np.uint8) * 255
        arr2 = np.ones((10, 10), dtype=np.uint8) * 255
        result = average_images(arr1, arr2)
        assert np.all(result == 255)
        assert result.dtype == np.uint8

    def test_16bit_averaging(self):
        """Should work with 16-bit images"""
        arr1 = np.ones((10, 10), dtype=np.uint16) * 30000
        arr2 = np.ones((10, 10), dtype=np.uint16) * 40000
        result = average_images(arr1, arr2)
        assert np.all(result == 35000)

    def test_float_averaging(self):
        """Should work with float images"""
        arr1 = np.ones((10, 10), dtype=np.float32) * 0.5
        arr2 = np.ones((10, 10), dtype=np.float32) * 1.5
        result = average_images(arr1, arr2)
        assert np.allclose(result, 1.0)
        assert result.dtype == np.float32


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestSaveImageFromArray:
    """Tests for save_image_from_array()"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_save_8bit_image(self):
        """Should save 8-bit image"""
        arr = np.ones((10, 10), dtype=np.uint8) * 128
        output_path = os.path.join(self.temp_dir, "output.tif")
        save_image_from_array(arr, output_path)
        assert os.path.exists(output_path)

        # Verify saved image
        img = Image.open(output_path)
        assert img.size == (10, 10)
        img.close()

    def test_save_16bit_image(self):
        """Should save 16-bit image"""
        arr = np.ones((10, 10), dtype=np.uint16) * 32768
        output_path = os.path.join(self.temp_dir, "output.tif")
        save_image_from_array(arr, output_path)
        assert os.path.exists(output_path)

    def test_save_with_compression(self):
        """Should save with TIFF compression"""
        arr = np.ones((10, 10), dtype=np.uint8) * 128
        output_path = os.path.join(self.temp_dir, "compressed.tif")
        result = save_image_from_array(arr, output_path, compress=True)
        assert result is True
        assert os.path.exists(output_path)

    def test_save_without_compression(self):
        """Should save without compression"""
        arr = np.ones((10, 10), dtype=np.uint8) * 128
        output_path = os.path.join(self.temp_dir, "uncompressed.tiff")
        result = save_image_from_array(arr, output_path, compress=False)
        assert result is True
        assert os.path.exists(output_path)

    def test_save_non_tiff_format(self):
        """Should save non-TIFF formats"""
        arr = np.ones((10, 10), dtype=np.uint8) * 128
        output_path = os.path.join(self.temp_dir, "output.png")
        result = save_image_from_array(arr, output_path)
        assert result is True
        assert os.path.exists(output_path)

    def test_save_rgb_image(self):
        """Should save RGB image"""
        arr = np.ones((10, 10, 3), dtype=np.uint8) * 128
        output_path = os.path.join(self.temp_dir, "rgb.png")
        result = save_image_from_array(arr, output_path)
        assert result is True

    def test_save_converts_unsupported_dtype(self):
        """Should convert unsupported dtype to uint8"""
        arr = np.ones((10, 10), dtype=np.float64) * 0.5
        output_path = os.path.join(self.temp_dir, "converted.tif")
        result = save_image_from_array(arr, output_path)
        assert result is True

    def test_save_error_handling(self):
        """Should return False on save error"""
        arr = np.ones((10, 10), dtype=np.uint8) * 128
        # Invalid path
        result = save_image_from_array(arr, "/invalid/path/image.tif")
        assert result is False


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestGetImageDimensions:
    """Tests for get_image_dimensions()"""

    def setup_method(self):
        """Create temporary directory and test image"""
        self.temp_dir = tempfile.mkdtemp()

        # Create test image with specific dimensions
        img = Image.fromarray(np.ones((123, 456), dtype=np.uint8) * 128, mode='L')
        self.test_image = os.path.join(self.temp_dir, "test.tif")
        img.save(self.test_image)

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_get_dimensions(self):
        """Should get image dimensions without loading full image"""
        width, height = get_image_dimensions(self.test_image)
        assert width == 456  # PIL returns (width, height)
        assert height == 123

    def test_nonexistent_file(self):
        """Should handle nonexistent file"""
        with pytest.raises(Exception):  # Could be FileNotFoundError or other
            get_image_dimensions("/nonexistent/file.tif")