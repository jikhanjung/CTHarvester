"""
Tests for FileHandler class

Tests the file operations logic extracted from main_window.py
"""

import os
import shutil
import tempfile

import numpy as np
import pytest
from PIL import Image

from core.file_handler import FileHandler
from security.file_validator import FileSecurityError


class TestFileHandler:
    """Test suite for FileHandler"""

    @pytest.fixture
    def handler(self):
        """Create a FileHandler instance"""
        return FileHandler()

    @pytest.fixture
    def temp_ct_dir(self):
        """Create a temporary directory with CT image stack"""
        temp_dir = tempfile.mkdtemp()

        # Create a CT stack: slice_0001.tif to slice_0010.tif
        for i in range(1, 11):
            img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * (i * 25))
            img.save(os.path.join(temp_dir, f"slice_{i:04d}.tif"))

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def temp_mixed_dir(self):
        """Create a directory with mixed file types"""
        temp_dir = tempfile.mkdtemp()

        # CT images
        for i in range(1, 6):
            img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
            img.save(os.path.join(temp_dir, f"scan_{i:03d}.tif"))

        # Other files (should be ignored)
        with open(os.path.join(temp_dir, "README.txt"), "w") as f:
            f.write("Test file")

        with open(os.path.join(temp_dir, "scan.log"), "w") as f:
            f.write("Log data")

        yield temp_dir

        shutil.rmtree(temp_dir)

    def test_initialization(self, handler):
        """Test handler initializes correctly"""
        assert handler is not None
        assert handler.validator is not None
        assert FileHandler.SUPPORTED_EXTENSIONS == {
            ".tif",
            ".tiff",
            ".bmp",
            ".jpg",
            ".jpeg",
            ".png",
        }

    def test_supported_extensions(self, handler):
        """Test supported extension list"""
        supported = handler.SUPPORTED_EXTENSIONS
        assert ".tif" in supported
        assert ".tiff" in supported
        assert ".jpg" in supported
        assert ".png" in supported
        assert ".bmp" in supported

    def test_open_directory_valid(self, handler, temp_ct_dir):
        """Test opening valid CT directory"""
        settings = handler.open_directory(temp_ct_dir)

        assert settings is not None
        assert settings["prefix"] == "slice_"
        assert settings["file_type"] == "tif"
        assert settings["seq_begin"] == 1
        assert settings["seq_end"] == 10
        assert settings["index_length"] == 4
        assert settings["image_width"] == 100
        assert settings["image_height"] == 100

    def test_open_directory_nonexistent(self, handler):
        """Test opening nonexistent directory"""
        settings = handler.open_directory("/nonexistent/path")
        assert settings is None

    def test_open_directory_empty(self, handler):
        """Test opening empty directory"""
        temp_dir = tempfile.mkdtemp()
        try:
            settings = handler.open_directory(temp_dir)
            assert settings is None
        finally:
            os.rmdir(temp_dir)

    def test_sort_file_list_from_dir_simple(self, handler, temp_ct_dir):
        """Test file sorting with simple pattern"""
        settings = handler.sort_file_list_from_dir(temp_ct_dir)

        assert settings is not None
        assert settings["prefix"] == "slice_"
        assert settings["file_type"] == "tif"
        assert settings["seq_begin"] == 1
        assert settings["seq_end"] == 10

    def test_sort_file_list_from_dir_mixed_files(self, handler, temp_mixed_dir):
        """Test file sorting with mixed file types"""
        settings = handler.sort_file_list_from_dir(temp_mixed_dir)

        assert settings is not None
        assert settings["prefix"] == "scan_"
        assert settings["file_type"] == "tif"
        assert settings["seq_begin"] == 1
        assert settings["seq_end"] == 5
        assert settings["index_length"] == 3

    def test_sort_file_list_no_pattern(self, handler):
        """Test sorting when no valid pattern exists"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create files without numeric pattern
            with open(os.path.join(temp_dir, "file_a.tif"), "w") as f:
                f.write("test")
            with open(os.path.join(temp_dir, "file_b.tif"), "w") as f:
                f.write("test")

            settings = handler.sort_file_list_from_dir(temp_dir)
            assert settings is None

        finally:
            shutil.rmtree(temp_dir)

    def test_natural_sort(self, handler):
        """Test natural sorting of filenames"""
        pattern = r"^(.*?)(\d+)\.(\w+)$"
        files = ["slice_1.tif", "slice_10.tif", "slice_2.tif", "slice_20.tif"]

        sorted_files = handler._natural_sort(files, pattern)

        assert sorted_files == ["slice_1.tif", "slice_2.tif", "slice_10.tif", "slice_20.tif"]

    def test_get_file_list(self, handler, temp_ct_dir):
        """Test getting full file paths"""
        settings = handler.sort_file_list_from_dir(temp_ct_dir)
        file_list = handler.get_file_list(temp_ct_dir, settings)

        assert len(file_list) == 10
        assert all(os.path.exists(f) for f in file_list)
        assert file_list[0].endswith("slice_0001.tif")
        assert file_list[-1].endswith("slice_0010.tif")

    def test_get_file_list_missing_files(self, handler, temp_ct_dir):
        """Test getting file list when some files are missing"""
        # Remove one file
        os.remove(os.path.join(temp_ct_dir, "slice_0005.tif"))

        settings = handler.sort_file_list_from_dir(temp_ct_dir)
        file_list = handler.get_file_list(temp_ct_dir, settings)

        # Should return 9 files (missing one)
        assert len(file_list) == 9
        assert not any("slice_0005.tif" in f for f in file_list)

    def test_validate_directory_structure_valid(self, handler, temp_ct_dir):
        """Test directory validation with valid directory"""
        result = handler.validate_directory_structure(temp_ct_dir)
        assert result is True

    def test_validate_directory_structure_nonexistent(self, handler):
        """Test directory validation with nonexistent path"""
        result = handler.validate_directory_structure("/nonexistent/path")
        assert result is False

    def test_validate_directory_structure_no_images(self, handler):
        """Test directory validation with no image files"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create only text files
            with open(os.path.join(temp_dir, "test.txt"), "w") as f:
                f.write("test")

            result = handler.validate_directory_structure(temp_dir)
            assert result is False

        finally:
            shutil.rmtree(temp_dir)

    def test_find_log_file_exists(self, handler, temp_mixed_dir):
        """Test finding log file when it exists"""
        log_path = handler.find_log_file(temp_mixed_dir)

        assert log_path is not None
        assert log_path.endswith("scan.log")
        assert os.path.exists(log_path)

    def test_find_log_file_not_exists(self, handler, temp_ct_dir):
        """Test finding log file when it doesn't exist"""
        log_path = handler.find_log_file(temp_ct_dir)
        assert log_path is None

    def test_count_files_in_directory(self, handler, temp_ct_dir):
        """Test counting files in directory"""
        count = handler.count_files_in_directory(temp_ct_dir)
        assert count == 10

    def test_count_files_with_extension_filter(self, handler, temp_mixed_dir):
        """Test counting files with extension filter"""
        # Count only .tif files
        count = handler.count_files_in_directory(temp_mixed_dir, ".tif")
        assert count == 5

        # Count all files
        total_count = handler.count_files_in_directory(temp_mixed_dir)
        assert total_count == 7  # 5 .tif + 1 .txt + 1 .log

    def test_count_files_nonexistent_directory(self, handler):
        """Test counting files in nonexistent directory"""
        count = handler.count_files_in_directory("/nonexistent/path")
        assert count == 0

    @pytest.mark.parametrize(
        "prefix,start,end,length,extension",
        [
            ("image_", 0, 99, 4, "tif"),
            ("scan_", 1, 50, 3, "png"),
            ("slice_", 100, 199, 5, "jpg"),
        ],
    )
    def test_various_patterns(self, handler, prefix, start, end, length, extension):
        """Test handling various file naming patterns"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create files with specified pattern
            for i in range(start, start + 5):  # Create 5 files
                img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
                filename = f"{prefix}{i:0{length}d}.{extension}"
                img.save(os.path.join(temp_dir, filename))

            settings = handler.sort_file_list_from_dir(temp_dir)

            assert settings is not None
            assert settings["prefix"] == prefix
            assert settings["file_type"] == extension
            assert settings["index_length"] == length

        finally:
            shutil.rmtree(temp_dir)

    def test_multiple_prefixes_chooses_most_common(self, handler):
        """Test that most common prefix is chosen when multiple prefixes exist"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create files with different prefixes
            # 10 files with 'main_' prefix
            for i in range(10):
                img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
                img.save(os.path.join(temp_dir, f"main_{i:03d}.tif"))

            # 3 files with 'other_' prefix
            for i in range(3):
                img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
                img.save(os.path.join(temp_dir, f"other_{i:03d}.tif"))

            settings = handler.sort_file_list_from_dir(temp_dir)

            # Should choose 'main_' as most common
            assert settings is not None
            assert settings["prefix"] == "main_"
            assert settings["seq_begin"] == 0
            assert settings["seq_end"] == 9

        finally:
            shutil.rmtree(temp_dir)

    def test_different_image_sizes(self, handler):
        """Test handling images with different sizes"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create images with different sizes (only first is checked)
            sizes = [100, 200, 150, 120, 180]
            for i, size in enumerate(sizes):
                img = Image.fromarray(np.ones((size, size), dtype=np.uint8) * 100)
                img.save(os.path.join(temp_dir, f"img_{i:03d}.tif"))

            settings = handler.sort_file_list_from_dir(temp_dir)

            # Should report size of first image
            assert settings is not None
            assert settings["image_width"] == 100
            assert settings["image_height"] == 100

        finally:
            shutil.rmtree(temp_dir)

    def test_unsupported_extension_ignored(self, handler):
        """Test that unsupported extensions are ignored"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create files with unsupported extension
            for i in range(5):
                with open(os.path.join(temp_dir, f"data_{i:03d}.dat"), "w") as f:
                    f.write("test data")

            settings = handler.sort_file_list_from_dir(temp_dir)

            # Should return None (no supported files)
            assert settings is None

        finally:
            shutil.rmtree(temp_dir)


class TestFileHandlerEdgeCases:
    """Edge case tests for FileHandler"""

    @pytest.fixture
    def handler(self):
        return FileHandler()

    def test_single_file(self, handler):
        """Test with only one file in directory"""
        temp_dir = tempfile.mkdtemp()
        try:
            img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
            img.save(os.path.join(temp_dir, "single_0001.tif"))

            settings = handler.sort_file_list_from_dir(temp_dir)

            assert settings is not None
            assert settings["seq_begin"] == 1
            assert settings["seq_end"] == 1

        finally:
            shutil.rmtree(temp_dir)

    def test_non_sequential_numbers(self, handler):
        """Test with non-sequential file numbers"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create files: 1, 5, 10, 15
            for i in [1, 5, 10, 15]:
                img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
                img.save(os.path.join(temp_dir, f"gap_{i:03d}.tif"))

            settings = handler.sort_file_list_from_dir(temp_dir)

            # Should report range based on first and last
            assert settings is not None
            assert settings["seq_begin"] == 1
            assert settings["seq_end"] == 15

        finally:
            shutil.rmtree(temp_dir)

    def test_very_long_prefix(self, handler):
        """Test with very long file prefix"""
        temp_dir = tempfile.mkdtemp()
        try:
            long_prefix = "very_long_prefix_name_for_ct_scan_data_"

            for i in range(3):
                img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
                img.save(os.path.join(temp_dir, f"{long_prefix}{i:04d}.tif"))

            settings = handler.sort_file_list_from_dir(temp_dir)

            assert settings is not None
            assert settings["prefix"] == long_prefix

        finally:
            shutil.rmtree(temp_dir)

    def test_corrupted_image_file(self, handler):
        """Test handling of corrupted image file"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create one valid image
            img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
            img.save(os.path.join(temp_dir, "valid_0001.tif"))

            # Create corrupted file (not a valid image)
            with open(os.path.join(temp_dir, "valid_0002.tif"), "w") as f:
                f.write("This is not a valid TIFF file")

            # Should still detect the pattern despite corrupted file
            settings = handler.sort_file_list_from_dir(temp_dir)

            assert settings is not None
            assert settings["prefix"] == "valid_"

        finally:
            shutil.rmtree(temp_dir)

    def test_unicode_prefix(self, handler):
        """Test with Unicode characters in prefix"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create files with Unicode prefix
            for i in range(3):
                img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
                img.save(os.path.join(temp_dir, f"데이터_{i:03d}.tif"))

            settings = handler.sort_file_list_from_dir(temp_dir)

            assert settings is not None
            assert settings["prefix"] == "데이터_"
            assert settings["seq_begin"] == 0
            assert settings["seq_end"] == 2

        finally:
            shutil.rmtree(temp_dir)

    def test_zero_padded_vs_non_padded(self, handler):
        """Test natural sorting with zero-padded numbers"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create mix of padded numbers
            for i in [1, 2, 10, 20, 100]:
                img = Image.fromarray(np.ones((50, 50), dtype=np.uint8) * 100)
                img.save(os.path.join(temp_dir, f"img_{i:04d}.tif"))

            settings = handler.sort_file_list_from_dir(temp_dir)
            file_list = handler.get_file_list(temp_dir, settings)

            # Should be in numeric order
            assert len(file_list) == 5
            assert "img_0001.tif" in file_list[0]
            assert "img_0100.tif" in file_list[4]

        finally:
            shutil.rmtree(temp_dir)
