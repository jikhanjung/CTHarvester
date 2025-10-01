"""
Unit tests for security/file_validator.py

Tests file security validation, directory traversal prevention, and safe file operations.
"""

import os
import shutil
import sys
import tempfile

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security.file_validator import FileSecurityError, SecureFileValidator, safe_open_image


@pytest.mark.integration
class TestValidateFilename:
    """Tests for SecureFileValidator.validate_filename()"""

    def test_valid_simple_filename(self):
        """Should accept simple filenames"""
        result = SecureFileValidator.validate_filename("test.txt")
        assert result == "test.txt"

    def test_valid_filename_with_numbers(self):
        """Should accept filenames with numbers"""
        result = SecureFileValidator.validate_filename("file_001.tif")
        assert result == "file_001.tif"

    def test_valid_filename_with_underscores(self):
        """Should accept filenames with underscores"""
        result = SecureFileValidator.validate_filename("my_file_name.jpg")
        assert result == "my_file_name.jpg"

    def test_valid_filename_with_hyphens(self):
        """Should accept filenames with hyphens"""
        result = SecureFileValidator.validate_filename("my-file-name.png")
        assert result == "my-file-name.png"

    def test_reject_directory_traversal_dotdot(self):
        """Should reject .. pattern"""
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_filename("../etc/passwd")

    def test_reject_directory_traversal_in_middle(self):
        """Should reject .. in middle of path"""
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_filename("dir/../file.txt")

    def test_reject_absolute_path_unix(self):
        """Should reject absolute paths (Unix)"""
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_filename("/etc/passwd")

    def test_reject_absolute_path_windows(self):
        """Should reject absolute paths (Windows)"""
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_filename("\\Windows\\System32\\cmd.exe")

    def test_reject_windows_forbidden_chars(self):
        """Should reject Windows forbidden characters"""
        forbidden_chars = ["<", ">", ":", '"', "|", "?", "*"]
        for char in forbidden_chars:
            with pytest.raises(FileSecurityError):
                SecureFileValidator.validate_filename(f"file{char}name.txt")

    def test_reject_null_byte(self):
        """Should reject null bytes"""
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_filename("file\x00name.txt")

    def test_reject_empty_filename(self):
        """Should reject empty filename"""
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_filename("")

    def test_extract_basename_from_path(self):
        """Should extract basename if path is provided"""
        # Note: This will succeed but only return the basename
        result = SecureFileValidator.validate_filename("subdir/file.txt")
        assert result == "file.txt"


@pytest.mark.integration
class TestValidateExtension:
    """Tests for SecureFileValidator.validate_extension()"""

    def test_valid_extensions(self):
        """Should accept allowed extensions"""
        valid_files = [
            "image.bmp",
            "image.jpg",
            "image.jpeg",
            "image.png",
            "image.tif",
            "image.tiff",
        ]
        for filename in valid_files:
            assert SecureFileValidator.validate_extension(filename) is True

    def test_case_insensitive(self):
        """Should be case-insensitive"""
        assert SecureFileValidator.validate_extension("image.TIF") is True
        assert SecureFileValidator.validate_extension("image.JPG") is True
        assert SecureFileValidator.validate_extension("image.PnG") is True

    def test_invalid_extensions(self):
        """Should reject invalid extensions"""
        invalid_files = ["file.txt", "file.pdf", "file.exe", "file.sh", "file.py"]
        for filename in invalid_files:
            assert SecureFileValidator.validate_extension(filename) is False

    def test_no_extension(self):
        """Should reject files without extension"""
        assert SecureFileValidator.validate_extension("filename") is False


@pytest.mark.integration
class TestValidatePath:
    """Tests for SecureFileValidator.validate_path()"""

    def setup_method(self):
        """Create temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("test content")

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_valid_path_inside_basedir(self):
        """Should accept path inside base directory"""
        result = SecureFileValidator.validate_path(self.test_file, self.temp_dir)
        assert os.path.isabs(result)
        assert result.startswith(os.path.abspath(self.temp_dir))

    def test_reject_path_outside_basedir(self):
        """Should reject path outside base directory"""
        outside_dir = tempfile.gettempdir()
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_path("/etc/passwd", outside_dir)

    def test_reject_directory_traversal_attempt(self):
        """Should reject directory traversal attempt"""
        malicious_path = os.path.join(self.temp_dir, "..", "..", "etc", "passwd")
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_path(malicious_path, self.temp_dir)

    def test_normalize_paths(self):
        """Should normalize paths correctly"""
        # Create a subdirectory
        subdir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)
        test_file = os.path.join(subdir, "file.txt")
        with open(test_file, "w") as f:
            f.write("test")

        # Path with redundant parts
        redundant_path = os.path.join(self.temp_dir, ".", "subdir", "file.txt")
        result = SecureFileValidator.validate_path(redundant_path, self.temp_dir)

        assert os.path.isabs(result)
        assert "subdir" in result
        assert "file.txt" in result

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_different_drive_windows(self):
        """Should reject paths on different drives (Windows)"""
        # On Windows, C:\ and D:\ would cause ValueError in commonpath
        with pytest.raises(FileSecurityError):
            SecureFileValidator.validate_path("D:\\file.tif", "C:\\base")


@pytest.mark.integration
class TestSafeJoin:
    """Tests for SecureFileValidator.safe_join()"""

    def setup_method(self):
        """Create temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_join_safe_paths(self):
        """Should safely join valid path components"""
        result = SecureFileValidator.safe_join(self.temp_dir, "subdir", "file.txt")
        assert result.startswith(os.path.abspath(self.temp_dir))
        assert "subdir" in result
        assert "file.txt" in result

    def test_reject_traversal_in_component(self):
        """Should reject directory traversal in components"""
        with pytest.raises(FileSecurityError):
            SecureFileValidator.safe_join(self.temp_dir, "..", "etc", "passwd")

    def test_single_component(self):
        """Should handle single path component"""
        result = SecureFileValidator.safe_join(self.temp_dir, "file.txt")
        assert result.startswith(os.path.abspath(self.temp_dir))
        assert "file.txt" in result


@pytest.mark.integration
class TestSecureListdir:
    """Tests for SecureFileValidator.secure_listdir()"""

    def setup_method(self):
        """Create temporary directory with test files"""
        self.temp_dir = tempfile.mkdtemp()

        # Create various test files
        self.image_files = ["test1.tif", "test2.jpg", "test3.png"]
        self.other_files = ["readme.txt", "data.csv"]

        for filename in self.image_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, "w") as f:
                f.write("test")

        for filename in self.other_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, "w") as f:
                f.write("test")

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_list_image_files_only(self):
        """Should list only image files"""
        result = SecureFileValidator.secure_listdir(self.temp_dir)
        assert len(result) == len(self.image_files)
        for filename in self.image_files:
            assert filename in result

    def test_list_custom_extensions(self):
        """Should list files with custom extensions"""
        result = SecureFileValidator.secure_listdir(self.temp_dir, extensions={".txt", ".csv"})
        assert len(result) == len(self.other_files)
        for filename in self.other_files:
            assert filename in result

    def test_reject_non_directory(self):
        """Should reject non-directory paths"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        with pytest.raises(FileSecurityError):
            SecureFileValidator.secure_listdir(test_file)

    def test_sorted_output(self):
        """Should return sorted file list"""
        result = SecureFileValidator.secure_listdir(self.temp_dir)
        assert result == sorted(result)

    def test_empty_directory(self):
        """Should handle empty directory"""
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir)

        result = SecureFileValidator.secure_listdir(empty_dir)
        assert result == []

    def test_listdir_with_invalid_file(self):
        """Should skip invalid files and continue"""
        # Create file with dangerous name (will be caught by validate_filename)
        # secure_listdir should catch FileSecurityError and continue
        dangerous_file = os.path.join(self.temp_dir, "../dangerous.tif")
        try:
            with open(dangerous_file, "w") as f:
                f.write("test")
        except:
            pass  # May fail to create, that's ok

        # Should still work and return valid files
        result = SecureFileValidator.secure_listdir(self.temp_dir)
        assert isinstance(result, list)

    def test_listdir_oserror(self):
        """Should raise FileSecurityError on OSError"""
        # Try to list a directory that doesn't exist or isn't accessible
        with pytest.raises(FileSecurityError):
            SecureFileValidator.secure_listdir("/nonexistent/directory/path")


@pytest.mark.integration
class TestValidateNoSymlink:
    """Tests for SecureFileValidator.validate_no_symlink()"""

    def setup_method(self):
        """Create temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.real_file = os.path.join(self.temp_dir, "real_file.txt")
        with open(self.real_file, "w") as f:
            f.write("test")

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_accept_regular_file(self):
        """Should accept regular files"""
        result = SecureFileValidator.validate_no_symlink(self.real_file)
        assert result == self.real_file

    @pytest.mark.skipif(sys.platform == "win32", reason="Symlink test may require admin on Windows")
    def test_reject_symlink(self):
        """Should reject symbolic links"""
        symlink = os.path.join(self.temp_dir, "symlink.txt")
        try:
            os.symlink(self.real_file, symlink)
            with pytest.raises(FileSecurityError):
                SecureFileValidator.validate_no_symlink(symlink)
        except OSError:
            pytest.skip("Cannot create symlink (permission denied)")


@pytest.mark.integration
class TestSafeOpenImage:
    """Tests for safe_open_image() function"""

    def setup_method(self):
        """Create temporary directory and test image"""
        self.temp_dir = tempfile.mkdtemp()

        # Create a minimal test image using PIL
        try:
            import numpy as np
            from PIL import Image

            # Create a small test image
            img_array = np.ones((10, 10), dtype=np.uint8) * 128
            img = Image.fromarray(img_array)
            self.test_image = os.path.join(self.temp_dir, "test.tif")
            img.save(self.test_image)
        except ImportError:
            pytest.skip("PIL not available")

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_open_valid_image(self):
        """Should open valid image file"""
        from PIL import Image

        img = safe_open_image(self.test_image, self.temp_dir)
        assert isinstance(img, Image.Image)
        img.close()

    def test_reject_path_outside_basedir(self):
        """Should reject image outside base directory"""
        with pytest.raises(FileSecurityError):
            safe_open_image("/tmp/malicious.jpg", self.temp_dir)

    def test_reject_invalid_extension(self):
        """Should reject invalid file extension"""
        # Create a file with invalid extension
        invalid_file = os.path.join(self.temp_dir, "test.txt")
        with open(invalid_file, "w") as f:
            f.write("not an image")

        with pytest.raises(FileSecurityError):
            safe_open_image(invalid_file, self.temp_dir)
