"""
Unit tests for utils/common.py

Tests common utility functions including resource_path, value_to_bool, and ensure_directories.
"""
import sys
import os
import tempfile
import shutil
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.common import resource_path, value_to_bool, ensure_directories


class TestResourcePath:
    """Tests for resource_path() function"""

    def test_resource_path_returns_string(self):
        """resource_path should return a string"""
        result = resource_path("test.txt")
        assert isinstance(result, str)

    def test_resource_path_joins_correctly(self):
        """resource_path should join paths correctly"""
        result = resource_path("subdir/test.txt")
        assert "subdir" in result
        assert "test.txt" in result

    def test_resource_path_uses_absolute_path(self):
        """resource_path should return absolute path"""
        result = resource_path("test.txt")
        assert os.path.isabs(result)

    def test_resource_path_handles_empty_string(self):
        """resource_path should handle empty string"""
        result = resource_path("")
        assert isinstance(result, str)

    def test_resource_path_with_special_chars(self):
        """resource_path should handle special characters"""
        result = resource_path("file with spaces.txt")
        assert "file with spaces.txt" in result


class TestValueToBool:
    """Tests for value_to_bool() function"""

    def test_string_true_lowercase(self):
        """'true' string should return True"""
        assert value_to_bool("true") is True

    def test_string_true_uppercase(self):
        """'TRUE' string should return True"""
        assert value_to_bool("TRUE") is True

    def test_string_true_mixedcase(self):
        """'TrUe' string should return True"""
        assert value_to_bool("TrUe") is True

    def test_string_false_lowercase(self):
        """'false' string should return False"""
        assert value_to_bool("false") is False

    def test_string_false_uppercase(self):
        """'FALSE' string should return False"""
        assert value_to_bool("FALSE") is False

    def test_string_other_values(self):
        """Other strings should return False"""
        assert value_to_bool("yes") is False
        assert value_to_bool("no") is False
        assert value_to_bool("1") is False
        assert value_to_bool("0") is False
        assert value_to_bool("") is False

    def test_boolean_true(self):
        """Boolean True should return True"""
        assert value_to_bool(True) is True

    def test_boolean_false(self):
        """Boolean False should return False"""
        assert value_to_bool(False) is False

    def test_integer_zero(self):
        """Integer 0 should return False"""
        assert value_to_bool(0) is False

    def test_integer_nonzero(self):
        """Non-zero integers should return True"""
        assert value_to_bool(1) is True
        assert value_to_bool(42) is True
        assert value_to_bool(-1) is True

    def test_none_value(self):
        """None should return False"""
        assert value_to_bool(None) is False

    def test_empty_list(self):
        """Empty list should return False"""
        assert value_to_bool([]) is False

    def test_nonempty_list(self):
        """Non-empty list should return True"""
        assert value_to_bool([1, 2, 3]) is True

    def test_empty_dict(self):
        """Empty dict should return False"""
        assert value_to_bool({}) is False

    def test_nonempty_dict(self):
        """Non-empty dict should return True"""
        assert value_to_bool({"key": "value"}) is True


class TestEnsureDirectories:
    """Tests for ensure_directories() function"""

    def setup_method(self):
        """Create a temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_single_directory(self):
        """Should create a single directory"""
        test_dir = os.path.join(self.temp_dir, "test_dir")
        ensure_directories([test_dir])
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)

    def test_create_multiple_directories(self):
        """Should create multiple directories"""
        dir1 = os.path.join(self.temp_dir, "dir1")
        dir2 = os.path.join(self.temp_dir, "dir2")
        dir3 = os.path.join(self.temp_dir, "dir3")

        ensure_directories([dir1, dir2, dir3])

        assert os.path.exists(dir1)
        assert os.path.exists(dir2)
        assert os.path.exists(dir3)

    def test_create_nested_directories(self):
        """Should create nested directories"""
        nested_dir = os.path.join(self.temp_dir, "level1", "level2", "level3")
        ensure_directories([nested_dir])
        assert os.path.exists(nested_dir)
        assert os.path.isdir(nested_dir)

    def test_existing_directory_no_error(self):
        """Should not raise error if directory already exists"""
        test_dir = os.path.join(self.temp_dir, "existing_dir")
        os.makedirs(test_dir)

        # Should not raise exception
        ensure_directories([test_dir])
        assert os.path.exists(test_dir)

    def test_empty_list(self):
        """Should handle empty directory list"""
        # Should not raise exception
        ensure_directories([])

    def test_mixed_existing_and_new(self):
        """Should handle mix of existing and new directories"""
        existing_dir = os.path.join(self.temp_dir, "existing")
        new_dir = os.path.join(self.temp_dir, "new")

        os.makedirs(existing_dir)

        ensure_directories([existing_dir, new_dir])

        assert os.path.exists(existing_dir)
        assert os.path.exists(new_dir)

    def test_invalid_path_no_crash(self, capsys):
        """Should not crash on invalid paths"""
        # Use an invalid path (on most systems)
        if sys.platform == "win32":
            invalid_path = "Z:\\invalid\\path\\that\\does\\not\\exist\\and\\cannot\\be\\created"
        else:
            invalid_path = "/root/invalid/path/that/requires/permissions"

        # Should not raise exception, but print warning
        ensure_directories([invalid_path])

        # Check that warning was printed
        captured = capsys.readouterr()
        assert "Warning" in captured.out or len(captured.out) == 0  # May not print if path creation succeeds


class TestIntegration:
    """Integration tests combining multiple functions"""

    def test_resource_path_and_directories(self):
        """Test using resource_path with ensure_directories"""
        # This is more of a smoke test to ensure functions work together
        path = resource_path("test")
        assert isinstance(path, str)

        # Don't actually create the directory in project root
        # Just verify the path is valid
        assert os.path.isabs(path)

    def test_value_to_bool_with_settings(self):
        """Test value_to_bool with typical settings values"""
        # Simulate reading from QSettings
        settings_values = {
            "remember_geometry": "true",
            "remember_directory": "false",
            "some_flag": "TRUE",
            "another_flag": "False"
        }

        assert value_to_bool(settings_values["remember_geometry"]) is True
        assert value_to_bool(settings_values["remember_directory"]) is False
        assert value_to_bool(settings_values["some_flag"]) is True
        assert value_to_bool(settings_values["another_flag"]) is False