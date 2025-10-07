"""User-friendly error messages and error handling utilities.

This module provides a centralized error message catalog and user-friendly
error dialogs for CTHarvester. All error messages are internationalized
and provide actionable guidance to users.

Phase: v1.0 Production Preparation
Created: 2025-10-07
"""

import logging
import traceback
from enum import Enum
from typing import Optional

from PyQt5.QtWidgets import QMessageBox, QTextEdit, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for user-facing errors."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCode(Enum):
    """Standardized error codes for CTHarvester."""

    # File System Errors (1xx)
    DIRECTORY_NOT_FOUND = 101
    DIRECTORY_NOT_READABLE = 102
    DIRECTORY_NOT_WRITABLE = 103
    NO_IMAGES_FOUND = 104
    INVALID_IMAGE_FORMAT = 105
    CORRUPTED_IMAGE = 106

    # Permission Errors (2xx)
    PERMISSION_DENIED = 201
    DISK_FULL = 202
    DISK_READ_ERROR = 203
    DISK_WRITE_ERROR = 204

    # Memory Errors (3xx)
    OUT_OF_MEMORY = 301
    IMAGE_TOO_LARGE = 302

    # Processing Errors (4xx)
    THUMBNAIL_GENERATION_FAILED = 401
    RUST_MODULE_ERROR = 402
    PYTHON_FALLBACK_FAILED = 403
    IMAGE_PROCESSING_ERROR = 404
    EXPORT_FAILED = 405

    # User Cancellation (5xx)
    USER_CANCELLED = 501

    # Configuration Errors (6xx)
    INVALID_SETTINGS = 601
    MISSING_DEPENDENCY = 602

    # Unknown Errors (9xx)
    UNKNOWN_ERROR = 999


class ErrorMessage:
    """Container for user-friendly error messages."""

    def __init__(
        self,
        title: str,
        message: str,
        details: str = "",
        suggestions: Optional[list[str]] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
    ):
        """Initialize error message.

        Args:
            title: Short error title for dialog
            message: User-friendly error description
            details: Technical details (exception message, stack trace)
            suggestions: List of actionable suggestions for user
            severity: Error severity level
        """
        self.title = title
        self.message = message
        self.details = details
        self.suggestions = suggestions or []
        self.severity = severity


# Error message catalog
ERROR_MESSAGES = {
    # File System Errors
    ErrorCode.DIRECTORY_NOT_FOUND: lambda path: ErrorMessage(
        title="Directory Not Found",
        message=f"The selected directory does not exist:\n{path}",
        suggestions=[
            "Check if the directory path is correct",
            "Verify the directory hasn't been moved or deleted",
            "Choose a different directory",
        ],
    ),
    ErrorCode.DIRECTORY_NOT_READABLE: lambda path: ErrorMessage(
        title="Cannot Read Directory",
        message=f"Unable to read from the selected directory:\n{path}",
        suggestions=[
            "Check if you have read permissions for this directory",
            "Verify the directory is not locked by another program",
            "Try running CTHarvester with administrator privileges",
        ],
    ),
    ErrorCode.DIRECTORY_NOT_WRITABLE: lambda path: ErrorMessage(
        title="Cannot Write to Directory",
        message=f"Unable to write to the selected directory:\n{path}",
        suggestions=[
            "Check if you have write permissions for this directory",
            "Verify the directory is not on a read-only drive",
            "Choose a different output location",
        ],
    ),
    ErrorCode.NO_IMAGES_FOUND: lambda path: ErrorMessage(
        title="No Images Found",
        message=f"No valid CT images found in the selected directory:\n{path}",
        suggestions=[
            "Verify the directory contains BMP, JPG, PNG, TIF, or TIFF files",
            "Check if the images follow the expected naming pattern",
            "Ensure the files are not corrupted",
        ],
        severity=ErrorSeverity.WARNING,
    ),
    ErrorCode.INVALID_IMAGE_FORMAT: lambda filename: ErrorMessage(
        title="Invalid Image Format",
        message=f"The file format is not supported:\n{filename}",
        suggestions=[
            "CTHarvester supports: BMP, JPG, PNG, TIF, TIFF",
            "Convert your images to a supported format",
            "Check if the file extension matches the actual format",
        ],
    ),
    ErrorCode.CORRUPTED_IMAGE: lambda filename: ErrorMessage(
        title="Corrupted Image File",
        message=f"Unable to read image file (file may be corrupted):\n{filename}",
        suggestions=[
            "Check if the file opens in an image viewer",
            "Try re-exporting the image from the CT scanner",
            "Remove corrupted files from the directory",
        ],
    ),
    # Permission Errors
    ErrorCode.PERMISSION_DENIED: lambda operation: ErrorMessage(
        title="Permission Denied",
        message=f"Operation not allowed: {operation}",
        suggestions=[
            "Run CTHarvester with administrator privileges",
            "Check file/folder permissions",
            "Ensure files are not locked by another program",
        ],
    ),
    ErrorCode.DISK_FULL: lambda path: ErrorMessage(
        title="Disk Full",
        message=f"Not enough disk space to complete the operation.\n\nLocation: {path}",
        suggestions=[
            "Free up disk space by deleting unnecessary files",
            "Choose a different output location with more space",
            "Reduce the number of resolution levels to generate",
        ],
        severity=ErrorSeverity.CRITICAL,
    ),
    ErrorCode.DISK_READ_ERROR: lambda path: ErrorMessage(
        title="Disk Read Error",
        message=f"Unable to read from disk:\n{path}",
        suggestions=[
            "Check if the drive is connected properly",
            "Verify the disk is not failing (run disk check)",
            "Try copying files to a different location",
        ],
    ),
    ErrorCode.DISK_WRITE_ERROR: lambda path: ErrorMessage(
        title="Disk Write Error",
        message=f"Unable to write to disk:\n{path}",
        suggestions=[
            "Check available disk space",
            "Verify write permissions",
            "Ensure the disk is not write-protected",
        ],
    ),
    # Memory Errors
    ErrorCode.OUT_OF_MEMORY: lambda *args: ErrorMessage(
        title="Out of Memory",
        message="Not enough memory to complete the operation.",
        suggestions=[
            "Close other applications to free up memory",
            "Process fewer images at once",
            "Reduce image resolution or bit depth",
            "Add more RAM to your system",
        ],
        severity=ErrorSeverity.CRITICAL,
    ),
    ErrorCode.IMAGE_TOO_LARGE: lambda size: ErrorMessage(
        title="Image Too Large",
        message=f"Image dimensions exceed recommended limits: {size}",
        suggestions=[
            "Consider downsampling images before processing",
            "Process images in smaller batches",
            "Use a machine with more RAM",
        ],
    ),
    # Processing Errors
    ErrorCode.THUMBNAIL_GENERATION_FAILED: lambda reason: ErrorMessage(
        title="Thumbnail Generation Failed",
        message=f"Unable to generate thumbnails:\n{reason}",
        suggestions=[
            "Check if all images are valid and readable",
            "Verify you have write permissions to the directory",
            "Ensure sufficient disk space is available",
            "Try closing and reopening the directory",
        ],
    ),
    ErrorCode.RUST_MODULE_ERROR: lambda error: ErrorMessage(
        title="High-Performance Module Error",
        message="The high-performance thumbnail module encountered an error.",
        suggestions=[
            "CTHarvester will automatically use the Python fallback",
            "The process may take longer but will still complete",
            "If errors persist, reinstall CTHarvester",
        ],
        severity=ErrorSeverity.WARNING,
    ),
    ErrorCode.PYTHON_FALLBACK_FAILED: lambda error: ErrorMessage(
        title="Thumbnail Generation Failed",
        message="Both high-performance and fallback methods failed.",
        suggestions=[
            "Verify all images are valid CT scan files",
            "Check system resources (memory, disk space)",
            "Try with a smaller subset of images",
            "Contact support if the problem persists",
        ],
        severity=ErrorSeverity.CRITICAL,
    ),
    ErrorCode.IMAGE_PROCESSING_ERROR: lambda filename: ErrorMessage(
        title="Image Processing Error",
        message=f"Unable to process image:\n{filename}",
        suggestions=[
            "Check if the image file is corrupted",
            "Verify the image format is supported",
            "Ensure the image has valid dimensions and bit depth",
        ],
    ),
    ErrorCode.EXPORT_FAILED: lambda format_type: ErrorMessage(
        title="Export Failed",
        message=f"Unable to export {format_type} file.",
        suggestions=[
            "Check available disk space",
            "Verify write permissions to the output directory",
            "Ensure the file is not open in another program",
        ],
    ),
    # User Cancellation
    ErrorCode.USER_CANCELLED: lambda operation: ErrorMessage(
        title="Operation Cancelled",
        message=f"{operation} was cancelled by user.",
        suggestions=[],
        severity=ErrorSeverity.INFO,
    ),
    # Configuration Errors
    ErrorCode.INVALID_SETTINGS: lambda setting: ErrorMessage(
        title="Invalid Settings",
        message=f"Invalid configuration setting: {setting}",
        suggestions=[
            "Reset settings to default values",
            "Check the settings file for corruption",
            "Reinstall CTHarvester if problems persist",
        ],
    ),
    ErrorCode.MISSING_DEPENDENCY: lambda dependency: ErrorMessage(
        title="Missing Dependency",
        message=f"Required component not found: {dependency}",
        suggestions=[
            "Reinstall CTHarvester to restore missing files",
            "Install the required dependency manually",
            "Contact support for installation assistance",
        ],
    ),
    # Unknown Errors
    ErrorCode.UNKNOWN_ERROR: lambda *args: ErrorMessage(
        title="Unexpected Error",
        message="An unexpected error occurred.",
        suggestions=[
            "Try the operation again",
            "Restart CTHarvester",
            "Check the log files for more information",
            "Report this error if it persists",
        ],
    ),
}


def get_error_message(
    error_code: ErrorCode, *args, exception: Optional[Exception] = None, **kwargs
) -> ErrorMessage:
    """Get user-friendly error message for an error code.

    Args:
        error_code: Error code from ErrorCode enum
        *args: Arguments to pass to error message factory
        exception: Original exception (for technical details)
        **kwargs: Keyword arguments for error message factory

    Returns:
        ErrorMessage instance with user-friendly message
    """
    if error_code not in ERROR_MESSAGES:
        error_code = ErrorCode.UNKNOWN_ERROR

    # Get error message factory and create message
    factory = ERROR_MESSAGES[error_code]
    try:
        error_msg = factory(*args, **kwargs)
    except TypeError:
        # Factory doesn't accept arguments, call with no args
        error_msg = factory()

    # Add exception details if provided
    if exception:
        error_msg.details = f"{type(exception).__name__}: {str(exception)}"

    return error_msg


def show_error_dialog(
    parent: QWidget,
    error_message: ErrorMessage,
    show_details: bool = False,
) -> int:
    """Show user-friendly error dialog with optional technical details.

    Args:
        parent: Parent widget for dialog
        error_message: ErrorMessage instance
        show_details: Whether to show technical details by default

    Returns:
        QMessageBox.StandardButton result
    """
    # Create message box
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(error_message.title)

    # Set icon based on severity
    if error_message.severity == ErrorSeverity.INFO:
        msg_box.setIcon(QMessageBox.Icon.Information)
    elif error_message.severity == ErrorSeverity.WARNING:
        msg_box.setIcon(QMessageBox.Icon.Warning)
    elif error_message.severity == ErrorSeverity.CRITICAL:
        msg_box.setIcon(QMessageBox.Icon.Critical)
    else:
        msg_box.setIcon(QMessageBox.Icon.Critical)

    # Build message text
    text_parts = [error_message.message]

    if error_message.suggestions:
        text_parts.append("\n\nSuggested actions:")
        for i, suggestion in enumerate(error_message.suggestions, 1):
            text_parts.append(f"{i}. {suggestion}")

    msg_box.setText("\n".join(text_parts))

    # Add detailed text if available
    if error_message.details:
        msg_box.setDetailedText(error_message.details)

    # Set standard buttons
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

    # Show dialog
    return msg_box.exec()


def show_error(
    parent: QWidget,
    error_code: ErrorCode,
    *args,
    exception: Optional[Exception] = None,
    include_traceback: bool = False,
    **kwargs,
) -> int:
    """Convenience function to show error dialog.

    Args:
        parent: Parent widget for dialog
        error_code: Error code from ErrorCode enum
        *args: Arguments for error message factory
        exception: Original exception
        include_traceback: Whether to include full traceback in details
        **kwargs: Keyword arguments for error message factory

    Returns:
        QMessageBox.StandardButton result

    Example:
        >>> try:
        >>>     open_directory(path)
        >>> except PermissionError as e:
        >>>     show_error(
        >>>         self,
        >>>         ErrorCode.PERMISSION_DENIED,
        >>>         "read directory",
        >>>         exception=e,
        >>>         include_traceback=True
        >>>     )
    """
    error_msg = get_error_message(error_code, *args, exception=exception, **kwargs)

    # Add full traceback if requested
    if include_traceback and exception:
        tb = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )
        error_msg.details = f"{error_msg.details}\n\nFull traceback:\n{tb}"

    # Log the error
    log_level = logging.ERROR
    if error_msg.severity == ErrorSeverity.INFO:
        log_level = logging.INFO
    elif error_msg.severity == ErrorSeverity.WARNING:
        log_level = logging.WARNING
    elif error_msg.severity == ErrorSeverity.CRITICAL:
        log_level = logging.CRITICAL

    logger.log(
        log_level,
        f"Error shown to user: {error_msg.title} - {error_msg.message}",
        exc_info=exception if include_traceback else None,
    )

    return show_error_dialog(parent, error_msg)


def map_exception_to_error_code(exception: Exception, context: str = "") -> ErrorCode:
    """Map a Python exception to an ErrorCode.

    Args:
        exception: The exception to map
        context: Context string (e.g., "reading directory", "processing image")

    Returns:
        Appropriate ErrorCode for the exception

    Example:
        >>> try:
        >>>     process_image(path)
        >>> except Exception as e:
        >>>     code = map_exception_to_error_code(e, "processing image")
        >>>     show_error(self, code, path, exception=e)
    """
    # FileHandler custom exceptions
    exception_class_name = exception.__class__.__name__
    if exception_class_name == "NoImagesFoundError":
        return ErrorCode.NO_IMAGES_FOUND
    if exception_class_name == "InvalidImageFormatError":
        return ErrorCode.INVALID_IMAGE_FORMAT
    if exception_class_name == "CorruptedImageError":
        return ErrorCode.CORRUPTED_IMAGE
    if exception_class_name == "FileSecurityError":
        return ErrorCode.PERMISSION_DENIED

    # Permission errors
    if isinstance(exception, PermissionError):
        return ErrorCode.PERMISSION_DENIED

    # File system errors
    if isinstance(exception, FileNotFoundError):
        return ErrorCode.DIRECTORY_NOT_FOUND
    if isinstance(exception, OSError):
        exception_str = str(exception).lower()
        context_lower = context.lower() if context else ""
        if "no space left" in exception_str or "disk full" in exception_str:
            return ErrorCode.DISK_FULL
        if "read" in context_lower or "read" in exception_str:
            return ErrorCode.DISK_READ_ERROR
        if "write" in context_lower or "write" in exception_str:
            return ErrorCode.DISK_WRITE_ERROR
        return ErrorCode.PERMISSION_DENIED

    # Memory errors
    if isinstance(exception, MemoryError):
        return ErrorCode.OUT_OF_MEMORY

    # Import errors (missing dependencies)
    if isinstance(exception, ImportError):
        return ErrorCode.MISSING_DEPENDENCY

    # Image processing errors (PIL/Pillow)
    if exception_class_name in ["UnidentifiedImageError", "DecompressionBombError"]:
        return ErrorCode.CORRUPTED_IMAGE

    # Default to unknown error
    return ErrorCode.UNKNOWN_ERROR
