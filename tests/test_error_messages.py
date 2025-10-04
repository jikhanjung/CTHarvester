"""
Tests for utils/error_messages.py - User-friendly error message generation

Part of Phase 1 quality improvement plan (devlog 072)
"""

import errno
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtWidgets import QMessageBox

from utils.error_messages import (
    ErrorMessageBuilder,
    UserError,
    show_error_dialog,
    show_warning_dialog,
    tr,
)


class TestUserError:
    """Test suite for UserError dataclass"""

    def test_user_error_creation(self):
        """Test creating a UserError instance"""
        error = UserError(
            title="Test Title",
            message="Test Message",
            solutions=["Solution 1", "Solution 2"],
            technical_details="Technical info",
        )

        assert error.title == "Test Title"
        assert error.message == "Test Message"
        assert len(error.solutions) == 2
        assert error.technical_details == "Technical info"

    def test_user_error_without_technical_details(self):
        """Test creating a UserError without technical details"""
        error = UserError(title="Test", message="Message", solutions=["Fix it"])

        assert error.title == "Test"
        assert error.technical_details is None


class TestErrorMessageBuilder:
    """Test suite for ErrorMessageBuilder class"""

    def test_error_templates_exist(self):
        """Test that error templates are defined"""
        templates = ErrorMessageBuilder.ERROR_TEMPLATES

        assert "file_not_found" in templates
        assert "permission_denied" in templates
        assert "invalid_image" in templates
        assert "out_of_memory" in templates
        assert "disk_space" in templates
        assert "opengl_error" in templates
        assert "rust_module_missing" in templates
        assert "directory_not_found" in templates
        assert "no_images_found" in templates

    def test_build_file_not_found_error(self):
        """Test building file not found error"""
        exception = FileNotFoundError("test.png")
        error = ErrorMessageBuilder.build_error("file_not_found", exception, filename="test.png")

        assert error.title == "Cannot find file"
        assert "test.png" in error.message
        assert len(error.solutions) > 0
        assert "FileNotFoundError" in error.technical_details

    def test_build_permission_denied_error(self):
        """Test building permission denied error"""
        exception = PermissionError("Access denied")
        error = ErrorMessageBuilder.build_error(
            "permission_denied", exception, filename="/root/test.png"
        )

        assert error.title == "Permission denied"
        assert "/root/test.png" in error.message
        assert any("permission" in sol.lower() for sol in error.solutions)

    def test_build_invalid_image_error(self):
        """Test building invalid image error"""
        exception = ValueError("Invalid image format")
        error = ErrorMessageBuilder.build_error("invalid_image", exception, filename="bad.png")

        assert error.title == "Invalid image file"
        assert "bad.png" in error.message
        assert any("image" in sol.lower() for sol in error.solutions)

    def test_build_out_of_memory_error(self):
        """Test building out of memory error"""
        exception = MemoryError()
        error = ErrorMessageBuilder.build_error("out_of_memory", exception)

        assert error.title == "Out of memory"
        assert "memory" in error.message.lower()
        assert len(error.solutions) >= 3

    def test_build_disk_space_error(self):
        """Test building disk space error"""
        exception = OSError(errno.ENOSPC, "No space left")
        error = ErrorMessageBuilder.build_error("disk_space", exception)

        assert error.title == "Not enough disk space"
        assert "disk" in error.message.lower()

    def test_build_opengl_error(self):
        """Test building OpenGL error"""
        exception = RuntimeError("OpenGL initialization failed")
        error = ErrorMessageBuilder.build_error("opengl_error", exception)

        assert error.title == "3D rendering error"
        assert "3D" in error.message or "OpenGL" in error.message

    def test_build_rust_module_missing_error(self):
        """Test building Rust module missing error"""
        exception = ModuleNotFoundError("ctharvester_rs not found")
        error = ErrorMessageBuilder.build_error("rust_module_missing", exception)

        assert "Rust" in error.title or "Performance" in error.title
        assert any("fallback" in sol.lower() or "python" in sol.lower() for sol in error.solutions)

    def test_build_unknown_error_type(self):
        """Test building error with unknown error type"""
        exception = ValueError("Random error")
        error = ErrorMessageBuilder.build_error("unknown_type", exception)

        assert error.title == "An error occurred"
        assert str(exception) in error.message or str(exception) in error.technical_details

    def test_build_error_with_template_variables(self):
        """Test that template variables are properly substituted"""
        exception = FileNotFoundError()
        filename = "myfile.txt"
        error = ErrorMessageBuilder.build_error("file_not_found", exception, filename=filename)

        assert filename in error.message

    def test_from_exception_file_not_found(self):
        """Test automatic error type detection for FileNotFoundError"""
        exception = FileNotFoundError("/path/to/file.png")
        error = ErrorMessageBuilder.from_exception(exception, filename="/path/to/file.png")

        assert error.title == "Cannot find file"
        assert "/path/to/file.png" in error.message

    def test_from_exception_permission_error(self):
        """Test automatic error type detection for PermissionError"""
        exception = PermissionError("Access denied")
        error = ErrorMessageBuilder.from_exception(exception)

        assert error.title == "Permission denied"

    def test_from_exception_memory_error(self):
        """Test automatic error type detection for MemoryError"""
        exception = MemoryError()
        error = ErrorMessageBuilder.from_exception(exception)

        assert error.title == "Out of memory"

    def test_from_exception_oserror_enospc(self):
        """Test automatic error type detection for OSError with ENOSPC"""
        exception = OSError(errno.ENOSPC, "No space left on device")
        error = ErrorMessageBuilder.from_exception(exception)

        assert error.title == "Not enough disk space"

    def test_from_exception_oserror_eacces(self):
        """Test automatic error type detection for OSError with EACCES"""
        exception = OSError(errno.EACCES, "Permission denied")
        error = ErrorMessageBuilder.from_exception(exception)

        assert error.title == "Permission denied"

    def test_from_exception_pil_error(self):
        """Test automatic error type detection for generic PIL/Image errors"""
        # Generic exception that's not specifically caught
        exception = ValueError("PIL error message")

        error = ErrorMessageBuilder.from_exception(exception)

        # Should fall through to generic error handling
        assert "error occurred" in error.title.lower()
        assert "ValueError" in error.technical_details

    def test_from_exception_module_not_found(self):
        """Test automatic error type detection for ModuleNotFoundError with ctharvester_rs"""
        exception = ModuleNotFoundError("No module named 'ctharvester_rs'")
        error = ErrorMessageBuilder.from_exception(exception)

        assert "Rust" in error.title or "module" in error.title.lower()

    def test_from_exception_generic_exception(self):
        """Test automatic error type detection for generic exceptions"""
        exception = RuntimeError("Something went wrong")
        error = ErrorMessageBuilder.from_exception(exception)

        assert "error occurred" in error.title.lower()
        assert "RuntimeError" in error.technical_details


@pytest.mark.parametrize(
    "exception_class,expected_title_keyword",
    [
        (FileNotFoundError, "find"),
        (PermissionError, "Permission"),
        (MemoryError, "memory"),
    ],
)
def test_from_exception_parametrized(exception_class, expected_title_keyword):
    """Parametrized test for from_exception with different exception types"""
    exception = exception_class("Test error")
    error = ErrorMessageBuilder.from_exception(exception)

    assert expected_title_keyword.lower() in error.title.lower()


class TestDialogFunctions:
    """Test suite for dialog display functions"""

    @patch("PyQt5.QtWidgets.QMessageBox")
    def test_show_error_dialog(self, mock_msgbox_class):
        """Test show_error_dialog creates and shows error dialog"""
        mock_msgbox = MagicMock()
        mock_msgbox_class.return_value = mock_msgbox
        mock_msgbox_class.Critical = QMessageBox.Critical

        parent = MagicMock()
        user_error = UserError(
            title="Test Error",
            message="Error message",
            solutions=["Solution 1", "Solution 2"],
            technical_details="Technical details",
        )

        show_error_dialog(parent, user_error)

        # Verify QMessageBox was created with correct parent
        mock_msgbox_class.assert_called_once_with(parent)

        # Verify error icon was set
        mock_msgbox.setIcon.assert_called_once_with(QMessageBox.Critical)

        # Verify title was set
        mock_msgbox.setWindowTitle.assert_called_once_with("Test Error")

        # Verify text was set (should include message and solutions)
        assert mock_msgbox.setText.called
        text_arg = mock_msgbox.setText.call_args[0][0]
        assert "Error message" in text_arg
        assert "Solution 1" in text_arg
        assert "Solution 2" in text_arg

        # Verify detailed text was set
        mock_msgbox.setDetailedText.assert_called_once_with("Technical details")

        # Verify dialog was shown
        mock_msgbox.exec_.assert_called_once()

    @patch("PyQt5.QtWidgets.QMessageBox")
    def test_show_warning_dialog(self, mock_msgbox_class):
        """Test show_warning_dialog creates and shows warning dialog"""
        mock_msgbox = MagicMock()
        mock_msgbox_class.return_value = mock_msgbox
        mock_msgbox_class.Warning = QMessageBox.Warning

        parent = MagicMock()
        user_error = UserError(title="Test Warning", message="Warning message", solutions=["Fix 1"])

        show_warning_dialog(parent, user_error)

        # Verify warning icon was set
        mock_msgbox.setIcon.assert_called_once_with(QMessageBox.Warning)

        # Verify title was set
        mock_msgbox.setWindowTitle.assert_called_once_with("Test Warning")

        # Verify dialog was shown
        mock_msgbox.exec_.assert_called_once()

    @patch("PyQt5.QtWidgets.QMessageBox")
    def test_show_error_dialog_without_technical_details(self, mock_msgbox_class):
        """Test show_error_dialog without technical details"""
        mock_msgbox = MagicMock()
        mock_msgbox_class.return_value = mock_msgbox
        mock_msgbox_class.Critical = QMessageBox.Critical

        parent = MagicMock()
        user_error = UserError(
            title="Test Error", message="Error message", solutions=["Solution 1"]
        )

        show_error_dialog(parent, user_error)

        # Detailed text should NOT be called if technical_details is None
        # (see show_error_dialog implementation - only calls if technical_details exists)
        mock_msgbox.setDetailedText.assert_not_called()


class TestTranslationFunction:
    """Test suite for tr() translation function"""

    def test_tr_function_returns_string(self):
        """Test that tr() returns a string"""
        result = tr("Test text")
        assert isinstance(result, str)

    def test_tr_function_with_text(self):
        """Test tr() with actual text"""
        # Note: Without actual translation files, this just returns the source text
        text = "File not found"
        result = tr(text)
        assert result is not None
        assert isinstance(result, str)
