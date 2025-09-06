import vtkmodules.all as vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QSlider, QWidget, QFileDialog
from PyQt5.QtCore import Qt
import sys, os
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PIL import Image
import numpy as np
import vtk.util.numpy_support as numpy_support

class CTVisualizationApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CT Scan 3D Visualization")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.vl = QVBoxLayout(self.central_widget)

        self.vtk_widget = QVTKRenderWindowInteractor(self.central_widget)
        self.vl.addWidget(self.vtk_widget)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)  # You can set your own range
        self.slider.setValue(500)  # Initial threshold value
        self.slider.valueChanged.connect(self.update_threshold)

        self.vl.addWidget(self.slider)

        self.button = QPushButton("Load BMP Data")
        self.button.clicked.connect(self.load_bmp_data)
        #self.button = QPushButton("Load CT Data")
        #self.button.clicked.connect(self.load_ct_data)
        self.vl.addWidget(self.button)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

        self.actor = None
        self.reader = None

    def load_bmp_data(self):
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open BMP Image", "", "BMP Files (*.bmp);;All Files (*)")

        if file_path:
            # Load the BMP image
            img = Image.open(file_path)
            img_array = np.array(img)

            # Create a VTK image data
            vtk_image = vtk.vtkImageData()
            vtk_image.SetDimensions(img_array.shape[1], img_array.shape[0], 1)
            vtk_image.SetSpacing(1.0, 1.0, 1.0)
            vtk_image.SetOrigin(0.0, 0.0, 0.0)
            vtk_image.GetPointData().SetScalars(numpy_support.numpy_to_vtk(img_array.ravel(), deep=True))

            # Create a VTK actor
            self.actor = vtk.vtkActor()

            self.mapper = vtk.vtkMarchingCubes()
            self.mapper.SetInputData(vtk_image)
            self.mapper.SetValue(0, self.slider.value())  # Initial threshold value

            self.actor.SetMapper(self.mapper)

            self.renderer.AddActor(self.actor)
            self.renderer.ResetCamera()

            self.render_window.Render()
            self.render_window_interactor.Start()

    def load_ct_data(self):
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open CT Scan Data", "", "DICOM Files (*.dcm);;All Files (*)")

        if file_path:
            self.reader = vtk.vtkDICOMImageReader()
            self.reader.SetFileName(file_path)

            self.actor = vtk.vtkActor()

            self.mapper = vtk.vtkMarchingCubes()
            self.mapper.SetInputConnection(self.reader.GetOutputPort())
            self.mapper.SetValue(0, self.slider.value() / 1000.0)  # Initial threshold value

            self.actor.SetMapper(self.mapper)

            self.renderer.AddActor(self.actor)
            self.renderer.ResetCamera()

            self.vtk_widget.GetRenderWindow().Render()
            self.interactor.Start()

    def update_threshold(self, value):
        if self.actor:
            self.mapper.SetValue(0, value / 1000.0)
            self.vtk_widget.GetRenderWindow().Render()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CTVisualizationApp()
    window.show()
    sys.exit(app.exec_())
