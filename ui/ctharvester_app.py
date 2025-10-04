"""Custom QApplication subclass with typed attributes for CTHarvester.

This module provides a type-safe QApplication subclass that defines
CTHarvester-specific application attributes. This eliminates mypy errors
from dynamic attribute assignment and improves IDE autocomplete support.

Created during mypy error resolution (devlog 080).
"""

from PyQt5.QtWidgets import QApplication


class CTHarvesterApp(QApplication):
    """Custom QApplication with CTHarvester-specific attributes.

    This subclass adds typed attributes for settings and preferences,
    eliminating mypy errors from dynamic attribute assignment and providing
    better IDE support for application-level configuration.

    Attributes:
        language: UI language code ('en', 'ko', etc.)
        default_directory: Default directory for file operations
        remember_geometry: Whether to save/restore window geometry
        remember_directory: Whether to remember last used directory
        use_rust_thumbnail: Whether to use Rust module for thumbnail generation

    Example:
        >>> app = CTHarvesterApp(sys.argv)
        >>> app.language = "ko"
        >>> app.use_rust_thumbnail = True
        >>> window = CTHarvesterMainWindow()
        >>> window.show()
    """

    def __init__(self, *args, **kwargs):
        """Initialize CTHarvester application with default settings.

        Args:
            *args: Positional arguments passed to QApplication
            **kwargs: Keyword arguments passed to QApplication
        """
        super().__init__(*args, **kwargs)

        # Language settings
        self.language: str = "en"

        # Directory settings
        self.default_directory: str = "."
        self.remember_directory: bool = True

        # Window settings
        self.remember_geometry: bool = True

        # Processing settings
        self.use_rust_thumbnail: bool = True
