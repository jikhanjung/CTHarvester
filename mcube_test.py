import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *


# Define the Marching Cubes lookup tables (as shown in the previous example)
edgeTable = [
    0x0, 0x109, 0x203, 0x30a, 0x406, 0x50f, 0x605, 0x70c,
    0x80c, 0x905, 0xa0f, 0xb06, 0xc0a, 0xd03, 0xe09, 0xf00,
]

triTable = [
    [],
    [0, 8, 3],
    [0, 1, 9],
    [1, 8, 3, 9, 8, 1],
    [1, 2, 10],
    [0, 8, 3, 1, 2, 10],
    [9, 2, 10, 0, 2, 9],
    [2, 8, 3, 2, 10, 8, 10, 9, 8],
    [3, 11, 2],
    [0, 11, 2, 8, 11, 0],
    [1, 9, 0, 2, 3, 11],
    [1, 11, 2, 1, 9, 11, 9, 8, 11],
    [3, 10, 1, 11, 10, 3],
    [0, 10, 1, 0, 8, 10, 8, 11, 10],
    [3, 9, 0, 3, 11, 9, 11, 10, 9],
    [9, 8, 10, 10, 8, 11],
]

# Define the cube vertices (as shown in the previous example)
cubeVertices = np.array([
    [0, 0, 0],
    [1, 0, 0],
    [1, 1, 0],
    [0, 1, 0],
    [0, 0, 1],
    [1, 0, 1],
    [1, 1, 1],
    [0, 1, 1],
])

# Define your scalar field function and perform Marching Cubes to get vertices and triangles
def scalar_field(x, y, z):
    # Your scalar field function logic here
    return 0.0  # Replace with the actual scalar field value


# Define a function to perform Marching Cubes
def marching_cubes(volume,isovalue):
    vertices = []
    triangles = []
    #grid = np.zeros((2, 2, 2))  # Define the grid to sample the scalar field
    grid = volume

    for i in range(grid.shape[0] - 1):
        for j in range(grid.shape[1] - 1):
            for k in range(grid.shape[2] - 1):
                cube = np.array([
                    [i, j, k],
                    [i+1, j, k],
                    [i+1, j+1, k],
                    [i, j+1, k],
                    [i, j, k+1],
                    [i+1, j, k+1],
                    [i+1, j+1, k+1],
                    [i, j+1, k+1],
                ])
                values = np.array([scalar_field(*v) for v in cube])

                cubeIndex = 0
                if values[0] < isovalue: cubeIndex |= 1
                if values[1] < isovalue: cubeIndex |= 2
                if values[2] < isovalue: cubeIndex |= 4
                if values[3] < isovalue: cubeIndex |= 8
                if values[4] < isovalue: cubeIndex |= 16
                if values[5] < isovalue: cubeIndex |= 32
                if values[6] < isovalue: cubeIndex |= 64
                if values[7] < isovalue: cubeIndex |= 128

                if edgeTable[cubeIndex] == 0:
                    continue

                verts = np.zeros((12, 3))
                for j in range(12):
                    if edgeTable[cubeIndex] & (1 << j):
                        v1, v2 = cube[triTable[j][0]], cube[triTable[j][1]]
                        edgeV = (isovalue - values[triTable[j][0]]) / (values[triTable[j][1]] - values[triTable[j][0]])
                        verts[j] = v1 + edgeV * (v2 - v1)

                for j in range(16):
                    if triTable[cubeIndex][j] != -1:
                        triangles.append(verts[triTable[cubeIndex][j]])

    return np.array(triangles)



# Define a custom OpenGL widget using QOpenGLWidget
class OpenGLWidget(QWidget):
    def __init__(self):
        super().__init__()

        volume = np.zeros((10, 10, 10))  # Define the volume to visualize

        # Example usage:
        isovalue = 0.0  # Adjust the isovalue as needed
        triangles = marching_cubes(volume,isovalue)
        print(triangles)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (width / height), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Set camera position and view
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)
        
        # Render the 3D surface
        glBegin(GL_TRIANGLES)
        for triangle in triangles:
            for vertex in triangle:
                glVertex3fv(vertices[vertex])
        glEnd()

# Define your PyQt main application
class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle("Marching Cubes Visualization")

        # Create the OpenGL widget and add it to the main window
        self.openglWidget = OpenGLWidget()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.openglWidget)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

def main():
    app = QApplication(sys.argv)
    window = MainApplication()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()