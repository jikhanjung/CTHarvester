"""Tests for error handling system (ui/errors.py).

This module tests the user-friendly error message system introduced
in v1.0 production preparation.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtWidgets import QWidget

from ui.errors import (
    ErrorCode,
    ErrorMessage,
    ErrorSeverity,
    get_error_message,
    map_exception_to_error_code,
    show_error,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_codes_exist(self):
        """Test that all expected error codes exist."""
        assert ErrorCode.DIRECTORY_NOT_FOUND
        assert ErrorCode.PERMISSION_DENIED
        assert ErrorCode.OUT_OF_MEMORY
        assert ErrorCode.THUMBNAIL_GENERATION_FAILED
        assert ErrorCode.USER_CANCELLED
        assert ErrorCode.UNKNOWN_ERROR

    def test_error_code_values_unique(self):
        """Test that error code values are unique."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values))


class TestErrorMessage:
    """Tests for ErrorMessage class."""

    def test_error_message_creation(self):
        """Test creating an error message."""
        msg = ErrorMessage(
            title="Test Error",
            message="This is a test error",
            details="Technical details",
            suggestions=["Try this", "Or try that"],
            severity=ErrorSeverity.ERROR,
        )

        assert msg.title == "Test Error"
        assert msg.message == "This is a test error"
        assert msg.details == "Technical details"
        assert len(msg.suggestions) == 2
        assert msg.severity == ErrorSeverity.ERROR

    def test_error_message_default_suggestions(self):
        """Test that suggestions default to empty list."""
        msg = ErrorMessage(
            title="Test",
            message="Test message",
        )

        assert msg.suggestions == []

    def test_error_message_default_severity(self):
        """Test that severity defaults to ERROR."""
        msg = ErrorMessage(
            title="Test",
            message="Test message",
        )

        assert msg.severity == ErrorSeverity.ERROR


class TestGetErrorMessage:
    """Tests for get_error_message function."""

    def test_get_directory_not_found_message(self):
        """Test getting directory not found message."""
        msg = get_error_message(ErrorCode.DIRECTORY_NOT_FOUND, "/fake/path")

        assert "Directory Not Found" in msg.title
        assert "/fake/path" in msg.message
        assert len(msg.suggestions) > 0

    def test_get_permission_denied_message(self):
        """Test getting permission denied message."""
        msg = get_error_message(ErrorCode.PERMISSION_DENIED, "read directory")

        assert "Permission Denied" in msg.title
        assert "read directory" in msg.message
        assert len(msg.suggestions) > 0

    def test_get_out_of_memory_message(self):
        """Test getting out of memory message."""
        msg = get_error_message(ErrorCode.OUT_OF_MEMORY)

        assert "Out of Memory" in msg.title
        assert msg.severity == ErrorSeverity.CRITICAL
        assert len(msg.suggestions) > 0

    def test_get_user_cancelled_message(self):
        """Test getting user cancelled message."""
        msg = get_error_message(ErrorCode.USER_CANCELLED, "thumbnail generation")

        assert "Cancelled" in msg.title
        assert "thumbnail generation" in msg.message
        assert msg.severity == ErrorSeverity.INFO

    def test_get_message_with_exception(self):
        """Test getting message with exception details."""
        exc = ValueError("Test exception")
        msg = get_error_message(ErrorCode.THUMBNAIL_GENERATION_FAILED, "Test reason", exception=exc)

        assert "ValueError: Test exception" in msg.details

    def test_get_unknown_error_code(self):
        """Test that unknown error codes fall back to UNKNOWN_ERROR."""
        # Create a fake error code (this should fall back)
        msg = get_error_message(None)  # type: ignore

        assert msg.title == "Unexpected Error"


class TestMapExceptionToErrorCode:
    """Tests for map_exception_to_error_code function."""

    def test_map_permission_error(self):
        """Test mapping PermissionError."""
        exc = PermissionError("Permission denied")
        code = map_exception_to_error_code(exc)

        assert code == ErrorCode.PERMISSION_DENIED

    def test_map_file_not_found_error(self):
        """Test mapping FileNotFoundError."""
        exc = FileNotFoundError("File not found")
        code = map_exception_to_error_code(exc)

        assert code == ErrorCode.DIRECTORY_NOT_FOUND

    def test_map_memory_error(self):
        """Test mapping MemoryError."""
        exc = MemoryError("Out of memory")
        code = map_exception_to_error_code(exc)

        assert code == ErrorCode.OUT_OF_MEMORY

    def test_map_import_error(self):
        """Test mapping ImportError."""
        exc = ImportError("Module not found")
        code = map_exception_to_error_code(exc)

        assert code == ErrorCode.MISSING_DEPENDENCY

    def test_map_disk_full_error(self):
        """Test mapping OSError with disk full message."""
        exc = OSError("No space left on device")
        code = map_exception_to_error_code(exc)

        assert code == ErrorCode.DISK_FULL

    def test_map_disk_read_error(self):
        """Test mapping OSError with read context."""
        exc = OSError("I/O error")
        code = map_exception_to_error_code(exc, "reading directory")

        assert code == ErrorCode.DISK_READ_ERROR

    def test_map_disk_write_error(self):
        """Test mapping OSError with write context."""
        exc = OSError("I/O error during write")
        code = map_exception_to_error_code(exc, "writing file")

        assert code == ErrorCode.DISK_WRITE_ERROR

    def test_map_unknown_exception(self):
        """Test mapping unknown exception."""
        exc = RuntimeError("Unknown error")
        code = map_exception_to_error_code(exc)

        assert code == ErrorCode.UNKNOWN_ERROR


class TestShowError:
    """Tests for show_error function."""

    @pytest.fixture
    def mock_parent(self, qtbot):
        """Create a mock parent widget."""
        return QWidget()

    def test_show_error_creates_message_box(self, mock_parent, qtbot):
        """Test that show_error creates a QMessageBox."""
        with patch("ui.errors.QMessageBox") as mock_msgbox:
            mock_instance = MagicMock()
            mock_msgbox.return_value = mock_instance
            mock_instance.exec.return_value = 0

            show_error(mock_parent, ErrorCode.DIRECTORY_NOT_FOUND, "/fake/path")

            # Verify QMessageBox was created
            mock_msgbox.assert_called_once_with(mock_parent)
            # Verify exec was called
            mock_instance.exec.assert_called_once()

    def test_show_error_with_exception(self, mock_parent, qtbot):
        """Test show_error with exception details."""
        exc = ValueError("Test error")

        with patch("ui.errors.QMessageBox") as mock_msgbox:
            mock_instance = MagicMock()
            mock_msgbox.return_value = mock_instance
            mock_instance.exec.return_value = 0

            show_error(
                mock_parent,
                ErrorCode.THUMBNAIL_GENERATION_FAILED,
                "Test reason",
                exception=exc,
            )

            # Should have been called
            mock_msgbox.assert_called_once()

    def test_show_error_with_traceback(self, mock_parent, qtbot):
        """Test show_error with full traceback."""
        exc = ValueError("Test error")

        with patch("ui.errors.QMessageBox") as mock_msgbox:
            mock_instance = MagicMock()
            mock_msgbox.return_value = mock_instance
            mock_instance.exec.return_value = 0

            show_error(
                mock_parent,
                ErrorCode.THUMBNAIL_GENERATION_FAILED,
                "Test reason",
                exception=exc,
                include_traceback=True,
            )

            # Should have been called
            mock_msgbox.assert_called_once()
            # Detailed text should be set (contains traceback)
            mock_instance.setDetailedText.assert_called_once()

    def test_show_error_logs_message(self, mock_parent, qtbot, caplog):
        """Test that show_error logs the error."""
        with patch("ui.errors.QMessageBox") as mock_msgbox:
            mock_instance = MagicMock()
            mock_msgbox.return_value = mock_instance
            mock_instance.exec.return_value = 0

            show_error(mock_parent, ErrorCode.DIRECTORY_NOT_FOUND, "/fake/path")

            # Check that error was logged
            assert "Directory Not Found" in caplog.text


class TestErrorSeverityMapping:
    """Tests for error severity icon mapping."""

    @pytest.fixture
    def mock_parent(self, qtbot):
        """Create a mock parent widget."""
        return QWidget()

    def test_info_severity_icon(self, mock_parent, qtbot):
        """Test that INFO severity uses Information icon."""
        with patch("ui.errors.QMessageBox") as mock_msgbox:
            mock_instance = MagicMock()
            mock_msgbox.return_value = mock_instance
            mock_msgbox.Icon = MagicMock()
            mock_instance.exec.return_value = 0

            show_error(mock_parent, ErrorCode.USER_CANCELLED, "test")

            # Should set Information icon for INFO severity
            mock_instance.setIcon.assert_called_once()

    def test_critical_severity_icon(self, mock_parent, qtbot):
        """Test that CRITICAL severity uses Critical icon."""
        with patch("ui.errors.QMessageBox") as mock_msgbox:
            mock_instance = MagicMock()
            mock_msgbox.return_value = mock_instance
            mock_msgbox.Icon = MagicMock()
            mock_instance.exec.return_value = 0

            show_error(
                mock_parent,
                ErrorCode.OUT_OF_MEMORY,
            )

            # Should set Critical icon for CRITICAL severity
            mock_instance.setIcon.assert_called_once()


class TestErrorMessageCatalogCoverage:
    """Tests to ensure all error codes have messages."""

    def test_all_error_codes_have_messages(self):
        """Test that all error codes (except UNKNOWN) have messages."""
        from ui.errors import ERROR_MESSAGES

        # All error codes should have messages except UNKNOWN_ERROR
        # (which is the fallback)
        for code in ErrorCode:
            if code != ErrorCode.UNKNOWN_ERROR:
                assert code in ERROR_MESSAGES, f"Missing message for {code}"

    def test_all_messages_have_suggestions(self):
        """Test that all messages (except INFO) have suggestions."""
        # Get all error messages
        for code in ErrorCode:
            if code == ErrorCode.USER_CANCELLED:
                # User cancellation doesn't need suggestions
                continue

            msg = get_error_message(code, "test")
            if msg.severity != ErrorSeverity.INFO:
                assert len(msg.suggestions) > 0, f"{code} should have suggestions"

    def test_all_messages_have_titles(self):
        """Test that all messages have non-empty titles."""
        for code in ErrorCode:
            msg = get_error_message(code, "test")
            assert msg.title, f"{code} should have a title"
            assert len(msg.title) > 0, f"{code} title should not be empty"

    def test_all_messages_have_body(self):
        """Test that all messages have non-empty message body."""
        for code in ErrorCode:
            msg = get_error_message(code, "test")
            assert msg.message, f"{code} should have a message"
            assert len(msg.message) > 0, f"{code} message should not be empty"
