"""Directory opening handler for UI operations.

This module handles the UI aspects of opening directories containing CT image stacks.
Extracted from CTHarvesterMainWindow during Phase 4.3 refactoring to reduce main_window.py size.

The handler coordinates:
- Directory selection dialog
- File analysis and validation
- UI state updates
- First image loading
- Thumbnail level detection
- Thumbnail generation trigger
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QFileDialog

from ui.errors import ErrorCode, show_error
from utils.ui_utils import wait_cursor

if TYPE_CHECKING:
    from ui.main_window import CTHarvesterMainWindow

logger = logging.getLogger(__name__)


class DirectoryOpenHandler:
    """Handles directory opening with UI dialogs and state management.

    Extracted from CTHarvesterMainWindow during Phase 4.3 refactoring
    to reduce file size and improve separation of concerns.

    The handler manages:
    - Directory selection dialog
    - Settings detection and validation
    - UI updates (directory path, image info)
    - First image preview loading
    - Existing thumbnail level detection
    - Thumbnail generation initiation
    """

    def __init__(self, main_window: "CTHarvesterMainWindow"):
        """Initialize the directory open handler.

        Args:
            main_window: Reference to main window for UI access
        """
        self.window = main_window

    def open_directory(self) -> None:
        """Open directory dialog and load CT image stack.

        Opens a directory selection dialog, analyzes the selected directory
        for CT images, updates UI with detected settings, loads first image
        for preview, checks for existing thumbnails, and initiates thumbnail
        generation if needed.
        """
        logger.info("open_dir method called - START")

        # Show directory selection dialog
        default_dir = self.window.m_app.default_directory if self.window.m_app else "."
        ddir = QFileDialog.getExistingDirectory(
            self.window, self.window.tr("Select directory"), default_dir
        )
        if not ddir:
            logger.info("Directory selection cancelled")
            return

        logger.info(f"Selected directory: {ddir}")
        self.window.edtDirname.setText(ddir)
        if self.window.m_app:
            self.window.m_app.default_directory = os.path.dirname(ddir)

        # Reset UI state
        self.window.settings_hash = {}
        self.window.initialized = False
        self.window._reset_ui_state()

        with wait_cursor():
            # Use FileHandler to analyze directory
            settings_result = self.window.file_handler.open_directory(ddir)
            if settings_result is None:
                logger.warning("No valid image files found")
                # Show user-friendly error message
                show_error(
                    self.window,
                    ErrorCode.NO_IMAGES_FOUND,
                    ddir,
                )
                return

            self.window.settings_hash = settings_result
            logger.info(
                f"Detected image sequence: prefix={self.window.settings_hash.get('prefix')}, "
                f"range={self.window.settings_hash.get('seq_begin')}-{self.window.settings_hash.get('seq_end')}"
            )

            # Update UI with detected settings
            self.window.edtNumImages.setText(
                str(
                    self.window.settings_hash["seq_end"]
                    - self.window.settings_hash["seq_begin"]
                    + 1
                )
            )
            self.window.edtImageDimension.setText(
                f"{self.window.settings_hash['image_width']} x {self.window.settings_hash['image_height']}"
            )

            # Build image file list
            image_file_list = self.window.file_handler.get_file_list(
                ddir, self.window.settings_hash
            )

            self.window.original_from_idx = 0
            self.window.original_to_idx = len(image_file_list) - 1

            # Load first image for preview
            self.window._load_first_image(ddir, image_file_list)

            # Initialize level_info
            self.window.level_info = []
            self.window.level_info.append(
                {
                    "name": "Original",
                    "width": self.window.settings_hash["image_width"],
                    "height": self.window.settings_hash["image_height"],
                    "seq_begin": self.window.settings_hash["seq_begin"],
                    "seq_end": self.window.settings_hash["seq_end"],
                }
            )

            # Check for existing thumbnail directories
            self.window._load_existing_thumbnail_levels(ddir)

            logger.info(f"Successfully loaded directory with {len(image_file_list)} images")

        # Generate thumbnails
        self.window.create_thumbnail()
