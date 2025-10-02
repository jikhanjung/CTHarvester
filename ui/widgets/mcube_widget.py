"""
MCubeWidget - 3D mesh visualization widget using OpenGL

Extracted from CTHarvester.py during Phase 4 UI refactoring.
Updated during Phase 1.2 UI/UX improvements with non-blocking mesh generation.
"""

import logging
import os
from copy import deepcopy
from queue import Queue

import mcubes
import numpy as np
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_COLOR_MATERIAL,
    GL_COMPILE,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_LIGHT0,
    GL_LIGHTING,
    GL_LINES,
    GL_MODELVIEW,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_POINT_SMOOTH,
    GL_PROJECTION,
    GL_QUADS,
    GL_SMOOTH,
    GL_SRC_ALPHA,
    GL_TRIANGLES,
    glBegin,
    glBlendFunc,
    glCallList,
    glClear,
    glClearColor,
    glColor3f,
    glColor4f,
    glDisable,
    glEnable,
    glEnd,
    glEndList,
    glGenLists,
    glLineWidth,
    glLoadIdentity,
    glMatrixMode,
    glNewList,
    glNormal3fv,
    glRotatef,
    glShadeModel,
    glTranslatef,
    glVertex3fv,
    glViewport,
)
from OpenGL.GLU import gluLookAt, gluPerspective
from PIL import Image
from PyQt5.QtCore import Qt, QThread, QThreadPool, QTimer, pyqtSignal
from PyQt5.QtGui import QCursor, QPixmap
from PyQt5.QtOpenGL import QGLWidget
from PyQt5.QtWidgets import QApplication, QCheckBox, QLabel
from scipy import ndimage

from config.view_modes import (
    MOVE_3DVIEW_MODE,
    OBJECT_MODE,
    PAN_MODE,
    ROI_BOX_RESOLUTION,
    ROTATE_MODE,
    VIEW_MODE,
    ZOOM_MODE,
)
from utils.common import resource_path
from utils.worker import Worker

logger = logging.getLogger(__name__)


class MeshGenerationThread(QThread):
    """
    Non-blocking mesh generation thread

    Performs marching cubes algorithm in background thread to prevent UI blocking.
    Emits signals for progress, completion, and errors.
    """

    finished = pyqtSignal(dict)  # emits generated_data dict
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, volume, isovalue, scale_factor, is_inverse):
        super().__init__()
        self.volume = volume
        self.isovalue = isovalue
        self.scale_factor = scale_factor
        self.is_inverse = is_inverse

    def run(self):
        try:
            logger.info(
                f"MeshGenerationThread started: isovalue={self.isovalue}, scale_factor={self.scale_factor}"
            )

            # Scale volume
            self.progress.emit(10)
            volume = ndimage.zoom(self.volume, self.scale_factor, order=1)

            # Invert if needed
            self.progress.emit(20)
            if self.is_inverse:
                volume = 255 - volume
                isovalue = 255 - self.isovalue
            else:
                isovalue = self.isovalue

            # Marching cubes algorithm
            self.progress.emit(30)
            logger.debug("Running marching cubes...")
            vertices, triangles = mcubes.marching_cubes(volume, isovalue)

            # Calculate face normals
            self.progress.emit(60)
            logger.debug("Calculating face normals...")
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

            # Calculate vertex normals
            self.progress.emit(80)
            logger.debug("Calculating vertex normals...")
            vertex_normals = np.zeros(vertices.shape)

            for i, triangle in enumerate(triangles):
                for vertex_index in triangle:
                    vertex_normals[vertex_index] += face_normals[i]

            # Normalize vertex normals
            for i in range(len(vertex_normals)):
                if np.linalg.norm(vertex_normals[i]) != 0:
                    vertex_normals[i] /= np.linalg.norm(vertex_normals[i])
                else:
                    vertex_normals[i] = np.array([0.0, 0.0, 0.0])

            self.progress.emit(95)

            # Create result dict
            generated_data = {
                "vertices": vertices,
                "triangles": triangles,
                "vertex_normals": vertex_normals,
            }

            logger.info(
                f"Mesh generated successfully: {len(vertices)} vertices, {len(triangles)} triangles"
            )
            self.progress.emit(100)
            self.finished.emit(generated_data)

        except Exception as e:
            logger.error(f"Mesh generation failed: {e}", exc_info=True)
            self.error.emit(str(e))


class MCubeWidget(QGLWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setMinimumSize(100, 100)
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
        # self.setMinimumSize(400,400)
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

        """ set up buttons """
        self.moveButton = QLabel(self)
        self.moveButton.setPixmap(QPixmap(resource_path("resources/icons/move.png")).scaled(15, 15))
        self.moveButton.hide()
        self.moveButton.setGeometry(0, 0, 15, 15)
        self.moveButton.mousePressEvent = self.moveButton_mousePressEvent
        self.moveButton.mouseMoveEvent = self.moveButton_mouseMoveEvent
        self.moveButton.mouseReleaseEvent = self.moveButton_mouseReleaseEvent
        self.expandButton = QLabel(self)
        self.expandButton.setPixmap(
            QPixmap(resource_path("resources/icons/expand.png")).scaled(15, 15)
        )
        self.expandButton.hide()
        self.expandButton.setGeometry(15, 0, 15, 15)
        self.expandButton.mousePressEvent = self.expandButton_mousePressEvent
        self.shrinkButton = QLabel(self)
        self.shrinkButton.setPixmap(
            QPixmap(resource_path("resources/icons/shrink.png")).scaled(15, 15)
        )
        self.shrinkButton.hide()
        self.shrinkButton.setGeometry(30, 0, 15, 15)
        self.shrinkButton.mousePressEvent = self.shrinkButton_mousePressEvent
        self.cbxRotation = QCheckBox(self)
        self.cbxRotation.setText("R")
        self.cbxRotation.setChecked(True)
        self.cbxRotation.stateChanged.connect(self.cbxRotation_stateChanged)
        self.cbxRotation.setStyleSheet("QCheckBox { background-color: #323232; color: white; }")
        self.cbxRotation.hide()
        self.cbxRotation.move(45, 0)

        self.curr_slice = None
        self.curr_slice_vertices = []
        self.scale = 0.20
        self.average_coordinates = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.bounding_box = None
        self.roi_box = None
        self.threadpool = QThreadPool()
        # print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        self.vertices = []
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.generate_mesh_under_way = False
        self.adjust_volume_under_way = False
        self.generated_data = None
        self.is_inverse = False

        self.queue = Queue()

        # Phase 1.2: Non-blocking mesh generation
        self.mesh_generation_thread = None

    def recalculate_geometry(self):
        # self.scale = self.parent.
        size = min(self.parent.width(), self.parent.height())
        self.scale = round((self.width() / size) * 10.0) / 10.0
        # self.resize(int(size*self.scale),int(size*self.scale))

        self.resize_self()
        self.reposition_self()

    def start_generate_mesh(self):
        self.threadpool.start(self.worker)

    def progress_fn(self, n):
        # print("progress_fn")
        return

    def execute_this_fn(self, progress_callback):
        return

        # return "Done."

    def print_output(self, s):
        return

    def thread_complete(self):
        # print("THREAD COMPLETE!")
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
        # self.reposition_self()

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
        if y + (self.height() / 2) > parent_geometry.height() / 2:
            y = parent_geometry.height() - self.height()
        else:
            y = 0
        if x + (self.width() / 2) > parent_geometry.width() / 2:
            x = parent_geometry.width() - self.width()
        else:
            x = 0

        self.move(x, y)

    def cbxRotation_stateChanged(self):
        self.auto_rotate = self.cbxRotation.isChecked()

    def resize_self(self):
        size = min(self.parent.width(), self.parent.height())
        self.resize(int(size * self.scale), int(size * self.scale))
        # print("resize:",self.parent.width(),self.parent.height())

    def make_box(self, box_coords):
        from_z = box_coords[0]
        to_z = box_coords[1]
        from_y = box_coords[2]
        to_y = box_coords[3]
        from_x = box_coords[4]
        to_x = box_coords[5]

        box_vertex = np.array(
            [
                np.array([from_z, from_y, from_x]),
                np.array([to_z, from_y, from_x]),
                np.array([from_z, to_y, from_x]),
                np.array([to_z, to_y, from_x]),
                np.array([from_z, from_y, to_x]),
                np.array([to_z, from_y, to_x]),
                np.array([from_z, to_y, to_x]),
                np.array([to_z, to_y, to_x]),
            ],
            dtype=np.float64,
        )

        box_edges = [
            [0, 1],
            [0, 2],
            [0, 4],
            [1, 3],
            [1, 5],
            [2, 3],
            [2, 6],
            [3, 7],
            [4, 5],
            [4, 6],
            [5, 7],
            [6, 7],
        ]
        return box_vertex, box_edges

    def update_boxes(self, bounding_box, roi_box, curr_slice_val):
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
        self.original_bounding_box_vertices, self.original_bounding_box_edges = self.make_box(
            self.original_bounding_box
        )

    def set_curr_slice(self, curr_slice):
        self.curr_slice = curr_slice
        self.original_curr_slice_vertices = np.array(
            [
                [
                    self.curr_slice,
                    self.original_bounding_box_vertices[0][1],
                    self.original_bounding_box_vertices[0][2],
                ],
                [
                    self.curr_slice,
                    self.original_bounding_box_vertices[2][1],
                    self.original_bounding_box_vertices[2][2],
                ],
                [
                    self.curr_slice,
                    self.original_bounding_box_vertices[6][1],
                    self.original_bounding_box_vertices[6][2],
                ],
                [
                    self.curr_slice,
                    self.original_bounding_box_vertices[4][1],
                    self.original_bounding_box_vertices[4][2],
                ],
            ],
            dtype=np.float64,
        )
        self.curr_slice_vertices = deepcopy(self.original_curr_slice_vertices)

    def set_roi_box(self, roi_box):
        roi_box_width = roi_box[1] - roi_box[0]
        roi_box_height = roi_box[3] - roi_box[2]
        roi_box_depth = roi_box[5] - roi_box[4]
        max_roi_box_dim = max(roi_box_width, roi_box_height, roi_box_depth)
        self.scale_factor = ROI_BOX_RESOLUTION / max_roi_box_dim
        self.original_roi_box = deepcopy(np.array(roi_box, dtype=np.float64))

        self.roi_box = deepcopy(np.array(roi_box, dtype=np.float64))
        self.original_roi_box_vertices, self.original_roi_box_edges = self.make_box(
            self.original_roi_box
        )
        self.roi_box_vertices, self.roi_box_edges = self.make_box(self.roi_box)

        self.roi_displacement = deepcopy(
            (self.roi_box_vertices[0] + self.roi_box_vertices[7]) / 2.0
        )
        self.volume_displacement = deepcopy(
            (self.roi_box_vertices[7] - self.roi_box_vertices[0]) / 2.0
        )

    def apply_roi_displacement(self):
        self.bounding_box_vertices = self.original_bounding_box_vertices - self.roi_displacement
        self.curr_slice_vertices = self.original_curr_slice_vertices - self.roi_displacement
        self.roi_box_vertices = self.original_roi_box_vertices - self.roi_displacement

    def rotate_boxes(self):
        # rotate bounding box and roi box
        for i in range(len(self.bounding_box_vertices)):
            self.bounding_box_vertices[i] = np.array(
                [
                    self.bounding_box_vertices[i][2],
                    self.bounding_box_vertices[i][0],
                    self.bounding_box_vertices[i][1],
                ]
            )
            if self.roi_box is not None:
                self.roi_box_vertices[i] = np.array(
                    [
                        self.roi_box_vertices[i][2],
                        self.roi_box_vertices[i][0],
                        self.roi_box_vertices[i][1],
                    ]
                )
                pass
        for i in range(len(self.curr_slice_vertices)):
            self.curr_slice_vertices[i] = np.array(
                [
                    self.curr_slice_vertices[i][2],
                    self.curr_slice_vertices[i][0],
                    self.curr_slice_vertices[i][1],
                ]
            )

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
        self.vertices = deepcopy(self.generated_data["vertices"])
        self.triangles = deepcopy(self.generated_data["triangles"])
        self.vertex_normals = deepcopy(self.generated_data["vertex_normals"])

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
        """
        Generate 3D mesh using non-blocking thread (Phase 1.2 improvement)

        Uses MeshGenerationThread to perform marching cubes in background,
        keeping UI responsive during mesh generation.
        """
        # Prevent concurrent mesh generation
        if self.mesh_generation_thread and self.mesh_generation_thread.isRunning():
            logger.warning("Mesh generation already in progress, skipping")
            return

        self.generate_mesh_under_way = True

        max_len = max(self.volume.shape)
        scale_factor = 50.0 / max_len

        # Create and start mesh generation thread
        self.mesh_generation_thread = MeshGenerationThread(
            volume=self.volume.copy(),  # Copy to avoid concurrent access issues
            isovalue=self.isovalue,
            scale_factor=scale_factor,
            is_inverse=self.is_inverse,
        )

        # Connect signals
        self.mesh_generation_thread.finished.connect(self._on_mesh_generated)
        self.mesh_generation_thread.error.connect(self._on_mesh_error)
        self.mesh_generation_thread.progress.connect(self._on_mesh_progress)

        logger.info("Starting non-blocking mesh generation thread")
        self.mesh_generation_thread.start()

    def _on_mesh_generated(self, generated_data):
        """Handle mesh generation completion"""
        self.generated_data = generated_data
        self.gl_list_generated = False
        self.generate_mesh_under_way = False
        logger.info("Mesh generation complete, triggering GL update")
        self.update()  # Trigger OpenGL repaint

    def _on_mesh_error(self, error_msg):
        """Handle mesh generation error with user-friendly dialog"""
        self.generate_mesh_under_way = False
        logger.error(f"Mesh generation error: {error_msg}")

        # Show user-friendly error dialog (Phase 1.3)
        from utils.error_messages import UserError, show_error_dialog

        user_error = UserError(
            title="3D Mesh Generation Failed",
            message="Failed to generate 3D visualization from the image stack.",
            solutions=[
                "Try adjusting the threshold value",
                "Check if the image stack has sufficient data",
                "Verify the images are not corrupted",
                "Try processing a smaller region",
            ],
            technical_details=error_msg,
        )

        show_error_dialog(self, user_error)

    def _on_mesh_progress(self, percentage):
        """Handle mesh generation progress update"""
        logger.debug(f"Mesh generation progress: {percentage}%")

    def apply_volume_displacement(self):
        if len(self.vertices) > 0:
            self.vertices = deepcopy(self.vertices - self.volume_displacement)

    def rotate_volume(self):
        # rotate vertices
        if len(self.vertices) > 0:
            # print(self.vertices.shape)
            for i in range(len(self.vertices)):
                # print("vertices[i]", i, self.vertices[i])
                self.vertices[i] = np.array(
                    [self.vertices[i][2], self.vertices[i][0], self.vertices[i][1]]
                )
                self.vertex_normals[i] = np.array(
                    [
                        self.vertex_normals[i][2],
                        self.vertex_normals[i][0],
                        self.vertex_normals[i][1],
                    ]
                )

        # print(self.bounding_box_vertices[0])

    def scale_volume(self):
        if len(self.vertices) > 0:
            self.vertices /= 10.0
        return

    def set_isovalue(self, isovalue):
        self.isovalue = isovalue

    def read_images_from_folder(self, folder):
        images = []
        try:
            for filename in os.listdir(folder):
                try:
                    # read images using Pillow with context manager
                    with Image.open(os.path.join(folder, filename)) as img:
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
        # print("timout2")
        if not self.queue.empty() and self.generate_mesh_under_way == False:
            while not self.queue.empty():
                (volume, isovalue) = self.queue.get()
            self.volume = volume
            self.isovalue = isovalue
            self.worker = Worker(
                self.generate_mesh
            )  # Any other args, kwargs are passed to the run function
            self.worker.signals.result.connect(self.print_output)
            self.worker.signals.finished.connect(self.thread_complete)
            self.worker.signals.progress.connect(self.progress_fn)
            self.threadpool.start(self.worker)
        self.updateGL()

    def rotate_timeout(self):
        # print("timout1")
        # print("timeout, auto_rotate:", self.auto_rotate)
        if self.auto_rotate == False:
            # print "no rotate"
            return
        if self.is_dragging:
            # print "dragging"
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
            self.temp_dolly = (self.curr_y - self.down_y) / 100.0
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
        glClearColor(0.94, 0.94, 0.94, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_LIGHTING)

        # Set camera position and view
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        glTranslatef(0, 0, -5.0 + self.dolly + self.temp_dolly)  # x, y, z
        glTranslatef(
            (self.pan_x + self.temp_pan_x) / 100.0, (self.pan_y + self.temp_pan_y) / -100.0, 0.0
        )

        # rotate viewpoint
        glRotatef(self.rotate_y + self.temp_rotate_y, 1.0, 0.0, 0.0)
        glRotatef(self.rotate_x + self.temp_rotate_x, 0.0, 1.0, 0.0)

        if len(self.triangles) == 0:
            return

        glClearColor(0.2, 0.2, 0.2, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        """ render bounding box """
        glDisable(GL_LIGHTING)
        if self.bounding_box is not None:
            glLineWidth(1)
            self.draw_box(
                self.bounding_box_vertices, self.bounding_box_edges, color=[0.0, 0.0, 1.0]
            )

        """ render roi box """
        if self.roi_box is not None:
            if not (self.roi_box_vertices == self.bounding_box_vertices).all():
                glLineWidth(2)
                self.draw_box(self.roi_box_vertices, self.roi_box_edges, color=[1.0, 0.0, 0.0])
        glEnable(GL_LIGHTING)

        """ render 3d model """
        glColor3f(0.0, 1.0, 0.0)
        if self.gl_list_generated == False:
            self.generate_gl_list()

        self.render_gl_list()

        """ draw current slice plane """
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
