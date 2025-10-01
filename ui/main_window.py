"""
CTHarvesterMainWindow - Main application window

Extracted from CTHarvester.py during Phase 4c refactoring.
"""

import logging
import os
import re
import sys
from copy import deepcopy

import numpy as np
from PIL import Image
from PyQt5.QtCore import QMargins, QObject, QPoint, QRect, Qt, QThreadPool, QTimer, QTranslator
from PyQt5.QtGui import QCursor, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from config.constants import (
    COMPANY_NAME,
    PROGRAM_NAME,
    PROGRAM_VERSION,
    SUPPORTED_IMAGE_EXTENSIONS,
    THUMBNAIL_DIR_NAME,
)
from core.file_handler import FileHandler
from core.progress_manager import ProgressManager
from core.thumbnail_generator import ThumbnailGenerator
from core.thumbnail_manager import ThumbnailManager
from core.volume_processor import VolumeProcessor
from security.file_validator import FileSecurityError, SecureFileValidator, safe_open_image
from ui.dialogs import InfoDialog, ProgressDialog, SettingsDialog
from ui.handlers import ExportHandler, WindowSettingsHandler
from ui.setup import MainWindowSetup
from ui.widgets import MCubeWidget, ObjectViewer2D
from ui.widgets.vertical_stack_slider import VerticalTimeline
from utils.common import resource_path, value_to_bool
from utils.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.m_app = QApplication.instance()

        # Window configuration
        self.setWindowIcon(QIcon(resource_path("resources/icons/CTHarvester_48_2.png")))
        self.setWindowTitle("{} v{}".format(self.tr("CT Harvester"), PROGRAM_VERSION))
        self.setGeometry(QRect(100, 100, 600, 550))

        # Data initialization
        self.settings_hash = {}
        self.level_info = []
        self.minimum_volume = None  # Initialize to None, will be set after thumbnail generation
        self.curr_level_idx = 0
        self.prev_level_idx = 0
        self.default_directory = "."
        self.threadpool = QThreadPool()
        logger.info(
            f"Initialized ThreadPool with maxThreadCount={self.threadpool.maxThreadCount()}"
        )

        # Initialize YAML-based settings manager (Phase 2.1)
        self.settings_manager = SettingsManager()
        logger.info(f"Settings file: {self.settings_manager.get_config_file_path()}")

        # Initialize extracted handlers (Phase 1 refactoring)
        self.file_handler = FileHandler()
        self.thumbnail_generator = ThumbnailGenerator()
        self.volume_processor = VolumeProcessor()
        logger.info("Initialized FileHandler, ThumbnailGenerator, and VolumeProcessor")

        # Initialize settings handler (Phase 2: Settings Separation)
        self.settings_handler = WindowSettingsHandler(self, self.settings_manager)

        # Initialize export handler (Phase 3: Export Operations Separation)
        self.export_handler = ExportHandler(self)

        # Read settings (must be done before UI setup to get mcube_geometry)
        self.settings_handler.read_all_settings()

        # UI initialization (Phase 1: UI Separation - delegated to MainWindowSetup)
        ui_setup = MainWindowSetup(self)
        ui_setup.setup_all()

    def rangeSliderMoved(self):
        """Handle range slider moved event (legacy - no longer used)."""
        return

    def rangeSliderPressed(self):
        """Handle range slider pressed event (legacy - no longer used)."""
        return

    def cbxInverse_stateChanged(self):
        """
        Handle inverse checkbox state change.

        Updates the inverse mode for both 2D viewer and 3D mesh widget,
        then refreshes the display.
        """
        if self.image_label.orig_pixmap is None:
            return
        self.mcube_widget.is_inverse = self.image_label.is_inverse = self.cbxInverse.isChecked()
        self.image_label.calculate_resize()
        self.image_label.repaint()
        self.update_3D_view(True)

    def show_advanced_settings(self):
        """Show advanced settings dialog (new comprehensive version - Phase 2.2)"""
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec_():
            logger.info("Advanced settings updated")
            # Optionally reload settings or notify user
            QMessageBox.information(
                self,
                "Settings Saved",
                "Settings have been saved.\n\nSome changes may require restarting the application.",
            )

    def show_info(self):
        """Show information dialog with application details and shortcuts."""
        self.info_dialog = InfoDialog(self)
        self.info_dialog.setModal(True)
        self.info_dialog.show()

    def update_language(self):
        """
        Update UI language based on current language setting.

        Loads translation file and updates all translatable UI strings.
        """
        translator = QTranslator()
        translator.load(resource_path(f"resources/translations/CTHarvester_{self.m_app.language}.qm"))
        self.m_app.installTranslator(translator)

        self.setWindowTitle(f"{self.tr(PROGRAM_NAME)} v{PROGRAM_VERSION}")
        self.btnOpenDir.setText(self.tr("Open Directory"))
        self.edtDirname.setPlaceholderText(self.tr("Select directory to load CT data"))
        self.lblLevel.setText(self.tr("Level"))
        self.btnSetBottom.setText(self.tr("Set Bottom"))
        self.btnSetTop.setText(self.tr("Set Top"))
        self.btnReset.setText(self.tr("Reset"))
        self.cbxOpenDirAfter.setText(self.tr("Open dir. after"))
        self.btnSave.setText(self.tr("Save cropped image stack"))
        self.btnExport.setText(self.tr("Export 3D Model"))
        self.lblCount.setText(self.tr("Count"))
        self.lblSize.setText(self.tr("Size"))
        self.status_text_format = self.tr(
            "Crop indices: {}~{} Cropped image size: {}x{} ({},{})-({},{}) Estimated stack size: {} MB [{}]"
        )
        self.progress_text_1_2 = self.tr("Saving image stack... {}/{}")
        self.progress_text_1_1 = self.tr("Saving image stack...")
        self.progress_text_2_1 = self.tr("Generating thumbnails (Level {})")
        self.progress_text_2_2 = self.tr("Generating thumbnails (Level {}) - {}/{}")
        self.progress_text_3_1 = self.tr("Loading thumbnails (Level {})")
        self.progress_text_3_2 = self.tr("Loading thumbnails (Level {}) - {}/{}")

    def set_bottom(self):
        """Set the bottom (lower) crop boundary to current timeline position."""
        _, curr, _ = self.timeline.values()
        self.timeline.setLower(curr)
        self.update_status()

    def set_top(self):
        """Set the top (upper) crop boundary to current timeline position."""
        _, curr, _ = self.timeline.values()
        self.timeline.setUpper(curr)
        self.update_status()

    # def resizeEvent(self, a0: QResizeEvent) -> None:
    #    #print("resizeEvent")
    #    return super().resizeEvent(a0)

    def update_3D_view_click(self):
        """Handle button click to update 3D view with volume recalculation."""
        self.update_3D_view(True)

    def update_3D_view(self, update_volume=True):
        """
        Update 3D mesh viewer with current crop region and bounding box.

        Args:
            update_volume: If True, recalculates volume from current settings.
                          If False, only updates display.

        The method scales bounding box dimensions based on current pyramid level
        to ensure proper visualization across different resolution levels.
        """
        # print("update 3d view")
        volume, roi_box = self.get_cropped_volume()

        # Check if volume is empty
        if volume.size == 0:
            logger.warning("Empty volume in update_3D_view, skipping update")
            return

        # Calculate bounding box based on current level
        # The minimum_volume is always the smallest level, but we need to scale it
        # based on the current viewing level
        if hasattr(self, "level_info") and self.level_info:
            smallest_level_idx = len(self.level_info) - 1
            level_diff = smallest_level_idx - self.curr_level_idx
            scale_factor = 2**level_diff  # Each level is 2x the size of the next
        else:
            # Default to no scaling if level_info is not available
            scale_factor = 1

        # Get the base dimensions from minimum_volume
        base_shape = self.minimum_volume.shape

        # Scale the dimensions according to current level
        scaled_depth = base_shape[0] * scale_factor
        scaled_height = base_shape[1] * scale_factor
        scaled_width = base_shape[2] * scale_factor

        bounding_box = [0, scaled_depth - 1, 0, scaled_height - 1, 0, scaled_width - 1]

        # Scale the current slice value as well
        try:
            _, curr, _ = self.timeline.values()
            denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
            curr_slice_val = curr / denom * scaled_depth
        except Exception:
            curr_slice_val = 0

        self.mcube_widget.update_boxes(bounding_box, roi_box, curr_slice_val)
        self.mcube_widget.adjust_boxes()

        if update_volume:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.mcube_widget.update_volume(volume)
            self.mcube_widget.generate_mesh_multithread()
            QApplication.restoreOverrideCursor()
        self.mcube_widget.adjust_volume()

    def update_curr_slice(self):
        """
        Update current slice indicator in 3D view without regenerating mesh.

        Calculates scaled slice position based on pyramid level and updates
        the 3D viewer's slice plane indicator. Skips update if volume not initialized.
        """
        # Check if minimum_volume is initialized
        if (
            not hasattr(self, "minimum_volume")
            or self.minimum_volume is None
            or len(self.minimum_volume) == 0
        ):
            logger.warning("minimum_volume not initialized in update_curr_slice")
            return

        # Calculate bounding box based on current level
        if hasattr(self, "level_info") and self.level_info:
            smallest_level_idx = len(self.level_info) - 1
            level_diff = smallest_level_idx - self.curr_level_idx
            scale_factor = 2**level_diff
        else:
            scale_factor = 1

        # Get the base dimensions from minimum_volume
        base_shape = self.minimum_volume.shape

        # Scale the dimensions according to current level
        scaled_depth = base_shape[0] * scale_factor
        scaled_height = base_shape[1] * scale_factor
        scaled_width = base_shape[2] * scale_factor

        bounding_box = [0, scaled_depth - 1, 0, scaled_height - 1, 0, scaled_width - 1]
        try:
            _, curr, _ = self.timeline.values()
            denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
            curr_slice_val = curr / denom * scaled_depth
        except Exception:
            curr_slice_val = 0

        self.update_3D_view(False)

    def get_cropped_volume(self):
        """Get cropped volume based on current selection

        Uses VolumeProcessor to handle cropping and coordinate transformation.
        """
        # Get UI state
        top_idx = self.image_label.top_idx
        bottom_idx = self.image_label.bottom_idx
        crop_box = self.image_label.get_crop_area(imgxy=True)

        # Use VolumeProcessor to get cropped volume
        return self.volume_processor.get_cropped_volume(
            minimum_volume=self.minimum_volume,
            level_info=self.level_info,
            curr_level_idx=self.curr_level_idx,
            top_idx=top_idx,
            bottom_idx=bottom_idx,
            crop_box=crop_box,
        )

    def export_3d_model(self):
        """
        Export 3D model to OBJ file (delegated to ExportHandler).

        This method is kept for backward compatibility but delegates to the handler.
        """
        self.export_handler.export_3d_model_to_obj()

    def save_result(self):
        """
        Save cropped image stack (delegated to ExportHandler).

        This method is kept for backward compatibility but delegates to the handler.
        """
        self.export_handler.save_cropped_image_stack()

    def rangeSliderValueChanged(self):
        """
        Handle range slider value change to update top/bottom crop boundaries.

        Updates image viewer crop indices and regenerates 3D mesh with new range.
        Skips update if level_info not yet initialized during startup.
        """
        # print("range slider value changed")
        try:
            # Check if necessary attributes are initialized
            if not hasattr(self, "level_info") or not self.level_info:
                # This is expected during initialization when sliders are disabled
                return

            lo, _, hi = self.timeline.values()
            bottom_idx, top_idx = lo, hi
            self.image_label.set_bottom_idx(bottom_idx)
            self.image_label.set_top_idx(top_idx)
            self.image_label.calculate_resize()
            self.image_label.repaint()
            self.update_3D_view(True)
            self.update_status()
        except Exception as e:
            logger.error(f"Error in rangeSliderValueChanged: {e}")

    def rangeSliderReleased(self):
        """Handle range slider release event (currently no-op)."""
        # print("range slider released")
        return

    def sliderValueChanged(self):
        """
        Handle timeline slider value change to display different image slice.

        Loads the image corresponding to the current slider position from either
        the original directory (level 0) or thumbnail cache (levels 1+).
        """
        if not self.initialized:
            return
        size_idx = self.comboLevel.currentIndex()
        _, curr_image_idx, _ = self.timeline.values()
        if size_idx < 0:
            size_idx = 0

        # get directory for size idx
        if size_idx == 0:
            dirname = self.edtDirname.text()
            filename = (
                self.settings_hash["prefix"]
                + str(self.level_info[size_idx]["seq_begin"] + curr_image_idx).zfill(
                    self.settings_hash["index_length"]
                )
                + "."
                + self.settings_hash["file_type"]
            )
        else:
            dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            # Match Rust naming: simple sequential numbering without prefix
            filename = f"{curr_image_idx:06}.tif"

        self.image_label.set_image(os.path.join(dirname, filename))
        self.image_label.set_curr_idx(curr_image_idx)
        self.update_curr_slice()

    def reset_crop(self):
        """
        Reset crop area and timeline range to defaults.

        Clears all crop selections and resets timeline to show full image range.
        """
        _, curr, _ = self.timeline.values()
        self.image_label.set_curr_idx(curr)
        self.image_label.reset_crop()
        self.timeline.setLower(self.timeline.minimum())
        self.timeline.setUpper(self.timeline.maximum())
        self.canvas_box = None
        self.update_status()

    def update_status(self):
        """
        Update status bar with current crop dimensions and estimated size.

        Displays crop indices, image dimensions, coordinates, and calculated
        memory size of the cropped image stack.
        """
        lo, _, hi = self.timeline.values()
        bottom_idx, top_idx = lo, hi
        [x1, y1, x2, y2] = self.image_label.get_crop_area(imgxy=True)
        count = top_idx - bottom_idx + 1
        # self.status_format = self.tr("Crop indices: {}~{}    Cropped image size: {}x{}    Estimated stack size: {} MB [{}]")
        status_text = self.status_text_format.format(
            bottom_idx,
            top_idx,
            x2 - x1,
            y2 - y1,
            x1,
            y1,
            x2,
            y2,
            round(count * (x2 - x1) * (y2 - y1) / 1024 / 1024, 2),
            str(self.image_label.edit_mode),
        )
        self.edtStatus.setText(status_text)

    def initializeComboSize(self):
        """
        Initialize pyramid level combo box with available resolution levels.

        Populates combo box with level names from level_info metadata.
        """
        # logger.info(f"initializeComboSize called, level_info count: {len(self.level_info) if hasattr(self, 'level_info') else 'not set'}")
        self.comboLevel.clear()
        for level in self.level_info:
            self.comboLevel.addItem(level["name"])
            # logger.info(f"Added level: {level['name']}, size: {level['width']}x{level['height']}, seq: {level['seq_begin']}-{level['seq_end']}")

    def comboLevelIndexChanged(self):
        """
        This method is called when the user selects a different level from the combo box.
        It updates the UI with information about the selected level, such as the image dimensions and number of images.
        It also updates the slider and range slider to reflect the number of images in the selected level.
        """
        # Check if level_info is initialized
        if not hasattr(self, "level_info") or not self.level_info:
            logger.warning("level_info not initialized in comboLevelIndexChanged")
            return

        self.prev_level_idx = self.curr_level_idx if hasattr(self, "curr_level_idx") else 0
        self.curr_level_idx = self.comboLevel.currentIndex()

        # Validate curr_level_idx
        if self.curr_level_idx < 0 or self.curr_level_idx >= len(self.level_info):
            logger.warning(f"Invalid curr_level_idx: {self.curr_level_idx}, resetting to 0")
            self.curr_level_idx = 0
            return

        level_info = self.level_info[self.curr_level_idx]
        seq_begin = level_info["seq_begin"]
        seq_end = level_info["seq_end"]

        self.edtImageDimension.setText(str(level_info["width"]) + " x " + str(level_info["height"]))
        image_count = seq_end - seq_begin + 1
        self.edtNumImages.setText(str(image_count))

        if not self.initialized:
            self.timeline.setRange(0, image_count - 1)
            self.timeline.setLower(0)
            self.timeline.setUpper(image_count - 1)
            self.timeline.setCurrent(0)
            self.timeline.setEnabled(True)  # Enable timeline now that data is loaded
            self.curr_level_idx = 0
            self.prev_level_idx = 0
            self.initialized = True

        level_diff = self.prev_level_idx - self.curr_level_idx
        _, curr_idx, _ = self.timeline.values()
        curr_idx = int(curr_idx * (2**level_diff))

        lo, _, hi = self.timeline.values()
        bottom_idx = int(lo * (2**level_diff))
        top_idx = int(hi * (2**level_diff))

        # apply new range and values to timeline
        self.timeline.setRange(0, image_count - 1)
        # clamp to range
        bottom_idx = max(0, min(bottom_idx, image_count - 1))
        top_idx = max(0, min(top_idx, image_count - 1))
        if bottom_idx > top_idx:
            bottom_idx, top_idx = top_idx, bottom_idx
        curr_idx = max(bottom_idx, min(curr_idx, top_idx))
        self.timeline.setLower(bottom_idx)
        self.timeline.setUpper(top_idx)
        self.timeline.setCurrent(curr_idx)

        self.sliderValueChanged()
        self.update_status()
        self.update_3D_view(True)

    def calculate_total_thumbnail_work(self, seq_begin, seq_end, size, max_size):
        """Calculate total number of operations for all LoD levels with size weighting

        Delegates to ThumbnailGenerator.calculate_total_thumbnail_work()
        """
        total_work = self.thumbnail_generator.calculate_total_thumbnail_work(
            seq_begin, seq_end, size, max_size
        )

        # Copy state from generator for backward compatibility
        self.level_sizes = self.thumbnail_generator.level_sizes
        self.level_work_distribution = self.thumbnail_generator.level_work_distribution
        self.total_levels = self.thumbnail_generator.total_levels
        self.weighted_total_work = self.thumbnail_generator.weighted_total_work

        return total_work

    def create_thumbnail(self):
        """
        Creates a thumbnail using Rust module if available and enabled, otherwise falls back to Python implementation.
        """
        import time
        from datetime import datetime

        # Check if user wants to use Rust module (from preferences)
        use_rust_preference = getattr(self.m_app, "use_rust_thumbnail", True)

        # Try to use Rust module if preferred
        if use_rust_preference:
            try:
                from ct_thumbnail import build_thumbnails

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

    def create_thumbnail_rust(self):
        """
        Creates a thumbnail using Rust-based high-performance module.
        """
        import time
        from datetime import datetime

        from ct_thumbnail import build_thumbnails

        # Start timing
        self.thumbnail_start_time = time.time()
        thumbnail_start_datetime = datetime.now()

        dirname = self.edtDirname.text()

        logger.info(f"=== Starting Rust thumbnail generation ===")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Directory: {dirname}")

        # Initialize progress dialog
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.update_language()
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        # Set initial progress text
        self.progress_dialog.lbl_text.setText(self.tr("Generating thumbnails"))
        self.progress_dialog.lbl_detail.setText(self.tr("Initializing..."))

        # Setup progress bar (0-100%)
        self.progress_dialog.pb_progress.setMinimum(0)
        self.progress_dialog.pb_progress.setMaximum(100)
        self.progress_dialog.pb_progress.setValue(0)

        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Variables for progress tracking
        self.last_progress = 0
        self.progress_start_time = time.time()
        self.rust_cancelled = False

        def progress_callback(percentage):
            """Progress callback from Rust module"""
            # Check for cancellation first
            if self.progress_dialog.is_cancelled:
                self.rust_cancelled = True
                logger.info(f"Cancellation requested at {percentage:.1f}%")
                return False  # Signal Rust to stop

            # Update progress bar
            self.progress_dialog.pb_progress.setValue(int(percentage))

            # Calculate elapsed time and ETA
            elapsed = time.time() - self.progress_start_time
            if percentage > 0 and percentage < 100:
                eta = elapsed * (100 - percentage) / percentage
                eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta/60)}m {int(eta%60)}s"
                elapsed_str = (
                    f"{int(elapsed)}s" if elapsed < 60 else f"{int(elapsed/60)}m {int(elapsed%60)}s"
                )

                # Update detail text
                self.progress_dialog.lbl_detail.setText(
                    f"{percentage:.1f}% - Elapsed: {elapsed_str} - ETA: {eta_str}"
                )
            else:
                self.progress_dialog.lbl_detail.setText(f"{percentage:.1f}%")

            # Process events to keep UI responsive
            QApplication.processEvents()

            self.last_progress = percentage
            return True  # Continue processing

        # Run Rust thumbnail generation with file pattern info
        success = False
        try:
            # Pass the file pattern information to Rust
            prefix = self.settings_hash.get("prefix", "")
            file_type = self.settings_hash.get("file_type", "tif")
            seq_begin = int(self.settings_hash.get("seq_begin", 0))
            seq_end = int(self.settings_hash.get("seq_end", 0))
            index_length = int(self.settings_hash.get("index_length", 0))

            # Call Rust with pattern parameters
            result = build_thumbnails(
                dirname, progress_callback, prefix, file_type, seq_begin, seq_end, index_length
            )

            # Check if user cancelled
            if self.rust_cancelled:
                success = False
                logger.info("Rust thumbnail generation cancelled by user")
                # Give Rust threads a moment to clean up
                QApplication.processEvents()
                QThread.msleep(100)  # Small delay for thread cleanup
            else:
                success = True

        except Exception as e:
            success = False
            if not self.rust_cancelled:  # Only show error if not cancelled
                logger.error(f"Error during Rust thumbnail generation: {e}")
                QMessageBox.warning(
                    self,
                    self.tr("Warning"),
                    self.tr(
                        f"Rust thumbnail generation failed: {e}\nFalling back to Python implementation."
                    ),
                )

        QApplication.restoreOverrideCursor()

        # Calculate total time
        total_elapsed = time.time() - self.thumbnail_start_time
        thumbnail_end_datetime = datetime.now()

        logger.info(f"=== Rust thumbnail generation completed ===")
        logger.info(f"End time: {thumbnail_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Total duration: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")

        if success and not self.rust_cancelled:
            # Load the generated thumbnails
            self.load_thumbnail_data_from_disk()

            # Update progress dialog
            self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation complete"))
            self.progress_dialog.lbl_detail.setText(f"Completed in {int(total_elapsed)}s")
        else:
            if self.rust_cancelled:
                self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation cancelled"))
            else:
                self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation failed"))

            # Initialize minimum_volume as empty to prevent errors
            if not hasattr(self, "minimum_volume"):
                self.minimum_volume = []
                logger.warning(
                    "Initialized empty minimum_volume after Rust thumbnail generation failure"
                )

        # Close progress dialog
        self.progress_dialog.close()
        self.progress_dialog = None

        # Initialize combo boxes
        self.initializeComboSize()
        self.reset_crop()

        # Trigger initial display
        if self.comboLevel.count() > 0:
            self.comboLevel.setCurrentIndex(0)
            if not self.initialized:
                self.comboLevelIndexChanged()

    def load_thumbnail_data_from_disk(self):
        """Load generated thumbnail data from disk into minimum_volume for 3D visualization

        Delegates to ThumbnailGenerator.load_thumbnail_data()
        """
        dirname = self.edtDirname.text()

        # Load thumbnail data using ThumbnailGenerator
        minimum_volume, thumbnail_info = self.thumbnail_generator.load_thumbnail_data(dirname)

        if minimum_volume is None:
            logger.warning("No thumbnail data loaded")
            return

        # Update instance state
        self.minimum_volume = minimum_volume
        logger.info(
            f"Loaded {len(self.minimum_volume)} thumbnails, shape: {self.minimum_volume.shape}"
        )

        # Update level_info from thumbnail_info
        self.level_info = []

        # Add level 0 (original images) info if we have settings_hash
        if hasattr(self, "settings_hash"):
            self.level_info.append(
                {
                    "name": "Level 0",
                    "width": int(self.settings_hash.get("image_width", 0)),
                    "height": int(self.settings_hash.get("image_height", 0)),
                    "seq_begin": int(self.settings_hash.get("seq_begin", 0)),
                    "seq_end": int(self.settings_hash.get("seq_end", 0)),
                }
            )

        # Add thumbnail levels from thumbnail_info
        if "levels" in thumbnail_info:
            for level in thumbnail_info["levels"]:
                self.level_info.append(
                    {
                        "name": level["name"],
                        "width": level["width"],
                        "height": level["height"],
                        "seq_begin": level["seq_begin"],
                        "seq_end": level["seq_end"],
                    }
                )

        # Update 3D view with loaded thumbnails
        self._update_3d_view_with_thumbnails()

    def _update_3d_view_with_thumbnails(self):
        """Update 3D view after loading thumbnails"""
        logger.info("Updating 3D view after loading thumbnails")
        bounding_box = self.minimum_volume.shape
        logger.info(f"Bounding box shape: {bounding_box}")

        if len(bounding_box) < 3:
            return

        # Calculate proper bounding box
        scaled_depth = bounding_box[0]
        scaled_height = bounding_box[1]
        scaled_width = bounding_box[2]

        scaled_bounding_box = np.array(
            [0, scaled_depth - 1, 0, scaled_height - 1, 0, scaled_width - 1]
        )

        try:
            _, curr, _ = self.timeline.values()
            denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
            curr_slice_val = curr / denom * scaled_depth
        except Exception:
            curr_slice_val = 0

        logger.info(f"Updating mcube_widget with scaled_bounding_box: {scaled_bounding_box}")

        if not hasattr(self, "mcube_widget"):
            logger.error("mcube_widget not initialized!")
            return

        # Show wait cursor during 3D model generation
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.mcube_widget.update_boxes(scaled_bounding_box, scaled_bounding_box, curr_slice_val)
            self.mcube_widget.adjust_boxes()
            self.mcube_widget.update_volume(self.minimum_volume)
            self.mcube_widget.generate_mesh()
            self.mcube_widget.adjust_volume()
            self.mcube_widget.show_buttons()
            logger.info("3D view update complete")
        finally:
            QApplication.restoreOverrideCursor()

        # Ensure the 3D widget doesn't cover the main image
        self.mcube_widget.setGeometry(QRect(0, 0, 150, 150))
        self.mcube_widget.recalculate_geometry()

    # Keep existing Python implementation as fallback
    def create_thumbnail_python(self):
        """
        Creates thumbnails using Python implementation (fallback when Rust is unavailable).

        This method delegates thumbnail generation to ThumbnailGenerator.generate_python(),
        which handles the actual business logic. The UI responsibilities remain here:
        setting up progress dialog, defining callbacks, and updating UI state.

        Core logic has been moved to: core/thumbnail_generator.py:263-673
        """
        # Calculate total work for progress tracking
        # This must be done before creating the progress dialog
        size = max(int(self.settings_hash["image_width"]), int(self.settings_hash["image_height"]))
        seq_begin = self.settings_hash["seq_begin"]
        seq_end = self.settings_hash["seq_end"]
        MAX_THUMBNAIL_SIZE = 512

        total_work = self.thumbnail_generator.calculate_total_thumbnail_work(
            seq_begin, seq_end, size, MAX_THUMBNAIL_SIZE
        )
        weighted_total_work = self.thumbnail_generator.weighted_total_work

        # Create progress dialog
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.update_language()
        self.progress_dialog.setModal(True)

        # Setup unified progress with calculated work amount
        self.progress_dialog.setup_unified_progress(weighted_total_work, None)
        self.progress_dialog.lbl_text.setText(self.tr("Generating thumbnails"))
        self.progress_dialog.lbl_detail.setText("Estimating...")

        self.progress_dialog.show()

        # Set wait cursor for long operation
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            # Call ThumbnailGenerator with progress dialog
            # Pass the progress dialog directly so ThumbnailManager can connect signals properly
            result = self.thumbnail_generator.generate_python(
                directory=self.edtDirname.text(),
                settings=self.settings_hash,
                threadpool=self.threadpool,
                progress_dialog=self.progress_dialog
            )

            # Restore cursor
            QApplication.restoreOverrideCursor()

            # Handle result
            if result is None:
                logger.error("Thumbnail generation failed - generate_python returned None")
                if self.progress_dialog:
                    self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation failed"))
                    self.progress_dialog.lbl_detail.setText("")
                    self.progress_dialog.close()
                    self.progress_dialog = None
                QMessageBox.critical(
                    self,
                    self.tr("Thumbnail Generation Failed"),
                    self.tr("An unknown error occurred during thumbnail generation.")
                )
                return

            # Handle cancellation
            if result.get('cancelled'):
                logger.info("Thumbnail generation cancelled by user")
                if self.progress_dialog:
                    self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation cancelled"))
                    self.progress_dialog.lbl_detail.setText("")
                    self.progress_dialog.close()
                    self.progress_dialog = None
                QMessageBox.information(
                    self,
                    self.tr("Thumbnail Generation Cancelled"),
                    self.tr("Thumbnail generation was cancelled by user.")
                )
                return

            # Handle generation failure (not cancelled, but success=False)
            if not result.get('success'):
                error_msg = result.get('error', 'Thumbnail generation failed')
                logger.error(f"Thumbnail generation failed: {error_msg}")
                if self.progress_dialog:
                    self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation failed"))
                    self.progress_dialog.lbl_detail.setText("")
                    self.progress_dialog.close()
                    self.progress_dialog = None
                QMessageBox.critical(
                    self,
                    self.tr("Thumbnail Generation Failed"),
                    self.tr("Thumbnail generation failed:\n\n{}").format(error_msg)
                )
                return

            # Update instance state from result (only if successful)
            self.minimum_volume = result.get('minimum_volume', [])
            self.level_info = result.get('level_info', [])

            # Show completion message
            if self.progress_dialog:
                self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation complete"))
                self.progress_dialog.lbl_detail.setText("")

            # Close progress dialog
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None

            # Proceed with UI updates (only if successful)
            # Load thumbnail data from disk (same as Rust does)
            self.load_thumbnail_data_from_disk()

            # If loading from disk failed and minimum_volume is still empty
            if self.minimum_volume is None or (hasattr(self.minimum_volume, '__len__') and len(self.minimum_volume) == 0):
                logger.warning("Failed to load thumbnails from disk after Python generation")

            # Initialize UI components
            self.initializeComboSize()
            self.reset_crop()

            # Trigger initial display by setting combo index if items exist
            if self.comboLevel.count() > 0:
                self.comboLevel.setCurrentIndex(0)
                # If comboLevelIndexChanged doesn't trigger, call it manually
                if not self.initialized:
                    self.comboLevelIndexChanged()

                # Update 3D view after initializing combo level
                self.update_3D_view(False)

        except Exception as e:
            # Handle unexpected errors
            QApplication.restoreOverrideCursor()
            logger.error(f"Unexpected error in create_thumbnail_python: {e}", exc_info=True)

            if self.progress_dialog:
                self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation failed"))
                self.progress_dialog.lbl_detail.setText(str(e))
                self.progress_dialog.close()
                self.progress_dialog = None

    def slider2ValueChanged(self, value):
        """
        Updates the isovalue of the image label and mcube widget based on the given slider value,
        and recalculates the image label's size.

        Args:
            value (float): The new value of the slider.
        """
        # print("value:", value)
        # update external readout to reflect 0-255 range accurately
        if hasattr(self, "threshold_value_label"):
            self.threshold_value_label.setText(str(int(value)))
        self.image_label.set_isovalue(value)
        self.mcube_widget.set_isovalue(value)
        self.image_label.calculate_resize()

    def slider2SliderReleased(self):
        self.update_3D_view(True)

    def sort_file_list_from_dir(self, directory_path):
        """Analyze directory and detect CT image stack pattern

        Delegates to FileHandler.sort_file_list_from_dir()
        """
        return self.file_handler.sort_file_list_from_dir(directory_path)

    def _reset_ui_state(self):
        """Reset all UI state when loading a new directory"""
        logger.info("Resetting bounds, bounding box, and threshold settings")

        # Reset timeline/range slider to full range
        if hasattr(self, "timeline"):
            self.timeline.setLower(self.timeline.minimum())
            self.timeline.setUpper(self.timeline.maximum())

        # Reset bounding box
        self.bounding_box = None
        if hasattr(self, "bounding_box_vertices"):
            self.bounding_box_vertices = None
        if hasattr(self, "bounding_box_edges"):
            self.bounding_box_edges = None

        # Reset ROI box in ObjectViewer2D
        if hasattr(self, "image_label"):
            self.image_label.reset_crop()

        # Reset threshold values if they exist
        if hasattr(self, "lower_threshold"):
            self.lower_threshold = 0
        if hasattr(self, "upper_threshold"):
            self.upper_threshold = 255

        # Reset inversion setting if it exists
        if hasattr(self, "invert_image"):
            self.invert_image = False

        # Clear any existing 3D scene data
        if hasattr(self, "minimum_volume"):
            self.minimum_volume = None
        if hasattr(self, "level_volumes"):
            self.level_volumes = {}

    def open_dir(self):
        """Opens a directory dialog to select a directory containing image files and log files

        Delegates file detection to FileHandler.open_directory()
        """
        logger.info("open_dir method called - START")

        # Show directory selection dialog
        ddir = QFileDialog.getExistingDirectory(
            self, self.tr("Select directory"), self.m_app.default_directory
        )
        if not ddir:
            logger.info("Directory selection cancelled")
            return

        logger.info(f"Selected directory: {ddir}")
        self.edtDirname.setText(ddir)
        self.m_app.default_directory = os.path.dirname(ddir)

        # Reset UI state
        self.settings_hash = {}
        self.initialized = False
        self._reset_ui_state()

        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Use FileHandler to analyze directory
        self.settings_hash = self.file_handler.open_directory(ddir)
        if self.settings_hash is None:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("No valid image files found in the selected directory."),
            )
            logger.warning("No valid image files found")
            return

        logger.info(
            f"Detected image sequence: prefix={self.settings_hash.get('prefix')}, range={self.settings_hash.get('seq_begin')}-{self.settings_hash.get('seq_end')}"
        )

        # Update UI with detected settings
        self.edtNumImages.setText(
            str(self.settings_hash["seq_end"] - self.settings_hash["seq_begin"] + 1)
        )
        self.edtImageDimension.setText(
            f"{self.settings_hash['image_width']} x {self.settings_hash['image_height']}"
        )

        # Build image file list
        image_file_list = self.file_handler.get_file_list(ddir, self.settings_hash)

        self.original_from_idx = 0
        self.original_to_idx = len(image_file_list) - 1

        # Load first image for preview
        self._load_first_image(ddir, image_file_list)

        # Initialize level_info
        self.level_info = []
        self.level_info.append(
            {
                "name": "Original",
                "width": self.settings_hash["image_width"],
                "height": self.settings_hash["image_height"],
                "seq_begin": self.settings_hash["seq_begin"],
                "seq_end": self.settings_hash["seq_end"],
            }
        )

        # Check for existing thumbnail directories
        self._load_existing_thumbnail_levels(ddir)

        QApplication.restoreOverrideCursor()
        logger.info(f"Successfully loaded directory with {len(image_file_list)} images")

        # Generate thumbnails
        self.create_thumbnail()

    def _load_first_image(self, ddir, image_file_list):
        """Load first image from list for preview"""
        if not image_file_list:
            return

        first_image_path = os.path.join(ddir, image_file_list[0])

        # Check if file exists (case-insensitive on Windows)
        actual_path = None
        if os.path.exists(first_image_path):
            actual_path = first_image_path
        else:
            # Try with lowercase extension
            base, ext = os.path.splitext(first_image_path)
            alt_path = base + ext.lower()
            if os.path.exists(alt_path):
                actual_path = alt_path

        if actual_path:
            try:
                pixmap = QPixmap(actual_path)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaledToWidth(512))
                else:
                    logger.error(f"QPixmap is null for {actual_path}")
            except Exception as e:
                logger.error(f"Error loading initial image: {e}")
        else:
            logger.error(f"Image file does not exist: {first_image_path}")

    def _load_existing_thumbnail_levels(self, ddir):
        """Check for existing thumbnail directories and populate level_info"""
        thumbnail_base = os.path.join(ddir, ".thumbnail")
        if not os.path.exists(thumbnail_base):
            return

        logger.info(f"Found existing thumbnail directory: {thumbnail_base}")
        level_idx = 1
        while True:
            level_dir = os.path.join(thumbnail_base, str(level_idx))
            if not os.path.exists(level_dir):
                break

            # Get first image from this level to determine dimensions
            try:
                files = sorted(
                    [
                        f
                        for f in os.listdir(level_dir)
                        if f.endswith("." + self.settings_hash["file_type"])
                    ]
                )
                if files:
                    first_img_path = os.path.join(level_dir, files[0])
                    # Use context manager to ensure image is properly closed
                    with Image.open(first_img_path) as img:
                        width, height = img.size

                    # Calculate sequence range for this level
                    seq_begin = self.settings_hash["seq_begin"]
                    seq_end = seq_begin + len(files) - 1

                    self.level_info.append(
                        {
                            "name": f"Level {level_idx}",
                            "width": width,
                            "height": height,
                            "seq_begin": seq_begin,
                            "seq_end": seq_end,
                        }
                    )
            except Exception as e:
                logger.error(f"Error reading thumbnail level {level_idx}: {e}")
                break

            level_idx += 1

    def read_settings(self):
        """
        Read settings from YAML (delegated to WindowSettingsHandler).

        This method is kept for backward compatibility but delegates to the handler.
        """
        self.settings_handler.read_all_settings()

    def save_settings(self):
        """
        Save settings to YAML (delegated to WindowSettingsHandler).

        This method is kept for backward compatibility but delegates to the handler.
        """
        self.settings_handler.save_all_settings()

    def closeEvent(self, event):
        """
        This method is called when the user closes the application window.
        It saves the current settings and accepts the close event.
        """
        logger.info("Application closing")
        self.save_settings()
        event.accept()


if __name__ == "__main__":
    # logger.info(f"Starting {PROGRAM_NAME} v{PROGRAM_VERSION}")
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon(resource_path("resources/icons/CTHarvester_48_2.png")))

    # Initialize YAML settings manager (no longer using QSettings)
    settings_manager = SettingsManager()

    # Apply saved log level
    saved_log_level = settings_manager.get("logging.level", "INFO")
    try:
        numeric_level = getattr(logging, saved_log_level, logging.INFO)
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            handler.setLevel(numeric_level)
        logger.info(f"Log level set to {saved_log_level} from settings")
    except Exception as e:
        logger.warning(f"Could not set log level from settings: {e}")

    translator = QTranslator(app)
    lang_code = settings_manager.get("application.language", "auto")
    lang_map = {"auto": "en", "en": "en", "ko": "ko"}
    app.language = lang_map.get(lang_code, "en")
    translator.load(resource_path(f"resources/translations/CTHarvester_{app.language}.qm"))
    app.installTranslator(translator)

    # Create instance of CTHarvesterMainWindow
    myWindow = CTHarvesterMainWindow()

    # Show the main window
    myWindow.show()
    # logger.info(f"{PROGRAM_NAME} main window displayed")

    # Enter the event loop (start the application)
    app.exec_()
    # logger.info(f"{PROGRAM_NAME} terminated")

"""
pyinstaller --onefile --noconsole --add-data "*.png;." --add-data "*.qm;." --icon="CTHarvester_48_2.png" CTHarvester.py
pyinstaller --onedir --noconsole --icon="CTHarvester_64.png" --noconfirm CTHarvester.py

pylupdate5 CTHarvester.py -ts CTHarvester_en.ts
pylupdate5 CTHarvester.py -ts CTHarvester_ko.ts
linguist

"""
