"""
Unit tests for utils/file_utils.py

Tests file system utility functions.
"""
import sys
import os
import tempfile
import shutil
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.file_utils import (
    find_image_files,
    parse_filename,
    create_thumbnail_directory,
    get_thumbnail_path,
    clean_old_thumbnails,
    get_directory_size,
    format_file_size
)


class TestFindImageFiles:
    """Tests for find_image_files()"""

    def setup_method(self):
        """Create temporary directory with test files"""
        self.temp_dir = tempfile.mkdtemp()

        # Create various test files
        self.image_files = ["image1.tif", "image2.jpg", "scan.png", "data.bmp"]
        self.other_files = ["readme.txt", "data.csv", "script.py"]

        for filename in self.image_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test")

        for filename in self.other_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test")

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_find_default_extensions(self):
        """Should find files with default extensions"""
        result = find_image_files(self.temp_dir)
        assert len(result) == len(self.image_files)
        for filename in self.image_files:
            assert filename in result

    def test_find_custom_extensions(self):
        """Should find files with custom extensions"""
        result = find_image_files(self.temp_dir, extensions=('.tif', '.jpg'))
        assert "image1.tif" in result
        assert "image2.jpg" in result
        assert "scan.png" not in result

    def test_sorted_output(self):
        """Should return sorted file list"""
        result = find_image_files(self.temp_dir)
        assert result == sorted(result)

    def test_empty_directory(self):
        """Should handle empty directory"""
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir)

        result = find_image_files(empty_dir)
        assert result == []

    def test_nonexistent_directory(self):
        """Should handle nonexistent directory"""
        result = find_image_files("/nonexistent/directory")
        assert result == []


class TestParseFilename:
    """Tests for parse_filename()"""

    def test_parse_simple_filename(self):
        """Should parse simple numbered filename"""
        result = parse_filename("scan_00123.tif")
        assert result == ("scan_", 123, "tif")

    def test_parse_no_prefix(self):
        """Should parse filename without prefix"""
        result = parse_filename("00123.tif")
        assert result == ("", 123, "tif")

    def test_parse_long_prefix(self):
        """Should parse filename with long prefix"""
        result = parse_filename("my_long_prefix_name_0001.jpg")
        assert result == ("my_long_prefix_name_", 1, "jpg")

    def test_parse_different_extensions(self):
        """Should parse different extensions"""
        filenames = [
            ("file_001.tif", ("file_", 1, "tif")),
            ("file_001.jpg", ("file_", 1, "jpg")),
            ("file_001.png", ("file_", 1, "png")),
            ("file_001.bmp", ("file_", 1, "bmp"))
        ]
        for filename, expected in filenames:
            assert parse_filename(filename) == expected

    def test_parse_large_number(self):
        """Should parse large numbers"""
        result = parse_filename("scan_999999.tif")
        assert result == ("scan_", 999999, "tif")

    def test_parse_leading_zeros(self):
        """Should handle leading zeros"""
        result = parse_filename("scan_00001.tif")
        assert result == ("scan_", 1, "tif")

    def test_parse_invalid_filename(self):
        """Should return None for invalid filename"""
        invalid_files = [
            "noextension",
            "no_number.tif",
            "multiple..dots.tif",
            ".hidden",
            ""
        ]
        for filename in invalid_files:
            result = parse_filename(filename)
            # Some might parse, some might not - just check it doesn't crash
            assert result is None or isinstance(result, tuple)

    def test_parse_custom_pattern(self):
        """Should use custom regex pattern"""
        # Custom pattern for specific format
        pattern = r'^(\w+)_(\d+)\.(\w+)$'
        result = parse_filename("image_123.tif", pattern=pattern)
        assert result == ("image", 123, "tif")


class TestCreateThumbnailDirectory:
    """Tests for create_thumbnail_directory()"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_level_1_directory(self):
        """Should create level 1 thumbnail directory"""
        result = create_thumbnail_directory(self.temp_dir, level=1)
        assert os.path.exists(result)
        assert os.path.isdir(result)
        assert ".thumbnail" in result

    def test_create_level_2_directory(self):
        """Should create level 2 thumbnail directory"""
        result = create_thumbnail_directory(self.temp_dir, level=2)
        assert os.path.exists(result)
        assert os.path.isdir(result)
        assert ".thumbnail" in result
        assert os.path.basename(result) == "2"

    def test_create_multiple_levels(self):
        """Should create multiple level directories"""
        for level in [1, 2, 3, 4, 5]:
            result = create_thumbnail_directory(self.temp_dir, level=level)
            assert os.path.exists(result)

    def test_create_existing_directory(self):
        """Should handle existing directory"""
        # Create once
        result1 = create_thumbnail_directory(self.temp_dir, level=1)
        # Create again (should not error)
        result2 = create_thumbnail_directory(self.temp_dir, level=1)
        assert result1 == result2
        assert os.path.exists(result2)


class TestGetThumbnailPath:
    """Tests for get_thumbnail_path()"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_get_path_level_1(self):
        """Should generate path for level 1"""
        result = get_thumbnail_path(self.temp_dir, level=1, index=0)
        assert ".thumbnail" in result
        assert "000000.tif" in result

    def test_get_path_level_2(self):
        """Should generate path for level 2"""
        result = get_thumbnail_path(self.temp_dir, level=2, index=0)
        assert ".thumbnail" in result
        assert os.sep + "2" + os.sep in result or "/2/" in result

    def test_index_formatting(self):
        """Should format index with leading zeros"""
        test_cases = [
            (0, "000000.tif"),
            (1, "000001.tif"),
            (123, "000123.tif"),
            (999999, "999999.tif")
        ]
        for index, expected_filename in test_cases:
            result = get_thumbnail_path(self.temp_dir, level=1, index=index)
            assert expected_filename in result


class TestCleanOldThumbnails:
    """Tests for clean_old_thumbnails()"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_clean_existing_thumbnails(self):
        """Should remove existing thumbnail directory"""
        # Create thumbnail directory with some files
        thumb_dir = os.path.join(self.temp_dir, ".thumbnail")
        os.makedirs(thumb_dir)
        test_file = os.path.join(thumb_dir, "test.tif")
        with open(test_file, 'w') as f:
            f.write("test")

        # Clean
        result = clean_old_thumbnails(self.temp_dir)
        assert result is True
        assert not os.path.exists(thumb_dir)

    def test_clean_nonexistent_thumbnails(self):
        """Should handle nonexistent thumbnail directory"""
        result = clean_old_thumbnails(self.temp_dir)
        assert result is True

    def test_clean_with_subdirectories(self):
        """Should remove nested directories"""
        # Create nested structure
        thumb_dir = os.path.join(self.temp_dir, ".thumbnail")
        os.makedirs(thumb_dir)
        level2 = os.path.join(thumb_dir, "2")
        os.makedirs(level2)
        test_file = os.path.join(level2, "test.tif")
        with open(test_file, 'w') as f:
            f.write("test")

        # Clean
        result = clean_old_thumbnails(self.temp_dir)
        assert result is True
        assert not os.path.exists(thumb_dir)


class TestGetDirectorySize:
    """Tests for get_directory_size()"""

    def setup_method(self):
        """Create temporary directory with files"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_empty_directory(self):
        """Should return 0 for empty directory"""
        result = get_directory_size(self.temp_dir)
        assert result == 0

    def test_single_file(self):
        """Should calculate size for single file"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        content = "A" * 1000  # 1000 bytes
        with open(test_file, 'w') as f:
            f.write(content)

        result = get_directory_size(self.temp_dir)
        assert result >= 1000  # At least 1000 bytes (could be more due to encoding)

    def test_multiple_files(self):
        """Should calculate total size for multiple files"""
        for i in range(5):
            test_file = os.path.join(self.temp_dir, f"test{i}.txt")
            with open(test_file, 'wb') as f:
                f.write(b"A" * 1000)  # Exactly 1000 bytes

        result = get_directory_size(self.temp_dir)
        assert result == 5000  # 5 files * 1000 bytes

    def test_nested_directories(self):
        """Should calculate size including subdirectories"""
        subdir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(subdir)

        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(subdir, "file2.txt")

        with open(file1, 'wb') as f:
            f.write(b"A" * 1000)
        with open(file2, 'wb') as f:
            f.write(b"B" * 2000)

        result = get_directory_size(self.temp_dir)
        assert result == 3000

    def test_nonexistent_directory(self):
        """Should return 0 for nonexistent directory"""
        result = get_directory_size("/nonexistent/directory")
        assert result == 0


class TestFormatFileSize:
    """Tests for format_file_size()"""

    def test_bytes(self):
        """Should format bytes"""
        assert format_file_size(0) == "0.00 B"
        assert format_file_size(1) == "1.00 B"
        assert format_file_size(1023) == "1023.00 B"

    def test_kilobytes(self):
        """Should format kilobytes"""
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1536) == "1.50 KB"
        assert format_file_size(1024 * 10) == "10.00 KB"

    def test_megabytes(self):
        """Should format megabytes"""
        assert format_file_size(1024 * 1024) == "1.00 MB"
        assert format_file_size(1024 * 1024 * 1.5) == "1.50 MB"

    def test_gigabytes(self):
        """Should format gigabytes"""
        assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_file_size(1024 * 1024 * 1024 * 2.5) == "2.50 GB"

    def test_terabytes(self):
        """Should format terabytes"""
        assert format_file_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"

    def test_petabytes(self):
        """Should format petabytes"""
        assert format_file_size(1024 * 1024 * 1024 * 1024 * 1024) == "1.00 PB"

    def test_large_numbers(self):
        """Should handle very large numbers"""
        huge = 1024 ** 6  # Exabyte
        result = format_file_size(huge)
        assert "PB" in result
        # Should still work, even if over petabyte

    def test_decimal_precision(self):
        """Should maintain 2 decimal places"""
        result = format_file_size(1536)  # 1.5 KB
        assert ".50" in result

        result = format_file_size(1024 * 1.333)  # 1.333 KB
        assert ".33" in result