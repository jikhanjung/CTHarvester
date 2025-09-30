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
    PROGRAM_NAME as CONST_PROGRAM_NAME,
    PROGRAM_VERSION as CONST_PROGRAM_VERSION,
    COMPANY_NAME as CONST_COMPANY_NAME,
    SUPPORTED_IMAGE_EXTENSIONS,
    THUMBNAIL_DIR_NAME,
    DEFAULT_LOG_LEVEL
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
# Python fallback implementation uses only PIL and NumPy for simplicity
# No additional libraries needed - maximum compatibility

def value_to_bool(value):
    return value.lower() == 'true' if isinstance(value, str) else bool(value)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

MODE = {}
MODE['VIEW'] = 0
MODE['ADD_BOX'] = 1
MODE['MOVE_BOX'] = 2
MODE['EDIT_BOX'] = 3
MODE['EDIT_BOX_READY'] = 4
MODE['EDIT_BOX_PROGRESS'] = 5
MODE['MOVE_BOX_PROGRESS'] = 6
MODE['MOVE_BOX_READY'] = 7
DISTANCE_THRESHOLD = 10

# Use constants from config module
COMPANY_NAME = CONST_COMPANY_NAME
PROGRAM_VERSION = CONST_PROGRAM_VERSION
PROGRAM_NAME = CONST_PROGRAM_NAME
PROGRAM_AUTHOR = "Jikhan Jung"

# Build-time year for copyright
BUILD_YEAR = 2025  # This will be set during build
PROGRAM_COPYRIGHT = f"© 2023-{BUILD_YEAR} Jikhan Jung"

# Directory setup
USER_PROFILE_DIRECTORY = os.path.expanduser('~')
DEFAULT_DB_DIRECTORY = os.path.join(USER_PROFILE_DIRECTORY, COMPANY_NAME, PROGRAM_NAME)
DEFAULT_STORAGE_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "data/")
DEFAULT_LOG_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "logs/")
DB_BACKUP_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "backups/")

def ensure_directories():
    """Safely create necessary directories with error handling."""
    directories = [
        DEFAULT_DB_DIRECTORY,
        DEFAULT_STORAGE_DIRECTORY,
        DEFAULT_LOG_DIRECTORY,
        DB_BACKUP_DIRECTORY
    ]
    
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Use print here since logger might not be initialized yet
            print(f"Warning: Could not create directory {directory}: {e}")
            # Don't fail completely, let the application try to continue

# Try to create directories on import, but don't fail if it doesn't work
try:
    ensure_directories()
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
