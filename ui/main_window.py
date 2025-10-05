"""
CTHarvesterMainWindow - Main application window

Extracted from CTHarvester.py during Phase 4c refactoring.
"""

import logging
import os
import re
import sys
from copy import deepcopy
from typing import Optional

import numpy as np
from PIL import Image
from PyQt5.QtCore import (
    QMargins,
    QObject,
    QPoint,
    QRect,
    Qt,
    QThread,
    QThreadPool,
    QTimer,
    QTranslator,
)
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
from ui.ctharvester_app import CTHarvesterApp
from ui.dialogs import InfoDialog, ProgressDialog, SettingsDialog
from ui.handlers import ExportHandler, WindowSettingsHandler
from ui.setup import MainWindowSetup
from ui.widgets import MCubeWidget, ObjectViewer2D
from ui.widgets.vertical_stack_slider import VerticalTimeline
from utils.common import resource_path, value_to_bool
from utils.image_utils import get_image_dimensions
from utils.settings_manager import SettingsManager
from utils.ui_utils import wait_cursor

logger = logging.getLogger(__name__)


class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.m_app: Optional[CTHarvesterApp] = QApplication.instance()  # type: ignore[assignment]

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

        # Image loading debounce timer
        self._image_load_timer = QTimer()
        self._image_load_timer.setSingleShot(True)
        self._image_load_timer.timeout.connect(self._perform_delayed_image_load)
        self._pending_image_path = None
        self._pending_image_idx = None
        self.default_directory = "."
        self.threadpool = QThreadPool()
        self.progress_dialog: Optional[ProgressDialog] = None  # Progress dialog for long operations
        self.initialized: bool = False  # Track initialization state
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

        # Initialize thumbnail creation handler (Phase 4.2: Thumbnail Creation Separation)
        from ui.handlers.thumbnail_creation_handler import ThumbnailCreationHandler

        self.thumbnail_creation_handler = ThumbnailCreationHandler(self)

        # Initialize directory open handler (Phase 4.3: Directory Opening Separation)
        from ui.handlers.directory_open_handler import DirectoryOpenHandler

        self.directory_open_handler = DirectoryOpenHandler(self)

        # Initialize view manager (Phase 4.4: View Management Separation)
        from ui.handlers.view_manager import ViewManager

        self.view_manager = ViewManager(self)

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
        if not self.m_app:
            logger.warning("Application instance not available for translation")
            return

        translator = QTranslator()
        translator.load(
            resource_path(f"resources/translations/CTHarvester_{self.m_app.language}.qm")
        )
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
        """Update 3D mesh viewer.

        Delegated to ViewManager (Phase 4.4).
        """
        return self.view_manager.update_3d_view(update_volume)

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
        except (AttributeError, ValueError, ZeroDivisionError):
            curr_slice_val = 0

        self.update_3D_view(False)

    def get_cropped_volume(self):
        """Get cropped volume based on current selection

        Uses VolumeProcessor to handle cropping and coordinate transformation.
        """
        if self.minimum_volume is None:
            logger.error("Cannot get cropped volume: minimum_volume is None")
            return None

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

        Uses debouncing to avoid loading every intermediate image when
        dragging the slider rapidly. Loads only after 50ms of no movement.
        """
        if not self.initialized:
            return
        size_idx = self.comboLevel.currentIndex()
        _, curr_image_idx, _ = self.timeline.values()
        if size_idx < 0:
            size_idx = 0

        # Build image path
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

        image_path = os.path.join(dirname, filename)

        # Store pending load and debounce
        self._pending_image_path = image_path
        self._pending_image_idx = curr_image_idx

        # Restart timer (cancels previous pending load)
        self._image_load_timer.stop()
        self._image_load_timer.start(50)  # 50ms debounce

    def _perform_delayed_image_load(self):
        """Actually perform the image load after debounce delay"""
        if self._pending_image_path is None:
            return

        # Load image
        self.image_label.set_image(self._pending_image_path)
        if self._pending_image_idx is not None:
            self.image_label.set_curr_idx(self._pending_image_idx)
        self.update_curr_slice()

        # Clear pending state
        self._pending_image_path = None
        self._pending_image_idx = None

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
        """Create thumbnails using Rust or Python implementation.

        Delegated to ThumbnailCreationHandler (Phase 4.2).
        """
        return self.thumbnail_creation_handler.create_thumbnail()

    def create_thumbnail_rust(self):
        """Create thumbnails using Rust implementation.

        Delegated to ThumbnailCreationHandler (Phase 4.2).
        """
        return self.thumbnail_creation_handler.create_thumbnail_rust()

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
        """Update 3D view after loading thumbnails.

        Delegated to ViewManager (Phase 4.4).
        """
        return self.view_manager.update_3d_view_with_thumbnails()

    def create_thumbnail_python(self):
        """Create thumbnails using Python implementation.

        Delegated to ThumbnailCreationHandler (Phase 4.2).
        """
        return self.thumbnail_creation_handler.create_thumbnail_python()

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
        """Open directory dialog to select CT image stack.

        Delegated to DirectoryOpenHandler (Phase 4.3).
        """
        return self.directory_open_handler.open_directory()

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
                from config.constants import PREVIEW_WIDTH

                pixmap = QPixmap(actual_path)
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaledToWidth(PREVIEW_WIDTH))
                else:
                    error_msg = f"Failed to load preview image: {os.path.basename(actual_path)}"
                    logger.error(f"QPixmap is null for {actual_path}")
                    self._show_preview_error_placeholder(error_msg)
            except OSError as e:
                error_msg = f"Failed to load preview image: {e}"
                logger.error(f"OS error loading initial image: {e}", exc_info=True)
                self._show_preview_error_placeholder(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error loading preview: {e}"
                logger.error(f"Error loading initial image: {e}", exc_info=True)
                self._show_preview_error_placeholder(error_msg)
        else:
            error_msg = f"Image file not found: {os.path.basename(first_image_path)}"
            logger.error(f"Image file does not exist: {first_image_path}")
            self._show_preview_error_placeholder(error_msg)

    def _show_preview_error_placeholder(self, error_message):
        """Show error placeholder in image preview area"""
        from config.constants import PREVIEW_WIDTH

        # Create a simple error placeholder pixmap
        placeholder = QPixmap(PREVIEW_WIDTH, PREVIEW_WIDTH)
        placeholder.fill(Qt.lightGray)

        # Optionally show error message to user (non-blocking)
        logger.warning(f"Preview unavailable: {error_message}")

        # Set placeholder in image label
        self.image_label.setPixmap(placeholder)

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
                    width, height = get_image_dimensions(first_img_path)

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

        # Wait for thread pool to finish (max 5 seconds)
        if self.threadpool.activeThreadCount() > 0:
            logger.info(
                f"Waiting for {self.threadpool.activeThreadCount()} active threads to finish..."
            )
            if not self.threadpool.waitForDone(5000):  # 5 second timeout
                logger.warning("Thread pool did not finish within timeout, forcing close")

        event.accept()


if __name__ == "__main__":
    # This module is imported by CTHarvester.py main() function
    # Direct execution is deprecated - use: python CTHarvester.py
    logger.warning("Direct execution of main_window.py is deprecated")
    logger.warning("Please use: python CTHarvester.py")
    sys.exit(1)

"""
pyinstaller --onefile --noconsole --add-data "*.png;." --add-data "*.qm;." --icon="CTHarvester_48_2.png" CTHarvester.py
pyinstaller --onedir --noconsole --icon="CTHarvester_64.png" --noconfirm CTHarvester.py

pylupdate5 CTHarvester.py -ts CTHarvester_en.ts
pylupdate5 CTHarvester.py -ts CTHarvester_ko.ts
linguist

"""
