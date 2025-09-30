"""
CTHarvesterMainWindow - Main application window

Extracted from CTHarvester.py during Phase 4c refactoring.
"""
import os
import sys
import re
import numpy as np
from copy import deepcopy
import logging
from PIL import Image

from PyQt5.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QApplication,
    QAbstractItemView, QRadioButton, QComboBox, QWidget,
    QHBoxLayout, QVBoxLayout, QProgressBar, QDialog, QLineEdit,
    QLabel, QPushButton, QSizePolicy, QGroupBox, QListWidget,
    QFormLayout, QCheckBox, QSlider
)
from PyQt5.QtCore import (
    Qt, QSettings, QTranslator, QRect, QThreadPool, QPoint,
    QMargins, QTimer, QObject
)
from PyQt5.QtGui import QIcon, QPixmap, QCursor

from config.constants import (
    PROGRAM_NAME, PROGRAM_VERSION, COMPANY_NAME,
    SUPPORTED_IMAGE_EXTENSIONS, THUMBNAIL_DIR_NAME
)
from ui.dialogs import InfoDialog, PreferencesDialog, ProgressDialog
from ui.widgets import MCubeWidget, ObjectViewer2D
from core.thumbnail_manager import ThumbnailManager
from security.file_validator import SecureFileValidator, FileSecurityError, safe_open_image
from vertical_stack_slider import VerticalTimeline
from utils.common import resource_path, value_to_bool


logger = logging.getLogger(__name__)


class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.m_app = QApplication.instance()

        self.setWindowIcon(QIcon(resource_path('CTHarvester_48_2.png')))
        self.setWindowTitle("{} v{}".format(self.tr("CT Harvester"), PROGRAM_VERSION))
        self.setGeometry(QRect(100, 100, 600, 550))
        self.settings_hash = {}
        self.level_info = []
        self.curr_level_idx = 0
        self.prev_level_idx = 0
        self.default_directory = "."
        self.threadpool = QThreadPool()  # Initialize threadpool for multithreading
        logger.info(f"Initialized ThreadPool with maxThreadCount={self.threadpool.maxThreadCount()}")
        self.read_settings()

        margin = QMargins(11,0,11,0)

        # add file open dialog
        self.dirname_layout = QHBoxLayout()
        self.dirname_widget = QWidget()
        self.btnOpenDir = QPushButton(self.tr("Open Directory"))
        self.btnOpenDir.clicked.connect(self.open_dir)
        self.edtDirname = QLineEdit()
        self.edtDirname.setReadOnly(True)
        self.edtDirname.setText("")
        self.edtDirname.setPlaceholderText(self.tr("Select directory to load CT data"))
        self.edtDirname.setMinimumWidth(400)
        self.edtDirname.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Add checkbox for Rust module (hidden but functional)
        self.cbxUseRust = QCheckBox(self.tr("Use Rust"))
        self.cbxUseRust.setChecked(True)  # Default to using Rust if available
        self.cbxUseRust.setToolTip(self.tr("Use high-performance Rust module for thumbnail generation"))
        self.cbxUseRust.setVisible(False)  # Hidden from UI

        self.dirname_layout.addWidget(self.edtDirname,stretch=1)
        # self.dirname_layout.addWidget(self.cbxUseRust,stretch=0)  # Hidden
        self.dirname_layout.addWidget(self.btnOpenDir,stretch=0)
        self.dirname_widget.setLayout(self.dirname_layout)
        self.dirname_layout.setContentsMargins(margin)

        ''' image info layout '''
        self.image_info_layout = QHBoxLayout()
        self.image_info_widget = QWidget()
        self.lblLevel = QLabel(self.tr("Level"))
        self.comboLevel = QComboBox()
        self.comboLevel.currentIndexChanged.connect(self.comboLevelIndexChanged)
        self.edtImageDimension = QLineEdit()
        self.edtImageDimension.setReadOnly(True)
        self.edtImageDimension.setText("")
        self.edtNumImages = QLineEdit()
        self.edtNumImages.setReadOnly(True)
        self.edtNumImages.setText("")
        self.image_info_layout.addWidget(self.lblLevel)
        self.image_info_layout.addWidget(self.comboLevel)
        self.lblSize = QLabel(self.tr("Size"))
        self.lblCount = QLabel(self.tr("Count")) 
        self.image_info_layout.addWidget(self.lblSize)
        self.image_info_layout.addWidget(self.edtImageDimension)
        self.image_info_layout.addWidget(self.lblCount)
        self.image_info_layout.addWidget(self.edtNumImages)
        self.image_info_widget.setLayout(self.image_info_layout)
        #self.image_info_layout2.setSpacing(0)
        self.image_info_layout.setContentsMargins(margin)

        ''' image layout '''
        self.image_widget = QWidget()
        self.image_layout = QHBoxLayout()
        self.image_label = ObjectViewer2D(self.image_widget)
        self.image_label.object_dialog = self
        self.image_label.setMouseTracking(True)
        # Unified timeline slider (replaces single + range sliders)
        self.timeline = VerticalTimeline(0, 0)
        self.timeline.setStep(1, 10)
        self.timeline.setEnabled(False)  # Disable until data is loaded
        self.timeline.currentChanged.connect(self.sliderValueChanged)
        self.timeline.rangeChanged.connect(self.rangeSliderValueChanged)

        self.image_layout.addWidget(self.image_label,stretch=1)
        self.image_layout.addWidget(self.timeline)
        self.image_widget.setLayout(self.image_layout)
        self.image_layout.setContentsMargins(margin)

        self.threshold_slider = QSlider(Qt.Vertical)
        # Ensure full 0-255 range is visible on the labeled slider
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(60)
        self.threshold_slider.setSingleStep(1)
        self.threshold_slider.valueChanged.connect(self.slider2ValueChanged)
        self.threshold_slider.sliderReleased.connect(self.slider2SliderReleased)
        # external numeric readout to avoid any internal 0-99 label limit
        self.threshold_value_label = QLabel(str(self.threshold_slider.value()))
        self.threshold_value_label.setAlignment(Qt.AlignHCenter)
        self.threshold_value_label.setMinimumWidth(30)
        self.threshold_value_label.setStyleSheet("QLabel { color: #202020; }")
        self.threshold_container = QWidget()
        _vl = QVBoxLayout()
        _vl.setContentsMargins(0,0,0,0)
        _vl.setSpacing(4)
        _vl.addWidget(self.threshold_slider)
        _vl.addWidget(self.threshold_value_label)
        self.threshold_container.setLayout(_vl)
        self.image_layout.addWidget(self.threshold_container)

        ''' crop layout '''
        self.crop_layout = QHBoxLayout()
        self.crop_widget = QWidget()
        self.btnSetBottom = QPushButton(self.tr("Set Bottom"))
        self.btnSetBottom.clicked.connect(self.set_bottom)
        self.btnSetTop = QPushButton(self.tr("Set Top"))
        self.btnSetTop.clicked.connect(self.set_top)
        self.btnReset = QPushButton(self.tr("Reset"))
        self.btnReset.clicked.connect(self.reset_crop)
        self.cbxInverse = QCheckBox(self.tr("Inv."))
        self.cbxInverse.stateChanged.connect(self.cbxInverse_stateChanged)
        self.cbxInverse.setChecked(False)

        self.crop_layout.addWidget(self.btnSetBottom,stretch=1)
        self.crop_layout.addWidget(self.btnSetTop,stretch=1)
        self.crop_layout.addWidget(self.btnReset,stretch=1)
        self.crop_layout.addWidget(self.cbxInverse,stretch=0)
        self.crop_widget.setLayout(self.crop_layout)
        self.crop_layout.setContentsMargins(margin)

        ''' status layout '''
        self.status_layout = QHBoxLayout()
        self.status_widget = QWidget()
        self.edtStatus = QLineEdit()
        self.edtStatus.setReadOnly(True)
        self.edtStatus.setText("")
        self.status_layout.addWidget(self.edtStatus)
        self.status_widget.setLayout(self.status_layout)
        #self.status_layout.setSpacing(0)
        self.status_layout.setContentsMargins(margin)

        ''' button layout '''
        self.cbxOpenDirAfter = QCheckBox(self.tr("Open dir. after"))
        self.cbxOpenDirAfter.setChecked(True)
        self.btnSave = QPushButton(self.tr("Save cropped image stack"))
        self.btnSave.clicked.connect(self.save_result)
        self.btnExport = QPushButton(self.tr("Export 3D Model"))
        self.btnExport.clicked.connect(self.export_3d_model)
        self.btnPreferences = QPushButton(QIcon(resource_path('M2Preferences_2.png')), "")
        self.btnPreferences.clicked.connect(self.show_preferences)
        self.btnInfo = QPushButton(QIcon(resource_path('info.png')), "")
        self.btnInfo.clicked.connect(self.show_info)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cbxOpenDirAfter,stretch=0)
        self.button_layout.addWidget(self.btnSave,stretch=1)
        self.button_layout.addWidget(self.btnExport,stretch=1)
        self.button_layout.addWidget(self.btnPreferences,stretch=0)
        self.button_layout.addWidget(self.btnInfo,stretch=0)
        self.button_widget = QWidget()
        self.button_widget.setLayout(self.button_layout)
        self.button_layout.setContentsMargins(margin)

        ''' layouts put together '''
        self.sub_layout = QVBoxLayout()
        self.sub_widget = QWidget()
        #self.right_layout.setSpacing(0)
        self.sub_layout.setContentsMargins(0,0,0,0)
        self.sub_widget.setLayout(self.sub_layout)
        #self.right_layout.addWidget(self.comboSize)
        self.sub_layout.addWidget(self.dirname_widget)
        self.sub_layout.addWidget(self.image_info_widget)
        self.sub_layout.addWidget(self.image_widget)
        self.sub_layout.addWidget(self.crop_widget)
        self.sub_layout.addWidget(self.button_widget)
        self.sub_layout.addWidget(self.status_widget)
        #self.right_layout.addWidget(self.btnSave)

        self.main_layout = QHBoxLayout()
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)
        self.main_layout.addWidget(self.sub_widget)


        ''' setting up texts'''
        self.status_text_format = self.tr("Crop indices: {}~{} Cropped image size: {}x{} ({},{})-({},{}) Estimated stack size: {} MB [{}]")
        self.progress_text_1_1 = self.tr("Saving image stack...")
        self.progress_text_1_2 = self.tr("Saving image stack... {}/{}")
        self.progress_text_2_1 = self.tr("Generating thumbnails (Level {})")
        self.progress_text_2_2 = self.tr("Generating thumbnails (Level {}) - {}/{}")
        self.progress_text_3_1 = self.tr("Loading thumbnails (Level {})")
        self.progress_text_3_2 = self.tr("Loading thumbnails (Level {}) - {}/{}")

        self.setCentralWidget(self.main_widget)

        ''' initialize mcube_widget '''
        self.mcube_widget = MCubeWidget(self.image_label)
        self.mcube_widget.setGeometry(self.mcube_geometry)
        self.mcube_widget.recalculate_geometry()
        #self.mcube_geometry
        self.initialized = False

    def rangeSliderMoved(self):
        return
    
    def rangeSliderPressed(self):
        return

    def cbxInverse_stateChanged(self):
        if self.image_label.orig_pixmap is None:
            return
        self.mcube_widget.is_inverse = self.image_label.is_inverse = self.cbxInverse.isChecked()
        #self.mcube_widget.is_inverse = 
        self.image_label.calculate_resize()
        self.image_label.repaint()
        self.update_3D_view(True)

    def show_preferences(self):
        self.settings_dialog = PreferencesDialog(self)
        self.settings_dialog.setModal(True)
        self.settings_dialog.show()

    def show_info(self):
        self.info_dialog = InfoDialog(self)
        self.info_dialog.setModal(True)
        self.info_dialog.show()

    def update_language(self):
        translator = QTranslator()
        translator.load('CTHarvester_{}.qm'.format(self.m_app.language))
        self.m_app.installTranslator(translator)

        self.setWindowTitle("{} v{}".format(self.tr(PROGRAM_NAME), PROGRAM_VERSION))
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
        self.status_text_format = self.tr("Crop indices: {}~{} Cropped image size: {}x{} ({},{})-({},{}) Estimated stack size: {} MB [{}]")
        self.progress_text_1_2 = self.tr("Saving image stack... {}/{}")
        self.progress_text_1_1 = self.tr("Saving image stack...")
        self.progress_text_2_1 = self.tr("Generating thumbnails (Level {})")
        self.progress_text_2_2 = self.tr("Generating thumbnails (Level {}) - {}/{}")
        self.progress_text_3_1 = self.tr("Loading thumbnails (Level {})")
        self.progress_text_3_2 = self.tr("Loading thumbnails (Level {}) - {}/{}")

    def set_bottom(self):
        # set lower bound to current index
        _, curr, _ = self.timeline.values()
        self.timeline.setLower(curr)
        self.update_status()
    def set_top(self):
        # set upper bound to current index
        _, curr, _ = self.timeline.values()
        self.timeline.setUpper(curr)
        self.update_status()

    #def resizeEvent(self, a0: QResizeEvent) -> None:
    #    #print("resizeEvent")
    #    return super().resizeEvent(a0)

    def update_3D_view_click(self):
        self.update_3D_view(True)

    def update_3D_view(self, update_volume=True):
        #print("update 3d view")
        volume, roi_box = self.get_cropped_volume()
        
        # Check if volume is empty
        if volume.size == 0:
            logger.warning("Empty volume in update_3D_view, skipping update")
            return
            
        # Calculate bounding box based on current level
        # The minimum_volume is always the smallest level, but we need to scale it
        # based on the current viewing level
        if hasattr(self, 'level_info') and self.level_info:
            smallest_level_idx = len(self.level_info) - 1
            level_diff = smallest_level_idx - self.curr_level_idx
            scale_factor = 2 ** level_diff  # Each level is 2x the size of the next
        else:
            # Default to no scaling if level_info is not available
            scale_factor = 1
        
        # Get the base dimensions from minimum_volume
        base_shape = self.minimum_volume.shape
        
        # Scale the dimensions according to current level
        scaled_depth = base_shape[0] * scale_factor
        scaled_height = base_shape[1] * scale_factor
        scaled_width = base_shape[2] * scale_factor
        
        bounding_box = [0, scaled_depth-1, 0, scaled_height-1, 0, scaled_width-1]
        
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
        # Check if minimum_volume is initialized
        if not hasattr(self, 'minimum_volume') or self.minimum_volume is None or len(self.minimum_volume) == 0:
            logger.warning("minimum_volume not initialized in update_curr_slice")
            return
            
        # Calculate bounding box based on current level
        if hasattr(self, 'level_info') and self.level_info:
            smallest_level_idx = len(self.level_info) - 1
            level_diff = smallest_level_idx - self.curr_level_idx
            scale_factor = 2 ** level_diff
        else:
            scale_factor = 1
        
        # Get the base dimensions from minimum_volume
        base_shape = self.minimum_volume.shape
        
        # Scale the dimensions according to current level
        scaled_depth = base_shape[0] * scale_factor
        scaled_height = base_shape[1] * scale_factor
        scaled_width = base_shape[2] * scale_factor
        
        bounding_box = [0, scaled_depth-1, 0, scaled_height-1, 0, scaled_width-1]
        try:
            _, curr, _ = self.timeline.values()
            denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
            curr_slice_val = curr / denom * scaled_depth
        except Exception:
            curr_slice_val = 0
        
        self.update_3D_view(False)

    def get_cropped_volume(self):
        # Check if level_info is initialized and curr_level_idx is valid
        if not hasattr(self, 'level_info') or not self.level_info:
            logger.warning("level_info not initialized in get_cropped_volume")
            # Return empty volume and box
            return np.array([]), [0, 0, 0, 0, 0, 0]
        
        if not hasattr(self, 'curr_level_idx'):
            self.curr_level_idx = 0
        
        # Ensure curr_level_idx is within bounds
        if self.curr_level_idx >= len(self.level_info):
            logger.warning(f"curr_level_idx {self.curr_level_idx} out of bounds, resetting to 0")
            self.curr_level_idx = 0
        
        level_info = self.level_info[self.curr_level_idx]
        seq_begin = level_info['seq_begin']
        seq_end = level_info['seq_end']
        image_count = seq_end - seq_begin + 1

        # get current size
        curr_width = level_info['width']
        curr_height = level_info['height']

        # get top and bottom idx; default to full range if not set
        top_idx = self.image_label.top_idx
        bottom_idx = self.image_label.bottom_idx
        if top_idx < 0 or bottom_idx < 0 or bottom_idx > top_idx:
            bottom_idx = 0
            top_idx = image_count - 1

        #get current crop box
        crop_box = self.image_label.get_crop_area(imgxy=True)

        # get cropbox coordinates when image width and height is 1
        from_x = crop_box[0] / float(curr_width)
        from_y = crop_box[1] / float(curr_height)
        to_x = crop_box[2] / float(curr_width)
        to_y = crop_box[3] / float(curr_height)

        # get top idx and bottom idx when image count is 1
        top_idx = top_idx / float(image_count)
        bottom_idx = bottom_idx / float(image_count)

        # get cropped volume for smallest size
        smallest_level_info = self.level_info[-1]

        smallest_count = smallest_level_info['seq_end'] - smallest_level_info['seq_begin'] + 1
        bottom_idx = int(bottom_idx * smallest_count)
        top_idx = int(top_idx * smallest_count)
        # clamp
        bottom_idx = max(0, min(bottom_idx, smallest_count-1))
        top_idx = max(0, min(top_idx, smallest_count))
        if top_idx <= bottom_idx:
            top_idx = min(bottom_idx+1, smallest_count)
        from_x = int(from_x * smallest_level_info['width'])
        from_y = int(from_y * smallest_level_info['height'])
        to_x = int(to_x * smallest_level_info['width'])-1
        to_y = int(to_y * smallest_level_info['height'])-1

        # Ensure minimum_volume is a numpy array
        if isinstance(self.minimum_volume, list):
            if len(self.minimum_volume) > 0:
                self.minimum_volume = np.array(self.minimum_volume)
            else:
                logger.error("minimum_volume is empty list")
                return np.array([]), []
        
        volume = self.minimum_volume[bottom_idx:top_idx, from_y:to_y, from_x:to_x]
        
        # Scale ROI box to current level coordinates
        # The ROI is currently in smallest level coordinates, need to scale to current level
        smallest_level_idx = len(self.level_info) - 1
        level_diff = smallest_level_idx - self.curr_level_idx
        scale_factor = 2 ** level_diff
        
        # Scale the ROI coordinates
        scaled_roi = [
            bottom_idx * scale_factor,
            top_idx * scale_factor,
            from_y * scale_factor,
            to_y * scale_factor,
            from_x * scale_factor,
            to_x * scale_factor
        ]
        
        return volume, scaled_roi

    def export_3d_model(self):
        # open dir dialog for save
        #logger.info("export_3d_model method called")
        threed_volume = []

        obj_filename, _ = QFileDialog.getSaveFileName(self, "Save File As", self.edtDirname.text(), "OBJ format (*.obj)")
        if obj_filename == "":
            logger.info("Export cancelled")
            return
        logger.info(f"Exporting 3D model to: {obj_filename}")

        try:
            threed_volume, _ = self.get_cropped_volume()
            isovalue = self.image_label.isovalue
            vertices, triangles = mcubes.marching_cubes(threed_volume, isovalue)

            for i in range(len(vertices)):
                vertices[i] = np.array([vertices[i][2],vertices[i][0],vertices[i][1]])
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to generate 3D mesh: {e}"))
            return


        # write as obj file format
        try:
            with open(obj_filename, 'w') as fh:
                for v in vertices:
                    fh.write('v {} {} {}\n'.format(v[0], v[1], v[2]))
                #for vn in vertex_normals:
                #    fh.write('vn {} {} {}\n'.format(vn[0], vn[1], vn[2]))
                #for f in triangles:
                #    fh.write('f {}/{} {}/{} {}/{}\n'.format(f[0]+1, f[0]+1, f[1]+1, f[1]+1, f[2]+1, f[2]+1))
                for f in triangles:
                    fh.write('f {} {} {}\n'.format(f[0]+1, f[1]+1, f[2]+1))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to save OBJ file: {e}"))
            logger.error(f"Error saving OBJ file: {e}")

    def save_result(self):
        # open dir dialog for save
        #logger.info("save_result method called")
        target_dirname = QFileDialog.getExistingDirectory(self, self.tr('Select directory to save'), self.edtDirname.text())
        if target_dirname == "":
            logger.info("Save cancelled")
            return
        #logger.info(f"Saving results to: {target_dirname}")
        # get crop box info
        from_x = self.image_label.crop_from_x
        from_y = self.image_label.crop_from_y
        to_x = self.image_label.crop_to_x
        to_y = self.image_label.crop_to_y
        # get size idx
        size_idx = self.comboLevel.currentIndex()
        # get filename from level from idx
        top_idx = self.image_label.top_idx
        bottom_idx = self.image_label.bottom_idx

        current_count = 0
        total_count = top_idx - bottom_idx + 1
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.update_language()
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        self.progress_dialog.lbl_text.setText(self.progress_text_1_1)
        self.progress_dialog.pb_progress.setValue(0)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        for i, idx in enumerate(range(bottom_idx, top_idx+1)):
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + idx).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
            # get full path
            if size_idx == 0:
                orig_dirname = self.edtDirname.text()
            else:
                orig_dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            fullpath = os.path.join(orig_dirname, filename)
            # open image
            try:
                img = Image.open(fullpath)
            except Exception as e:
                logger.error(f"Error opening image {fullpath}: {e}")
                continue
            # crop image
            if from_x > -1:
                img = img.crop((from_x, from_y, to_x, to_y))
            # save image
            img.save(os.path.join(target_dirname, filename))

            self.progress_dialog.lbl_text.setText(self.progress_text_1_2.format(i+1, int(total_count)))
            self.progress_dialog.pb_progress.setValue(int(((i+1)/float(int(total_count)))*100))
            self.progress_dialog.update()
            QApplication.processEvents()

        QApplication.restoreOverrideCursor()
        self.progress_dialog.close()
        self.progress_dialog = None
        if self.cbxOpenDirAfter.isChecked():
            os.startfile(target_dirname)

    def rangeSliderValueChanged(self):
        #print("range slider value changed")
        try:
            # Check if necessary attributes are initialized
            if not hasattr(self, 'level_info') or not self.level_info:
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
        #print("range slider released")
        return


    def sliderValueChanged(self):
        if not self.initialized:
            return
        size_idx = self.comboLevel.currentIndex()
        _, curr_image_idx, _ = self.timeline.values()
        if size_idx < 0:
            size_idx = 0

        # get directory for size idx
        if size_idx == 0:
            dirname = self.edtDirname.text()
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + curr_image_idx).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
        else:
            dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            # Match Rust naming: simple sequential numbering without prefix
            filename = "{:06}.tif".format(curr_image_idx)

        self.image_label.set_image(os.path.join(dirname, filename))
        self.image_label.set_curr_idx(curr_image_idx)
        self.update_curr_slice()

    def reset_crop(self):
        _, curr, _ = self.timeline.values()
        self.image_label.set_curr_idx(curr)
        self.image_label.reset_crop()
        self.timeline.setLower(self.timeline.minimum())
        self.timeline.setUpper(self.timeline.maximum())
        self.canvas_box = None
        self.update_status()

    def update_status(self):
        lo, _, hi = self.timeline.values()
        bottom_idx, top_idx = lo, hi
        [ x1, y1, x2, y2 ] = self.image_label.get_crop_area(imgxy=True)
        count = ( top_idx - bottom_idx + 1 )
        #self.status_format = self.tr("Crop indices: {}~{}    Cropped image size: {}x{}    Estimated stack size: {} MB [{}]")
        status_text = self.status_text_format.format(bottom_idx, top_idx, x2 - x1, y2 - y1, x1, y1, x2, y2, round(count * (x2 - x1 ) * (y2 - y1 ) / 1024 / 1024 , 2), str(self.image_label.edit_mode))
        self.edtStatus.setText(status_text)

    def initializeComboSize(self):
        #logger.info(f"initializeComboSize called, level_info count: {len(self.level_info) if hasattr(self, 'level_info') else 'not set'}")
        self.comboLevel.clear()
        for level in self.level_info:
            self.comboLevel.addItem( level['name'])
            #logger.info(f"Added level: {level['name']}, size: {level['width']}x{level['height']}, seq: {level['seq_begin']}-{level['seq_end']}")

    def comboLevelIndexChanged(self):
        """
        This method is called when the user selects a different level from the combo box.
        It updates the UI with information about the selected level, such as the image dimensions and number of images.
        It also updates the slider and range slider to reflect the number of images in the selected level.
        """
        # Check if level_info is initialized
        if not hasattr(self, 'level_info') or not self.level_info:
            logger.warning("level_info not initialized in comboLevelIndexChanged")
            return
        
        self.prev_level_idx = self.curr_level_idx if hasattr(self, 'curr_level_idx') else 0
        self.curr_level_idx = self.comboLevel.currentIndex()
        
        # Validate curr_level_idx
        if self.curr_level_idx < 0 or self.curr_level_idx >= len(self.level_info):
            logger.warning(f"Invalid curr_level_idx: {self.curr_level_idx}, resetting to 0")
            self.curr_level_idx = 0
            return
        
        level_info = self.level_info[self.curr_level_idx]
        seq_begin = level_info['seq_begin']
        seq_end = level_info['seq_end']

        self.edtImageDimension.setText(str(level_info['width']) + " x " + str(level_info['height']))
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
        curr_idx = int(curr_idx * (2 ** level_diff))

        lo, _, hi = self.timeline.values()
        bottom_idx = int(lo * (2 ** level_diff))
        top_idx = int(hi * (2 ** level_diff))

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
        """Calculate total number of operations for all LoD levels with size weighting"""
        import logging
        logger = logging.getLogger('CTHarvester')

        total_work = 0
        weighted_work = 0  # Work weighted by image size
        temp_seq_begin = seq_begin
        temp_seq_end = seq_end
        temp_size = size
        level_count = 0
        level_details = []
        self.level_sizes = []  # Store size info for each level
        self.level_work_distribution = []  # Store work distribution per level

        while temp_size >= max_size:
            temp_size /= 2
            level_count += 1
            # Each level processes half the images from previous level
            images_to_process = (temp_seq_end - temp_seq_begin + 1) // 2 + 1
            total_work += images_to_process

            # Weight by relative image size (smaller images process faster)
            size_factor = (temp_size / size) ** 2  # Quadratic because it's 2D

            # Additional weight for first level due to reading original images from disk
            if level_count == 1:
                size_factor *= 1.5  # First level is 50% slower due to I/O overhead

            weighted_work += images_to_process * size_factor

            level_details.append(f"Level {level_count}: {images_to_process} images, size={int(temp_size)}px, weight={size_factor:.2f}")
            self.level_sizes.append((level_count, temp_size, images_to_process))
            self.level_work_distribution.append({
                'level': level_count,
                'images': images_to_process,
                'size': int(temp_size),
                'weight': size_factor
            })
            temp_seq_end = int((temp_seq_end - temp_seq_begin) / 2) + temp_seq_begin

        # Store total level count for better estimation
        self.total_levels = level_count

        logger.info(f"Thumbnail generation will create {level_count} levels")
        logger.info(f"Total operations: {total_work}, Weighted work: {weighted_work:.1f}")
        for detail in level_details:
            logger.info(f"  {detail}")

        # Return both for compatibility, store weighted for internal use
        self.weighted_total_work = weighted_work
        return total_work
    
    def create_thumbnail(self):
        """
        Creates a thumbnail using Rust module if available and enabled, otherwise falls back to Python implementation.
        """
        import time
        from datetime import datetime

        # Check if user wants to use Rust module
        use_rust_preference = self.cbxUseRust.isChecked() if hasattr(self, 'cbxUseRust') else True

        # Try to use Rust module if preferred
        if use_rust_preference:
            try:
                from ct_thumbnail import build_thumbnails
                use_rust = True
                logger.info("Using Rust-based thumbnail generation")
            except ImportError:
                use_rust = False
                logger.warning("ct_thumbnail module not found, falling back to Python implementation")
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
                elapsed_str = f"{int(elapsed)}s" if elapsed < 60 else f"{int(elapsed/60)}m {int(elapsed%60)}s"

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
            prefix = self.settings_hash.get('prefix', '')
            file_type = self.settings_hash.get('file_type', 'tif')
            seq_begin = int(self.settings_hash.get('seq_begin', 0))
            seq_end = int(self.settings_hash.get('seq_end', 0))
            index_length = int(self.settings_hash.get('index_length', 0))

            # Call Rust with pattern parameters
            result = build_thumbnails(
                dirname,
                progress_callback,
                prefix,
                file_type,
                seq_begin,
                seq_end,
                index_length
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
                QMessageBox.warning(self, self.tr("Warning"),
                                   self.tr(f"Rust thumbnail generation failed: {e}\nFalling back to Python implementation."))

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
            if not hasattr(self, 'minimum_volume'):
                self.minimum_volume = []
                logger.warning("Initialized empty minimum_volume after Rust thumbnail generation failure")

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
        This is used by both Rust and Python thumbnail generation"""

        MAX_THUMBNAIL_SIZE = 512  # Must match Python's MAX_THUMBNAIL_SIZE

        # Find the highest level thumbnail directory
        thumbnail_base = os.path.join(self.edtDirname.text(), ".thumbnail")

        if not os.path.exists(thumbnail_base):
            logger.warning("No thumbnail directory found")
            return

        # Find all level directories
        level_dirs = []
        for i in range(1, 20):  # Check up to level 20
            level_dir = os.path.join(thumbnail_base, str(i))
            if os.path.exists(level_dir):
                level_dirs.append((i, level_dir))
            else:
                break

        if not level_dirs:
            logger.warning("No thumbnail levels found")
            return

        # Find the appropriate level to load (first level with size < MAX_THUMBNAIL_SIZE)
        level_num = None
        thumbnail_dir = None

        for ln, ld in level_dirs:
            # Check the size of images in this level
            files = [f for f in os.listdir(ld) if f.endswith('.tif')]
            if files:
                img = Image.open(os.path.join(ld, files[0]))
                width, height = img.size
                img.close()

                size = max(width, height)
                if size < MAX_THUMBNAIL_SIZE:
                    level_num = ln
                    thumbnail_dir = ld
                    logger.info(f"Found appropriate level {level_num} with size {width}x{height} (< {MAX_THUMBNAIL_SIZE})")
                    break
                else:
                    logger.debug(f"Level {ln} size {width}x{height} is >= {MAX_THUMBNAIL_SIZE}, continuing...")

        if level_num is None or thumbnail_dir is None:
            # Fallback to highest level if none meet the criteria
            level_num, thumbnail_dir = level_dirs[-1]
            logger.warning(f"No level with size < {MAX_THUMBNAIL_SIZE} found, using highest level {level_num}")

        logger.info(f"Loading thumbnails from level {level_num}: {thumbnail_dir}")

        try:
            # List all tif files in the directory
            files = sorted([f for f in os.listdir(thumbnail_dir) if f.endswith('.tif')])

            logger.info(f"Found {len(files)} thumbnail files")

            self.minimum_volume = []
            for file in files:
                filepath = os.path.join(thumbnail_dir, file)
                img = Image.open(filepath)
                img_array = np.array(img)

                # Normalize to 8-bit range (0-255) for marching cubes
                # Check if image is 16-bit
                if img_array.dtype == np.uint16:
                    # Convert 16-bit to 8-bit
                    img_array = (img_array / 256).astype(np.uint8)
                elif img_array.dtype != np.uint8:
                    # For other types, normalize to 0-255
                    img_min = img_array.min()
                    img_max = img_array.max()
                    if img_max > img_min:
                        img_array = ((img_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
                    else:
                        img_array = np.zeros_like(img_array, dtype=np.uint8)

                self.minimum_volume.append(img_array)
                img.close()

            if len(self.minimum_volume) > 0:
                self.minimum_volume = np.array(self.minimum_volume)
                logger.info(f"Loaded {len(self.minimum_volume)} thumbnails, shape: {self.minimum_volume.shape}")

                # Update level_info to match what Python implementation expects
                self.level_info = []

                # Add level 0 (original images) info if we have settings_hash
                if hasattr(self, 'settings_hash'):
                    self.level_info.append({
                        'name': 'Level 0',
                        'width': int(self.settings_hash.get('image_width', 0)),
                        'height': int(self.settings_hash.get('image_height', 0)),
                        'seq_begin': int(self.settings_hash.get('seq_begin', 0)),
                        'seq_end': int(self.settings_hash.get('seq_end', 0))
                    })

                # Add thumbnail levels
                for i, (level_num, level_dir) in enumerate(level_dirs):
                    # Get dimensions from first file in level
                    files = [f for f in os.listdir(level_dir) if f.endswith('.tif')]
                    if files:
                        img = Image.open(os.path.join(level_dir, files[0]))
                        width, height = img.size
                        img.close()

                        self.level_info.append({
                            'name': f"Level {level_num}",
                            'width': width,
                            'height': height,
                            'seq_begin': 0,
                            'seq_end': len(files) - 1
                        })

                # Update 3D view with loaded thumbnails
                logger.info("Updating 3D view after loading thumbnails")
                bounding_box = self.minimum_volume.shape
                logger.info(f"Bounding box shape: {bounding_box}")
                if len(bounding_box) >= 3:
                    # Calculate proper bounding box
                    scaled_depth = bounding_box[0]
                    scaled_height = bounding_box[1]
                    scaled_width = bounding_box[2]

                    scaled_bounding_box = np.array([0, scaled_depth-1, 0, scaled_height-1, 0, scaled_width-1])

                    try:
                        _, curr, _ = self.timeline.values()
                        denom = float(self.timeline.maximum()) if self.timeline.maximum() > 0 else 1.0
                        curr_slice_val = curr / denom * scaled_depth
                    except Exception:
                        curr_slice_val = 0

                    logger.info(f"Updating mcube_widget with scaled_bounding_box: {scaled_bounding_box}")

                    if not hasattr(self, 'mcube_widget'):
                        logger.error("mcube_widget not initialized!")
                        return

                    self.mcube_widget.update_boxes(scaled_bounding_box, scaled_bounding_box, curr_slice_val)
                    self.mcube_widget.adjust_boxes()
                    self.mcube_widget.update_volume(self.minimum_volume)
                    self.mcube_widget.generate_mesh()
                    self.mcube_widget.adjust_volume()
                    self.mcube_widget.show_buttons()
                    logger.info("3D view update complete")

                    # Ensure the 3D widget doesn't cover the main image
                    self.mcube_widget.setGeometry(QRect(0, 0, 150, 150))
                    self.mcube_widget.recalculate_geometry()

        except Exception as e:
            logger.error(f"Error loading thumbnails and updating 3D view: {e}", exc_info=True)

    # Keep existing Python implementation as fallback
    def create_thumbnail_python(self):
        #logger.info("Starting thumbnail creation")
        """
        Creates a thumbnail of the image sequence by downsampling the images and averaging them.
        The resulting thumbnail is saved in a temporary directory and used to generate a mesh for visualization.
        This is the original Python implementation kept as fallback.
        """
        import time
        from datetime import datetime

        # Start timing for entire thumbnail generation
        self.thumbnail_start_time = time.time()  # Store as instance variable for access in ThumbnailManager
        thumbnail_start_time = self.thumbnail_start_time  # Keep local variable for backward compatibility
        thumbnail_start_datetime = datetime.now()

        # Log system information
        import platform
        try:
            import psutil 
            has_psutil = True
        except ImportError:
            has_psutil = False
            logger.warning("psutil not installed - cannot get detailed system info")

        MAX_THUMBNAIL_SIZE = 512
        size =  max(int(self.settings_hash['image_width']), int(self.settings_hash['image_height']))
        width = int(self.settings_hash['image_width'])
        height = int(self.settings_hash['image_height'])

        logger.info(f"=== Starting Python thumbnail generation (fallback) ===")
        logger.info(f"Thread configuration: maxThreadCount={self.threadpool.maxThreadCount()}")
        logger.info(f"Start time: {thumbnail_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Image dimensions: width={width}, height={height}, size={size}")

        # System information
        try:
            cpu_count = os.cpu_count()
            logger.info(f"System: {platform.system()} {platform.release()}")
            logger.info(f"CPU cores: {cpu_count}")
            if has_psutil:
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage(self.edtDirname.text())
                logger.info(f"Memory: {mem.total/1024**3:.1f}GB total, {mem.available/1024**3:.1f}GB available ({mem.percent:.1f}% used)")
                logger.info(f"Disk: {disk.total/1024**3:.1f}GB total, {disk.free/1024**3:.1f}GB free ({disk.percent:.1f}% used)")
            logger.info(f"Thread pool: max={self.threadpool.maxThreadCount()}, active={self.threadpool.activeThreadCount()}")
        except Exception as e:
            logger.warning(f"Could not get system info: {e}")

        i = 0
        # create temporary directory for thumbnail
        dirname = self.edtDirname.text()
        logger.info(f"Working directory: {dirname}")

        # Check if directory is on network drive (common cause of slowness)
        try:
            drive = os.path.splitdrive(dirname)[0]
            if drive and drive.startswith('\\\\'):
                logger.warning(f"Working on network drive: {drive} - this may cause slow performance")
            elif drive:
                logger.info(f"Working on local drive: {drive}")
        except Exception as e:
            logger.debug(f"Could not determine drive type: {e}")

        self.minimum_volume = []
        seq_begin = self.settings_hash['seq_begin']
        seq_end = self.settings_hash['seq_end']
        logger.info(f"Processing sequence: {seq_begin} to {seq_end}, directory: {dirname}")
        
        # Calculate total work amount for all LoD levels
        total_work = self.calculate_total_thumbnail_work(seq_begin, seq_end, size, MAX_THUMBNAIL_SIZE)

        # Don't show initial estimate - will show "Estimating..." instead
        estimated_seconds = None  # Will be calculated after sampling
        time_estimate = "Estimating..."  # Show this initially

        # Store initial estimates for comparison at the end
        self.initial_estimate_seconds = 0  # No initial estimate since we're using sampling
        self.initial_estimate_str = time_estimate
        self.sampled_estimate_seconds = None  # Will be updated after sampling
        self.sampled_estimate_str = None

        logger.info(f"Starting thumbnail generation: {self.total_levels} levels, {total_work} operations")
        logger.info(f"Initial estimate: {time_estimate} (will be refined after sampling)")

        current_count = 0
        global_step_counter = 0  # Track overall progress

        # Variables for dynamic time estimation
        # For 3-stage sampling, we need at least 3x the base sample size
        base_sample = max(20, min(30, int(total_work * 0.02)))  # Base: 20-30 images
        self.sample_size = base_sample  # This is the base unit for each stage
        total_sample = base_sample * 3  # Total samples across all stages
        logger.info(f"Multi-stage sampling: {base_sample} images per stage, {total_sample} total images")

        # Create a shared ProgressManager that will be reused across levels
        self.shared_progress_manager = ProgressManager()
        self.shared_progress_manager.level_work_distribution = self.level_work_distribution if hasattr(self, 'level_work_distribution') else None
        self.shared_progress_manager.weighted_total_work = self.weighted_total_work if hasattr(self, 'weighted_total_work') else None
        # Initialize with the weighted total
        if self.shared_progress_manager.weighted_total_work:
            self.shared_progress_manager.start(self.shared_progress_manager.weighted_total_work)
        else:
            self.shared_progress_manager.start(total_work)

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.update_language()
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        
        # Setup unified progress with weighted work amount
        # Use weighted_total_work if available for accurate progress tracking
        progress_total = self.weighted_total_work if hasattr(self, 'weighted_total_work') else total_work
        self.progress_dialog.setup_unified_progress(progress_total, None)  # Pass None to show "Estimating..."
        self.progress_dialog.lbl_text.setText(self.tr("Generating thumbnails"))
        self.progress_dialog.lbl_detail.setText("Estimating...")

        # Pass level work distribution to progress dialog for better ETA calculation
        if hasattr(self, 'level_work_distribution'):
            self.progress_dialog.level_work_distribution = self.level_work_distribution
            self.progress_dialog.weighted_total_work = self.weighted_total_work
        
        QApplication.setOverrideCursor(Qt.WaitCursor)

        while True:
            # Check for cancellation before starting new level
            if self.progress_dialog.is_cancelled:
                logger.info("Thumbnail generation cancelled by user before level start")
                break

            # Start timing for this level
            level_start_time = time.time()
            level_start_datetime = datetime.now()

            size /= 2
            width = int(width / 2)
            height = int(height / 2)

            # Store the current level size for checking later
            current_level_size = size

            if size < 2:
                logger.info(f"Stopping at level {i+1}: size {size} is too small to continue")
                break

            if i == 0:
                from_dir = dirname
                logger.debug(f"Level {i+1}: Reading from original directory: {from_dir}")
                total_count = seq_end - seq_begin + 1
            else:
                from_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i))
                logger.debug(f"Level {i+1}: Reading from thumbnail directory: {from_dir}")

                # For levels > 0, count actual files in the previous level directory
                if os.path.exists(from_dir):
                    actual_files = [f for f in os.listdir(from_dir) if f.endswith('.tif')]
                    total_count = len(actual_files)
                    # Update seq_end based on actual file count
                    seq_end = seq_begin + total_count - 1
                    logger.info(f"Level {i+1}: Found {total_count} actual files in previous level")
                else:
                    total_count = seq_end - seq_begin + 1
                    logger.warning(f"Level {i+1}: Previous level directory not found, using calculated count: {total_count}")

            # create thumbnail
            to_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i+1))
            if not os.path.exists(to_dir):
                mkdir_start = time.time()
                os.makedirs(to_dir)
                mkdir_time = (time.time() - mkdir_start) * 1000
                logger.debug(f"Created directory {to_dir} in {mkdir_time:.1f}ms")
            else:
                logger.debug(f"Directory already exists: {to_dir}")
            last_count = 0

            logger.info(f"--- Level {i+1} ---")
            logger.info(f"Level {i+1} start time: {level_start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.info(f"Level {i+1}: Processing {total_count} images (size: {int(size)}x{int(size)})")

            # Initialize thumbnail manager for multithreaded processing
            # Pass the shared progress manager to maintain ETA across levels
            logger.info(f"Creating ThumbnailManager for level {i+1}")
            shared_pm = self.shared_progress_manager if hasattr(self, 'shared_progress_manager') else None
            self.thumbnail_manager = ThumbnailManager(self, self.progress_dialog, self.threadpool, shared_pm)
            logger.info(f"ThumbnailManager created, starting process_level")

            # Use multithreaded processing for this level
            process_start = time.time()
            level_img_arrays, was_cancelled = self.thumbnail_manager.process_level(
                i, from_dir, to_dir, seq_begin, seq_end,
                self.settings_hash, size, MAX_THUMBNAIL_SIZE, global_step_counter
            )
            process_time = time.time() - process_start
            logger.info(f"Level {i+1}: process_level completed in {process_time:.2f}s")

            # Calculate and log time for this level
            level_end_datetime = datetime.now()
            level_elapsed = time.time() - level_start_time
            logger.info(f"Level {i+1} end time: {level_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.info(f"Level {i+1}: Completed in {level_elapsed:.2f} seconds")

            # Update global step counter based on actual progress made
            global_step_counter = self.thumbnail_manager.global_step_counter

            # Note: We no longer add images to minimum_volume here
            # Instead, we'll load them from disk later, just like Rust does
            # This ensures both Python and Rust follow the same path
            
            # Check for cancellation
            if was_cancelled or self.progress_dialog.is_cancelled:
                logger.info("Thumbnail generation cancelled by user")
                break
            
            # Update seq_end for next level (each level has half the images of the previous)
            # Number of thumbnails generated = (current_count // 2) + 1 if odd
            current_count = seq_end - seq_begin + 1
            next_count = (current_count // 2) + (current_count % 2)  # Add 1 if odd number
            seq_end = seq_begin + next_count - 1
            logger.info(f"Level {i+1}: {current_count} images -> {next_count} thumbnails generated")
            logger.info(f"Next level will process range: {seq_begin}-{seq_end}")

            i += 1
            
            # Only add to level_info if this level doesn't already exist
            level_name = f"Level {i}"
            level_exists = any(level['name'] == level_name for level in self.level_info)
            if not level_exists:
                self.level_info.append( {'name': level_name, 'width': width, 'height': height, 'seq_begin': seq_begin, 'seq_end': seq_end} )
                #logger.info(f"Added new level to level_info: {level_name}")
            else:
                pass  #logger.info(f"Level {level_name} already exists in level_info, skipping")
            # Check if we've reached the size limit
            # Stop when images are small enough (< MAX_THUMBNAIL_SIZE)
            if current_level_size < MAX_THUMBNAIL_SIZE:
                logger.info(f"Reached target thumbnail size at level {i}")
                break

        logger.info(f"Exited thumbnail generation loop at level {i+1}")
        QApplication.restoreOverrideCursor()

        # Calculate and log total time for entire thumbnail generation
        thumbnail_end_datetime = datetime.now()
        total_elapsed = time.time() - thumbnail_start_time

        logger.info(f"=== Thumbnail generation completed ===")
        logger.info(f"End time: {thumbnail_end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"Total duration: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
        logger.info(f"Total levels processed: {i + 1}")
        if total_elapsed > 0:
            images_per_second = total_work / total_elapsed if 'total_work' in locals() else 0
            logger.info(f"Average processing speed: {images_per_second:.1f} images/second")

        # Compare estimated vs actual time
        logger.info(f"=== Time Estimation Accuracy ===")
        if self.initial_estimate_seconds > 0:
            logger.info(f"Initial estimate (before sampling): {self.initial_estimate_str} ({self.initial_estimate_seconds:.1f}s)")
            initial_accuracy = (1 - abs(self.initial_estimate_seconds - total_elapsed) / total_elapsed) * 100 if total_elapsed > 0 else 0
            logger.info(f"Initial estimate accuracy: {initial_accuracy:.1f}%")
        else:
            logger.info(f"No initial estimate was provided (used sampling instead)")

        if self.sampled_estimate_str:
            logger.info(f"Estimate after sampling: {self.sampled_estimate_str} ({self.sampled_estimate_seconds:.1f}s)")
            sampled_accuracy = (1 - abs(self.sampled_estimate_seconds - total_elapsed) / total_elapsed) * 100 if total_elapsed > 0 else 0
            logger.info(f"Sampling estimate accuracy: {sampled_accuracy:.1f}%")

        actual_time_str = f"{int(total_elapsed)}s" if total_elapsed < 60 else f"{int(total_elapsed/60)}m {int(total_elapsed%60)}s"
        logger.info(f"Actual time taken: {actual_time_str} ({total_elapsed:.1f}s)")

        # Calculate overall generation statistics
        total_generated = 0
        total_loaded = 0
        if hasattr(self, 'thumbnail_manager'):
            total_generated = self.thumbnail_manager.generated_count
            total_loaded = self.thumbnail_manager.loaded_count
            generation_percentage = total_generated / (total_generated + total_loaded) * 100 if (total_generated + total_loaded) > 0 else 0
            logger.info(f"Overall: {total_generated} generated, {total_loaded} loaded ({generation_percentage:.1f}% generated)")

        # No longer saving coefficients - real-time sampling provides better accuracy
        # Each run measures actual performance including all variables:
        # - Drive speed (SSD/HDD/Network)
        # - Image dimensions
        # - Bit depth (8-bit, 16-bit, etc.)
        # - File format and compression
        # - Current CPU load
        # - Available memory
        if hasattr(self, 'weighted_total_work') and self.weighted_total_work > 0:
            actual_coefficient = total_elapsed / self.weighted_total_work
            logger.info(f"Actual performance: {actual_coefficient:.3f}s per weighted unit")
            logger.info(f"This varies based on image size, bit depth, drive speed, and system load")

        # Show completion or cancellation message
        if self.progress_dialog.is_cancelled:
            self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation cancelled"))
            self.progress_dialog.lbl_detail.setText("")
            logger.info("Thumbnail generation was cancelled by user")
        else:
            self.progress_dialog.lbl_text.setText(self.tr("Thumbnail generation complete"))
            self.progress_dialog.lbl_detail.setText("")

        self.progress_dialog.close()
        self.progress_dialog = None

        # Load thumbnail data from disk (same as Rust does)
        # This will load the thumbnails that were just saved to disk and update the 3D view
        self.load_thumbnail_data_from_disk()

        # If loading from disk failed and minimum_volume is still empty
        if len(self.minimum_volume) == 0:
            logger.warning("Failed to load thumbnails from disk after Python generation")

        self.initializeComboSize()
        self.reset_crop()
        
        # Trigger initial display by setting combo index if items exist
        if self.comboLevel.count() > 0:
            #logger.info("Triggering initial display by setting combo index to 0")
            self.comboLevel.setCurrentIndex(0)
            # If comboLevelIndexChanged doesn't trigger, call it manually
            if not self.initialized:
                #logger.info("Manually calling comboLevelIndexChanged")
                self.comboLevelIndexChanged()

            # Update 3D view after initializing combo level
            self.update_3D_view(False)

    def slider2ValueChanged(self, value):
            """
            Updates the isovalue of the image label and mcube widget based on the given slider value,
            and recalculates the image label's size.
            
            Args:
                value (float): The new value of the slider.
            """
            #print("value:", value)
            # update external readout to reflect 0-255 range accurately
            if hasattr(self, 'threshold_value_label'):
                self.threshold_value_label.setText(str(int(value)))
            self.image_label.set_isovalue(value)
            self.mcube_widget.set_isovalue(value)
            self.image_label.calculate_resize()
    
    def slider2SliderReleased(self):
        self.update_3D_view(True)

    def sort_file_list_from_dir(self, directory_path):
        # Step 1: Get a list of all files in the directory
        #directory_path = "/path/to/your/directory"  # Replace with the path to your directory
        all_files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]

        # Step 2: Regular expression pattern
        pattern = r'^(.*?)(\d+)\.(\w+)$'

        ct_stack_files = []
        matching_files = []
        other_files = []
        prefix_hash = {}
        extension_hash = {}
        settings_hash = {}

        for file in all_files:
            if re.match(pattern, file):
                matching_files.append(file)
                if re.match(pattern, file).group(1) in prefix_hash:
                    prefix_hash[re.match(pattern, file).group(1)] += 1
                else:
                    prefix_hash[re.match(pattern, file).group(1)] = 1
                if re.match(pattern, file).group(3) in extension_hash:
                    extension_hash[re.match(pattern, file).group(3)] += 1
                else:
                    extension_hash[re.match(pattern, file).group(3)] = 1

            else:
                other_files.append(file)

        # determine prefix
        max_prefix_count = 0
        max_prefix = ""
        for prefix in prefix_hash:
            if prefix_hash[prefix] > max_prefix_count:
                max_prefix_count = prefix_hash[prefix]
                max_prefix = prefix
        
        #logger.info(f"Detected prefixes: {list(prefix_hash.keys())[:5]}")
        #logger.info(f"Most common prefix: '{max_prefix}' with {max_prefix_count} files")

        # determine extension
        max_extension_count = 0
        max_extension = ""
        for extension in extension_hash:
            if extension_hash[extension] > max_extension_count:
                max_extension_count = extension_hash[extension]
                max_extension = extension
        
        #logger.info(f"Most common extension: '{max_extension}' with {max_extension_count} files")

        if matching_files:
            for file in matching_files:
                if re.match(pattern, file).group(1) == max_prefix and re.match(pattern, file).group(3) == max_extension:
                    ct_stack_files.append(file)

        # Determine the pattern if needed further
        if ct_stack_files:
            # If there are CT stack files, we can determine some common patterns
            # Here as an example, we are just displaying the prefix of the first matched file
            # This can be expanded upon based on specific needs
            first_file = ct_stack_files[0]
            last_file = ct_stack_files[-1]
            imagefile_name = os.path.join(directory_path, first_file)
            # get width and height
            try:
                img = Image.open(imagefile_name)
                width, height = img.size
            except Exception as e:
                logger.error(f"Error opening image {imagefile_name}: {e}")
                return None


            match1 = re.match(pattern, first_file)
            match2 = re.match(pattern, last_file)

            if match1 and match2:
                start_index = match1.group(2)
                end_index = match2.group(2)
            image_count = int(match2.group(2)) - int(match1.group(2)) + 1
            number_of_images = len(ct_stack_files)
            seq_length = len(match1.group(2))

            settings_hash['prefix'] = max_prefix
            settings_hash['image_width'] = width
            settings_hash['image_height'] = height
            settings_hash['file_type'] = max_extension
            settings_hash['index_length'] = seq_length
            settings_hash['seq_begin'] = start_index
            settings_hash['seq_end'] = end_index
            settings_hash['index_length'] = int(settings_hash['index_length'])
            settings_hash['seq_begin'] = int(settings_hash['seq_begin'])
            settings_hash['seq_end'] = int(settings_hash['seq_end'])

            return settings_hash
        else:
            return None
        


    def open_dir(self):
            """
            Opens a directory dialog to select a directory containing image files and log files.
            Parses the log file to extract settings information and updates the UI accordingly.
            """
            #logger.info("=" * 60)
            logger.info("open_dir method called - START")
            #logger.info("=" * 60)
            
            # Check current state
            if hasattr(self, 'minimum_volume'):
                pass
                #logger.info(f"Current minimum_volume state: type={type(self.minimum_volume)}, len={len(self.minimum_volume) if isinstance(self.minimum_volume, (list, np.ndarray)) else 'N/A'}")
            else:
                pass  #logger.info("minimum_volume not yet initialized")
            
            ddir = QFileDialog.getExistingDirectory(self, self.tr("Select directory"), self.m_app.default_directory)
            if ddir:
                logger.info(f"Selected directory: {ddir}")
                self.edtDirname.setText(ddir)
                self.m_app.default_directory = os.path.dirname(ddir)
            else:
                logger.info("Directory selection cancelled")
                return
            
            #logger.info("Resetting settings_hash and image_file_list")
            self.settings_hash = {}
            self.initialized = False
            image_file_list = []

            # Reset upper/lower bounds, bounding box, threshold, and inversion settings
            logger.info("Resetting bounds, bounding box, and threshold settings")

            # Reset timeline/range slider to full range
            if hasattr(self, 'timeline'):
                self.timeline.setLower(self.timeline.minimum())
                self.timeline.setUpper(self.timeline.maximum())

            # Reset bounding box
            self.bounding_box = None
            if hasattr(self, 'bounding_box_vertices'):
                self.bounding_box_vertices = None
            if hasattr(self, 'bounding_box_edges'):
                self.bounding_box_edges = None

            # Reset ROI box in ObjectViewer2D
            if hasattr(self, 'image_label'):
                self.image_label.reset_crop()

            # Reset threshold values if they exist
            if hasattr(self, 'lower_threshold'):
                self.lower_threshold = 0
            if hasattr(self, 'upper_threshold'):
                self.upper_threshold = 255

            # Reset inversion setting if it exists
            if hasattr(self, 'invert_image'):
                self.invert_image = False

            # Clear any existing 3D scene data
            if hasattr(self, 'minimum_volume'):
                self.minimum_volume = None
            if hasattr(self, 'level_volumes'):
                self.level_volumes = {}

            QApplication.setOverrideCursor(Qt.WaitCursor)

            try:
                # Use secure file listing to prevent directory traversal attacks
                # This includes .log files for parsing
                all_extensions = SecureFileValidator.ALLOWED_EXTENSIONS | {'.log'}
                files = SecureFileValidator.secure_listdir(ddir, extensions=all_extensions)
                logger.info(f"Found {len(files)} validated files in directory")
            except FileSecurityError as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, self.tr("Security Error"),
                                   self.tr(f"Directory access denied for security reasons: {e}"))
                logger.error(f"File security error: {e}")
                return
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to read directory: {e}"))
                logger.error(f"Failed to read directory: {e}")
                return

            log_files_found = 0
            for file in files:
                # get extension
                ext = os.path.splitext(file)[-1].lower()
                if ext in [".bmp", ".jpg", ".png", ".tif", ".tiff"]:
                    pass #image_file_list.append(file)
                elif ext == '.log':
                    log_files_found += 1
                    try:
                        settings = QSettings(os.path.join(ddir, file), QSettings.IniFormat)
                        prefix = settings.value("File name convention/Filename Prefix")
                        if not prefix:
                            continue
                        if file != prefix + ".log":
                            continue
                        
                        logger.info(f"Found valid log file: {file}")
                        self.settings_hash['prefix'] = settings.value("File name convention/Filename Prefix")
                        self.settings_hash['image_width'] = settings.value("Reconstruction/Result Image Width (pixels)")
                        self.settings_hash['image_height'] = settings.value("Reconstruction/Result Image Height (pixels)")
                        self.settings_hash['file_type'] = settings.value("Reconstruction/Result File Type")
                        self.settings_hash['index_length'] = settings.value("File name convention/Filename Index Length")
                        self.settings_hash['seq_begin'] = settings.value("Reconstruction/First Section")
                        self.settings_hash['seq_end'] = settings.value("Reconstruction/Last Section")
                        self.settings_hash['image_width'] = int(self.settings_hash['image_width'])
                        self.settings_hash['image_height'] = int(self.settings_hash['image_height'])
                        self.settings_hash['index_length'] = int(self.settings_hash['index_length'])
                        self.settings_hash['seq_begin'] = int(self.settings_hash['seq_begin'])
                        self.settings_hash['seq_end'] = int(self.settings_hash['seq_end'])
                        self.edtNumImages.setText(str(self.settings_hash['seq_end'] - self.settings_hash['seq_begin'] + 1))
                        self.edtImageDimension.setText(str(self.settings_hash['image_width']) + " x " + str(self.settings_hash['image_height']))
                    except Exception as e:
                        logger.error(f"Error reading log file {file}: {e}")
                        continue

            #logger.info(f"Log files found: {log_files_found}")
            
            if 'prefix' not in self.settings_hash:
                #logger.info("No valid log file found, trying to detect image sequence...")
                self.settings_hash = self.sort_file_list_from_dir(ddir)
                if self.settings_hash is None:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.warning(self, self.tr("Warning"), self.tr("No valid image files found in the selected directory."))
                    logger.warning("No valid image files found")
                    return
                logger.info(f"Detected image sequence: prefix={self.settings_hash.get('prefix')}, range={self.settings_hash.get('seq_begin')}-{self.settings_hash.get('seq_end')}")

            for seq in range(self.settings_hash['seq_begin'], self.settings_hash['seq_end']+1):
                filename = self.settings_hash['prefix'] + str(seq).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
                image_file_list.append(filename)
            
            #logger.info(f"Created image list with {len(image_file_list)} files")
            #logger.info(f"First image: {image_file_list[0] if image_file_list else 'None'}")
            
            self.original_from_idx = 0
            self.original_to_idx = len(image_file_list) - 1
            
            # Try to load the first image
            if image_file_list:
                first_image_path = os.path.join(ddir, image_file_list[0])
                #logger.info(f"Trying to load first image: {first_image_path}")
                
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
                        #logger.info(f"Found file with lowercase extension: {alt_path}")
                
                if actual_path:
                    #logger.info(f"Image file exists: {actual_path}")
                    try:
                        pixmap = QPixmap(actual_path)
                        if pixmap.isNull():
                            logger.error(f"QPixmap is null for {actual_path}")
                        else:
                            #logger.info(f"Successfully loaded pixmap, size: {pixmap.width()}x{pixmap.height()}")
                            self.image_label.setPixmap(pixmap.scaledToWidth(512))
                    except Exception as e:
                        logger.error(f"Error loading initial image: {e}")
                else:
                    logger.error(f"Image file does not exist: {first_image_path} (also tried lowercase extension)")
            self.level_info = []
            self.level_info.append( {'name': 'Original', 'width': self.settings_hash['image_width'], 'height': self.settings_hash['image_height'], 'seq_begin': self.settings_hash['seq_begin'], 'seq_end': self.settings_hash['seq_end']} )
            
            # Check for existing thumbnail directories and populate level_info
            thumbnail_base = os.path.join(self.edtDirname.text(), ".thumbnail")
            if os.path.exists(thumbnail_base):
                logger.info(f"Found existing thumbnail directory: {thumbnail_base}")
                level_idx = 1
                while True:
                    level_dir = os.path.join(thumbnail_base, str(level_idx))
                    if not os.path.exists(level_dir):
                        break
                    
                    # Get first image from this level to determine dimensions
                    try:
                        files = sorted([f for f in os.listdir(level_dir) if f.endswith(('.' + self.settings_hash['file_type']))])
                        if files:
                            first_img_path = os.path.join(level_dir, files[0])
                            img = Image.open(first_img_path)
                            width, height = img.size
                            img.close()
                            
                            # Calculate sequence range for this level
                            seq_begin = self.settings_hash['seq_begin']
                            seq_end = seq_begin + len(files) - 1
                            
                            self.level_info.append({
                                'name': f"Level {level_idx}",
                                'width': width,
                                'height': height,
                                'seq_begin': seq_begin,
                                'seq_end': seq_end
                            })
                            #logger.info(f"Added level {level_idx}: {width}x{height}, {len(files)} images")
                    except Exception as e:
                        logger.error(f"Error reading thumbnail level {level_idx}: {e}")
                        break
                    
                    level_idx += 1
            
            QApplication.restoreOverrideCursor()
            logger.info(f"Successfully loaded directory with {len(image_file_list)} images")
            #logger.info(f"Level info count: {len(self.level_info)}")
            #logger.info("Calling create_thumbnail...")
            self.create_thumbnail()
            #logger.info(f"After create_thumbnail, minimum_volume type: {type(self.minimum_volume) if hasattr(self, 'minimum_volume') else 'not set'}")
            if hasattr(self, 'minimum_volume'):
                if isinstance(self.minimum_volume, list):
                    pass
                    #logger.info(f"minimum_volume is list with length: {len(self.minimum_volume)}")
                elif isinstance(self.minimum_volume, np.ndarray):
                    pass  #logger.info(f"minimum_volume is numpy array with shape: {self.minimum_volume.shape}")

    def read_settings(self):
            """
            Reads the application settings and updates the corresponding values in the application object.
            """
            try:
                settings = self.m_app.settings

                self.m_app.remember_directory = value_to_bool(settings.value("Remember directory", True))
                if self.m_app.remember_directory:
                    self.m_app.default_directory = settings.value("Default directory", ".")
                else:
                    self.m_app.default_directory = "."

                self.m_app.remember_geometry = value_to_bool(settings.value("Remember geometry", True))
                if self.m_app.remember_geometry:
                    self.setGeometry(settings.value("MainWindow geometry", QRect(100, 100, 600, 550)))
                    self.mcube_geometry = settings.value("mcube_widget geometry", QRect(0, 0, 150, 150))
                else:
                    self.setGeometry(QRect(100, 100, 600, 550))
                    self.mcube_geometry = QRect(0, 0, 150, 150)
                self.m_app.language = settings.value("Language", "en")

                # Read Rust module preference
                use_rust_default = value_to_bool(settings.value("Use Rust Module", True))
                if hasattr(self, 'cbxUseRust'):
                    self.cbxUseRust.setChecked(use_rust_default)

            except Exception as e:
                logger.error(f"Error reading main window settings: {e}")
                # Set defaults if reading fails
                self.m_app.remember_directory = True
                self.m_app.default_directory = "."
                self.m_app.remember_geometry = True
                self.setGeometry(QRect(100, 100, 600, 550))
                self.mcube_geometry = QRect(0, 0, 150, 150)
                self.m_app.language = "en"
                if hasattr(self, 'cbxUseRust'):
                    self.cbxUseRust.setChecked(True)

    def save_settings(self):
            """
            Saves the current application settings to persistent storage.
            If the 'remember_directory' setting is enabled, saves the default directory.
            If the 'remember_geometry' setting is enabled, saves the main window and mcube widget geometries.
            """
            try:
                if self.m_app.remember_directory:
                    self.m_app.settings.setValue("Default directory", self.m_app.default_directory)
                if self.m_app.remember_geometry:
                    self.m_app.settings.setValue("MainWindow geometry", self.geometry())
                    self.m_app.settings.setValue("mcube_widget geometry", self.mcube_widget.geometry())

                # Save Rust module preference
                if hasattr(self, 'cbxUseRust'):
                    self.m_app.settings.setValue("Use Rust Module", self.cbxUseRust.isChecked())

            except Exception as e:
                logger.error(f"Error saving main window settings: {e}")

    def closeEvent(self, event):
        """
        This method is called when the user closes the application window.
        It saves the current settings and accepts the close event.
        """
        logger.info("Application closing")
        self.save_settings()
        event.accept()
        

if __name__ == "__main__":
    #logger.info(f"Starting {PROGRAM_NAME} v{PROGRAM_VERSION}")
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon(resource_path('CTHarvester_48_2.png')))
    app.settings = QSettings(QSettings.IniFormat, QSettings.UserScope,COMPANY_NAME, PROGRAM_NAME)

    # Apply saved log level
    saved_log_level = app.settings.value("Log Level", "INFO")
    try:
        numeric_level = getattr(logging, saved_log_level, logging.INFO)
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            handler.setLevel(numeric_level)
        logger.info(f"Log level set to {saved_log_level} from settings")
    except Exception as e:
        logger.warning(f"Could not set log level from settings: {e}")

    translator = QTranslator(app)
    app.language = app.settings.value("Language", "en")
    translator.load(resource_path("CTHarvester_{}.qm".format(app.language)))
    app.installTranslator(translator)

    # Create instance of CTHarvesterMainWindow
    myWindow = CTHarvesterMainWindow()

    # Show the main window
    myWindow.show()
    #logger.info(f"{PROGRAM_NAME} main window displayed")

    # Enter the event loop (start the application)
    app.exec_()
    #logger.info(f"{PROGRAM_NAME} terminated")

'''
pyinstaller --onefile --noconsole --add-data "*.png;." --add-data "*.qm;." --icon="CTHarvester_48_2.png" CTHarvester.py
pyinstaller --onedir --noconsole --icon="CTHarvester_64.png" --noconfirm CTHarvester.py

pylupdate5 CTHarvester.py -ts CTHarvester_en.ts
pylupdate5 CTHarvester.py -ts CTHarvester_ko.ts
linguist

'''
