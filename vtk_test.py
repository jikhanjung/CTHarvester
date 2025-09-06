import vtkmodules.all as vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QFrame, QVBoxLayout, QPushButton, QSlider, QWidget, QFileDialog
from PyQt5.QtCore import Qt
from PIL import Image
import numpy as np
import sys
import os

class CTVisualizationApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CT Scan 3D Visualization")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.vl = QVBoxLayout(self.central_widget)

        self.frame = QFrame(self.central_widget)
        self.vl.addWidget(self.frame)

        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.render_window_interactor = vtk.vtkRenderWindowInteractor()
        self.render_window_interactor.SetRenderWindow(self.render_window)

        self.frame.setLayout(self.renderer)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(255)  # Adjust as per your BMP image range
        self.slider.setValue(128)  # Initial threshold value
        self.slider.valueChanged.connect(self.update_threshold)

        self.vl.addWidget(self.slider)

        self.button = QPushButton("Load BMP Data")
        self.button.clicked.connect(self.load_bmp_data)
        self.vl.addWidget(self.button)

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
            vtk_image.GetPointData().SetScalars(vtk.util.numpy_support.numpy_to_vtk(img_array.ravel(), deep=True))

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

    def update_threshold(self, value):
        if self.actor:
            self.mapper.SetValue(0, value)
            self.render_window.Render()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CTVisualizationApp()
    window.show()
    sys.exit(app.exec_())
