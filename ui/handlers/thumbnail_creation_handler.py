"""Thumbnail creation handler for Rust and Python implementations.

This module handles thumbnail generation using either Rust (high-performance) or
Python (fallback) implementations. Extracted from CTHarvesterMainWindow during
Phase 4.2 refactoring to reduce main_window.py size.

The handler coordinates:
- Rust/Python implementation selection
- Progress dialog management
- Thumbnail generation orchestration
- UI state updates after generation
"""

import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication, QMessageBox

from ui.dialogs.progress_dialog import ProgressDialog
from utils.ui_utils import wait_cursor

if TYPE_CHECKING:
    from ui.main_window import CTHarvesterMainWindow

logger = logging.getLogger(__name__)


class ThumbnailCreationHandler:
    """Handles thumbnail creation using Rust or Python fallback.

    Extracted from CTHarvesterMainWindow during Phase 4.2 refactoring
    to reduce file size and improve separation of concerns.

    The handler manages:
    - Implementation selection (Rust vs Python)
    - Progress tracking and UI updates
    - Error handling and recovery
    - Post-generation UI initialization
    """

    def __init__(self, main_window: "CTHarvesterMainWindow"):
        """Initialize the thumbnail creation handler.

        Args:
            main_window: Reference to main window for UI access
        """
        self.window = main_window

    def create_thumbnail(self) -> bool:
        """Create thumbnails using Rust or Python implementation.

        Checks user preference and Rust module availability, then
        delegates to appropriate implementation.

        Returns:
            bool: True if generation succeeded, False otherwise
        """
        # Check if user wants to use Rust module (from preferences)
        use_rust_preference = getattr(self.window.m_app, "use_rust_thumbnail", True)

        # Try to use Rust module if preferred
        if use_rust_preference:
            try:
                from ct_thumbnail import build_thumbnails  # noqa: F401

                use_rust = True
                logger.info("Using Rust-based thumbnail generation")
            except ImportError:
                use_rust = False
                logger.warning(
                    "ct_thumbnail module not found, falling back to Python implementation"
                )
        else:
            use_rust = False
            logger.info("Using Python implementation (Rust module disabled by user)")

        if use_rust:
            return self.create_thumbnail_rust()
        else:
            return self.create_thumbnail_python()

    def create_thumbnail_rust(self) -> bool:
        """Create thumbnails using Rust-based high-performance module.

        Returns:
            bool: True if generation succeeded, False if cancelled/failed
        """
        from ct_thumbnail import build_thumbnails

        # Start timing
        self.window.thumbnail_start_time = time.time()
        thumbnail_start_datetime = datetime.now()

        dirname = self.window.edtDirname.text()

        logger.info("=== Starting Rust thumbnail generation ===")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Directory: {dirname}")

        # Initialize progress dialog
        self.window.progress_dialog = ProgressDialog(self.window)
        self.window.progress_dialog.update_language()
        self.window.progress_dialog.setModal(True)
        self.window.progress_dialog.show()

        # Set initial progress text
        self.window.progress_dialog.lbl_text.setText(self.window.tr("Generating thumbnails"))
        self.window.progress_dialog.lbl_detail.setText(self.window.tr("Initializing..."))

        # Setup progress bar (0-100%)
        self.window.progress_dialog.pb_progress.setMinimum(0)
        self.window.progress_dialog.pb_progress.setMaximum(100)
        self.window.progress_dialog.pb_progress.setValue(0)

        # Variables for progress tracking
        self.window.last_progress = 0
        self.window.progress_start_time = time.time()
        self.window.rust_cancelled = False

        def progress_callback(percentage: float) -> bool:
            """Progress callback from Rust module.

            Args:
                percentage: Progress percentage (0-100)

            Returns:
                True to continue, False to cancel
            """
            # Process events FIRST to handle any pending Cancel button clicks
            QApplication.processEvents()

            # Check if progress dialog exists
            if not self.window.progress_dialog:
                return False

            # Check for cancellation after processing events
            if self.window.progress_dialog.is_cancelled:
                self.window.rust_cancelled = True
                return False  # Signal Rust to stop

            # Update progress bar
            self.window.progress_dialog.pb_progress.setValue(int(percentage))

            # Calculate elapsed time and ETA
            elapsed = time.time() - self.window.progress_start_time
            if percentage > 0 and percentage < 100:
                eta = elapsed * (100 - percentage) / percentage
                eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta/60)}m {int(eta % 60)}s"
                elapsed_str = (
                    f"{int(elapsed)}s"
                    if elapsed < 60
                    else f"{int(elapsed/60)}m {int(elapsed % 60)}s"
                )

                # Update detail text
                self.window.progress_dialog.lbl_detail.setText(
                    f"{percentage:.1f}% - Elapsed: {elapsed_str} - ETA: {eta_str}"
                )
            else:
                self.window.progress_dialog.lbl_detail.setText(f"{percentage:.1f}%")

            # Process events again to keep UI responsive
            QApplication.processEvents()

            self.window.last_progress = percentage
            return True  # Continue processing

        # Run Rust thumbnail generation with file pattern info
        success = False
        with wait_cursor():
            try:
                # Pass the file pattern information to Rust
                prefix = self.window.settings_hash.get("prefix", "")
                file_type = self.window.settings_hash.get("file_type", "tif")
                seq_begin = int(self.window.settings_hash.get("seq_begin", 0))
                seq_end = int(self.window.settings_hash.get("seq_end", 0))
                index_length = int(self.window.settings_hash.get("index_length", 0))

                # Call Rust with pattern parameters
                build_thumbnails(
                    dirname, progress_callback, prefix, file_type, seq_begin, seq_end, index_length
                )

                # Check if user cancelled
                if self.window.rust_cancelled:
                    success = False
                    logger.info("Rust thumbnail generation cancelled by user")

                    # Give Rust threads a moment to clean up
                    QApplication.processEvents()
                    QThread.msleep(100)  # Small delay for thread cleanup

                    # Close progress dialog
                    if hasattr(self.window, "progress_dialog") and self.window.progress_dialog:
                        self.window.progress_dialog.close()
                        self.window.progress_dialog = None

                    # Return early - don't try to load thumbnails
                    return False
                else:
                    success = True

            except Exception as e:
                success = False
                if not self.window.rust_cancelled:  # Only show error if not cancelled
                    logger.error(f"Error during Rust thumbnail generation: {e}")
                    QMessageBox.warning(
                        self.window,
                        self.window.tr("Warning"),
                        self.window.tr(
                            f"Rust thumbnail generation failed: {e}\nFalling back to Python implementation."
                        ),
                    )

        # Calculate total time
        total_elapsed = time.time() - self.window.thumbnail_start_time
        thumbnail_end_datetime = datetime.now()

        logger.info("=== Rust thumbnail generation completed ===")
        logger.info(f"End time: {thumbnail_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Total duration: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")

        if success and not self.window.rust_cancelled:
            # Load the generated thumbnails
            self.window.load_thumbnail_data_from_disk()

            # Update progress dialog
            if self.window.progress_dialog:
                self.window.progress_dialog.lbl_text.setText(
                    self.window.tr("Thumbnail generation complete")
                )
                self.window.progress_dialog.lbl_detail.setText(
                    f"Completed in {int(total_elapsed)}s"
                )
        else:
            if self.window.progress_dialog:
                if self.window.rust_cancelled:
                    self.window.progress_dialog.lbl_text.setText(
                        self.window.tr("Thumbnail generation cancelled")
                    )
                else:
                    self.window.progress_dialog.lbl_text.setText(
                        self.window.tr("Thumbnail generation failed")
                    )

            # Initialize minimum_volume as empty to prevent errors
            if not hasattr(self.window, "minimum_volume"):
                self.window.minimum_volume = []
                logger.warning(
                    "Initialized empty minimum_volume after Rust thumbnail generation failure"
                )

        # Close progress dialog
        if self.window.progress_dialog:
            self.window.progress_dialog.close()
        self.window.progress_dialog = None

        # Initialize combo boxes
        self.window.initializeComboSize()
        self.window.reset_crop()

        # Trigger initial display
        if self.window.comboLevel.count() > 0:
            self.window.comboLevel.setCurrentIndex(0)
            if not self.window.initialized:
                self.window.comboLevelIndexChanged()

        return success

    def create_thumbnail_python(self) -> bool:
        """Create thumbnails using Python implementation (fallback).

        This method delegates thumbnail generation to ThumbnailGenerator.generate_python(),
        which handles the actual business logic. The UI responsibilities remain here:
        setting up progress dialog, defining callbacks, and updating UI state.

        Returns:
            bool: True if generation succeeded, False if cancelled/failed
        """
        # Calculate total work for progress tracking
        # This must be done before creating the progress dialog
        size = max(
            int(self.window.settings_hash["image_width"]),
            int(self.window.settings_hash["image_height"]),
        )
        seq_begin = self.window.settings_hash["seq_begin"]
        seq_end = self.window.settings_hash["seq_end"]
        MAX_THUMBNAIL_SIZE = 512

        # Calculate total work (result unused but triggers internal calculation)
        self.window.thumbnail_generator.calculate_total_thumbnail_work(
            seq_begin, seq_end, size, MAX_THUMBNAIL_SIZE
        )
        weighted_total_work = self.window.thumbnail_generator.weighted_total_work

        # Create progress dialog
        self.window.progress_dialog = ProgressDialog(self.window)
        self.window.progress_dialog.update_language()
        self.window.progress_dialog.setModal(True)

        # Setup unified progress with calculated work amount
        self.window.progress_dialog.setup_unified_progress(weighted_total_work, None)
        self.window.progress_dialog.lbl_text.setText(self.window.tr("Generating thumbnails"))
        self.window.progress_dialog.lbl_detail.setText("Estimating...")

        self.window.progress_dialog.show()

        # Set wait cursor for long operation
        with wait_cursor():
            try:
                # Call ThumbnailGenerator with progress dialog
                # Pass the progress dialog directly so ThumbnailManager can connect signals properly
                result = self.window.thumbnail_generator.generate_python(
                    directory=self.window.edtDirname.text(),
                    settings=self.window.settings_hash,
                    threadpool=self.window.threadpool,
                    progress_dialog=self.window.progress_dialog,
                )

                # Handle result
                if result is None:
                    logger.error("Thumbnail generation failed - generate_python returned None")
                    if self.window.progress_dialog:
                        self.window.progress_dialog.lbl_text.setText(
                            self.window.tr("Thumbnail generation failed")
                        )
                        self.window.progress_dialog.lbl_detail.setText("")
                        self.window.progress_dialog.close()
                        self.window.progress_dialog = None
                    QMessageBox.critical(
                        self.window,
                        self.window.tr("Thumbnail Generation Failed"),
                        self.window.tr("An unknown error occurred during thumbnail generation."),
                    )
                    return False

                # Handle cancellation
                if result.get("cancelled"):
                    logger.info("Thumbnail generation cancelled by user")
                    if self.window.progress_dialog:
                        self.window.progress_dialog.lbl_text.setText(
                            self.window.tr("Thumbnail generation cancelled")
                        )
                        self.window.progress_dialog.lbl_detail.setText("")
                        self.window.progress_dialog.close()
                        self.window.progress_dialog = None
                    QMessageBox.information(
                        self.window,
                        self.window.tr("Thumbnail Generation Cancelled"),
                        self.window.tr("Thumbnail generation was cancelled by user."),
                    )
                    return False

                # Handle generation failure (not cancelled, but success=False)
                if not result.get("success"):
                    error_msg = result.get("error", "Thumbnail generation failed")
                    logger.error(f"Thumbnail generation failed: {error_msg}")
                    if self.window.progress_dialog:
                        self.window.progress_dialog.lbl_text.setText(
                            self.window.tr("Thumbnail generation failed")
                        )
                        self.window.progress_dialog.lbl_detail.setText("")
                        self.window.progress_dialog.close()
                        self.window.progress_dialog = None
                    QMessageBox.critical(
                        self.window,
                        self.window.tr("Thumbnail Generation Failed"),
                        self.window.tr("Thumbnail generation failed:\n\n{}").format(error_msg),
                    )
                    return False

                # Update instance state from result (only if successful)
                self.window.minimum_volume = result.get("minimum_volume", [])
                self.window.level_info = result.get("level_info", [])

                # Show completion message
                if self.window.progress_dialog:
                    self.window.progress_dialog.lbl_text.setText(
                        self.window.tr("Thumbnail generation complete")
                    )
                    self.window.progress_dialog.lbl_detail.setText("")

                # Close progress dialog
                if self.window.progress_dialog:
                    self.window.progress_dialog.close()
                    self.window.progress_dialog = None

                # Proceed with UI updates (only if successful)
                # Load thumbnail data from disk (same as Rust does)
                self.window.load_thumbnail_data_from_disk()

                # If loading from disk failed and minimum_volume is still empty
                if self.window.minimum_volume is None or (
                    hasattr(self.window.minimum_volume, "__len__")
                    and len(self.window.minimum_volume) == 0
                ):
                    logger.warning("Failed to load thumbnails from disk after Python generation")

                # Initialize UI components
                self.window.initializeComboSize()
                self.window.reset_crop()

                # Trigger initial display by setting combo index if items exist
                if self.window.comboLevel.count() > 0:
                    self.window.comboLevel.setCurrentIndex(0)
                    # If comboLevelIndexChanged doesn't trigger, call it manually
                    if not self.window.initialized:
                        self.window.comboLevelIndexChanged()

                    # Update 3D view after initializing combo level
                    self.window.update_3D_view(False)

                return True

            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error in create_thumbnail_python: {e}", exc_info=True)

                if self.window.progress_dialog:
                    self.window.progress_dialog.lbl_text.setText(
                        self.window.tr("Thumbnail generation failed")
                    )
                    self.window.progress_dialog.lbl_detail.setText(str(e))
                    self.window.progress_dialog.close()
                    self.window.progress_dialog = None

                return False
