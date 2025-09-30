"""
User-friendly error message generation

Provides templates and builders for converting technical exceptions
into user-friendly error messages with helpful solutions.

Created during Phase 1.3 UI/UX improvements.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import errno
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserError:
    """User-friendly error information"""
    title: str
    message: str
    solutions: List[str]
    technical_details: Optional[str] = None


class ErrorMessageBuilder:
    """Error message builder with templates for common errors"""

    # Error type templates
    ERROR_TEMPLATES = {
        'file_not_found': UserError(
            title="Cannot find file",
            message="The file '{filename}' could not be found.",
            solutions=[
                "Check if the file was moved or deleted",
                "Verify the file path is correct",
                "Try selecting the file again"
            ]
        ),
        'permission_denied': UserError(
            title="Permission denied",
            message="You don't have permission to access '{filename}'.",
            solutions=[
                "Check file permissions",
                "Try running the application as administrator",
                "Move the file to a different location"
            ]
        ),
        'invalid_image': UserError(
            title="Invalid image file",
            message="The file '{filename}' is not a valid image or is corrupted.",
            solutions=[
                "Check if the file can be opened with other image viewers",
                "Try converting the image to a different format",
                "Re-export the image from the source"
            ]
        ),
        'out_of_memory': UserError(
            title="Out of memory",
            message="Not enough memory to process this image stack.",
            solutions=[
                "Close other applications to free up memory",
                "Try processing a smaller region",
                "Consider upgrading your system memory",
                "Use a lower resolution level"
            ]
        ),
        'disk_space': UserError(
            title="Not enough disk space",
            message="There is not enough disk space to save the output.",
            solutions=[
                "Free up disk space by deleting unnecessary files",
                "Choose a different output location",
                "Reduce the output quality or resolution"
            ]
        ),
        'opengl_error': UserError(
            title="3D rendering error",
            message="Failed to initialize 3D visualization.",
            solutions=[
                "Update your graphics drivers",
                "Check if your system supports OpenGL 3.0+",
                "Try disabling 3D features in preferences"
            ]
        ),
        'rust_module_missing': UserError(
            title="Performance module not available",
            message="The high-performance Rust module could not be loaded.",
            solutions=[
                "Reinstall the application",
                "The program will use slower Python fallback",
                "Check the log file for details"
            ]
        ),
        'directory_not_found': UserError(
            title="Cannot find directory",
            message="The directory '{dirname}' could not be found.",
            solutions=[
                "Check if the directory was moved or deleted",
                "Verify the directory path is correct",
                "Try selecting the directory again"
            ]
        ),
        'no_images_found': UserError(
            title="No images found",
            message="No valid image files were found in the selected directory.",
            solutions=[
                "Check if the directory contains .tif, .tiff, .png, or .jpg files",
                "Verify the image files are not corrupted",
                "Try a different directory"
            ]
        )
    }

    @classmethod
    def build_error(
        cls,
        error_type: str,
        exception: Exception,
        **kwargs
    ) -> UserError:
        """
        Build user-friendly error message

        Args:
            error_type: Error type key
            exception: Original exception
            **kwargs: Template variables (e.g., filename)

        Returns:
            UserError object
        """
        # Get template
        template = cls.ERROR_TEMPLATES.get(error_type)

        if template is None:
            # Default error
            return UserError(
                title="An error occurred",
                message=str(exception),
                solutions=["Please check the log file for details"],
                technical_details=f"{type(exception).__name__}: {exception}"
            )

        # Apply variables to template
        title = template.title
        message = template.message.format(**kwargs) if kwargs else template.message
        solutions = template.solutions.copy()

        # Add technical details
        technical_details = f"{type(exception).__name__}: {exception}"

        return UserError(
            title=title,
            message=message,
            solutions=solutions,
            technical_details=technical_details
        )

    @classmethod
    def from_exception(cls, exception: Exception, **kwargs) -> UserError:
        """
        Automatically detect error type from exception

        Args:
            exception: Exception object
            **kwargs: Additional context (e.g., filename)

        Returns:
            UserError object
        """
        # FileNotFoundError
        if isinstance(exception, FileNotFoundError):
            return cls.build_error('file_not_found', exception, **kwargs)

        # PermissionError
        elif isinstance(exception, PermissionError):
            return cls.build_error('permission_denied', exception, **kwargs)

        # MemoryError
        elif isinstance(exception, MemoryError):
            return cls.build_error('out_of_memory', exception, **kwargs)

        # OSError with specific errno
        elif isinstance(exception, OSError):
            if hasattr(exception, 'errno'):
                if exception.errno == errno.ENOSPC:
                    return cls.build_error('disk_space', exception, **kwargs)
                elif exception.errno == errno.EACCES:
                    return cls.build_error('permission_denied', exception, **kwargs)

        # PIL/Image errors
        elif 'PIL' in str(type(exception)) or 'Image' in str(type(exception)):
            return cls.build_error('invalid_image', exception, **kwargs)

        # OpenGL errors
        elif 'OpenGL' in str(exception) or 'GL' in str(type(exception).__name__):
            return cls.build_error('opengl_error', exception, **kwargs)

        # ModuleNotFoundError for Rust
        elif isinstance(exception, (ModuleNotFoundError, ImportError)):
            if 'ctharvester_rs' in str(exception):
                return cls.build_error('rust_module_missing', exception, **kwargs)

        # Default handling
        return cls.build_error('unknown', exception, **kwargs)


def show_error_dialog(parent, user_error: UserError):
    """
    Show error dialog with user-friendly message

    Args:
        parent: Parent widget
        user_error: UserError object
    """
    from PyQt5.QtWidgets import QMessageBox

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(user_error.title)

    # Compose message
    text = user_error.message + "\n\n"
    text += "Possible solutions:\n"
    for i, solution in enumerate(user_error.solutions, 1):
        text += f"{i}. {solution}\n"

    msg_box.setText(text)

    # Technical details (collapsible)
    if user_error.technical_details:
        msg_box.setDetailedText(user_error.technical_details)

    msg_box.exec_()


def show_warning_dialog(parent, user_error: UserError):
    """
    Show warning dialog (same format as error but with warning icon)

    Args:
        parent: Parent widget
        user_error: UserError object
    """
    from PyQt5.QtWidgets import QMessageBox

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setWindowTitle(user_error.title)

    # Compose message
    text = user_error.message + "\n\n"
    if user_error.solutions:
        text += "Suggestions:\n"
        for i, solution in enumerate(user_error.solutions, 1):
            text += f"{i}. {solution}\n"

    msg_box.setText(text)

    # Technical details (collapsible)
    if user_error.technical_details:
        msg_box.setDetailedText(user_error.technical_details)

    msg_box.exec_()