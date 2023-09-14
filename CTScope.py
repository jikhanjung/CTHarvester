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
        print("distance_threshold:", self.distance_threshold)
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
        print("distance_check", self.crop_from_x, self.crop_to_x, x, self.crop_from_y, self.crop_to_y, y, self.edit_x1, self.edit_x2, self.edit_y1, self.edit_y2)
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
        me = QMouseEvent(event)
        print("mouseMoveEvent", me.x(), me.y(), self.edit_mode)
        print(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y)
        if me.buttons() == Qt.LeftButton:
            if self.edit_mode == MODE['ADD_BOX']:
                self.mouse_curr_x = me.x()
                self.mouse_curr_y = me.y()
                self.crop_to_x = self._2imgx(self.mouse_curr_x)
                self.crop_to_y = self._2imgy(self.mouse_curr_y)
                self.object_dialog.edtStatus.setText("({}, {})-({}, {})".format(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y))
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

        me = QMouseEvent(event)
        print("mousePressEvent", me.x(), me.y(),self.edit_mode)
        print(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y)
        if me.button() == Qt.LeftButton:
            #if self.object_dialog is None:
            #    return
            if self.edit_mode == MODE['ADD_BOX'] or self.edit_mode == MODE['EDIT_BOX']:
                self.set_mode(MODE['ADD_BOX'])
                img_x = self._2imgx(me.x())
                img_y = self._2imgy(me.y())
                print("mousePressEvent", img_x, img_y)
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
        me = QMouseEvent(ev)
        print("mouseReleaseEvent", me.x(), me.y(),self.edit_mode)
        print(self.crop_from_x, self.crop_from_y, self.crop_to_x, self.crop_to_y)
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


        self.repaint()

    def paintEvent(self, event):
        # fill background with dark gray

        painter = QPainter(self)
        #painter.fillRect(self.rect(), QBrush(QColor()))#as_qt_color(COLOR['BACKGROUND'])))
        if self.curr_pixmap is not None:
            #print("paintEvent", self.curr_pixmap.width(), self.curr_pixmap.height())
            painter.drawPixmap(0,0,self.curr_pixmap)

        if self.crop_from_x > -1:
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
            

    def calculate_resize(self):
        #print("objectviewer calculate resize", self, self.object, self.object.landmark_list, self.landmark_list)
        if self.orig_pixmap is not None:
            self.distance_threshold = self._2imgx(5)
            print("distance_threshold:", self.distance_threshold)
            self.orig_width = self.orig_pixmap.width()
            self.orig_height = self.orig_pixmap.height()
            image_wh_ratio = self.orig_width / self.orig_height
            label_wh_ratio = self.width() / self.height()
            if image_wh_ratio > label_wh_ratio:
                self.image_canvas_ratio = self.orig_width / self.width()
            else:
                self.image_canvas_ratio = self.orig_height / self.height()
            self.curr_pixmap = self.orig_pixmap.scaled(int(self.orig_width*self.scale/self.image_canvas_ratio),int(self.orig_width*self.scale/self.image_canvas_ratio), Qt.KeepAspectRatio)

def resample2():

    mypath_format = "D:/CT/CO-{}/CO-{}_Rec/small/"
    file_prefix_format = "CO-{}__rec"

    begin_idx = 215
    end_idx = 969

    for i in range(1,2):
        for z_idx in range(begin_idx,end_idx,2):
            print("idx:", z_idx)
            num1 = "000000" + str( z_idx )
            num2 = "000000" + str( z_idx +1)
            num3 = "000000" + str(begin_idx+int((z_idx-begin_idx) / 2))
            filename1 = file_prefix_format.format(i) + num1[-8:] + ".bmp"
            filename2 = file_prefix_format.format(i) + num2[-8:] + ".bmp"
            filename3 = file_prefix_format.format(i) + num3[-8:] + ".bmp"
            img1 = Image.open(mypath_format.format(i,i) + filename1 )
            img2 = Image.open(mypath_format.format(i,i) + filename2 )

            small_img1 = img1.resize( (int(img1.width/2),int(img1.height/2)) )
            small_img2 = img2.resize((int(img1.width / 2), int(img1.height / 2)))

            new_img_ops = ImageChops.add(small_img1, small_img2, scale=2.0)
            new_path2 = mypath_format.format(i,i) + "smaller2/"
            if not os.path.exists(new_path2):
                os.makedirs(new_path2)
            new_img_ops.save(new_path2 + filename3)

class CTScopeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #self.setWindowIcon(QIcon(mu.resource_path('icons/Modan2_2.png')))
        self.setWindowTitle("CT Scape")
        self.setGeometry(QRect(100, 100, 600, 550))
        self.settings_hash = {}
        self.level_info = []

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
        self.image_info_layout.addWidget(QLabel("Image Dimension:"))
        self.image_info_layout.addWidget(self.edtImageDimension)
        self.image_info_layout.addWidget(QLabel("Number of Images:"))
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
        self.btnCrop = QPushButton("Set Crop")
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

        self.lblLevel = QLabel("Select level:")
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
        self.image_info_layout2.addWidget(QLabel("Image Dimension:"))
        self.image_info_layout2.addWidget(self.edtImageDimension2)
        self.image_info_layout2.addWidget(QLabel("Number of Images:"))
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
        self.btnCrop2 = QPushButton("Set Crop")
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


        self.right_layout = QVBoxLayout()
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.right_layout)
        #self.right_layout.addWidget(self.comboSize)
        self.right_layout.addWidget(self.dirname_widget)
        self.right_layout.addWidget(self.image_info_widget2)
        self.right_layout.addWidget(self.image_widget2)
        self.right_layout.addWidget(self.crop_widget2)
        self.right_layout.addWidget(self.edtStatus)

        self.main_layout = QHBoxLayout()
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)
        #self.main_layout.addWidget(self.left_widget)
        self.main_layout.addWidget(self.right_widget)

        self.setCentralWidget(self.main_widget)


    def sliderValueChanged(self):
        # print current slide value
        #print("sliderValueChanged")
        #print("slider value:", self.slider.value())
        # get scale factor
        size_idx = self.comboLevel.currentIndex()
        # get directory for size idx
        if size_idx == 0:
            dirname = self.edtDirname.text()
            filename = self.lstFileList.item(self.slider.value()).text()
        else:
            dirname = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(size_idx))
            # get filename from level from idx
            filename = self.settings_hash['prefix'] + str(self.level_info[size_idx]['seq_begin'] + self.slider.value()).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']

        self.image_label2.set_image(os.path.join(dirname, filename))
        #self.image_label2.setPixmap(QPixmap(os.path.join(dirname, filename)).scaledToWidth(512))

    def set_from_image(self):
        self.edtFromImage.setText(self.lstFileList.currentItem().text())
        self.original_from_idx = self.lstFileList.currentRow()
    
    def set_to_image(self):
        self.edtToImage.setText(self.lstFileList.currentItem().text())
        self.original_to_idx = self.lstFileList.currentRow()

    def set_from_image2(self):
        self.edtFromImage2.setText(str(self.slider.value()))
    
    def set_to_image2(self):
        self.edtToImage2.setText(str(self.slider.value()))

    def set_crop2(self):
        self.image_label2.set_mode(MODE['CROP'])

    def calculate_target_idx(self):
        self.target_from_idx = self.original_from_idx
        size_idx = self.comboLevel.currentIndex()
        if size_idx > 0:
            self.target_from_idx = int(self.original_from_idx / 2**size_idx)
        #print("target_from_idx:", self.target_from_idx)
        self.slider.setMinimum(self.target_from_idx)
        #self.slider.setValue(self.target_from_idx)

        self.target_to_idx = self.original_to_idx
        size_idx = self.comboLevel.currentIndex()
        if size_idx > 0:
            self.target_to_idx = int(self.original_to_idx / 2**size_idx)
        #print("target_to_idx:", self.target_to_idx)
        self.slider.setMaximum(self.target_to_idx)
    
    def set_crop(self):
        pass

    def initializeComboSize(self):
        self.comboLevel.clear()
        for level in self.level_info:
            self.comboLevel.addItem( level['name'])

    def comboLevelIndexChanged(self):
        #print("comboSizeIndexChanged")
        idx = self.comboLevel.currentIndex()
        #print("idx:", idx)
        #print("level_info:", self.level_info)
        self.edtImageDimension2.setText(str(self.level_info[idx]['width']) + " x " + str(self.level_info[idx]['height']))
        self.edtNumImages2.setText(str(self.level_info[idx]['seq_end'] - self.level_info[idx]['seq_begin'] + 1))

        self.edtFromImage2.setText(str(0))
        self.edtToImage2.setText(str(self.level_info[idx]['seq_end'] - self.level_info[idx]['seq_begin'] + 1))
        self.slider.setValue(0)

        self.calculate_target_idx()

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
        while True:
            size /= 2
            width = int(width / 2)
            height = int(height / 2)

            if i == 0:
                from_dir = dirname
            else:
                from_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i))

            # create thumbnail
            to_dir = os.path.join(self.edtDirname.text(), ".thumbnail/" + str(i+1))
            if not os.path.exists(to_dir):
                os.makedirs(to_dir)
            

            for idx, seq in enumerate(range(seq_begin, seq_end+1, 2)):
                filename1 = self.settings_hash['prefix'] + str(seq).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
                filename2 = self.settings_hash['prefix'] + str(seq+1).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type']
                filename3 = os.path.join(to_dir, self.settings_hash['prefix'] + str(seq_begin + idx).zfill(self.settings_hash['index_length']) + "." + self.settings_hash['file_type'])
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
                    continue
                new_img_ops = ImageChops.add(img1, img2, scale=2.0)
                # resize to half
                new_img_ops = new_img_ops.resize((int(img1.width / 2), int(img1.height / 2)))
                # save to temporary directory
                new_img_ops.save(filename3)
            i+= 1
            seq_end = int((seq_end - seq_begin) / 2) + seq_begin
            self.level_info.append( {'name': "Level " + str(i), 'width': width, 'height': height, 'seq_begin': seq_begin, 'seq_end': seq_end} )
            if size < MAX_THUMBNAIL_SIZE:
                break
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
        # ddir is a QString containing the path to the directory you selected
        #print(ddir)  # this will output something like 'C://path/you/selected'
        self.edtDirname.setText(ddir)
        image_file_list = []
        for r, d, files in os.walk(ddir):
            for file in files:
                # get extension
                ext = os.path.splitext(file)[-1].lower()
                if ext in [".bmp", ".jpg", ".png", ".tif", ".tiff"]:
                    pass #image_file_list.append(file)
                elif ext == '.log':
                    settings = QSettings(os.path.join(r,file), QSettings.IniFormat)
                    self.settings_hash['prefix'] = settings.value("File name convention/Filename Prefix")
                    self.settings_hash['image_width'] = settings.value("Reconstruction/Result Image Width (pixels)")
                    self.settings_hash['image_height'] = settings.value("Reconstruction/Result Image Height (pixels)")
                    self.settings_hash['file_type'] = settings.value("Reconstruction/Result File Type")
                    self.settings_hash['index_length'] = int(settings.value("File name convention/Filename Index Length"))
                    self.settings_hash['seq_begin'] = int(settings.value("Reconstruction/First Section"))
                    self.settings_hash['seq_end'] = int(settings.value("Reconstruction/Last Section"))
                    self.edtNumImages.setText(str(self.settings_hash['seq_end'] - self.settings_hash['seq_begin'] + 1))
                    self.edtImageDimension.setText(str(self.settings_hash['image_width']) + " x " + str(self.settings_hash['image_height']))
                    #print("Settings hash:", settings_hash)
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
        self.initializeComboSize()
        #self.open_dir()
        self.create_thumbnail()

        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    #app.setWindowIcon(QIcon(mu.resource_path('icons/Modan2_2.png')))
    #app.settings = 
    #app.preferences = QSettings("Modan", "Modan2")

    #WindowClass의 인스턴스 생성
    myWindow = CTScopeMainWindow()

    #프로그램 화면을 보여주는 코드
    myWindow.show()

    #프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    app.exec_()
'''
pyinstaller --onefile --noconsole CTScope.py
'''