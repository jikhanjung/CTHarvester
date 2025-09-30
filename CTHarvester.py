from PyQt5.QtGui import QIcon, QColor, QPainter, QPen, QPixmap, QPainter, QMouseEvent, QResizeEvent, QImage, QCursor, QFont, QFontMetrics
from PyQt5.QtWidgets import QMainWindow, QApplication, QAbstractItemView, QRadioButton, QComboBox, \
                            QFileDialog, QWidget, QHBoxLayout, QVBoxLayout, QProgressBar, QApplication, \
                            QDialog, QLineEdit, QLabel, QPushButton, QAbstractItemView, \
                            QSizePolicy, QGroupBox, QListWidget, QFormLayout, QCheckBox, QMessageBox, QSlider
from PyQt5.QtCore import Qt, QRect, QPoint, QSettings, QTranslator, QMargins, QTimer, QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot, QEvent, QThread, QMutex, QMutexLocker
#from PyQt5.QtCore import QT_TR_NOOP as tr
from PyQt5.QtOpenGL import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from queue import Queue

from vertical_stack_slider import VerticalTimeline

import os, sys, re
from PIL import Image, ImageChops
import numpy as np
import mcubes
from scipy import ndimage  # For interpolation
import math
from copy import deepcopy
import datetime
import time
import gc  # For explicit garbage collection
import traceback  # For error stack traces

# Project modules
from security.file_validator import SecureFileValidator, FileSecurityError, safe_open_image
from config.constants import (
    PROGRAM_NAME, PROGRAM_VERSION, COMPANY_NAME, PROGRAM_AUTHOR,
    PROGRAM_COPYRIGHT, BUILD_YEAR,
    DEFAULT_DB_DIRECTORY, DEFAULT_STORAGE_DIRECTORY,
    DEFAULT_LOG_DIRECTORY, DB_BACKUP_DIRECTORY,
    SUPPORTED_IMAGE_EXTENSIONS, THUMBNAIL_DIR_NAME, DEFAULT_LOG_LEVEL
)
from core.thumbnail_worker import ThumbnailWorker, ThumbnailWorkerSignals
from ui.dialogs import InfoDialog, PreferencesDialog, ProgressDialog
from ui.widgets import MCubeWidget, ObjectViewer2D
from utils.worker import Worker, WorkerSignals
from config.view_modes import (
    OBJECT_MODE, VIEW_MODE, PAN_MODE, ROTATE_MODE, ZOOM_MODE,
    MOVE_3DVIEW_MODE, ROI_BOX_RESOLUTION
)

from core.progress_manager import ProgressManager
from core.thumbnail_manager import ThumbnailManager
from ui.main_window import CTHarvesterMainWindow
from utils.common import resource_path, value_to_bool, ensure_directories

# Try to create directories on import, but don't fail if it doesn't work
try:
    ensure_directories([
        DEFAULT_DB_DIRECTORY,
        DEFAULT_STORAGE_DIRECTORY,
        DEFAULT_LOG_DIRECTORY,
        DB_BACKUP_DIRECTORY
    ])
except Exception as e:
    # Use print here since logger might not be initialized yet
    print(f"Warning: Directory initialization failed: {e}")
    pass

# Setup logger
from CTLogger import setup_logger
logger = setup_logger(PROGRAM_NAME)




def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName(PROGRAM_NAME)
    app.setOrganizationName(COMPANY_NAME)
    app.setOrganizationDomain("github.com/jikhanjung")
    
    # Set application icon
    app.setWindowIcon(QIcon(resource_path("icon.png")))
    
    # Create settings object
    app.settings = QSettings(COMPANY_NAME, PROGRAM_NAME)
    
    # Initialize application attributes
    app.remember_geometry = True
    app.remember_directory = True
    app.language = "en"
    
    # Create and show main window
    window = CTHarvesterMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
