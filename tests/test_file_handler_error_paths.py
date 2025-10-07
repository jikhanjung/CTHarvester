"""
Error path tests for FileHandler class

Tests error handling scenarios including permissions, corrupted files,
and edge cases.
"""

import os
import shutil
import tempfile

import numpy as np
import pytest
from PIL import Image

from core.file_handler import (
    CorruptedImageError,
    FileHandler,
    InvalidImageFormatError,
    NoImagesFoundError,
)
from utils.image_utils import ImageLoadError, safe_load_image


@pytest.mark.unit
class TestFileHandlerErrorPaths:
    """Error path test suite for FileHandler"""

    @pytest.fixture
    def handler(self):
        """Create a FileHandler instance"""
        return FileHandler()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        if os.path.exists(temp_dir):
            # Restore permissions before cleanup
            for root, dirs, files in os.walk(temp_dir):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), 0o755)
                    except:
                        pass
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), 0o644)
                    except:
                        pass
            shutil.rmtree(temp_dir)

    # ===== Permission Errors =====

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_open_directory_no_read_permission(self, handler, temp_dir):
        """Test opening directory without read permission"""
        # Create some valid images first
        for i in range(1, 4):
            img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
            img.save(os.path.join(temp_dir, f"img_{i:03d}.tif"))

        # Remove read permission
        os.chmod(temp_dir, 0o000)

        try:
            # Should raise PermissionError
            with pytest.raises(PermissionError):
                handler.open_directory(temp_dir)
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_dir, 0o755)

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_read_image_no_permission(self, temp_dir):
        """Test reading image file without read permission"""
        img_path = os.path.join(temp_dir, "test.tif")
        img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
        img.save(img_path)

        os.chmod(img_path, 0o000)

        try:
            with pytest.raises(ImageLoadError):
                safe_load_image(img_path)
        finally:
            os.chmod(img_path, 0o644)

    # ===== Corrupted File Errors =====

    def test_read_corrupted_image(self, temp_dir):
        """Test reading a corrupted image file"""
        corrupted_path = os.path.join(temp_dir, "corrupted.tif")
        with open(corrupted_path, "wb") as f:
            f.write(b"This is not a valid image file")

        with pytest.raises(ImageLoadError):
            safe_load_image(corrupted_path)

    def test_read_truncated_image(self, temp_dir):
        """Test reading a truncated image file"""
        truncated_path = os.path.join(temp_dir, "truncated.tif")

        # Create a valid image first
        img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * 128)
        img.save(truncated_path)

        # Truncate the file (remove last 50% of data)
        file_size = os.path.getsize(truncated_path)
        with open(truncated_path, "r+b") as f:
            f.truncate(file_size // 2)

        with pytest.raises(ImageLoadError):
            safe_load_image(truncated_path)

    # ===== Empty/Invalid Data Errors =====

    def test_open_empty_directory(self, handler, temp_dir):
        """Test opening empty directory"""
        # Should raise NoImagesFoundError
        with pytest.raises(NoImagesFoundError):
            handler.open_directory(temp_dir)

    def test_open_directory_no_images(self, handler, temp_dir):
        """Test opening directory with no image files"""
        # Create only non-image files
        with open(os.path.join(temp_dir, "readme.txt"), "w") as f:
            f.write("No images here")

        # Should raise NoImagesFoundError
        with pytest.raises(NoImagesFoundError):
            handler.open_directory(temp_dir)

    # ===== Null/Invalid Input =====

    def test_open_directory_none(self, handler):
        """Test opening None directory"""
        # Should raise TypeError or similar
        with pytest.raises((TypeError, ValueError, AttributeError)):
            handler.open_directory(None)

    def test_open_directory_empty_string(self, handler):
        """Test opening empty string directory"""
        # Empty string is current directory, should raise appropriate error
        with pytest.raises((NoImagesFoundError, InvalidImageFormatError, FileNotFoundError)):
            handler.open_directory("")

    def test_read_image_none_path(self):
        """Test reading None image path"""
        with pytest.raises((TypeError, AttributeError, ImageLoadError)):
            safe_load_image(None)

    # ===== File System Edge Cases =====

    def test_open_directory_is_file(self, handler, temp_dir):
        """Test opening a file instead of directory"""
        file_path = os.path.join(temp_dir, "not_a_dir.txt")
        with open(file_path, "w") as f:
            f.write("test")

        # Should raise NotADirectoryError
        with pytest.raises(NotADirectoryError):
            handler.open_directory(file_path)
