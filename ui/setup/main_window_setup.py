"""
MainWindowSetup - UI initialization helper for CTHarvesterMainWindow

Separates UI widget creation and layout setup from business logic.
Extracted from main_window.py __init__ method (Phase 1: UI Separation)
"""

import logging

from PyQt5.QtCore import QMargins, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import MCubeWidget, ObjectViewer2D
from ui.widgets.vertical_stack_slider import VerticalTimeline
from utils.common import resource_path

logger = logging.getLogger(__name__)


class MainWindowSetup:
    """
    UI initialization helper for CTHarvesterMainWindow.

    Separates UI widget creation and layout configuration from business logic,
    making the main window class more focused and maintainable.
    """

    def __init__(self, main_window):
        """
        Initialize setup helper.

        Args:
            main_window (CTHarvesterMainWindow): The main window instance to set up
        """
        self.window = main_window
        self.margin = QMargins(11, 0, 11, 0)

    def setup_all(self):
        """
        Execute all UI setup steps in correct order.

        This is the main entry point that orchestrates the entire UI initialization.
        """
        logger.info("Starting UI setup")

        self.setup_directory_controls()
        self.setup_image_info_controls()
        self.setup_viewer_controls()
        self.setup_threshold_slider()
        self.setup_crop_controls()
        self.setup_status_controls()
        self.setup_action_buttons()
        self.setup_layouts()
        self.setup_text_templates()
        self.setup_3d_viewer()

        logger.info("UI setup completed")

    def setup_directory_controls(self):
        """Create directory selection controls (top section)."""
        self.window.dirname_layout = QHBoxLayout()
        self.window.dirname_widget = QWidget()

        # Open Directory button
        self.window.btnOpenDir = QPushButton(self.window.tr("Open Directory"))
        self.window.btnOpenDir.clicked.connect(self.window.open_dir)

        # Directory path display
        self.window.edtDirname = QLineEdit()
        self.window.edtDirname.setReadOnly(True)
        self.window.edtDirname.setText("")
        self.window.edtDirname.setPlaceholderText(
            self.window.tr("Select directory to load CT data")
        )
        self.window.edtDirname.setMinimumWidth(400)
        self.window.edtDirname.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Rust module checkbox (hidden but functional)
        self.window.cbxUseRust = QCheckBox(self.window.tr("Use Rust"))
        self.window.cbxUseRust.setChecked(True)  # Default to using Rust if available
        self.window.cbxUseRust.setToolTip(
            self.window.tr("Use high-performance Rust module for thumbnail generation")
        )
        self.window.cbxUseRust.setVisible(False)  # Hidden from UI

        # Layout
        self.window.dirname_layout.addWidget(self.window.edtDirname, stretch=1)
        self.window.dirname_layout.addWidget(self.window.btnOpenDir, stretch=0)
        self.window.dirname_widget.setLayout(self.window.dirname_layout)
        self.window.dirname_layout.setContentsMargins(self.margin)

    def setup_image_info_controls(self):
        """Create image information display controls (Level, Size, Count)."""
        self.window.image_info_layout = QHBoxLayout()
        self.window.image_info_widget = QWidget()

        # Level selector
        self.window.lblLevel = QLabel(self.window.tr("Level"))
        self.window.comboLevel = QComboBox()
        self.window.comboLevel.currentIndexChanged.connect(self.window.comboLevelIndexChanged)

        # Image dimension display
        self.window.edtImageDimension = QLineEdit()
        self.window.edtImageDimension.setReadOnly(True)
        self.window.edtImageDimension.setText("")

        # Image count display
        self.window.edtNumImages = QLineEdit()
        self.window.edtNumImages.setReadOnly(True)
        self.window.edtNumImages.setText("")

        # Labels
        self.window.lblSize = QLabel(self.window.tr("Size"))
        self.window.lblCount = QLabel(self.window.tr("Count"))

        # Layout
        self.window.image_info_layout.addWidget(self.window.lblLevel)
        self.window.image_info_layout.addWidget(self.window.comboLevel)
        self.window.image_info_layout.addWidget(self.window.lblSize)
        self.window.image_info_layout.addWidget(self.window.edtImageDimension)
        self.window.image_info_layout.addWidget(self.window.lblCount)
        self.window.image_info_layout.addWidget(self.window.edtNumImages)
        self.window.image_info_widget.setLayout(self.window.image_info_layout)
        self.window.image_info_layout.setContentsMargins(self.margin)

    def setup_viewer_controls(self):
        """Create main image viewer and timeline slider."""
        self.window.image_widget = QWidget()
        self.window.image_layout = QHBoxLayout()

        # 2D Object viewer
        self.window.image_label = ObjectViewer2D(self.window.image_widget)
        self.window.image_label.object_dialog = self.window
        self.window.image_label.setMouseTracking(True)

        # Unified timeline slider (replaces single + range sliders)
        self.window.timeline = VerticalTimeline(0, 0)
        self.window.timeline.setStep(1, 10)
        self.window.timeline.setEnabled(False)  # Disable until data is loaded
        self.window.timeline.currentChanged.connect(self.window.sliderValueChanged)
        self.window.timeline.rangeChanged.connect(self.window.rangeSliderValueChanged)

        # Layout
        self.window.image_layout.addWidget(self.window.image_label, stretch=1)
        self.window.image_layout.addWidget(self.window.timeline)
        self.window.image_widget.setLayout(self.window.image_layout)
        self.window.image_layout.setContentsMargins(self.margin)

    def setup_threshold_slider(self):
        """Create threshold slider with value label."""
        self.window.threshold_slider = QSlider(Qt.Vertical)
        # Ensure full 0-255 range is visible on the labeled slider
        self.window.threshold_slider.setRange(0, 255)
        self.window.threshold_slider.setValue(60)
        self.window.threshold_slider.setSingleStep(1)
        self.window.threshold_slider.valueChanged.connect(self.window.slider2ValueChanged)
        self.window.threshold_slider.sliderReleased.connect(self.window.slider2SliderReleased)

        # External numeric readout to avoid any internal 0-99 label limit
        self.window.threshold_value_label = QLabel(str(self.window.threshold_slider.value()))
        self.window.threshold_value_label.setAlignment(Qt.AlignHCenter)
        self.window.threshold_value_label.setMinimumWidth(30)
        self.window.threshold_value_label.setStyleSheet("QLabel { color: #202020; }")

        # Container with vertical layout
        self.window.threshold_container = QWidget()
        _vl = QVBoxLayout()
        _vl.setContentsMargins(0, 0, 0, 0)
        _vl.setSpacing(4)
        _vl.addWidget(self.window.threshold_slider)
        _vl.addWidget(self.window.threshold_value_label)
        self.window.threshold_container.setLayout(_vl)

        # Add to image layout
        self.window.image_layout.addWidget(self.window.threshold_container)

    def setup_crop_controls(self):
        """Create crop control buttons (Set Bottom, Set Top, Reset, Inverse)."""
        self.window.crop_layout = QHBoxLayout()
        self.window.crop_widget = QWidget()

        # Crop buttons
        self.window.btnSetBottom = QPushButton(self.window.tr("Set Bottom"))
        self.window.btnSetBottom.clicked.connect(self.window.set_bottom)

        self.window.btnSetTop = QPushButton(self.window.tr("Set Top"))
        self.window.btnSetTop.clicked.connect(self.window.set_top)

        self.window.btnReset = QPushButton(self.window.tr("Reset"))
        self.window.btnReset.clicked.connect(self.window.reset_crop)

        # Inverse checkbox
        self.window.cbxInverse = QCheckBox(self.window.tr("Inv."))
        self.window.cbxInverse.stateChanged.connect(self.window.cbxInverse_stateChanged)
        self.window.cbxInverse.setChecked(False)

        # Layout
        self.window.crop_layout.addWidget(self.window.btnSetBottom, stretch=1)
        self.window.crop_layout.addWidget(self.window.btnSetTop, stretch=1)
        self.window.crop_layout.addWidget(self.window.btnReset, stretch=1)
        self.window.crop_layout.addWidget(self.window.cbxInverse, stretch=0)
        self.window.crop_widget.setLayout(self.window.crop_layout)
        self.window.crop_layout.setContentsMargins(self.margin)

    def setup_status_controls(self):
        """Create status display line edit."""
        self.window.status_layout = QHBoxLayout()
        self.window.status_widget = QWidget()

        self.window.edtStatus = QLineEdit()
        self.window.edtStatus.setReadOnly(True)
        self.window.edtStatus.setText("")

        self.window.status_layout.addWidget(self.window.edtStatus)
        self.window.status_widget.setLayout(self.window.status_layout)
        self.window.status_layout.setContentsMargins(self.margin)

    def setup_action_buttons(self):
        """Create action buttons (Save, Export, Preferences, Info)."""
        # Open directory after save checkbox
        self.window.cbxOpenDirAfter = QCheckBox(self.window.tr("Open dir. after"))
        self.window.cbxOpenDirAfter.setChecked(True)

        # Save button
        self.window.btnSave = QPushButton(self.window.tr("Save cropped image stack"))
        self.window.btnSave.clicked.connect(self.window.save_result)

        # Export button
        self.window.btnExport = QPushButton(self.window.tr("Export 3D Model"))
        self.window.btnExport.clicked.connect(self.window.export_3d_model)

        # Preferences button
        self.window.btnPreferences = QPushButton(QIcon(resource_path("M2Preferences_2.png")), "")
        self.window.btnPreferences.clicked.connect(self.window.show_advanced_settings)
        self.window.btnPreferences.setToolTip("Settings (Advanced)")

        # Info button
        self.window.btnInfo = QPushButton(QIcon(resource_path("resources/icons/info.png")), "")
        self.window.btnInfo.clicked.connect(self.window.show_info)

        # Layout
        self.window.button_layout = QHBoxLayout()
        self.window.button_layout.addWidget(self.window.cbxOpenDirAfter, stretch=0)
        self.window.button_layout.addWidget(self.window.btnSave, stretch=1)
        self.window.button_layout.addWidget(self.window.btnExport, stretch=1)
        self.window.button_layout.addWidget(self.window.btnPreferences, stretch=0)
        self.window.button_layout.addWidget(self.window.btnInfo, stretch=0)

        self.window.button_widget = QWidget()
        self.window.button_widget.setLayout(self.window.button_layout)
        self.window.button_layout.setContentsMargins(self.margin)

    def setup_layouts(self):
        """Assemble all sub-layouts into main layout."""
        # Right side vertical layout
        self.window.sub_layout = QVBoxLayout()
        self.window.sub_widget = QWidget()
        self.window.sub_layout.setContentsMargins(0, 0, 0, 0)
        self.window.sub_widget.setLayout(self.window.sub_layout)

        # Add all widgets to right layout
        self.window.sub_layout.addWidget(self.window.dirname_widget)
        self.window.sub_layout.addWidget(self.window.image_info_widget)
        self.window.sub_layout.addWidget(self.window.image_widget)
        self.window.sub_layout.addWidget(self.window.crop_widget)
        self.window.sub_layout.addWidget(self.window.button_widget)
        self.window.sub_layout.addWidget(self.window.status_widget)

        # Main horizontal layout
        self.window.main_layout = QHBoxLayout()
        self.window.main_widget = QWidget()
        self.window.main_widget.setLayout(self.window.main_layout)
        self.window.main_layout.addWidget(self.window.sub_widget)

        # Set as central widget
        self.window.setCentralWidget(self.window.main_widget)

    def setup_text_templates(self):
        """Initialize text templates for status and progress messages."""
        self.window.status_text_format = self.window.tr(
            "Crop indices: {}~{} Cropped image size: {}x{} ({},{})-({},{}) "
            "Estimated stack size: {} MB [{}]"
        )
        self.window.progress_text_1_1 = self.window.tr("Saving image stack...")
        self.window.progress_text_1_2 = self.window.tr("Saving image stack... {}/{}")
        self.window.progress_text_2_1 = self.window.tr("Generating thumbnails (Level {})")
        self.window.progress_text_2_2 = self.window.tr("Generating thumbnails (Level {}) - {}/{}")
        self.window.progress_text_3_1 = self.window.tr("Loading thumbnails (Level {})")
        self.window.progress_text_3_2 = self.window.tr("Loading thumbnails (Level {}) - {}/{}")

    def setup_3d_viewer(self):
        """Initialize 3D mesh viewer widget."""
        self.window.mcube_widget = MCubeWidget(self.window.image_label)
        self.window.mcube_widget.setGeometry(self.window.mcube_geometry)
        self.window.mcube_widget.recalculate_geometry()
        self.window.initialized = False
