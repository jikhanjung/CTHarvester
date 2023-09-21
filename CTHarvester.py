from PyQt5 import QtGui
from PyQt5.QtWidgets import QMainWindow, QHeaderView, QApplication, QAbstractItemView, QSlider,\
                            QMessageBox, QTreeView, QTableView, QSplitter, QAction, QMenu, \
                            QStatusBar, QInputDialog, QToolBar
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem, QKeySequence
from PyQt5.QtCore import Qt, QRect, QSortFilterProxyModel, QSettings, QSize, QTranslator

from PyQt5.QtCore import pyqtSlot

from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView, QFileDialog, QCheckBox, QColorDialog, \
                            QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QProgressBar, QApplication, \
                            QDialog, QLineEdit, QLabel, QPushButton, QAbstractItemView, QStatusBar, QMessageBox, \
                            QTableView, QSplitter, QRadioButton, QComboBox, QTextEdit, QSizePolicy, \
                            QTableWidget, QGridLayout, QAbstractButton, QButtonGroup, QGroupBox, \
                            QTabWidget, QListWidget
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap, QStandardItemModel, QStandardItem, QImage,\
                        QFont, QPainter, QBrush, QMouseEvent, QWheelEvent, QDoubleValidator, QResizeEvent
from PyQt5.QtCore import Qt, QRect, QSortFilterProxyModel, QSize, QPoint,\
                         pyqtSlot, QItemSelectionModel, QTimer
from superqt import QLabeledRangeSlider, QLabeledSlider
#import vtkmodules.all as vtk

import os, sys, re

import numpy
from PIL import Image, ImageDraw, ImageChops

from os import listdir
from os.path import isfile, join

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
PROGRAM_NAME = "CT Harvester"
PROGRAM_VERSION = "0.1"
PROGRAM_AUTHOR = "Jikhan Jung"

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
        self.remember_geometry = False
        self.language = "en"
        self.default_directory = "."


        self.rbRememberGeometryYes = QRadioButton("Yes")
        self.rbRememberGeometryYes.setChecked(self.remember_geometry)
        self.rbRememberGeometryYes.clicked.connect(self.on_rbRememberGeometryYes_clicked)
        self.rbRememberGeometryNo = QRadioButton("No")
        self.rbRememberGeometryNo.setChecked(not self.remember_geometry)
        self.rbRememberGeometryNo.clicked.connect(self.on_rbRememberGeometryNo_clicked)

        self.gbRememberGeomegry = QGroupBox()
        self.gbRememberGeomegry.setLayout(QHBoxLayout())
        self.gbRememberGeomegry.layout().addWidget(self.rbRememberGeometryYes)
        self.gbRememberGeomegry.layout().addWidget(self.rbRememberGeometryNo)

        self.read_settings()

    def read_settings(self):
        self.remember_geometry = mu.value_to_bool(self.m_app.settings.value("WindowGeometry/RememberGeometry", True))


    def save_settings(self):
        self.settings.setValue("Default directory", self.default_directory)
        self.settings.setValue("Window geometry", self.geometry())
        self.settings.setValue("Language", self.language)

class ProgressDialog(QDialog):
    def __init__(self,parent):
        super().__init__()
        #self.setupUi(self)
        #self.setGeometry(200, 250, 400, 250)
        self.setWindowTitle(self.tr("CTHarvester - Progress Dialog"))
        self.parent = parent
        self.setGeometry(QRect(100, 100, 320, 180))
        self.move(self.parent.pos()+QPoint(100,100))

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(50,50, 50, 50)

        self.lbl_text = QLabel(self)
        #self.lbl_text.setGeometry(50, 50, 320, 80)
        #self.pb_progress = QProgressBar(self)
        self.pb_progress = QProgressBar(self)
        #self.pb_progress.setGeometry(50, 150, 320, 40)
        self.pb_progress.setValue(0)
        self.stop_progress = False
        self.btnStop = QPushButton(self)
        #self.btnStop.setGeometry(175, 200, 50, 30)
        self.btnStop.setText(self.tr("Stop"))
        self.btnStop.clicked.connect(self.set_stop_progress)
        self.layout.addWidget(self.lbl_text)
        self.layout.addWidget(self.pb_progress)
        self.layout.addWidget(self.btnStop)
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
        #self.lbl_text.setText(label_text)
        self.update()
        QApplication.processEvents()

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
        #print("distance_threshold:", self.distance_threshold)
        self.setMouseTracking(True)
        self.object_dialog = None
        self.top_idx = -1
        self.bottom_idx = -1
        self.curr_idx = -1
        self.move_x = 0
        self.move_y = 0
        self.reset_crop()

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
        #print("distance_check", self.crop_from_x, self.crop_to_x, x, self.crop_from_y, self.crop_to_y, y, self.edit_x1, self.edit_x2, self.edit_y1, self.edit_y2)
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
        #print("mouseMoveEvent", me.x(), me.y(), self.edit_mode)
        #print(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y)
        if me.buttons() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX']:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.temp_x2 = self._2imgx(self.mouse_curr_x)
                self.temp_y2 = self._2imgy(self.mouse_curr_y)
                #self.object_dialog.edtStatus.setText("({}, {})-({}, {})".format(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y))
            elif self.edit_mode in [ MODE['EDIT_BOX_PROGRESS'], MODE['MOVE_BOX_PROGRESS'] ]:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.move_x = self.mouse_curr_x - self.mouse_down_x
                self.move_y = self.mouse_curr_y - self.mouse_down_y
                #print("move", self.move_x, self.move_y)
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
        #print("mousePressEvent", me.x(), me.y(),self.edit_mode)
        #print(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y)
        if me.button() == Qt.LeftButton:
            #if self.object_dialog is None:
            #    return
            if self.edit_mode == MODE['ADD_BOX'] or self.edit_mode == MODE['EDIT_BOX']:
                self.set_mode(MODE['ADD_BOX'])
                img_x = self._2imgx(me.x())
                img_y = self._2imgy(me.y())
                #print("mousePressEvent", img_x, img_y)
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
        #print("mouseReleaseEvent", me.x(), me.y(),self.edit_mode)
        #print(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y)
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
            #self.object_dialog.update_status()

        self.object_dialog.update_status()
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
            #return [from_x, from_y, to_x, to_y]
        elif self.crop_from_x > -1:
            from_x = self._2canx(min(self.crop_from_x, self.crop_to_x))
            to_x = self._2canx(max(self.crop_from_x, self.crop_to_x))
            from_y = self._2cany(min(self.crop_from_y, self.crop_to_y))
            to_y = self._2cany(max(self.crop_from_y, self.crop_to_y))

        if imgxy == True:
            #print("imagexy true", from_x, self.orig_pixmap)
            if from_x <= 0 and from_y <= 0 and to_x <= 0 and to_y <= 0 and self.orig_pixmap:
                return [ 0,0,self.orig_pixmap.width()-1,self.orig_pixmap.height()-1]
            else:
                return [self._2imgx(from_x), self._2imgy(from_y), self._2imgx(to_x), self._2imgy(to_y)]
        else:
            return [from_x, from_y, to_x, to_y]


    def paintEvent(self, event):
        # fill background with dark gray
        painter = QPainter(self)
        #painter.fillRect(self.rect(), QBrush(QColor()))#as_qt_color(COLOR['BACKGROUND'])))
        if self.curr_pixmap is not None:
            #print("paintEvent", self.curr_pixmap.width(), self.curr_pixmap.height())
            painter.drawPixmap(0,0,self.curr_pixmap)

        if self.curr_idx > self.top_idx or self.curr_idx < self.bottom_idx:
            painter.setPen(QPen(QColor(128,0,0), 1, Qt.DotLine))
        else:
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        [ x1, y1, x2, y2 ] = self.get_crop_area()
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def set_image(self,file_path):
        #print("set_image", file_path)
        # check if file exists
        if not os.path.exists(file_path):
            #print("file not exists:", file_path)
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
        #print("set_curr_idx", curr_idx, self.max_idx, self.min_idx)
        #print("set_curr_idx", )
    def set_bottom_idx(self, bottom_idx):
        self.bottom_idx = bottom_idx

    def calculate_resize(self):
        #print("objectviewer calculate resize", self, self.object, self.object.landmark_list, self.landmark_list)
        if self.orig_pixmap is not None:
            self.distance_threshold = self._2imgx(DISTANCE_THRESHOLD)
            #print("distance_threshold:", self.distance_threshold)
            self.orig_width = self.orig_pixmap.width()
            self.orig_height = self.orig_pixmap.height()
            image_wh_ratio = self.orig_width / self.orig_height
            label_wh_ratio = self.width() / self.height()
            if image_wh_ratio > label_wh_ratio:
                self.image_canvas_ratio = self.orig_width / self.width()
            else:
                self.image_canvas_ratio = self.orig_height / self.height()
            #if self.image_canvas_ratio < 1.0:
            #    self.scale = 1.0 / self.image_canvas_ratio
            #else:
            #    self.scale = 1.0
            
            #print("calculate_resize", self.orig_width, self.orig_height, self.width(), self.height(), self.image_canvas_ratio, self.scale)

            self.curr_pixmap = self.orig_pixmap.scaled(int(self.orig_width*self.scale/self.image_canvas_ratio),int(self.orig_width*self.scale/self.image_canvas_ratio), Qt.KeepAspectRatio)
    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.calculate_resize()
        return super().resizeEvent(a0)


class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(resource_path('CTHarvester_48_2.png')))
        self.setWindowTitle("{} v{}".format(self.tr("CT Harvester"), PROGRAM_VERSION))
        self.setGeometry(QRect(100, 100, 600, 550))
        self.settings_hash = {}
        self.level_info = []
        self.curr_level_idx = 0
        self.prev_level_idx = 0
        self.default_directory = "."
        self.read_settings()

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
        #self.edtDirname.setMaximumWidth(400)
        self.edtDirname.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dirname_layout.addWidget(self.edtDirname,stretch=1)
        self.dirname_layout.addWidget(self.btnOpenDir,stretch=0)
        self.dirname_widget.setLayout(self.dirname_layout)

        self.image_info_layout = QHBoxLayout()
        self.image_info_widget = QWidget()
        self.edtImageDimension = QLineEdit()
        self.edtImageDimension.setReadOnly(True)
        self.edtImageDimension.setText("")
        self.edtNumImages = QLineEdit()
        self.edtNumImages.setReadOnly(True)
        self.edtNumImages.setText("")
        self.image_info_layout.addWidget(QLabel(self.tr("Size:")))
        self.image_info_layout.addWidget(self.edtImageDimension)
        self.image_info_layout.addWidget(QLabel(self.tr("Count:")))
        self.image_info_layout.addWidget(self.edtNumImages)
        self.image_info_widget.setLayout(self.image_info_layout)

        self.image_layout = QHBoxLayout()
        self.image_label = QLabel()
        self.image_label.setPixmap(QPixmap("D:/CT/CO-1/CO-1_Rec/small/CO-1__rec00000001.bmp"))
        self.image_layout.addWidget(self.image_label)
        self.lstFileList = QListWidget()
        self.lstFileList.setAlternatingRowColors(True)
        self.lstFileList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lstFileList.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.lstFileList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lstFileList.itemSelectionChanged.connect(self.lstFileListSelectionChanged)

        self.crop_layout = QHBoxLayout()
        self.crop_widget = QWidget()
        self.btnFromImage = QPushButton("From >")
        #self.btnFromImage.clicked.connect(self.set_from_image)
        self.edtFromImage = QLineEdit()
        self.btnToImage = QPushButton("To >")
        #self.btnToImage.clicked.connect(self.set_to_image)
        self.edtToImage = QLineEdit()
        self.btnCrop = QPushButton("Reset")
        #self.btnCrop.clicked.connect(self.set_crop)

        self.crop_layout.addWidget(self.btnFromImage)
        self.crop_layout.addWidget(self.edtFromImage)
        self.crop_layout.addWidget(self.btnToImage)
        self.crop_layout.addWidget(self.edtToImage)
        self.crop_layout.addWidget(self.btnCrop)
        self.crop_widget.setLayout(self.crop_layout)
        
        self.image_layout.addWidget(self.lstFileList)
        self.image_widget = QWidget()
        self.image_widget.setLayout(self.image_layout)

        self.btnCreateThumbnail = QPushButton("Prepare View")
        self.btnCreateThumbnail.clicked.connect(self.create_thumbnail)


        self.left_layout = QVBoxLayout()
        self.left_widget = QWidget()
        self.left_widget.setLayout(self.left_layout)
        #self.left_layout.addWidget(self.dirname_widget)
        self.left_layout.addWidget(self.image_info_widget)
        self.left_layout.addWidget(self.image_widget)
        self.left_layout.addWidget(self.btnCreateThumbnail)
        #self.left_layout.addWidget(self.crop_widget)

        self.lblLevel = QLabel(self.tr("Level"))
        self.comboLevel = QComboBox()
        self.comboLevel.currentIndexChanged.connect(self.comboLevelIndexChanged)

        self.image_info_layout2 = QHBoxLayout()
        self.image_info_widget2 = QWidget()
        
        self.edtImageDimension2 = QLineEdit()
        self.edtImageDimension2.setReadOnly(True)
        self.edtImageDimension2.setText("")
        self.edtNumImages2 = QLineEdit()
        self.edtNumImages2.setReadOnly(True)
        self.edtNumImages2.setText("")
        self.image_info_layout2.addWidget(self.lblLevel)
        self.image_info_layout2.addWidget(self.comboLevel)
        self.image_info_layout2.addWidget(QLabel(self.tr("Size")))
        self.image_info_layout2.addWidget(self.edtImageDimension2)
        self.image_info_layout2.addWidget(QLabel(self.tr("Count")))
        self.image_info_layout2.addWidget(self.edtNumImages2)
        self.image_info_widget2.setLayout(self.image_info_layout2)

        self.image_widget2 = QWidget()
        self.image_layout2 = QHBoxLayout()
        self.image_label2 = ObjectViewer2D(self.image_widget2)
        self.image_label2.object_dialog = self
        self.slider = QLabeledSlider(Qt.Vertical)
        self.slider.setValue(0)
        self.range_slider = QLabeledRangeSlider(Qt.Vertical)
        self.range_slider.setValue((0,99))

        #self.slider.setTickInterval(1)
        #self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setSingleStep(1)
        self.range_slider.setSingleStep(1)
        #self.slider.setPageStep(1)
        #self.slider.setMinimum(0)
        #self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.sliderValueChanged)
        self.range_slider.valueChanged.connect(self.rangeSliderValueChanged)
        self.range_slider.setMinimumWidth(100)

        self.image_layout2.addWidget(self.image_label2,stretch=1)
        self.image_layout2.addWidget(self.slider)
        self.image_layout2.addWidget(self.range_slider)
        self.image_widget2.setLayout(self.image_layout2)
        #self.image_layout2.setSpacing(20)

        self.crop_layout2 = QHBoxLayout()
        self.crop_widget2 = QWidget()
        self.btnSetBottom = QPushButton(self.tr("Set Bottom"))
        self.btnSetBottom.clicked.connect(self.set_bottom)
        self.btnSetTop = QPushButton(self.tr("Set Top"))
        self.btnSetTop.clicked.connect(self.set_top)
        self.btnReset = QPushButton(self.tr("Reset"))
        self.btnReset.clicked.connect(self.reset_crop)

        self.crop_layout2.addWidget(self.btnSetBottom)
        self.crop_layout2.addWidget(self.btnSetTop)
        self.crop_layout2.addWidget(self.btnReset)
        self.crop_widget2.setLayout(self.crop_layout2)

        self.edtStatus = QLineEdit()
        self.edtStatus.setReadOnly(True)
        self.edtStatus.setText("")

        self.btnSave = QPushButton(self.tr("Save cropped image stack"))
        self.btnSave.clicked.connect(self.save_result)

        self.right_layout = QVBoxLayout()
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.right_layout)
        #self.right_layout.addWidget(self.comboSize)
        self.right_layout.addWidget(self.dirname_widget)
        self.right_layout.addWidget(self.image_info_widget2)
        self.right_layout.addWidget(self.image_widget2)
        self.right_layout.addWidget(self.crop_widget2)
        self.right_layout.addWidget(self.edtStatus)
        self.right_layout.addWidget(self.btnSave)

        self.main_layout = QHBoxLayout()
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)
        #self.main_layout.addWidget(self.left_widget)
        self.main_layout.addWidget(self.right_widget)

        self.setCentralWidget(self.main_widget)
        self.initialized = False

    def set_bottom(self):
        #self.image_label2.set_bottom_idx(self.slider.value())
        #self.image_label2.set_curr_idx(self.slider.value())
        self.range_slider.setValue((self.slider.value(), self.range_slider.value()[1]))
        self.update_status()
    def set_top(self):
        #self.image_label2.set_top_idx(self.slider.value())
        #self.image_label2.set_curr_idx(self.slider.value())
        self.range_slider.setValue((self.range_slider.value()[0], self.slider.value()))
        self.update_status()

    def resizeEvent(self, a0: QResizeEvent) -> None:
        #print("resizeEvent")

        return super().resizeEvent(a0)
    

    def save_result(self):
        # open dir dialog for save
        target_dirname = QFileDialog.getExistingDirectory(self, self.tr('Select directory to save'), self.edtDirname.text())
        if target_dirname == "":
            return
        # get crop box info
        from_x = self.image_label2.crop_from_x
        from_y = self.image_label2.crop_from_y
        to_x = self.image_label2.crop_to_x
        to_y = self.image_label2.crop_to_y
        # get size idx
        size_idx = self.comboLevel.currentIndex()
        # get filename from level from idx
        top_idx = self.image_label2.top_idx
        bottom_idx = self.image_label2.bottom_idx

        current_count = 0
        total_count = top_idx - bottom_idx + 1
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        self.progress_dialog.lbl_text.setText(self.tr("Saving image stack..."))
        self.progress_dialog.pb_progress.setValue(0)

        for i, idx in enumerate(range(bottom_idx, top_idx+1)):
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + idx).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
            # get full path
            if size_idx == 0:
                orig_dirname = self.edtDirname.text()
            else:
                orig_dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            fullpath = os.path.join(orig_dirname, filename)
            # open image
            img = Image.open(fullpath)
            # crop image
            img = img.crop((from_x, from_y, to_x, to_y))
            # save image
            img.save(os.path.join(target_dirname, filename))

            self.progress_dialog.lbl_text.setText(self.tr("Saving image stack... {}/{}").format(i+1, int(total_count)))
            self.progress_dialog.pb_progress.setValue(int(((i+1)/float(int(total_count)))*100))
            self.progress_dialog.update()
            QApplication.processEvents()

        self.progress_dialog.close()


    def rangeSliderValueChanged(self):
        (bottom_idx, top_idx) = self.range_slider.value()
        self.image_label2.set_bottom_idx(bottom_idx)
        self.image_label2.set_top_idx(top_idx)
        self.image_label2.repaint()
        self.update_status()

    def sliderValueChanged(self):
        # print current slide value
        #print("sliderValueChanged")
        #print("slider value:", self.slider.value())
        # get scale factor
        if not self.initialized:
            return
        size_idx = self.comboLevel.currentIndex()
        curr_image_idx = self.slider.value()
        #print("curr_image_idx:", curr_image_idx)
        #print("size_idx:", size_idx)
        #print("settings hash", self.settings_hash)
        if size_idx < 0:
            size_idx = 0
        # get directory for size idx
        if size_idx == 0:
            dirname = self.edtDirname.text()
            #filename = self.lstFileList.item(self.slider.value()).text()
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + self.slider.value()).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
        else:
            dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            # get filename from level from idx
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + self.slider.value()).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
        #print("dirname:", dirname)
        #print("filename:", filename)

        self.image_label2.set_image(os.path.join(dirname, filename))
        self.image_label2.set_curr_idx(self.slider.value())
        #self.edtCurrentImage.setText(str(self.slider.value()))
        #self.image_label2.setPixmap(QPixmap(os.path.join(dirname, filename)).scaledToWidth(512))

    def reset_crop(self):
        #self.image_label2.set_top_idx(self.slider.minimum())
        #self.image_label2.set_bottom_idx(self.slider.maximum())
        self.image_label2.set_curr_idx(self.slider.value())
        self.image_label2.reset_crop()
        self.range_slider.setValue((self.slider.minimum(), self.slider.maximum()))
        self.canvas_box = None
        self.update_status()

    def update_status(self):
        ( bottom_idx, top_idx ) = self.range_slider.value()
        [ x1, y1, x2, y2 ] = self.image_label2.get_crop_area(imgxy=True)
        count = ( top_idx - bottom_idx + 1 )

        txt = self.tr("Crop indices: {}~{}").format(bottom_idx, top_idx)
        txt += self.tr("    Cropped image size: {}x{}").format(x2 - x1+1, y2 - y1+1)
        txt += self.tr("    Estimated stack size: {} MB").format(round(count * (x2 - x1+1 ) * (y2 - y1+1 ) / 1024 / 1024 , 2))    
        txt += self.tr(" [")+str(self.image_label2.edit_mode)+self.tr("]")
        self.edtStatus.setText(txt)
   
    def initializeComboSize(self):
        #print("initializeComboSize")
        self.comboLevel.clear()
        for level in self.level_info:
                
            #print("level:", level)
            self.comboLevel.addItem( level['name'])

        #self.comboLevel.setCurrentIndex(0)
        #self.comboLevelIndexChanged()

    def comboLevelIndexChanged(self):

        #print("-----------------------------[[[comboSizeIndexChanged]]]-----------------------------")
        self.prev_level_idx = self.curr_level_idx
        self.curr_level_idx = self.comboLevel.currentIndex()
        if self.curr_level_idx < 0:
            return
        
        #print("prev_level_idx:", self.prev_level_idx)
        #print("curr_level_idx:", self.curr_level_idx)

        level_info = self.level_info[self.curr_level_idx]
        #print("level_info:", self.level_info)
        seq_begin = level_info['seq_begin']
        seq_end = level_info['seq_end']

        self.edtImageDimension2.setText(str(level_info['width']) + " x " + str(level_info['height']))
        image_count = seq_end - seq_begin + 1
        self.edtNumImages2.setText(str(image_count))

        if not self.initialized:
            #print("not initialized. image_count:", image_count)
            self.slider.setMaximum(image_count - 1)
            self.slider.setMinimum(0)
            self.slider.setValue(0)
            self.range_slider.setRange(0,image_count - 1)
            self.range_slider.setValue((0, image_count - 1))
            #print("range_slider value:", self.range_slider.value())
            #print("range_slider range:", self.range_slider.minimum(), self.range_slider.maximum())
            self.curr_level_idx = 0
            self.prev_level_idx = 0
            self.initialized = True


        level_diff = self.prev_level_idx-self.curr_level_idx
        #print("level_diff:", level_diff)
        #print("prev_level_idx:", self.prev_level_idx)
        #print("curr_level_idx:", self.curr_level_idx)
        curr_idx = self.slider.value()
        #print("curr_idx 1:", curr_idx)
        curr_idx = int(curr_idx * (2**level_diff))
        #print("curr_idx 2:", curr_idx)

        (bottom_idx, top_idx) = self.range_slider.value()
        #print("bottom_idx:", bottom_idx)
        #print("top_idx:", top_idx)
        bottom_idx = int(bottom_idx * (2**level_diff))
        top_idx = int(top_idx * (2**level_diff))
        #print("bottom_idx:", bottom_idx)
        #print("top_idx:", top_idx)

        self.range_slider.setRange(0, image_count - 1)
        self.range_slider.setValue((bottom_idx, top_idx))

        self.slider.setMaximum(image_count -1)
        self.slider.setMinimum(0)
        #print("curr_idx 3:", curr_idx)
        self.slider.setValue(curr_idx)
        #print("curr_idx 4:", self.slider.value())

        self.sliderValueChanged()
        self.update_status()

    def create_thumbnail(self):
        # determine thumbnail size
        #print("create thumbnail")
        MAX_THUMBNAIL_SIZE = 512
        size =  max(int(self.settings_hash['image_width']), int(self.settings_hash['image_height']))
        width = int(self.settings_hash['image_width'])
        height = int(self.settings_hash['image_height'])
        #print("size:", size)
        #print("width:", width)
        #print("height:", height)
        #print("settings_hash:", self.settings_hash)

        i = 0
        # create temporary directory for thumbnail
        dirname = self.edtDirname.text()
        
        seq_begin = self.settings_hash['seq_begin']
        seq_end = self.settings_hash['seq_end']

        current_count = 0
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        while True:
            size /= 2
            width = int(width / 2)
            height = int(height / 2)

            if i == 0:
                from_dir = dirname
            else:
                from_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i))

            total_count = seq_end - seq_begin + 1
            self.progress_dialog.lbl_text.setText(self.tr("Creating thumbnail level {}...").format(i+1))
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
                self.progress_dialog.lbl_text.setText(self.tr("Creating rescaled images level {}... {}/{}").format(i+1, idx+1, int(total_count/2)))
                self.progress_dialog.pb_progress.setValue(int(((idx+1)/float(int(total_count/2)))*100))
                self.progress_dialog.update()
                if os.path.exists(os.path.join(from_dir, filename3)):
                    continue
                # check if filename exist
                img1 = None
                if os.path.exists(os.path.join(from_dir, filename1)):
                    img1 = Image.open(os.path.join(from_dir, filename1))
                img2 = None
                if os.path.exists(os.path.join(from_dir, filename2)):
                    img2 = Image.open(os.path.join(from_dir, filename2))
                # average two images
                if img1 is None or img2 is None:
                    last_count = -1
                    continue
                new_img_ops = ImageChops.add(img1, img2, scale=2.0)
                # resize to half
                new_img_ops = new_img_ops.resize((int(img1.width / 2), int(img1.height / 2)))
                # save to temporary directory
                new_img_ops.save(filename3)
                QApplication.processEvents()

            i+= 1
            seq_end = int((seq_end - seq_begin) / 2) + seq_begin + last_count
            self.level_info.append( {'name': "Level " + str(i), 'width': width, 'height': height, 'seq_begin': seq_begin, 'seq_end': seq_end} )
            if size < MAX_THUMBNAIL_SIZE:
                break

        self.progress_dialog.close()
        self.initializeComboSize()
        self.reset_crop()
        thumbnail_size = int(size)
        #print("thumbnail size:", thumbnail_size)
        #print("i:", i)

    def lstFileListSelectionChanged(self):
        #print("lstFileListSelectionChanged")
        self.image_label.setPixmap(QPixmap(os.path.join(self.edtDirname.text(), self.lstFileList.currentItem().text())).scaledToWidth(512))

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
        #print("max_prefix:", max_prefix)
        #print("max_count:", max_prefix_count)
        # determine extension
        max_extension_count = 0
        for extension in extension_hash:
            if extension_hash[extension] > max_extension_count:
                max_extension_count = extension_hash[extension]
                max_extension = extension
        #print("max_extension:", max_extension)
        #print("max_count:", max_extension_count)

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
            img = Image.open(imagefile_name)
            width, height = img.size


            match1 = re.match(pattern, first_file)
            match2 = re.match(pattern, last_file)
            #if match1:
                #print("\nDetermined Pattern:")
                #print("Prefix:", match1.group(1))
                #print("Extension:", match1.group(3))

            if match1 and match2:
                #print("Start Index:", match1.group(2))
                #print("End Index:", match2.group(2))
                start_index = match1.group(2)
                end_index = match2.group(2)
            image_count = int(match2.group(2)) - int(match1.group(2)) + 1
            number_of_images = len(ct_stack_files)
            #print("Number of images:", number_of_images)
            #print("Image count:", image_count)
            seq_length = len(match1.group(2))
            #print("Sequence length:", seq_length)

            settings_hash['prefix'] = prefix
            settings_hash['image_width'] = width
            settings_hash['image_height'] = height
            settings_hash['file_type'] = max_extension
            settings_hash['index_length'] = seq_length
            settings_hash['seq_begin'] = start_index
            settings_hash['seq_end'] = end_index
            #print("Settings hash:", settings_hash)
            settings_hash['index_length'] = int(settings_hash['index_length'])
            settings_hash['seq_begin'] = int(settings_hash['seq_begin'])
            settings_hash['seq_end'] = int(settings_hash['seq_end'])

            return settings_hash
        else:
            return None
        


    def open_dir(self):
        #pass
        #print("open_dir")
        ddir = QFileDialog.getExistingDirectory(self, "Select directory", self.default_directory)
        if ddir:
        # ddir is a QString containing the path to the directory you selected
            #print("loading from:", ddir)  # this will output something like 'C://path/you/selected'
            self.edtDirname.setText(ddir)
            self.default_directory = os.path.dirname(ddir)
        else:
            return
        self.settings_hash = {}
        self.initialized = False
        image_file_list = []
        self.lstFileList.clear()
        files = [f for f in os.listdir(ddir) if os.path.isfile(os.path.join(ddir, f))]

        for file in files:
            # get extension
            ext = os.path.splitext(file)[-1].lower()
            if ext in [".bmp", ".jpg", ".png", ".tif", ".tiff"]:
                pass #image_file_list.append(file)
            elif ext == '.log':
                fn = file
                #print("log file:", fn)
                settings = QSettings(file, QSettings.IniFormat)
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
                #print("Settings hash:", self.settings_hash)
                self.settings_hash['index_length'] = int(self.settings_hash['index_length'])
                self.settings_hash['seq_begin'] = int(self.settings_hash['seq_begin'])
                self.settings_hash['seq_end'] = int(self.settings_hash['seq_end'])
                #print("Settings hash:", self.settings_hash)
                self.edtNumImages.setText(str(self.settings_hash['seq_end'] - self.settings_hash['seq_begin'] + 1))
                self.edtImageDimension.setText(str(self.settings_hash['image_width']) + " x " + str(self.settings_hash['image_height']))
                #print("Settings hash:", settings_hash)
        #print("Settings hash:", self.settings_hash)
        if 'prefix' not in self.settings_hash:
            #print("prefix not found. trying to find prefix from file name")
            self.settings_hash = self.sort_file_list_from_dir(ddir)
            if self.settings_hash is None:
                return
            #return
        #print("Settings hash:", self.settings_hash)
        #print("dir:", ddir)
        for seq in range(self.settings_hash['seq_begin'], self.settings_hash['seq_end']+1):
            filename = self.settings_hash['prefix'] + str(seq).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
            self.lstFileList.addItem(filename)
            image_file_list.append(filename)
        self.original_from_idx = 0
        self.edtFromImage.setText(image_file_list[0])
        self.original_to_idx = len(image_file_list) - 1
        self.edtToImage.setText(image_file_list[-1])
        self.image_label.setPixmap(QPixmap(os.path.join(ddir,image_file_list[0])).scaledToWidth(512))
        self.image_label2.setPixmap(QPixmap(os.path.join(ddir,image_file_list[0])).scaledToWidth(512))
        self.level_info = []
        self.level_info.append( {'name': 'Original', 'width': self.settings_hash['image_width'], 'height': self.settings_hash['image_height'], 'seq_begin': self.settings_hash['seq_begin'], 'seq_end': self.settings_hash['seq_end']} )
        #print("level_info in open_dir:", self.level_info)
        #self.initializeComboSize()
        #self.open_dir()
        self.create_thumbnail()

    def read_settings(self):
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope,COMPANY_NAME, PROGRAM_NAME)
        self.default_directory = self.settings.value("Default directory", ".")
        self.setGeometry(self.settings.value("Window geometry", QRect(100, 100, 600, 550)))    

    def save_settings(self):
        self.settings.setValue("Default directory", self.default_directory)
        self.settings.setValue("Window geometry", self.geometry())

    def closeEvent(self, event):
        self.save_settings()
        event.accept()
        

if __name__ == "__main__":
    app = QApplication(sys.argv)

    translator = QTranslator(app)
    translator.load("CTHarvester_ko.qm")     
    app.installTranslator(translator)

    app.setWindowIcon(QIcon(resource_path('CTHarvester_48_2.png')))
    #app.settings = 
    #app.preferences = QSettings("Modan", "Modan2")

    #WindowClass의 인스턴스 생성
    myWindow = CTHarvesterMainWindow()

    #프로그램 화면을 보여주는 코드
    myWindow.show()

    #프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    app.exec_()
'''
pyinstaller --onefile --noconsole --add-data "*.png;." --icon="CTHarvester_48_2.png" CTHarvester.py

pylupdate5 CTHarvester.py -ts CTHarvester_en.ts
pylupdate5 CTHarvester.py -ts CTHarvester_ko.ts
'''