from PyQt5.QtWidgets import QMainWindow, QHeaderView, QApplication, QAbstractItemView, QSlider,\
                            QMessageBox, QTreeView, QTableView, QSplitter, QAction, QMenu, \
                            QStatusBar, QInputDialog, QToolBar
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem, QKeySequence
from PyQt5.QtCore import Qt, QRect, QSortFilterProxyModel, QSettings, QSize

from PyQt5.QtCore import pyqtSlot

from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView, QFileDialog, QCheckBox, QColorDialog, \
                            QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QProgressBar, QApplication, \
                            QDialog, QLineEdit, QLabel, QPushButton, QAbstractItemView, QStatusBar, QMessageBox, \
                            QTableView, QSplitter, QRadioButton, QComboBox, QTextEdit, QSizePolicy, \
                            QTableWidget, QGridLayout, QAbstractButton, QButtonGroup, QGroupBox, \
                            QTabWidget, QListWidget
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap, QStandardItemModel, QStandardItem, QImage,\
                        QFont, QPainter, QBrush, QMouseEvent, QWheelEvent, QDoubleValidator
from PyQt5.QtCore import Qt, QRect, QSortFilterProxyModel, QSize, QPoint,\
                         pyqtSlot, QItemSelectionModel, QTimer

import os, sys

import numpy
from PIL import Image, ImageDraw, ImageChops

import os
from os import listdir
from os.path import isfile, join

MODE = {}
MODE['VIEW'] = 0
MODE['ADD_BOX'] = 1
MODE['MOVE_BOX'] = 2
MODE['EDIT_BOX'] = 3
MODE['EDIT_BOX_READY'] = 4
MODE['EDIT_BOX_PROGRESS'] = 5

class ProgressDialog(QDialog):
    def __init__(self,parent):
        super().__init__()
        #self.setupUi(self)
        #self.setGeometry(200, 250, 400, 250)
        self.setWindowTitle("CTHarvester - Progress Dialog")
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
        self.btnStop.setText("Stop")
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
        self.crop_from_x = -1
        self.crop_from_y = -1
        self.crop_to_x = -1
        self.crop_to_y = -1
        self.orig_pixmap = None
        self.curr_pixmap = None
        self.distance_threshold = self._2imgx(5)
        #print("distance_threshold:", self.distance_threshold)
        self.edit_x1 = False
        self.edit_x2 = False
        self.edit_y1 = False
        self.edit_y2 = False
        self.setMouseTracking(True)
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
        elif self.edit_mode == MODE['MOVE_BOX']:
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
        else:
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
                self.crop_to_x = self._2imgx(self.mouse_curr_x)
                self.crop_to_y = self._2imgy(self.mouse_curr_y)
                #self.object_dialog.edtStatus.setText("({}, {})-({}, {})".format(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y))
            elif self.edit_mode == MODE['EDIT_BOX_PROGRESS']:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                if self.edit_x1:
                    self.crop_from_x = self._2imgx(self.mouse_curr_x)
                elif self.edit_x2:
                    self.crop_to_x = self._2imgx(self.mouse_curr_x)
                if self.edit_y1:
                    self.crop_from_y = self._2imgy(self.mouse_curr_y)
                elif self.edit_y2:
                    self.crop_to_y = self._2imgy(self.mouse_curr_y)
        else:
            if self.edit_mode == MODE['EDIT_BOX']:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    self.set_mode(MODE['EDIT_BOX_READY'])
                else:
                    pass #self.set_mode(MODE['EDIT_BOX'])
            elif self.edit_mode == MODE['EDIT_BOX_READY']:
                self.distance_check(me.x(), me.y())
                if self.edit_x1 or self.edit_x2 or self.edit_y1 or self.edit_y2:
                    pass #self.set_mode(MODE['EDIT_BOX_PROGRESS'])
                else:
                    self.set_mode(MODE['EDIT_BOX'])

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
                self.crop_from_x = img_x
                self.crop_from_y = img_y
                self.crop_to_x = img_x
                self.crop_to_y = img_y
            elif self.edit_mode == MODE['EDIT_BOX_READY']:
                self.mouse_down_x = me.x()
                self.mouse_down_y = me.y()
                self.set_mode(MODE['EDIT_BOX_PROGRESS'])

        self.repaint()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if self.orig_pixmap is None:
            return
        me = QMouseEvent(ev)
        #print("mouseReleaseEvent", me.x(), me.y(),self.edit_mode)
        #print(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y)
        if me.button() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX']:
                img_x = self._2imgx(self.mouse_curr_x)
                img_y = self._2imgy(self.mouse_curr_y)
                if img_x < 0 or img_x > self.orig_pixmap.width() or img_y < 0 or img_y > self.orig_pixmap.height():
                    return
                self.crop_to_x = img_x
                self.crop_to_y = img_y
                self.set_mode(MODE['EDIT_BOX'])
            elif self.edit_mode == MODE['EDIT_BOX_PROGRESS']:
                self.set_mode(MODE['EDIT_BOX'])

            from_x = min(self.crop_from_x, self.crop_to_x)
            to_x = max(self.crop_from_x, self.crop_to_x)
            from_y = min(self.crop_from_y, self.crop_to_y)
            to_y = max(self.crop_from_y, self.crop_to_y)
            self.crop_from_x = from_x
            self.crop_from_y = from_y
            self.crop_to_x = to_x
            self.crop_to_y = to_y
            self.canvas_box = QRect(self._2canx(from_x), self._2cany(from_y), self._2canx(to_x - from_x), self._2cany(to_y - from_y))
            self.object_dialog.update_status()


        self.repaint()

    def paintEvent(self, event):
        # fill background with dark gray

        painter = QPainter(self)
        #painter.fillRect(self.rect(), QBrush(QColor()))#as_qt_color(COLOR['BACKGROUND'])))
        if self.curr_pixmap is not None:
            #print("paintEvent", self.curr_pixmap.width(), self.curr_pixmap.height())
            painter.drawPixmap(0,0,self.curr_pixmap)

        if self.crop_from_x > -1 and self.curr_idx <= self.max_idx and self.curr_idx >= self.min_idx:
            painter.setPen(QPen(Qt.red, 1, Qt.SolidLine))
            from_x = min(self.crop_from_x, self.crop_to_x)
            to_x = max(self.crop_from_x, self.crop_to_x)
            from_y = min(self.crop_from_y, self.crop_to_y)
            to_y = max(self.crop_from_y, self.crop_to_y)
            painter.drawRect(self._2canx(from_x), self._2cany(from_y), self._2canx(to_x - from_x), self._2cany(to_y - from_y))

    def set_image(self,file_path):
        self.fullpath = file_path
        self.curr_pixmap = self.orig_pixmap = QPixmap(file_path)
        self.setPixmap(self.curr_pixmap)
        self.calculate_resize()
        if self.canvas_box:
            self.crop_from_x = self._2imgx(self.canvas_box.x())
            self.crop_from_y = self._2imgy(self.canvas_box.y())
            self.crop_to_x = self._2imgx(self.canvas_box.x() + self.canvas_box.width())
            self.crop_to_y = self._2imgy(self.canvas_box.y() + self.canvas_box.height())
    def set_max_idx(self, max_idx):
        self.max_idx = max_idx
    def set_curr_idx(self, curr_idx):
        self.curr_idx = curr_idx
        #print("set_curr_idx", curr_idx, self.max_idx, self.min_idx)
        #print("set_curr_idx", )
    def set_min_idx(self, min_idx):
        self.min_idx = min_idx

    def calculate_resize(self):
        #print("objectviewer calculate resize", self, self.object, self.object.landmark_list, self.landmark_list)
        if self.orig_pixmap is not None:
            self.distance_threshold = self._2imgx(5)
            #print("distance_threshold:", self.distance_threshold)
            self.orig_width = self.orig_pixmap.width()
            self.orig_height = self.orig_pixmap.height()
            image_wh_ratio = self.orig_width / self.orig_height
            label_wh_ratio = self.width() / self.height()
            if image_wh_ratio > label_wh_ratio:
                self.image_canvas_ratio = self.orig_width / self.width()
            else:
                self.image_canvas_ratio = self.orig_height / self.height()
            self.curr_pixmap = self.orig_pixmap.scaled(int(self.orig_width*self.scale/self.image_canvas_ratio),int(self.orig_width*self.scale/self.image_canvas_ratio), Qt.KeepAspectRatio)

class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #self.setWindowIcon(QIcon(mu.resource_path('icons/Modan2_2.png')))
        self.setWindowTitle("CT Harvester")
        self.setGeometry(QRect(100, 100, 600, 550))
        self.settings_hash = {}
        self.level_info = []
        self.curr_level_idx = 0
        self.prev_level_idx = 0

        # add file open dialog
        self.dirname_layout = QHBoxLayout()
        self.dirname_widget = QWidget()
        self.btnOpenDir = QPushButton("Open Directory")
        self.btnOpenDir.clicked.connect(self.open_dir)
        self.edtDirname = QLineEdit()
        self.edtDirname.setReadOnly(True)
        self.edtDirname.setText("")
        self.edtDirname.setPlaceholderText("Select directory to load CT data")
        self.edtDirname.setMinimumWidth(400)
        self.edtDirname.setMaximumWidth(400)
        self.edtDirname.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dirname_layout.addWidget(self.edtDirname)
        self.dirname_layout.addWidget(self.btnOpenDir)
        self.dirname_widget.setLayout(self.dirname_layout)

        self.image_info_layout = QHBoxLayout()
        self.image_info_widget = QWidget()
        self.edtImageDimension = QLineEdit()
        self.edtImageDimension.setReadOnly(True)
        self.edtImageDimension.setText("")
        self.edtNumImages = QLineEdit()
        self.edtNumImages.setReadOnly(True)
        self.edtNumImages.setText("")
        self.image_info_layout.addWidget(QLabel("Size:"))
        self.image_info_layout.addWidget(self.edtImageDimension)
        self.image_info_layout.addWidget(QLabel("Count:"))
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
        self.btnFromImage.clicked.connect(self.set_from_image)
        self.edtFromImage = QLineEdit()
        self.btnToImage = QPushButton("To >")
        self.btnToImage.clicked.connect(self.set_to_image)
        self.edtToImage = QLineEdit()
        self.btnCrop = QPushButton("Reset")
        self.btnCrop.clicked.connect(self.set_crop)

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

        self.lblLevel = QLabel("Level")
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
        self.image_info_layout2.addWidget(QLabel("Size"))
        self.image_info_layout2.addWidget(self.edtImageDimension2)
        self.image_info_layout2.addWidget(QLabel("Count"))
        self.image_info_layout2.addWidget(self.edtNumImages2)
        self.image_info_widget2.setLayout(self.image_info_layout2)

        self.image_widget2 = QWidget()
        self.image_layout2 = QHBoxLayout()
        self.image_label2 = ObjectViewer2D(self.image_widget2)
        self.image_label2.object_dialog = self
        self.slider = QSlider(Qt.Vertical)
        #self.slider.setTickInterval(1)
        #self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setSingleStep(1)
        #self.slider.setPageStep(1)
        #self.slider.setMinimum(0)
        #self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.sliderValueChanged)

        self.image_layout2.addWidget(self.image_label2)
        self.image_layout2.addWidget(self.slider)
        self.image_widget2.setLayout(self.image_layout2)

        self.crop_layout2 = QHBoxLayout()
        self.crop_widget2 = QWidget()
        self.btnFromImage2 = QPushButton("From >")
        self.btnFromImage2.clicked.connect(self.set_from_image2)
        self.edtFromImage2 = QLineEdit()
        self.btnToImage2 = QPushButton("To >")
        self.btnToImage2.clicked.connect(self.set_to_image2)
        self.edtToImage2 = QLineEdit()
        self.btnCrop2 = QPushButton("Reset")
        self.btnCrop2.clicked.connect(self.set_crop2)

        self.crop_layout2.addWidget(self.btnFromImage2)
        self.crop_layout2.addWidget(self.edtFromImage2)
        self.crop_layout2.addWidget(self.btnToImage2)
        self.crop_layout2.addWidget(self.edtToImage2)
        self.crop_layout2.addWidget(self.btnCrop2)
        self.crop_widget2.setLayout(self.crop_layout2)

        self.edtStatus = QLineEdit()
        self.edtStatus.setReadOnly(True)
        self.edtStatus.setText("")

        self.btnSave = QPushButton("Save")
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

    def save_result(self):
        # open dir dialog for save
        target_dirname = QFileDialog.getExistingDirectory(self, 'Select directory to save', self.edtDirname.text())
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

        for idx in range(int(self.edtFromImage2.text()), int(self.edtToImage2.text())+1):
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

    def sliderValueChanged(self):
        # print current slide value
        #print("sliderValueChanged")
        #print("slider value:", self.slider.value())
        # get scale factor
        size_idx = self.comboLevel.currentIndex()
        #print("size_idx:", size_idx)
        # get directory for size idx
        if size_idx == 0:
            dirname = self.edtDirname.text()
            filename = self.lstFileList.item(self.slider.value()).text()
        else:
            dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            # get filename from level from idx
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + self.slider.value()).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
        #print("dirname:", dirname)
        #print("filename:", filename)

        self.image_label2.set_image(os.path.join(dirname, filename))
        self.image_label2.set_curr_idx(self.slider.value())
        #self.image_label2.setPixmap(QPixmap(os.path.join(dirname, filename)).scaledToWidth(512))

    def set_from_image(self):
        self.edtFromImage.setText(self.lstFileList.currentItem().text())
        self.original_from_idx = self.lstFileList.currentRow()
    
    def set_to_image(self):
        self.edtToImage.setText(self.lstFileList.currentItem().text())
        self.original_to_idx = self.lstFileList.currentRow()

    def set_from_image2(self):
        self.edtFromImage2.setText(str(self.slider.value()))
        self.image_label2.set_min_idx(self.slider.value())
        self.update_status()
    
    def set_to_image2(self):
        self.edtToImage2.setText(str(self.slider.value()))
        self.image_label2.set_max_idx(self.slider.value())
        self.update_status()

    def set_crop2(self):
        self.edtFromImage2.setText(str(self.slider.minimum()))
        self.edtToImage2.setText(str(self.slider.maximum()))
        self.update_status()

    def update_status(self):
        txt = "Images {}-{}".format(self.edtFromImage2.text(), self.edtToImage2.text())
        # add crop box info
        txt += " ({}, {})-({}, {}) ".format(self.image_label2.crop_from_x, self.image_label2.crop_from_y, self.image_label2.crop_to_x, self.image_label2.crop_to_y)
        count = ( int( self.edtToImage2.text() ) - int( self.edtFromImage2.text() ) )
        txt += "Est. {} MB".format(round(count * (self.image_label2.crop_to_x - self.image_label2.crop_from_x) * (self.image_label2.crop_to_y - self.image_label2.crop_from_y) * 2 / 1024 / 1024 , 2))    
        self.edtStatus.setText(txt)

    def calculate_target_idx(self):
        self.target_from_idx = self.original_from_idx
        size_idx = self.comboLevel.currentIndex()
        if size_idx > 0:
            self.target_from_idx = int(self.original_from_idx / 2**size_idx)
        #print("target_from_idx:", self.target_from_idx)
        self.slider.setMinimum(self.target_from_idx)
        self.image_label2.set_min_idx(self.target_from_idx)

        #self.slider.setValue(self.target_from_idx)

        self.target_to_idx = self.original_to_idx
        size_idx = self.comboLevel.currentIndex()
        if size_idx > 0:
            self.target_to_idx = int(self.original_to_idx / 2**size_idx)
        #print("target_to_idx:", self.target_to_idx)
        self.slider.setMaximum(self.target_to_idx)
        self.image_label2.set_max_idx(self.target_to_idx)
    
    def set_crop(self):
        pass

    def initializeComboSize(self):
        self.comboLevel.clear()
        for level in self.level_info:
            #print("level:", level)
            self.comboLevel.addItem( level['name'])
        self.comboLevel.setCurrentIndex(0)
        #self.comboLevelIndexChanged()

    def comboLevelIndexChanged(self):
        #print("comboSizeIndexChanged")
        self.prev_level_idx = self.curr_level_idx
        self.curr_level_idx = self.comboLevel.currentIndex()
        #print("idx:", idx)
        #print("level_info:", self.level_info)
        self.edtImageDimension2.setText(str(self.level_info[self.curr_level_idx]['width']) + " x " + str(self.level_info[self.curr_level_idx]['height']))
        image_count = self.level_info[self.curr_level_idx]['seq_end'] - self.level_info[self.curr_level_idx]['seq_begin'] + 1
        self.edtNumImages2.setText(str(image_count))

        curr_idx = self.slider.value()

        from_idx = 0
        if self.edtFromImage2.text() != '':
            from_idx = int(self.edtFromImage2.text())
            #print("from_idx 1:", from_idx)
            from_idx = int(from_idx * 2**(self.prev_level_idx-self.curr_level_idx))
        #print("from_idx 2:", from_idx)

        to_idx = image_count - 1
        if self.edtToImage2.text() != '':
            to_idx = int(self.edtToImage2.text())
            #print("to_idx 1:", to_idx)
            to_idx = int(to_idx * 2**(self.prev_level_idx-self.curr_level_idx))
        else:
            to_idx = image_count - 1
        #print("to_idx 2:", to_idx)

        #print("curr_idx 1:", curr_idx)
        curr_idx = int(curr_idx * 2**(self.prev_level_idx-self.curr_level_idx))
        #print("curr_idx 2:", curr_idx)
        
        
        self.calculate_target_idx()

        self.edtFromImage2.setText(str(from_idx))
        self.image_label2.set_min_idx(from_idx)
        self.edtToImage2.setText(str(to_idx))
        self.image_label2.set_max_idx(to_idx)

        self.slider.setValue(curr_idx)
        self.sliderValueChanged()
        self.update_status()


    def create_thumbnail(self):
        # determine thumbnail size
        MAX_THUMBNAIL_SIZE = 512
        size =  max(int(self.settings_hash['image_width']), int(self.settings_hash['image_height']))
        width = int(self.settings_hash['image_width'])
        height = int(self.settings_hash['image_height'])
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
            self.progress_dialog.lbl_text.setText("Creating thumbnail level {}...".format(i+1))
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
                self.progress_dialog.lbl_text.setText("Creating smaller images level {}... {}/{}".format(i+1, idx+1, int(total_count/2)))
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
        thumbnail_size = int(size)
        #print("thumbnail size:", thumbnail_size)
        #print("i:", i)

    def lstFileListSelectionChanged(self):
        #print("lstFileListSelectionChanged")
        self.image_label.setPixmap(QPixmap(os.path.join(self.edtDirname.text(), self.lstFileList.currentItem().text())).scaledToWidth(512))

    def open_dir(self):
        #pass
        ddir = QFileDialog.getExistingDirectory(self, "Select directory")
        if ddir:
        # ddir is a QString containing the path to the directory you selected
        #print(ddir)  # this will output something like 'C://path/you/selected'
            self.edtDirname.setText(ddir)
        else:
            return
        image_file_list = []
        for r, d, files in os.walk(ddir):
            for file in files:
                # get extension
                ext = os.path.splitext(file)[-1].lower()
                if ext in [".bmp", ".jpg", ".png", ".tif", ".tiff"]:
                    pass #image_file_list.append(file)
                elif ext == '.log':
                    fn = os.path.join(r,file)
                    #print("log file:", fn)
                    settings = QSettings(os.path.join(r,file), QSettings.IniFormat)
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
        if 'prefix' not in self.settings_hash:
            return
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
        #self.initializeComboSize()
        #self.open_dir()
        self.create_thumbnail()

        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    #app.setWindowIcon(QIcon(mu.resource_path('icons/Modan2_2.png')))
    #app.settings = 
    #app.preferences = QSettings("Modan", "Modan2")

    #WindowClass의 인스턴스 생성
    myWindow = CTHarvesterMainWindow()

    #프로그램 화면을 보여주는 코드
    myWindow.show()

    #프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    app.exec_()
'''
pyinstaller --onefile --noconsole CTHarvester.py
'''