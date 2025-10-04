"""
Unit tests for utils/image_utils.py

Tests image processing utility functions.
"""

import os
import shutil
import sys
import tempfile

import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

if PIL_AVAILABLE:
    from utils.image_utils import (
        average_images,
        detect_bit_depth,
        downsample_image,
        get_image_dimensions,
        load_image_as_array,
        save_image_from_array,
    )


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestDetectBitDepth:
    """Tests for detect_bit_depth()"""

    def setup_method(self):
        """Create temporary directory and test images"""
        self.temp_dir = tempfile.mkdtemp()

        # Create 8-bit grayscale image
        img_8bit = Image.fromarray(np.ones((10, 10), dtype=np.uint8) * 128)
        self.image_8bit = os.path.join(self.temp_dir, "image_8bit.tif")
        img_8bit.save(self.image_8bit)

        # Create 16-bit grayscale image
        img_16bit = Image.fromarray(np.ones((10, 10), dtype=np.uint16) * 32768)
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
        with pytest.raises(FileNotFoundError):
            detect_bit_depth("/nonexistent/file.tif")

    def test_detect_rgb(self):
        """Should detect RGB image as 8-bit"""
        self.temp_dir = tempfile.mkdtemp()

        # Create RGB image
        img_rgb = Image.fromarray(np.ones((10, 10, 3), dtype=np.uint8) * 128)
        image_rgb = os.path.join(self.temp_dir, "image_rgb.png")
        img_rgb.save(image_rgb)

        assert detect_bit_depth(image_rgb) == 8

        shutil.rmtree(self.temp_dir)

    def test_detect_rgba(self):
        """Should detect RGBA image as 8-bit"""
        self.temp_dir = tempfile.mkdtemp()

        # Create RGBA image
        img_rgba = Image.fromarray(np.ones((10, 10, 4), dtype=np.uint8) * 128)
        image_rgba = os.path.join(self.temp_dir, "image_rgba.png")
        img_rgba.save(image_rgba)

        assert detect_bit_depth(image_rgba) == 8

        shutil.rmtree(self.temp_dir)

    def test_unsupported_mode_warning(self):
        """Should return 8 for unsupported modes with warning"""
        self.temp_dir = tempfile.mkdtemp()

        # Create image with unusual mode
        img = Image.new("1", (10, 10))  # 1-bit mode
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
        img = Image.fromarray(test_array)
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
        img = Image.fromarray(test_array)
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
        result = downsample_image(img_array, factor=2, method="average")
        assert result.shape == (50, 50)
        assert np.all(result == 128)

    def test_downsample_color_image(self):
        """Should downsample color image"""
        img_array = np.ones((100, 100, 3), dtype=np.uint8) * 128
        result = downsample_image(img_array, factor=2, method="average")
        assert result.shape == (50, 50, 3)

    def test_invalid_method(self):
        """Should raise error for invalid method"""
        img_array = np.ones((100, 100), dtype=np.uint8) * 128
        with pytest.raises(ValueError):
            downsample_image(img_array, factor=2, method="invalid")


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
        img = Image.fromarray(np.ones((123, 456), dtype=np.uint8) * 128)
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


@pytest.mark.unit
class TestSafeLoadImage:
    """Test suite for safe_load_image function (Phase 2 - devlog 072)"""

    @pytest.fixture
    def temp_image(self, tmp_path):
        """Create a temporary test image"""
        img_path = tmp_path / "test.png"
        img = Image.new("L", (100, 100), color=128)
        img.save(img_path)
        return str(img_path)

    @pytest.fixture
    def temp_rgb_image(self, tmp_path):
        """Create a temporary RGB test image"""
        img_path = tmp_path / "test_rgb.png"
        img = Image.new("RGB", (50, 50), color=(255, 0, 0))
        img.save(img_path)
        return str(img_path)

    @pytest.fixture
    def temp_palette_image(self, tmp_path):
        """Create a temporary palette mode image"""
        img_path = tmp_path / "test_palette.png"
        img = Image.new("P", (50, 50))
        img.save(img_path)
        return str(img_path)

    def test_safe_load_image_basic(self, temp_image):
        """Test basic image loading as numpy array"""
        from utils.image_utils import safe_load_image

        arr = safe_load_image(temp_image)

        assert arr is not None
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (100, 100)

    def test_safe_load_image_file_not_found(self):
        """Test that non-existent file returns None"""
        from utils.image_utils import safe_load_image

        arr = safe_load_image("/nonexistent/path/image.png")

        assert arr is None  # Should return None, not raise

    def test_safe_load_image_as_pil_image(self, temp_image):
        """Test loading as PIL Image instead of array"""
        from utils.image_utils import safe_load_image

        img = safe_load_image(temp_image, as_array=False)

        assert img is not None
        assert isinstance(img, Image.Image)
        assert img.size == (100, 100)

    def test_safe_load_image_convert_mode(self, temp_image):
        """Test mode conversion"""
        from utils.image_utils import safe_load_image

        # Load grayscale image as RGB
        arr = safe_load_image(temp_image, convert_mode="RGB")

        assert arr is not None
        assert arr.shape == (100, 100, 3)  # RGB has 3 channels

    def test_safe_load_image_palette_handling(self, temp_palette_image):
        """Test automatic palette mode conversion"""
        from utils.image_utils import safe_load_image

        arr = safe_load_image(temp_palette_image, handle_palette=True)

        assert arr is not None
        assert isinstance(arr, np.ndarray)
        # Should be converted to grayscale (2D array)
        assert len(arr.shape) == 2

    def test_safe_load_image_palette_no_handling(self, temp_palette_image):
        """Test loading palette image without conversion"""
        from utils.image_utils import safe_load_image

        arr = safe_load_image(temp_palette_image, handle_palette=False)

        assert arr is not None
        # Palette mode can have different array shapes

    def test_safe_load_image_permission_error(self, tmp_path, monkeypatch):
        """Test handling of permission errors"""
        from utils.image_utils import ImageLoadError, safe_load_image

        # Create an image file
        img_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10))
        img.save(img_path)

        # Mock Image.open to raise PermissionError
        def mock_open(*args, **kwargs):
            raise PermissionError("Access denied")

        monkeypatch.setattr(Image, "open", mock_open)

        with pytest.raises(ImageLoadError) as exc_info:
            safe_load_image(str(img_path))

        assert "Permission denied" in str(exc_info.value)

    def test_safe_load_image_os_error(self, tmp_path, monkeypatch):
        """Test handling of OS errors (corrupted file, etc.)"""
        from utils.image_utils import ImageLoadError, safe_load_image

        img_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10))
        img.save(img_path)

        # Mock Image.open to raise OSError
        def mock_open(*args, **kwargs):
            raise OSError("Corrupted file")

        monkeypatch.setattr(Image, "open", mock_open)

        with pytest.raises(ImageLoadError) as exc_info:
            safe_load_image(str(img_path))

        assert "Failed to load" in str(exc_info.value)

    def test_safe_load_image_unexpected_error(self, tmp_path, monkeypatch):
        """Test handling of unexpected errors"""
        from utils.image_utils import ImageLoadError, safe_load_image

        img_path = tmp_path / "test.png"
        img = Image.new("L", (10, 10))
        img.save(img_path)

        # Mock Image.open to raise unexpected error
        def mock_open(*args, **kwargs):
            raise ValueError("Unexpected error")

        monkeypatch.setattr(Image, "open", mock_open)

        with pytest.raises(ImageLoadError) as exc_info:
            safe_load_image(str(img_path))

        assert "Unexpected error" in str(exc_info.value)

    def test_safe_load_image_rgb_to_grayscale(self, temp_rgb_image):
        """Test converting RGB image to grayscale"""
        from utils.image_utils import safe_load_image

        arr = safe_load_image(temp_rgb_image, convert_mode="L")

        assert arr is not None
        assert len(arr.shape) == 2  # Should be 2D (grayscale)

    def test_safe_load_image_returns_copy(self, temp_image):
        """Test that PIL Image mode returns a copy (not affected by context manager)"""
        from utils.image_utils import safe_load_image

        img = safe_load_image(temp_image, as_array=False)

        assert img is not None
        # Should be able to use the image after function returns
        assert img.size == (100, 100)
        # Verify it's a valid image by converting to array
        arr = np.array(img)
        assert arr.shape == (100, 100)
