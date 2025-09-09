from PyQt5.QtGui import QIcon, QColor, QPainter, QPen, QPixmap, QPainter, QMouseEvent, QResizeEvent, QImage, QCursor
from PyQt5.QtWidgets import QMainWindow, QApplication, QAbstractItemView, QRadioButton, QComboBox, \
                            QFileDialog, QWidget, QHBoxLayout, QVBoxLayout, QProgressBar, QApplication, \
                            QDialog, QLineEdit, QLabel, QPushButton, QAbstractItemView, \
                            QSizePolicy, QGroupBox, QListWidget, QFormLayout, QCheckBox, QMessageBox
from PyQt5.QtCore import Qt, QRect, QPoint, QSettings, QTranslator, QMargins, QTimer, QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot, QEvent
#from PyQt5.QtCore import QT_TR_NOOP as tr
from PyQt5.QtOpenGL import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from queue import Queue

from superqt import QLabeledRangeSlider, QLabeledSlider

import os, sys, re
from PIL import Image, ImageChops
import numpy as np
import mcubes
from scipy import ndimage  # For interpolation
import math
from copy import deepcopy
import datetime

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
COMPANY_NAME = "PaleoBytes"
try:
    from version import __version__ as PROGRAM_VERSION
except ImportError:
    PROGRAM_VERSION = "0.2.0"  # Fallback version

PROGRAM_NAME = "CTHarvester"
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

OBJECT_MODE = 1
VIEW_MODE = 1
PAN_MODE = 2
ROTATE_MODE = 3
ZOOM_MODE = 4
MOVE_3DVIEW_MODE = 5

ROI_BOX_RESOLUTION = 50.0

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        #self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            #traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

# Define a custom OpenGL widget using QOpenGLWidget
class MCubeWidget(QGLWidget):
    def __init__(self,parent):
        super().__init__(parent=parent)
        self.setMinimumSize(100,100)
        self.isovalue = 60  # Adjust the isovalue as needed
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.temp_pan_x = 0
        self.temp_pan_y = 0
        self.rotate_x = 0
        self.rotate_y = 0
        self.temp_rotate_x = 0
        self.temp_rotate_y = 0
        self.curr_x = 0
        self.curr_y = 0
        self.down_x = 0
        self.down_y = 0
        self.temp_dolly = 0
        self.dolly = 0
        self.data_mode = OBJECT_MODE
        self.view_mode = VIEW_MODE
        self.auto_rotate = True
        self.is_dragging = False
        #self.setMinimumSize(400,400)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.rotate_timeout)
        self.timer.start()
        self.timer2 = QTimer(self)
        self.timer2.setInterval(50)
        self.timer2.timeout.connect(self.generate_mesh_timeout)
        self.timer2.start()

        self.triangles = []
        self.gl_list_generated = False
        self.parent = parent
        self.parent.set_threed_view(self)

        ''' set up buttons '''
        self.moveButton = QLabel(self)
        self.moveButton.setPixmap(QPixmap(resource_path("move.png")).scaled(15,15))
        self.moveButton.hide()
        self.moveButton.setGeometry(0,0,15,15)
        self.moveButton.mousePressEvent = self.moveButton_mousePressEvent
        self.moveButton.mouseMoveEvent = self.moveButton_mouseMoveEvent
        self.moveButton.mouseReleaseEvent = self.moveButton_mouseReleaseEvent
        self.expandButton = QLabel(self)
        self.expandButton.setPixmap(QPixmap(resource_path("expand.png")).scaled(15,15))
        self.expandButton.hide()
        self.expandButton.setGeometry(15,0,15,15)
        self.expandButton.mousePressEvent = self.expandButton_mousePressEvent
        self.shrinkButton = QLabel(self)
        self.shrinkButton.setPixmap(QPixmap(resource_path("shrink.png")).scaled(15,15))
        self.shrinkButton.hide()
        self.shrinkButton.setGeometry(30,0,15,15)
        self.shrinkButton.mousePressEvent = self.shrinkButton_mousePressEvent
        self.cbxRotation = QCheckBox(self)
        self.cbxRotation.setText("R")
        self.cbxRotation.setChecked(True)
        self.cbxRotation.stateChanged.connect(self.cbxRotation_stateChanged)
        self.cbxRotation.setStyleSheet("QCheckBox { background-color: #323232; color: white; }")        
        self.cbxRotation.hide()
        self.cbxRotation.move(45,0)

        self.curr_slice = None
        self.curr_slice_vertices = []
        self.scale = 0.20
        self.average_coordinates = np.array([0.0,0.0,0.0], dtype=np.float64)
        self.bounding_box = None
        self.roi_box = None
        self.threadpool = QThreadPool()
        #print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        self.vertices = []
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.generate_mesh_under_way = False
        self.adjust_volume_under_way = False
        self.generated_data = None
        self.is_inverse = False

        self.queue = Queue()

    def recalculate_geometry(self):
        #self.scale = self.parent.
        size = min(self.parent.width(),self.parent.height())
        self.scale = round( ( self.width() / size ) * 10.0 ) / 10.0
        #self.resize(int(size*self.scale),int(size*self.scale))

        self.resize_self()
        self.reposition_self()

    def start_generate_mesh(self):
        self.threadpool.start(self.worker)

    def progress_fn(self, n):
        #print("progress_fn")
        return

    def execute_this_fn(self, progress_callback):
        return

        #return "Done."

    def print_output(self, s):
        return

    def thread_complete(self):
        #print("THREAD COMPLETE!")
        self.adjust_volume()
        return

    def expandButton_mousePressEvent(self, event):
        self.scale += 0.1
        self.resize_self()
        self.reposition_self()

    def shrinkButton_mousePressEvent(self, event):
        self.scale -= 0.1
        if self.scale < 0.1:
            self.scale = 0.1
        self.resize_self()
        self.reposition_self()

    def moveButton_mousePressEvent(self, event):
        self.down_x = event.x()
        self.down_y = event.y()
        self.view_mode = MOVE_3DVIEW_MODE

    def moveButton_mouseMoveEvent(self, event):
        self.curr_x = event.x()
        self.curr_y = event.y()
        if self.view_mode == MOVE_3DVIEW_MODE:
            self.move(self.x() + self.curr_x - self.down_x, self.y() + self.curr_y - self.down_y)
        #self.reposition_self()

    def moveButton_mouseReleaseEvent(self, event):
        self.curr_x = event.x()
        self.curr_y = event.y()
        if self.view_mode == MOVE_3DVIEW_MODE:
            self.move(self.x() + self.curr_x - self.down_x, self.y() + self.curr_y - self.down_y)

        self.view_mode = VIEW_MODE
        # get parent's geometry
        self.reposition_self()

    def reposition_self(self):
        x, y = self.x(), self.y()
        parent_geometry = self.parent.get_pixmap_geometry()
        if parent_geometry is None:
            return
        if y + ( self.height() / 2 ) > parent_geometry.height() / 2 :
            y = parent_geometry.height() - self.height()
        else:
            y = 0
        if x + ( self.width() / 2 ) > parent_geometry.width() / 2 :
            x = parent_geometry.width() - self.width()
        else:
            x = 0
        
        self.move(x, y)                

    def cbxRotation_stateChanged(self):
        self.auto_rotate = self.cbxRotation.isChecked()

    def resize_self(self):
        size = min(self.parent.width(),self.parent.height())
        self.resize(int(size*self.scale),int(size*self.scale))
        #print("resize:",self.parent.width(),self.parent.height())

    def make_box(self, box_coords):
        from_z = box_coords[0]
        to_z = box_coords[1]
        from_y = box_coords[2]
        to_y = box_coords[3]
        from_x = box_coords[4]
        to_x = box_coords[5]

        box_vertex = np.array([
            np.array([from_z, from_y, from_x]),
            np.array([to_z, from_y, from_x]),
            np.array([from_z, to_y, from_x]),
            np.array([to_z, to_y, from_x]),
            np.array([from_z, from_y, to_x]),
            np.array([to_z, from_y, to_x]),
            np.array([from_z, to_y, to_x]),
            np.array([to_z, to_y, to_x])
        ], dtype=np.float64)

        box_edges = [
            [0,1],
            [0,2],
            [0,4],
            [1,3],
            [1,5],
            [2,3],
            [2,6],
            [3,7],
            [4,5],
            [4,6],
            [5,7],
            [6,7]
        ]
        return box_vertex, box_edges

    def update_boxes(self, bounding_box, roi_box,curr_slice_val):
        self.set_bounding_box(bounding_box)
        self.set_roi_box(roi_box)
        self.set_curr_slice(curr_slice_val)

    def adjust_boxes(self):
        # apply roi_displacement to bounding box, roi box, and curr_slice
        self.apply_roi_displacement()
        self.rotate_boxes()
        self.scale_boxes()
        
    def scale_boxes(self):
        factor = 10.0
        self.roi_box_vertices *= self.scale_factor / factor
        self.bounding_box_vertices *= self.scale_factor / factor
        self.curr_slice_vertices *= self.scale_factor / factor
        self.volume_displacement *= self.scale_factor / factor

    def set_bounding_box(self, bounding_box):
        self.original_bounding_box = deepcopy(np.array(bounding_box, dtype=np.float64))
        self.bounding_box = deepcopy(np.array(bounding_box, dtype=np.float64))
        self.bounding_box_vertices, self.bounding_box_edges = self.make_box(self.bounding_box)
        self.original_bounding_box_vertices, self.original_bounding_box_edges = self.make_box(self.original_bounding_box)
    
    def set_curr_slice(self, curr_slice):
        self.curr_slice = curr_slice
        self.original_curr_slice_vertices = np.array([
            [self.curr_slice, self.original_bounding_box_vertices[0][1], self.original_bounding_box_vertices[0][2]],
            [self.curr_slice, self.original_bounding_box_vertices[2][1], self.original_bounding_box_vertices[2][2]],
            [self.curr_slice, self.original_bounding_box_vertices[6][1], self.original_bounding_box_vertices[6][2]],
            [self.curr_slice, self.original_bounding_box_vertices[4][1], self.original_bounding_box_vertices[4][2]]
        ], dtype=np.float64)
        self.curr_slice_vertices = deepcopy(self.original_curr_slice_vertices)

    def set_roi_box(self, roi_box):
        roi_box_width = roi_box[1] - roi_box[0]
        roi_box_height = roi_box[3] - roi_box[2]
        roi_box_depth = roi_box[5] - roi_box[4]
        max_roi_box_dim = max(roi_box_width, roi_box_height, roi_box_depth)
        self.scale_factor = ROI_BOX_RESOLUTION/max_roi_box_dim
        self.original_roi_box = deepcopy(np.array(roi_box, dtype=np.float64))

        self.roi_box = deepcopy(np.array(roi_box, dtype=np.float64))
        self.original_roi_box_vertices, self.original_roi_box_edges = self.make_box(self.original_roi_box)
        self.roi_box_vertices, self.roi_box_edges = self.make_box(self.roi_box)

        self.roi_displacement = deepcopy((self.roi_box_vertices[0]+self.roi_box_vertices[7])/2.0)
        self.volume_displacement = deepcopy((self.roi_box_vertices[7]-self.roi_box_vertices[0])/2.0)

    def apply_roi_displacement(self):
        self.bounding_box_vertices = self.original_bounding_box_vertices - self.roi_displacement
        self.curr_slice_vertices = self.original_curr_slice_vertices - self.roi_displacement
        self.roi_box_vertices = self.original_roi_box_vertices - self.roi_displacement

    def rotate_boxes(self):
        # rotate bounding box and roi box
        for i in range(len(self.bounding_box_vertices)):
            self.bounding_box_vertices[i] = np.array([self.bounding_box_vertices[i][2],self.bounding_box_vertices[i][0],self.bounding_box_vertices[i][1]])
            if self.roi_box is not None:
                self.roi_box_vertices[i] = np.array([self.roi_box_vertices[i][2],self.roi_box_vertices[i][0],self.roi_box_vertices[i][1]])
                pass
        for i in range(len(self.curr_slice_vertices)):
            self.curr_slice_vertices[i] = np.array([self.curr_slice_vertices[i][2],self.curr_slice_vertices[i][0],self.curr_slice_vertices[i][1]])

        return

    def generate_mesh_multithread(self):
        # put current parameters to the queue
        self.queue.put((self.volume, self.isovalue))

    def update_volume(self, volume):
        self.set_volume(volume)
        
    def adjust_volume(self):
        if self.generate_mesh_under_way == True:
            return
        
        if self.generated_data is None:
            return
        
        if self.adjust_volume_under_way == True:
            return
        
        self.adjust_volume_under_way = True
        self.vertices = deepcopy(self.generated_data['vertices'])
        self.triangles = deepcopy(self.generated_data['triangles'])
        self.vertex_normals = deepcopy(self.generated_data['vertex_normals'])

        self.scale_volume()
        self.apply_volume_displacement()
        self.rotate_volume()

        self.adjust_volume_under_way = False

    def set_volume(self, volume):
        self.volume = volume

    def show_buttons(self):
        self.cbxRotation.show()
        self.moveButton.show()
        self.expandButton.show()
        self.shrinkButton.show()

    def generate_mesh(self):
        self.generate_mesh_under_way = True

        max_len = max(self.volume.shape)
        self.scale_factor = 50.0/max_len

        volume = ndimage.zoom(self.volume, self.scale_factor, order=1)
        if self.is_inverse:
            volume = 255 - volume
            isovalue = 255 - self.isovalue
        else:
            isovalue = self.isovalue
        vertices, triangles = mcubes.marching_cubes(volume, isovalue)

        face_normals = []
        for triangle in triangles:
            v0 = vertices[triangle[0]]
            v1 = vertices[triangle[1]]
            v2 = vertices[triangle[2]]
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            norm = np.linalg.norm(normal)
            if norm == 0:
                normal = np.array([0, 0, 0])
            else:
                normal /= np.linalg.norm(normal)
            face_normals.append(normal)

        vertex_normals = np.zeros(vertices.shape)

        # Calculate vertex normals by averaging face normals
        for i, triangle in enumerate(triangles):
            for vertex_index in triangle:
                vertex_normals[vertex_index] += face_normals[i]

        # Normalize vertex normals
        for i in range(len(vertex_normals)):
            if np.linalg.norm(vertex_normals[i]) != 0:
                vertex_normals[i] /= np.linalg.norm(vertex_normals[i])
            else:
                vertex_normals[i] = np.array([0.0, 0.0, 0.0])
        
        self.generated_data = {}
        self.generated_data['vertices'] = vertices
        self.generated_data['triangles'] = triangles
        self.generated_data['vertex_normals'] = vertex_normals

        self.gl_list_generated = False
        self.generate_mesh_under_way = False

    def apply_volume_displacement(self):
        if len(self.vertices) > 0:        
            self.vertices = deepcopy( self.vertices - self.volume_displacement )

    def rotate_volume(self):
        # rotate vertices
        if len(self.vertices) > 0:        
            #print(self.vertices.shape)
            for i in range(len(self.vertices)):
                #print("vertices[i]", i, self.vertices[i])
                self.vertices[i] = np.array([self.vertices[i][2],self.vertices[i][0],self.vertices[i][1]])
                self.vertex_normals[i] = np.array([self.vertex_normals[i][2],self.vertex_normals[i][0],self.vertex_normals[i][1]])

        #print(self.bounding_box_vertices[0])
    def scale_volume(self):
        if len(self.vertices) > 0:        
            self.vertices /= 10.0
        return

    def set_isovalue(self, isovalue):
        self.isovalue = isovalue

    def read_images_from_folder(self,folder):
        images = []
        try:
            for filename in os.listdir(folder):
                try:
                    # read images using Pillow
                    img = Image.open(os.path.join(folder,filename))
                    #img = cv2.imread(os.path.join(folder,filename),0)
                    if img is not None:
                        images.append(np.array(img))
                except Exception as e:
                    logger.error(f"Error reading image {filename}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error accessing folder {folder}: {e}")
            return np.array([])
        return np.array(images)

    def generate_mesh_timeout(self):
        #print("timout2")
        if not self.queue.empty() and self.generate_mesh_under_way == False:
            while not self.queue.empty():
                (volume, isovalue) = self.queue.get()
            self.volume = volume
            self.isovalue = isovalue
            self.worker = Worker(self.generate_mesh) # Any other args, kwargs are passed to the run function
            self.worker.signals.result.connect(self.print_output)
            self.worker.signals.finished.connect(self.thread_complete)
            self.worker.signals.progress.connect(self.progress_fn)
            self.threadpool.start(self.worker)
        self.updateGL()

    def rotate_timeout(self):
        #print("timout1")
        #print("timeout, auto_rotate:", self.auto_rotate)
        if self.auto_rotate == False:
            #print "no rotate"
            return
        if self.is_dragging:
            #print "dragging"
            return

        self.rotate_x += 1
        self.updateGL()

    def mousePressEvent(self, event):
        self.down_x = event.x()
        self.down_y = event.y()
        if event.buttons() == Qt.LeftButton:
            self.view_mode = ROTATE_MODE
        elif event.buttons() == Qt.RightButton:
            self.view_mode = ZOOM_MODE
        elif event.buttons() == Qt.MiddleButton:
            self.view_mode = PAN_MODE

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.curr_x = event.x()
        self.curr_y = event.y()

        if event.button() == Qt.LeftButton:
                self.rotate_x += self.temp_rotate_x
                self.rotate_y += self.temp_rotate_y
                self.rotate_y = 0
                self.temp_rotate_x = 0
                self.temp_rotate_y = 0
        elif event.button() == Qt.RightButton:
            self.dolly += self.temp_dolly 
            self.temp_dolly = 0
        elif event.button() == Qt.MiddleButton:
            self.pan_x += self.temp_pan_x
            self.pan_y += self.temp_pan_y
            self.temp_pan_x = 0
            self.temp_pan_y = 0
        self.view_mode = VIEW_MODE
        self.updateGL()

    def mouseMoveEvent(self, event):
        self.curr_x = event.x()
        self.curr_y = event.y()

        if event.buttons() == Qt.LeftButton and self.view_mode == ROTATE_MODE:
            self.is_dragging = True
            self.temp_rotate_x = self.curr_x - self.down_x
            self.temp_rotate_y = self.curr_y - self.down_y
        elif event.buttons() == Qt.RightButton and self.view_mode == ZOOM_MODE:
            self.is_dragging = True
            self.temp_dolly = ( self.curr_y - self.down_y ) / 100.0
        elif event.buttons() == Qt.MiddleButton and self.view_mode == PAN_MODE:
            self.is_dragging = True
            self.temp_pan_x = self.curr_x - self.down_x
            self.temp_pan_y = self.curr_y - self.down_y
        self.updateGL()

    def wheelEvent(self, event):
        self.dolly -= event.angleDelta().y() / 240.0
        self.updateGL()


    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_COLOR_MATERIAL)
        glShadeModel(GL_SMOOTH)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (width / height), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)

    def draw_box(self, box_vertices, box_edges, color=[1.0, 0.0, 0.0]):
        glColor3f(color[0], color[1], color[2])
        v = box_vertices
        glBegin(GL_LINES)
        for e in box_edges:
            for idx in e:
                glVertex3fv(v[idx])
        glEnd()


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()


        glMatrixMode(GL_MODELVIEW)
        glClearColor(0.94,0.94,0.94, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_LIGHTING)

        # Set camera position and view
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        glTranslatef(0, 0, -5.0 + self.dolly + self.temp_dolly)   # x, y, z 
        glTranslatef((self.pan_x + self.temp_pan_x)/100.0, (self.pan_y + self.temp_pan_y)/-100.0, 0.0)

        # rotate viewpoint
        glRotatef(self.rotate_y + self.temp_rotate_y, 1.0, 0.0, 0.0)
        glRotatef(self.rotate_x + self.temp_rotate_x, 0.0, 1.0, 0.0)

        if len(self.triangles) == 0:
            return

        glClearColor(0.2,0.2,0.2, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        ''' render bounding box '''
        glDisable(GL_LIGHTING)
        if self.bounding_box is not None:
            glLineWidth(1)
            self.draw_box(self.bounding_box_vertices, self.bounding_box_edges, color=[0.0, 0.0, 1.0])

        ''' render roi box '''
        if self.roi_box is not None:
            if not (self.roi_box_vertices == self.bounding_box_vertices).all():
                glLineWidth(2)
                self.draw_box(self.roi_box_vertices, self.roi_box_edges, color=[1.0, 0.0, 0.0])
        glEnable(GL_LIGHTING)

        ''' render 3d model '''
        glColor3f(0.0, 1.0, 0.0)
        if self.gl_list_generated == False:
            self.generate_gl_list()

        self.render_gl_list()

        ''' draw current slice plane '''
        glColor4f(0.0, 1.0, 0.0, 0.5) 
        glBegin(GL_QUADS)
        for vertex in self.curr_slice_vertices:
            glVertex3fv(vertex)
        glEnd()

        return

    def render_gl_list(self):
        if self.gl_list_generated == False:
            return
        glCallList(self.gl_list)
        return

    def generate_gl_list(self):
        self.gl_list = glGenLists(1)
        glNewList(self.gl_list, GL_COMPILE)

        # Render the 3D surface
        glBegin(GL_TRIANGLES)
        
        for triangle in self.triangles:
            for vertex in triangle:
                glNormal3fv(self.vertex_normals[vertex])
                glVertex3fv(self.vertices[vertex])
        glEnd()
        glEndList()
        self.gl_list_generated = True


class InfoDialog(QDialog):
    '''
    InfoDialog shows application information.
    '''
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add title
        title_label = QLabel("<h2>CTHarvester</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Add version info
        version_label = QLabel(self.tr("Version {}").format(PROGRAM_VERSION))
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # Add description
        desc_label = QLabel(self.tr("CT Image Stack Processing Tool"))
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add copyright
        copyright_label = QLabel(self.tr(PROGRAM_COPYRIGHT))
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # Add GitHub link
        github_label = QLabel('<a href="https://github.com/jikhanjung/CTHarvester">GitHub Repository</a>')
        github_label.setOpenExternalLinks(True)
        github_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(github_label)
        
        # Add spacing
        layout.addSpacing(20)
        
        # Add OK button
        button_layout = QHBoxLayout()
        btn_ok = QPushButton(self.tr("OK"))
        btn_ok.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setWindowTitle(self.tr("About CTHarvester"))
        self.setFixedSize(300, 200)
        self.move(self.parent.pos() + QPoint(150, 150))


class PreferencesDialog(QDialog):
    '''
    PreferencesDialog shows preferences.

    Args:
        None

    Attributes:
        well..
    '''
    def __init__(self,parent):
        super().__init__()
        self.parent = parent
        self.m_app = QApplication.instance()

        self.rbRememberGeometryYes = QRadioButton(self.tr("Yes"))
        self.rbRememberGeometryYes.setChecked(self.m_app.remember_geometry)
        self.rbRememberGeometryYes.clicked.connect(self.on_rbRememberGeometryYes_clicked)
        self.rbRememberGeometryNo = QRadioButton(self.tr("No"))
        self.rbRememberGeometryNo.setChecked(not self.m_app.remember_geometry)
        self.rbRememberGeometryNo.clicked.connect(self.on_rbRememberGeometryNo_clicked)

        self.rbRememberDirectoryYes = QRadioButton(self.tr("Yes"))
        self.rbRememberDirectoryYes.setChecked(self.m_app.remember_directory)
        self.rbRememberDirectoryYes.clicked.connect(self.on_rbRememberDirectoryYes_clicked)
        self.rbRememberDirectoryNo = QRadioButton(self.tr("No"))
        self.rbRememberDirectoryNo.setChecked(not self.m_app.remember_directory)
        self.rbRememberDirectoryNo.clicked.connect(self.on_rbRememberDirectoryNo_clicked)

        self.gbRememberGeometry = QGroupBox()
        self.gbRememberGeometry.setLayout(QHBoxLayout())
        self.gbRememberGeometry.layout().addWidget(self.rbRememberGeometryYes)
        self.gbRememberGeometry.layout().addWidget(self.rbRememberGeometryNo)

        self.gbRememberDirectory = QGroupBox()
        self.gbRememberDirectory.setLayout(QHBoxLayout())
        self.gbRememberDirectory.layout().addWidget(self.rbRememberDirectoryYes)
        self.gbRememberDirectory.layout().addWidget(self.rbRememberDirectoryNo)

        self.comboLang = QComboBox()
        self.comboLang.addItem(self.tr("English"))
        self.comboLang.addItem(self.tr("Korean"))
        self.comboLang.currentIndexChanged.connect(self.comboLangIndexChanged)

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.setLayout(self.main_layout)
        self.form_layout.addRow(self.tr("Remember Geometry"), self.gbRememberGeometry)
        self.form_layout.addRow(self.tr("Remember Directory"), self.gbRememberDirectory)
        self.form_layout.addRow(self.tr("Language"), self.comboLang)
        self.button_layout = QHBoxLayout()
        self.btnOK = QPushButton(self.tr("OK"))
        self.btnOK.clicked.connect(self.on_btnOK_clicked)
        self.btnCancel = QPushButton(self.tr("Cancel"))
        self.btnCancel.clicked.connect(self.on_btnCancel_clicked)
        self.button_layout.addWidget(self.btnOK)
        self.button_layout.addWidget(self.btnCancel)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.button_layout)
        self.setWindowTitle(self.tr("CTHarvester - Preferences"))
        self.setGeometry(QRect(100, 100, 320, 180))
        self.move(self.parent.pos()+QPoint(100,100))

        self.read_settings()

    def on_btnOK_clicked(self):
        self.save_settings()
        self.close()

    def on_btnCancel_clicked(self):
        self.close()

    def on_rbRememberGeometryYes_clicked(self):
        self.m_app.remember_geometry = True

    def on_rbRememberGeometryNo_clicked(self):
        self.m_app.remember_geometry = False

    def on_rbRememberDirectoryYes_clicked(self):
        self.m_app.remember_directory = True

    def on_rbRememberDirectoryNo_clicked(self):
        self.m_app.remember_directory = False

    def comboLangIndexChanged(self, index):
        if index == 0:
            self.m_app.language = "en"
        elif index == 1:
            self.m_app.language = "ko"
        #print("self.language:", self.m_app.language)

    def update_language(self):
        #print("update_language", self.m_app.language)
        translator = QTranslator()
        translator.load(resource_path('CTHarvester_{}.qm').format(self.m_app.language))
        self.m_app.installTranslator(translator)
        
        self.rbRememberGeometryYes.setText(self.tr("Yes"))
        self.rbRememberGeometryNo.setText(self.tr("No"))
        self.rbRememberDirectoryYes.setText(self.tr("Yes"))
        self.rbRememberDirectoryNo.setText(self.tr("No"))
        self.gbRememberGeometry.setTitle("")
        self.gbRememberDirectory.setTitle("")
        self.comboLang.setItemText(0, self.tr("English"))
        self.comboLang.setItemText(1, self.tr("Korean"))
        self.btnOK.setText(self.tr("OK"))
        self.btnCancel.setText(self.tr("Cancel"))
        self.form_layout.labelForField(self.gbRememberGeometry).setText(self.tr("Remember Geometry"))
        self.form_layout.labelForField(self.gbRememberDirectory).setText(self.tr("Remember Directory"))
        self.form_layout.labelForField(self.comboLang).setText(self.tr("Language"))
        self.setWindowTitle(self.tr("CTHarvester - Preferences"))
        self.parent.update_language()
        self.parent.update_status()

    def read_settings(self):
        try:
            self.m_app.remember_geometry = value_to_bool(self.m_app.settings.value("Remember geometry", True))
            self.m_app.remember_directory = value_to_bool(self.m_app.settings.value("Remember directory", True))
            self.m_app.language = self.m_app.settings.value("Language", "en")

            self.rbRememberGeometryYes.setChecked(self.m_app.remember_geometry)
            self.rbRememberGeometryNo.setChecked(not self.m_app.remember_geometry)
            self.rbRememberDirectoryYes.setChecked(self.m_app.remember_directory)
            self.rbRememberDirectoryNo.setChecked(not self.m_app.remember_directory)

            if self.m_app.language == "en":
                self.comboLang.setCurrentIndex(0)
            elif self.m_app.language == "ko":
                self.comboLang.setCurrentIndex(1)
            self.update_language()
        except Exception as e:
            logger.error(f"Error reading settings: {e}")
            # Use default values if settings can't be read
            self.m_app.remember_geometry = True
            self.m_app.remember_directory = True
            self.m_app.language = "en"

    def save_settings(self):
        try:
            self.m_app.settings.setValue("Remember geometry", self.m_app.remember_geometry)
            self.m_app.settings.setValue("Remember directory", self.m_app.remember_directory)
            self.m_app.settings.setValue("Language", self.m_app.language)
            self.update_language()
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

class ProgressDialog(QDialog):
    def __init__(self,parent):
        super().__init__()
        self.setWindowTitle(self.tr("CTHarvester - Progress Dialog"))
        self.parent = parent
        self.m_app = QApplication.instance()
        self.setGeometry(QRect(100, 100, 320, 180))
        self.move(self.parent.pos()+QPoint(100,100))

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(50,50, 50, 50)

        self.lbl_text = QLabel(self)
        self.pb_progress = QProgressBar(self)
        self.pb_progress.setValue(0)
        self.stop_progress = False
        self.btnStop = QPushButton(self)
        self.btnStop.setText(self.tr("Stop"))
        self.btnStop.clicked.connect(self.set_stop_progress)
        self.btnStop.hide()
        self.layout.addWidget(self.lbl_text)
        self.layout.addWidget(self.pb_progress)
        self.setLayout(self.layout)

    def set_stop_progress(self):
        self.stop_progress = True

    def set_progress_text(self,text_format):
        self.text_format = text_format

    def set_max_value(self,max_value):
        self.max_value = max_value

    def set_curr_value(self,curr_value):
        self.curr_value = curr_value
        self.pb_progress.setValue(int((self.curr_value/float(self.max_value))*100))
        self.lbl_text.setText(self.text_format.format(self.curr_value, self.max_value))
        self.update()
        QApplication.processEvents()

    def update_language(self):
        translator = QTranslator()
        translator.load(resource_path('CTHarvester_{}.qm').format(self.m_app.language))
        self.m_app.installTranslator(translator)
        
        self.setWindowTitle(self.tr("CTHarvester - Progress Dialog"))
        self.btnStop.setText(self.tr("Stop"))


class ObjectViewer2D(QLabel):
    def __init__(self, widget):
        super(ObjectViewer2D, self).__init__(widget)
        self.setMinimumSize(512,512)
        self.image_canvas_ratio = 1.0
        self.scale = 1.0
        self.mouse_down_x = 0
        self.mouse_down_y = 0
        self.mouse_curr_x = 0
        self.mouse_curr_y = 0
        self.edit_mode = MODE['ADD_BOX']
        self.orig_pixmap = None
        self.curr_pixmap = None
        self.distance_threshold = self._2imgx(5)
        self.setMouseTracking(True)
        self.object_dialog = None
        self.top_idx = -1
        self.bottom_idx = -1
        self.curr_idx = 0
        self.move_x = 0
        self.move_y = 0
        self.threed_view = None
        self.isovalue = 60
        self.is_inverse = False
        self.reset_crop()

    def get_pixmap_geometry(self):
        if self.curr_pixmap:
            return self.curr_pixmap.rect()

    def set_isovalue(self, isovalue):
        self.isovalue = isovalue
        self.update()

    def set_threed_view(self, threed_view):
        self.threed_view = threed_view

    def reset_crop(self):
        self.crop_from_x = -1
        self.crop_from_y = -1
        self.crop_to_x = -1
        self.crop_to_y = -1
        self.temp_x1 = -1
        self.temp_y1 = -1
        self.temp_x2 = -1
        self.temp_y2 = -1
        self.edit_x1 = False
        self.edit_x2 = False
        self.edit_y1 = False
        self.edit_y2 = False
        self.canvas_box = None

    def _2canx(self, coord):
        return round((float(coord) / self.image_canvas_ratio) * self.scale)
    def _2cany(self, coord):
        return round((float(coord) / self.image_canvas_ratio) * self.scale)
    def _2imgx(self, coord):
        return round(((float(coord)) / self.scale) * self.image_canvas_ratio)
    def _2imgy(self, coord):
        return round(((float(coord)) / self.scale) * self.image_canvas_ratio)

    def set_mode(self, mode):
        self.edit_mode = mode
        if self.edit_mode == MODE['ADD_BOX']:
            self.setCursor(Qt.CrossCursor)
        elif self.edit_mode in [ MODE['MOVE_BOX'], MODE['MOVE_BOX_READY'], MODE['MOVE_BOX_PROGRESS'] ]:
            self.setCursor(Qt.OpenHandCursor)
        elif self.edit_mode in [ MODE['EDIT_BOX'], MODE['EDIT_BOX_READY'], MODE['EDIT_BOX_PROGRESS'] ]:
            pass
        else:
            self.setCursor(Qt.ArrowCursor)

    def distance_check(self, x, y):
        x = self._2imgx(x)
        y = self._2imgy(y)
        if self.crop_from_x - self.distance_threshold >= x or self.crop_to_x + self.distance_threshold <= x or self.crop_from_y - self.distance_threshold >= y or self.crop_to_y + self.distance_threshold <= y:
            self.edit_x1 = False
            self.edit_x2 = False
            self.edit_y1 = False
            self.edit_y2 = False
            self.inside_box = False
        else:
            if self.crop_from_x + self.distance_threshold <= x and self.crop_to_x - self.distance_threshold >= x \
                and self.crop_from_y + self.distance_threshold <= y and self.crop_to_y - self.distance_threshold >= y:
                self.edit_x1 = False
                self.edit_x2 = False
                self.edit_y1 = False
                self.edit_y2 = False
                self.inside_box = True
                #print("move box ready")
            else:
                self.inside_box = False
            if abs(self.crop_from_x - x) <= self.distance_threshold:
                self.edit_x1 = True
            else:
                self.edit_x1 = False
            if abs(self.crop_to_x - x) <= self.distance_threshold:
                self.edit_x2 = True
            else:
                self.edit_x2 = False
            if abs(self.crop_from_y - y) <= self.distance_threshold:
                self.edit_y1 = True
            else:
                self.edit_y1 = False
            if abs(self.crop_to_y - y) <= self.distance_threshold:
                self.edit_y2 = True
            else:
                self.edit_y2 = False
        self.set_cursor_mode()

    def set_cursor_mode(self):
        if self.edit_x1 and self.edit_y1:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edit_x2 and self.edit_y2:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edit_x1 and self.edit_y2:
            self.setCursor(Qt.SizeBDiagCursor)
        elif self.edit_x2 and self.edit_y1:
            self.setCursor(Qt.SizeBDiagCursor)
        elif self.edit_x1 or self.edit_x2:
            self.setCursor(Qt.SizeHorCursor)
        elif self.edit_y1 or self.edit_y2:
            self.setCursor(Qt.SizeVerCursor)
        elif self.inside_box:
            self.setCursor(Qt.OpenHandCursor)
        else: 
            self.setCursor(Qt.ArrowCursor)

    def mouseMoveEvent(self, event):
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(event)
        if me.buttons() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX']:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.temp_x2 = self._2imgx(self.mouse_curr_x)
                self.temp_y2 = self._2imgy(self.mouse_curr_y)
            elif self.edit_mode in [ MODE['EDIT_BOX_PROGRESS'], MODE['MOVE_BOX_PROGRESS'] ]:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.move_x = self.mouse_curr_x - self.mouse_down_x
                self.move_y = self.mouse_curr_y - self.mouse_down_y
            self.calculate_resize()
        else:
            if self.edit_mode == MODE['EDIT_BOX']:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    self.set_mode(MODE['EDIT_BOX_READY'])
                elif self.inside_box:
                    self.set_mode(MODE['MOVE_BOX_READY'])
            elif self.edit_mode == MODE['EDIT_BOX_READY']:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    pass #self.set_mode(MODE['EDIT_BOX_PROGRESS'])
                elif self.inside_box:
                    self.set_mode(MODE['MOVE_BOX_READY'])
                else:
                    self.set_mode(MODE['EDIT_BOX'])
            elif self.edit_mode == MODE['MOVE_BOX_READY']:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    self.set_mode(MODE['EDIT_BOX_READY'])
                elif self.inside_box == False:
                    self.set_mode(MODE['EDIT_BOX'])
        self.object_dialog.update_status()
        self.repaint()

    def mousePressEvent(self, event):
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(event)
        if me.button() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX'] or self.edit_mode == MODE['EDIT_BOX']:
                self.set_mode(MODE['ADD_BOX'])
                img_x = self._2imgx(me.x())
                img_y = self._2imgy(me.y())
                if img_x < 0 or img_x > self.orig_pixmap.width() or img_y < 0 or img_y > self.orig_pixmap.height():
                    return
                self.temp_x1 = img_x
                self.temp_y1 = img_y
                self.temp_x2 = img_x
                self.temp_y2 = img_y
            elif self.edit_mode == MODE['EDIT_BOX_READY']:
                self.mouse_down_x = me.x()
                self.mouse_down_y = me.y()
                self.move_x = 0
                self.move_y = 0
                self.temp_x1 = self.crop_from_x
                self.temp_y1 = self.crop_from_y
                self.temp_x2 = self.crop_to_x
                self.temp_y2 = self.crop_to_y
                self.set_mode(MODE['EDIT_BOX_PROGRESS'])
            elif self.edit_mode == MODE['MOVE_BOX_READY']:
                self.mouse_down_x = me.x()
                self.mouse_down_y = me.y()
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.move_x = 0
                self.move_y = 0
                self.temp_x1 = self.crop_from_x
                self.temp_y1 = self.crop_from_y
                self.temp_x2 = self.crop_to_x
                self.temp_y2 = self.crop_to_y
                self.set_mode(MODE['MOVE_BOX_PROGRESS'])
        self.object_dialog.update_status()
        self.repaint()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(ev)
        if self.mouse_down_x == me.x() and self.mouse_down_y == me.y():
            return
        if me.button() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX']:
                img_x = self._2imgx(self.mouse_curr_x)
                img_y = self._2imgy(self.mouse_curr_y)
                if img_x < 0 or img_x > self.orig_pixmap.width() or img_y < 0 or img_y > self.orig_pixmap.height():
                    return
                self.crop_from_x = min(self.temp_x1, self.temp_x2)
                self.crop_to_x = max(self.temp_x1, self.temp_x2)
                self.crop_from_y = min(self.temp_y1, self.temp_y2)
                self.crop_to_y = max(self.temp_y1, self.temp_y2)
                self.set_mode(MODE['EDIT_BOX'])
            elif self.edit_mode == MODE['EDIT_BOX_PROGRESS']:
                if self.edit_x1:
                    self.crop_from_x = min(self.temp_x1, self.temp_x2) + self._2imgx(self.move_x)
                if self.edit_x2:
                    self.crop_to_x = max(self.temp_x1, self.temp_x2) + self._2imgx(self.move_x)
                if self.edit_y1:
                    self.crop_from_y = min(self.temp_y1, self.temp_y2) + self._2imgy(self.move_y)
                if self.edit_y2:
                    self.crop_to_y = max(self.temp_y1, self.temp_y2) + self._2imgy(self.move_y)
                self.move_x = 0
                self.move_y = 0
                self.set_mode(MODE['EDIT_BOX'])
            elif self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                self.crop_from_x = self.temp_x1 + self._2imgx(self.move_x)
                self.crop_to_x = self.temp_x2 + self._2imgx(self.move_x)
                self.crop_from_y = self.temp_y1 + self._2imgy(self.move_y)
                self.crop_to_y = self.temp_y2 + self._2imgy(self.move_y)
                self.move_x = 0
                self.move_y = 0
                self.set_mode(MODE['MOVE_BOX_READY'])

            from_x = min(self.crop_from_x, self.crop_to_x)
            to_x = max(self.crop_from_x, self.crop_to_x)
            from_y = min(self.crop_from_y, self.crop_to_y)
            to_y = max(self.crop_from_y, self.crop_to_y)
            self.crop_from_x = from_x
            self.crop_from_y = from_y
            self.crop_to_x = to_x
            self.crop_to_y = to_y
            self.canvas_box = QRect(self._2canx(from_x), self._2cany(from_y), self._2canx(to_x - from_x), self._2cany(to_y - from_y))
            self.calculate_resize()

        self.object_dialog.update_status()
        self.object_dialog.update_3D_view(True)
        self.repaint()

    def get_crop_area(self, imgxy = False):
        from_x = -1
        to_x = -1
        from_y = -1
        to_y = -1
        if self.edit_mode == MODE['ADD_BOX']:
            from_x = self._2canx(min(self.temp_x1, self.temp_x2))
            to_x = self._2canx(max(self.temp_x1, self.temp_x2))
            from_y = self._2cany(min(self.temp_y1, self.temp_y2))
            to_y = self._2cany(max(self.temp_y1, self.temp_y2))
            #return [from_x, from_y, to_x, to_y]
        elif self.edit_mode in [ MODE['EDIT_BOX_PROGRESS'], MODE['MOVE_BOX_PROGRESS'] ]:
            from_x = self._2canx(min(self.temp_x1, self.temp_x2)) 
            to_x = self._2canx(max(self.temp_x1, self.temp_x2))
            from_y = self._2cany(min(self.temp_y1, self.temp_y2))
            to_y = self._2cany(max(self.temp_y1, self.temp_y2))
            if self.edit_x1 or self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                from_x += self.move_x
            if self.edit_x2 or self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                to_x += self.move_x
            if self.edit_y1 or self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                from_y += self.move_y
            if self.edit_y2 or self.edit_mode == MODE['MOVE_BOX_PROGRESS']:
                to_y += self.move_y
        elif self.crop_from_x > -1:
            from_x = self._2canx(min(self.crop_from_x, self.crop_to_x))
            to_x = self._2canx(max(self.crop_from_x, self.crop_to_x))
            from_y = self._2cany(min(self.crop_from_y, self.crop_to_y))
            to_y = self._2cany(max(self.crop_from_y, self.crop_to_y))

        if imgxy == True:
            if from_x <= 0 and from_y <= 0 and to_x <= 0 and to_y <= 0 and self.orig_pixmap:
                return [ 0,0,self.orig_pixmap.width(),self.orig_pixmap.height()]
            else:
                return [self._2imgx(from_x), self._2imgy(from_y), self._2imgx(to_x), self._2imgy(to_y)]
        else:
            return [from_x, from_y, to_x, to_y]


    def paintEvent(self, event):
        painter = QPainter(self)
        if self.curr_pixmap is not None:
            painter.drawPixmap(0,0,self.curr_pixmap)

        if self.curr_idx > self.top_idx or self.curr_idx < self.bottom_idx:
            painter.setPen(QPen(QColor(128,0,0), 2, Qt.DotLine))
        else:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        [ x1, y1, x2, y2 ] = self.get_crop_area()
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def apply_threshold_and_colorize(self,qt_pixmap, threshold, color=np.array([0, 255, 0], dtype=np.uint8)):
        qt_image = qt_pixmap.toImage()
        width = qt_image.width()
        height = qt_image.height()
        buffer = qt_image.bits()
        buffer.setsize(qt_image.byteCount())
        qt_image_array = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
        
        # Extract the alpha channel (if present)
        if qt_image_array.shape[2] == 4:
            qt_image_array = qt_image_array[:, :, :3]  # Remove the alpha channel

        color = np.array([0, 255, 0], dtype=np.uint8)

        # Check the dtype of image_array
        if qt_image_array.dtype != np.uint8:
            raise ValueError("image_array should have dtype np.uint8")

        # Check the threshold value (example threshold)
        threshold = self.isovalue
        if not 0 <= threshold <= 255:
            raise ValueError("Threshold should be in the range 0-255")
        
        [ x1, y1, x2, y2 ] = self.get_crop_area()
        if x1 == x2 == y1 == y2 == 0:
            # whole pixmap is selected
            x1, x2, y1, y2 = 0, qt_image_array.shape[1], 0, qt_image_array.shape[0]

        if self.is_inverse:
            region_mask = (qt_image_array[y1:y2+1, x1:x2+1, 0] <= threshold)
        else:
            region_mask = (qt_image_array[y1:y2+1, x1:x2+1, 0] > threshold)

        # Apply the threshold and colorize
        qt_image_array[y1:y2+1, x1:x2+1][region_mask] = color

        # Convert the NumPy array back to a QPixmap
        height, width, channel = qt_image_array.shape
        bytes_per_line = 3 * width
        qt_image = QImage(np.copy(qt_image_array.data), width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Convert the QImage to a QPixmap
        modified_pixmap = QPixmap.fromImage(qt_image)
        return modified_pixmap

    def set_image(self,file_path):
        #print("set_image", file_path)
        # check if file exists
        if not os.path.exists(file_path):
            self.curr_pixmap = None
            self.orig_pixmap = None
            self.crop_from_x = -1
            self.crop_from_y = -1
            self.crop_to_x = -1
            self.crop_to_y = -1
            self.canvas_box = None
            return
        self.fullpath = file_path
        self.curr_pixmap = self.orig_pixmap = QPixmap(file_path)

        self.setPixmap(self.curr_pixmap)
        self.calculate_resize()
        if self.canvas_box:
            self.crop_from_x = self._2imgx(self.canvas_box.x())
            self.crop_from_y = self._2imgy(self.canvas_box.y())
            self.crop_to_x = self._2imgx(self.canvas_box.x() + self.canvas_box.width())
            self.crop_to_y = self._2imgy(self.canvas_box.y() + self.canvas_box.height())

    def set_top_idx(self, top_idx):
        self.top_idx = top_idx

    def set_curr_idx(self, curr_idx):
        self.curr_idx = curr_idx

    def set_bottom_idx(self, bottom_idx):
        self.bottom_idx = bottom_idx

    def calculate_resize(self):
        #print("objectviewer calculate resize")
        if self.orig_pixmap is not None:
            self.distance_threshold = self._2imgx(DISTANCE_THRESHOLD)
            self.orig_width = self.orig_pixmap.width()
            self.orig_height = self.orig_pixmap.height()
            image_wh_ratio = self.orig_width / self.orig_height
            label_wh_ratio = self.width() / self.height()
            if image_wh_ratio > label_wh_ratio:
                self.image_canvas_ratio = self.orig_width / self.width()
            else:
                self.image_canvas_ratio = self.orig_height / self.height()

            self.curr_pixmap = self.orig_pixmap.scaled(int(self.orig_width*self.scale/self.image_canvas_ratio),int(self.orig_width*self.scale/self.image_canvas_ratio), Qt.KeepAspectRatio)
            if self.isovalue > 0 and self.curr_idx >= self.bottom_idx and self.curr_idx <= self.top_idx:
                self.curr_pixmap = self.apply_threshold_and_colorize(self.curr_pixmap, self.isovalue)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.calculate_resize()
        self.object_dialog.mcube_widget.reposition_self()

        if self.canvas_box:
            self.canvas_box = QRect(self._2canx(self.crop_from_x), self._2cany(self.crop_from_y), self._2canx(self.crop_to_x - self.crop_from_x), self._2cany(self.crop_to_y - self.crop_from_y))
        self.threed_view.resize_self()
        return super().resizeEvent(a0)

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
        self.dirname_layout.addWidget(self.edtDirname,stretch=1)
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
        self.slider = QLabeledSlider(Qt.Vertical)
        self.slider.setValue(0)
        self.slider.setEnabled(False)  # Disable until data is loaded
        self.range_slider = QLabeledRangeSlider(Qt.Vertical)
        self.range_slider.setValue((0,99))
        self.range_slider.setEnabled(False)  # Disable until data is loaded
        self.slider.setSingleStep(1)
        self.range_slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.sliderValueChanged)
        self.range_slider.valueChanged.connect(self.rangeSliderValueChanged)
        self.range_slider._slider.sliderReleased.connect(self.rangeSliderReleased)
        self.range_slider.setMinimumWidth(100)

        self.image_layout.addWidget(self.image_label,stretch=1)
        self.image_layout.addWidget(self.slider)
        self.image_layout.addWidget(self.range_slider)
        self.image_widget.setLayout(self.image_layout)
        self.image_layout.setContentsMargins(margin)

        self.threshold_slider = QLabeledSlider(Qt.Vertical)
        self.threshold_slider.setValue(60)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setSingleStep(1)
        self.threshold_slider.valueChanged.connect(self.slider2ValueChanged)
        self.threshold_slider.sliderReleased.connect(self.slider2SliderReleased)
        self.image_layout.addWidget(self.threshold_slider)

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
        self.progress_text_2_1 = self.tr("Creating rescaled images level {}...")
        self.progress_text_2_2 = self.tr("Creating rescaled images level {}... {}/{}")
        self.progress_text_3_1 = self.tr("Checking rescaled images level {}...")
        self.progress_text_3_2 = self.tr("Checking rescaled images level {}... {}/{}")

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
        self.progress_text_2_1 = self.tr("Creating rescaled images level {}...")
        self.progress_text_2_2 = self.tr("Creating rescaled images level {}... {}/{}")
        self.progress_text_3_1 = self.tr("Checking rescaled images level {}...")
        self.progress_text_3_2 = self.tr("Checking rescaled images level {}... {}/{}")

    def set_bottom(self):
        self.range_slider.setValue((self.slider.value(), self.range_slider.value()[1]))
        self.update_status()
    def set_top(self):
        self.range_slider.setValue((self.range_slider.value()[0], self.slider.value()))
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
        bounding_box = self.minimum_volume.shape
        bounding_box = [ 0, bounding_box[0]-1, 0, bounding_box[1]-1, 0, bounding_box[2]-1 ]
        curr_slice_val = self.slider.value()/float(self.slider.maximum()) * self.minimum_volume.shape[0]
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
        
        bounding_box = self.minimum_volume.shape
        bounding_box = [ 0, bounding_box[0]-1, 0, bounding_box[1]-1, 0, bounding_box[2]-1 ]
        curr_slice_val = self.slider.value()/float(self.slider.maximum()) * self.minimum_volume.shape[0]
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

        # get top and bottom idx
        top_idx = self.image_label.top_idx
        bottom_idx = self.image_label.bottom_idx

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
        from_x = int(from_x * smallest_level_info['width'])
        from_y = int(from_y * smallest_level_info['height'])
        to_x = int(to_x * smallest_level_info['width'])-1
        to_y = int(to_y * smallest_level_info['height'])-1

        volume = self.minimum_volume[bottom_idx:top_idx, from_y:to_y, from_x:to_x]
        return volume, [ bottom_idx, top_idx, from_y, to_y, from_x, to_x ]

    def export_3d_model(self):
        # open dir dialog for save
        logger.info("export_3d_model method called")
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
        logger.info("save_result method called")
        target_dirname = QFileDialog.getExistingDirectory(self, self.tr('Select directory to save'), self.edtDirname.text())
        if target_dirname == "":
            logger.info("Save cancelled")
            return
        logger.info(f"Saving results to: {target_dirname}")
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
            
            (bottom_idx, top_idx) = self.range_slider.value()
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
        curr_image_idx = self.slider.value()
        if size_idx < 0:
            size_idx = 0

        # get directory for size idx
        if size_idx == 0:
            dirname = self.edtDirname.text()
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + self.slider.value()).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
        else:
            dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            # get filename from level from idx
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + self.slider.value()).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']

        self.image_label.set_image(os.path.join(dirname, filename))
        self.image_label.set_curr_idx(self.slider.value())
        self.update_curr_slice()

    def reset_crop(self):
        self.image_label.set_curr_idx(self.slider.value())
        self.image_label.reset_crop()
        self.range_slider.setValue((self.slider.minimum(), self.slider.maximum()))
        self.canvas_box = None
        self.update_status()

    def update_status(self):
        ( bottom_idx, top_idx ) = self.range_slider.value()
        [ x1, y1, x2, y2 ] = self.image_label.get_crop_area(imgxy=True)
        count = ( top_idx - bottom_idx + 1 )
        #self.status_format = self.tr("Crop indices: {}~{}    Cropped image size: {}x{}    Estimated stack size: {} MB [{}]")
        status_text = self.status_text_format.format(bottom_idx, top_idx, x2 - x1, y2 - y1, x1, y1, x2, y2, round(count * (x2 - x1 ) * (y2 - y1 ) / 1024 / 1024 , 2), str(self.image_label.edit_mode))
        self.edtStatus.setText(status_text)

    def initializeComboSize(self):
        #print("initializeComboSize")
        self.comboLevel.clear()
        for level in self.level_info:
            self.comboLevel.addItem( level['name'])

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
            self.slider.setMaximum(image_count - 1)
            self.slider.setMinimum(0)
            self.slider.setValue(0)
            self.slider.setEnabled(True)  # Enable slider now that data is loaded
            self.range_slider.setRange(0,image_count - 1)
            self.range_slider.setValue((0, image_count - 1))
            self.range_slider.setEnabled(True)  # Enable range slider now that data is loaded
            self.curr_level_idx = 0
            self.prev_level_idx = 0
            self.initialized = True


        level_diff = self.prev_level_idx-self.curr_level_idx
        curr_idx = self.slider.value()
        curr_idx = int(curr_idx * (2**level_diff))

        (bottom_idx, top_idx) = self.range_slider.value()
        bottom_idx = int(bottom_idx * (2**level_diff))
        top_idx = int(top_idx * (2**level_diff))

        self.range_slider.setRange(0, image_count - 1)
        self.range_slider.setValue((bottom_idx, top_idx))

        self.slider.setMaximum(image_count -1)
        self.slider.setMinimum(0)
        self.slider.setValue(curr_idx)

        self.sliderValueChanged()
        self.update_status()
        self.update_3D_view(True)

    def create_thumbnail(self):
        logger.info("Starting thumbnail creation")
        """
        Creates a thumbnail of the image sequence by downsampling the images and averaging them.
        The resulting thumbnail is saved in a temporary directory and used to generate a mesh for visualization.
        """
        MAX_THUMBNAIL_SIZE = 512
        size =  max(int(self.settings_hash['image_width']), int(self.settings_hash['image_height']))
        width = int(self.settings_hash['image_width'])
        height = int(self.settings_hash['image_height'])

        i = 0
        # create temporary directory for thumbnail
        dirname = self.edtDirname.text()

        self.minimum_volume = []
        seq_begin = self.settings_hash['seq_begin']
        seq_end = self.settings_hash['seq_end']

        current_count = 0
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.update_language()
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        QApplication.setOverrideCursor(Qt.WaitCursor)

        while True:
            size /= 2
            width = int(width / 2)
            height = int(height / 2)

            if i == 0:
                from_dir = dirname
            else:
                from_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i))

            total_count = seq_end - seq_begin + 1
            self.progress_dialog.lbl_text.setText(self.progress_text_2_1.format(i+1))
            self.progress_dialog.pb_progress.setValue(0)

            # create thumbnail
            to_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i+1))
            if not os.path.exists(to_dir):
                os.makedirs(to_dir)
            last_count = 0

            for idx, seq in enumerate(range(seq_begin, seq_end+1, 2)):
                filename1 = self.settings_hash['prefix'] + str(seq).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
                filename2 = self.settings_hash['prefix'] + str(seq+1).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
                filename3 = os.path.join(to_dir, self.settings_hash['prefix'] + str(seq_begin + idx).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type'])

                if os.path.exists(filename3):  
                    self.progress_dialog.lbl_text.setText(self.progress_text_3_2.format(i+1, idx+1, int(total_count/2)))
                    self.progress_dialog.pb_progress.setValue(int(((idx+1)/float(int(total_count/2)))*100))
                    self.progress_dialog.update()
                    QApplication.processEvents()
                    if size < MAX_THUMBNAIL_SIZE:
                        try:
                            img= Image.open(os.path.join(from_dir,filename3))
                            #print("new_img_ops:", np.array(img).shape)
                            self.minimum_volume.append(np.array(img))
                        except Exception as e:
                            logger.error(f"Error opening thumbnail image {filename3}: {e}")
                    continue
                else:
                    self.progress_dialog.lbl_text.setText(self.progress_text_2_2.format(i+1, idx+1, int(total_count/2)))
                    self.progress_dialog.pb_progress.setValue(int(((idx+1)/float(int(total_count/2)))*100))
                    self.progress_dialog.update()
                    QApplication.processEvents()
                    # check if filename exist
                    img1 = None
                    if os.path.exists(os.path.join(from_dir, filename1)):
                        try:
                            img1 = Image.open(os.path.join(from_dir, filename1))
                            if img1.mode[0] == 'I':
                                img1 = Image.fromarray(np.divide(np.array(img1), 2**8-1)).convert('L')
                            elif img1.mode == 'P':
                                img1 = img1.convert('L')
                        except Exception as e:
                            logger.error(f"Error processing image {filename1}: {e}")
                            img1 = None
                    img2 = None
                    if os.path.exists(os.path.join(from_dir, filename2)):
                        try:
                            img2 = Image.open(os.path.join(from_dir, filename2))
                            if img2.mode[0] == 'I':
                                img2 = Image.fromarray(np.divide(np.array(img2), 2**8-1)).convert('L')
                            elif img2.mode == 'P':
                                img2 = img2.convert('L')
                        except Exception as e:
                            logger.error(f"Error processing image {filename2}: {e}")
                            img2 = None
                    # average two images
                    #print("img1:", img1.mode, "img2:", img2.mode)
                    if img1 is None or img2 is None:
                        last_count = -1
                        continue
                    try:
                        new_img_ops = ImageChops.add(img1, img2, scale=2.0)
                        # resize to half
                        new_img_ops = new_img_ops.resize((int(img1.width / 2), int(img1.height / 2)))
                        # save to temporary directory
                        new_img_ops.save(filename3)
                    except Exception as e:
                        logger.error(f"Error creating thumbnail {filename3}: {e}")
                        continue

                    if size < MAX_THUMBNAIL_SIZE:
                        #print("new_img_ops:", np.array(new_img_ops).shape)
                        self.minimum_volume.append(np.array(new_img_ops))

            i+= 1
            seq_end = int((seq_end - seq_begin) / 2) + seq_begin + last_count
            self.level_info.append( {'name': "Level " + str(i), 'width': width, 'height': height, 'seq_begin': seq_begin, 'seq_end': seq_end} )
            if size < MAX_THUMBNAIL_SIZE:
                self.minimum_volume = np.array(self.minimum_volume)
                bounding_box = self.minimum_volume.shape
                bounding_box = np.array([ 0, bounding_box[0]-1, 0, bounding_box[1]-1, 0, bounding_box[2]-1 ])
                curr_slice_val = self.slider.value()/float(self.slider.maximum()) * self.minimum_volume.shape[0]

                self.mcube_widget.update_boxes(bounding_box, bounding_box, curr_slice_val)
                self.mcube_widget.adjust_boxes()
                self.mcube_widget.update_volume(self.minimum_volume)
                self.mcube_widget.generate_mesh()
                self.mcube_widget.adjust_volume()
                self.mcube_widget.show_buttons()
                break
            
        QApplication.restoreOverrideCursor()
        self.progress_dialog.close()
        self.progress_dialog = None
        self.initializeComboSize()
        self.reset_crop()

    def slider2ValueChanged(self, value):
            """
            Updates the isovalue of the image label and mcube widget based on the given slider value,
            and recalculates the image label's size.
            
            Args:
                value (float): The new value of the slider.
            """
            #print("value:", value)
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
        for prefix in prefix_hash:
            if prefix_hash[prefix] > max_prefix_count:
                max_prefix_count = prefix_hash[prefix]
                max_prefix = prefix

        # determine extension
        max_extension_count = 0
        for extension in extension_hash:
            if extension_hash[extension] > max_extension_count:
                max_extension_count = extension_hash[extension]
                max_extension = extension

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

            settings_hash['prefix'] = prefix
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
            logger.info("open_dir method called")
            ddir = QFileDialog.getExistingDirectory(self, self.tr("Select directory"), self.m_app.default_directory)
            if ddir:
                logger.info(f"Selected directory: {ddir}")
                self.edtDirname.setText(ddir)
                self.m_app.default_directory = os.path.dirname(ddir)
            else:
                logger.info("Directory selection cancelled")
                return
            self.settings_hash = {}
            self.initialized = False
            image_file_list = []
            QApplication.setOverrideCursor(Qt.WaitCursor)

            try:
                files = [f for f in os.listdir(ddir) if os.path.isfile(os.path.join(ddir, f))]
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to read directory: {e}"))
                return

            for file in files:
                # get extension
                ext = os.path.splitext(file)[-1].lower()
                if ext in [".bmp", ".jpg", ".png", ".tif", ".tiff"]:
                    pass #image_file_list.append(file)
                elif ext == '.log':
                    try:
                        settings = QSettings(os.path.join(ddir, file), QSettings.IniFormat)
                        prefix = settings.value("File name convention/Filename Prefix")
                        if not prefix:
                            continue
                        if file != prefix + ".log":
                            continue

                        self.settings_hash['prefix'] = settings.value("File name convention/Filename Prefix")
                        self.settings_hash['image_width'] = settings.value("Reconstruction/Result Image Width (pixels)")
                        self.settings_hash['image_height'] = settings.value("Reconstruction/Result Image Height (pixels)")
                        self.settings_hash['file_type'] = settings.value("Reconstruction/Result File Type")
                        self.settings_hash['index_length'] = settings.value("File name convention/Filename Index Length")
                        self.settings_hash['seq_begin'] = settings.value("Reconstruction/First Section")
                        self.settings_hash['seq_end'] = settings.value("Reconstruction/Last Section")
                        self.settings_hash['index_length'] = int(self.settings_hash['index_length'])
                        self.settings_hash['seq_begin'] = int(self.settings_hash['seq_begin'])
                        self.settings_hash['seq_end'] = int(self.settings_hash['seq_end'])
                        self.edtNumImages.setText(str(self.settings_hash['seq_end'] - self.settings_hash['seq_begin'] + 1))
                        self.edtImageDimension.setText(str(self.settings_hash['image_width']) + " x " + str(self.settings_hash['image_height']))
                    except Exception as e:
                        logger.error(f"Error reading log file {file}: {e}")
                        continue

            if 'prefix' not in self.settings_hash:
                self.settings_hash = self.sort_file_list_from_dir(ddir)
                if self.settings_hash is None:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.warning(self, self.tr("Warning"), self.tr("No valid image files found in the selected directory."))
                    return

            for seq in range(self.settings_hash['seq_begin'], self.settings_hash['seq_end']+1):
                filename = self.settings_hash['prefix'] + str(seq).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
                image_file_list.append(filename)
            self.original_from_idx = 0
            self.original_to_idx = len(image_file_list) - 1
            try:
                self.image_label.setPixmap(QPixmap(os.path.join(ddir,image_file_list[0])).scaledToWidth(512))
            except Exception as e:
                logger.error(f"Error loading initial image: {e}")
            self.level_info = []
            self.level_info.append( {'name': 'Original', 'width': self.settings_hash['image_width'], 'height': self.settings_hash['image_height'], 'seq_begin': self.settings_hash['seq_begin'], 'seq_end': self.settings_hash['seq_end']} )
            QApplication.restoreOverrideCursor()
            logger.info(f"Successfully loaded directory with {len(image_file_list)} images")
            self.create_thumbnail()

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
            except Exception as e:
                logger.error(f"Error reading main window settings: {e}")
                # Set defaults if reading fails
                self.m_app.remember_directory = True
                self.m_app.default_directory = "."
                self.m_app.remember_geometry = True
                self.setGeometry(QRect(100, 100, 600, 550))
                self.mcube_geometry = QRect(0, 0, 150, 150)
                self.m_app.language = "en"

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
    logger.info(f"Starting {PROGRAM_NAME} v{PROGRAM_VERSION}")
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon(resource_path('CTHarvester_48_2.png')))
    app.settings = QSettings(QSettings.IniFormat, QSettings.UserScope,COMPANY_NAME, PROGRAM_NAME)

    translator = QTranslator(app)
    app.language = app.settings.value("Language", "en")
    translator.load(resource_path("CTHarvester_{}.qm".format(app.language)))
    app.installTranslator(translator)

    #WindowClass의 인스턴스 생성
    myWindow = CTHarvesterMainWindow()

    #프로그램 화면을 보여주는 코드
    myWindow.show()
    logger.info(f"{PROGRAM_NAME} main window displayed")

    #프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    app.exec_()
    logger.info(f"{PROGRAM_NAME} terminated")

'''
pyinstaller --onefile --noconsole --add-data "*.png;." --add-data "*.qm;." --icon="CTHarvester_48_2.png" CTHarvester.py
pyinstaller --onedir --noconsole --icon="CTHarvester_64.png" --noconfirm CTHarvester.py

pylupdate5 CTHarvester.py -ts CTHarvester_en.ts
pylupdate5 CTHarvester.py -ts CTHarvester_ko.ts
linguist

'''