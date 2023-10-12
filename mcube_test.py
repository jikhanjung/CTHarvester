import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QCheckBox
from PyQt5.QtCore import Qt, QTimer
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from PIL import Image
import mcubes
from PyQt5.QtOpenGL import *

import numpy as np
from scipy import ndimage  # For interpolation
import math

OBJECT_MODE = 1
VIEW_MODE = 1
PAN_MODE = 2
ROTATE_MODE = 3
ZOOM_MODE = 4



# Define a custom OpenGL widget using QOpenGLWidget
class MCubeWidget(QGLWidget):
    def __init__(self,parent):
        super().__init__(parent=parent)
        #self.parent = parent
        self.setMinimumSize(100,100)
        #self.volume = self.read_images_from_folder( "D:/CT/CO-1/CO-1_Rec/Cropped" ) #np.zeros((10, 10, 10))  # Define the volume to visualize
        # Example usage:
        self.isovalue = 60  # Adjust the isovalue as needed
        #self.triangles, self.vertices = self.marching_cubes(self.volume,isovalue)
        #print(triangles)
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
        self.timer.timeout.connect(self.timeout)
        self.timer.start()
        self.triangles = []
        self.gl_list_generated = False
        self.parent = parent
        self.parent.set_threed_view(self)
        self.cbxRotation = QCheckBox(self)
        self.cbxRotation.setText("R")
        self.cbxRotation.setChecked(True)
        self.cbxRotation.stateChanged.connect(self.cbxRotation_stateChanged)
        self.cbxRotation.setStyleSheet("QCheckBox { background-color: #323232; color: white; }")        
        self.cbxRotation.hide()
        #setStyleSheet("QCheckBox { background-color: #323232 }")

        #print("init")

    def cbxRotation_stateChanged(self):
        self.auto_rotate = self.cbxRotation.isChecked()

    def resize_self(self):
        size = min(self.parent.width(),self.parent.height())
        self.resize(int(size*0.25),int(size*0.25))
        #print("resize:",self.parent.width(),self.parent.height())

    def generate_mesh(self):
        self.cbxRotation.show()
        self.vertices, self.triangles = mcubes.marching_cubes(self.volume, self.isovalue)
        self.vertices /= 10.0
        average_coordinates = np.mean(self.vertices, axis=0)
        self.vertices -= average_coordinates

        face_normals = []
        for triangle in self.triangles:
            v0 = self.vertices[triangle[0]]
            v1 = self.vertices[triangle[1]]
            v2 = self.vertices[triangle[2]]
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            norm = np.linalg.norm(normal)
            if norm == 0:
                normal = np.array([0, 0, 0])
            else:
                normal /= np.linalg.norm(normal)
            face_normals.append(normal)

        vertex_normals = np.zeros(self.vertices.shape)

        # Calculate vertex normals by averaging face normals
        for i, triangle in enumerate(self.triangles):
            for vertex_index in triangle:
                vertex_normals[vertex_index] += face_normals[i]

        # Normalize vertex normals
        '''
        norms = np.linalg.norm(vertex_normals, axis=1)
        vertex_normals = np.where(norms != 0, vertex_normals / norms[:, np.newaxis], np.array([0.0, 0.0, 0.0]))
        self.vertex_normals = vertex_normals

        '''
        for i in range(len(vertex_normals)):
            if np.linalg.norm(vertex_normals[i]) != 0:
                vertex_normals[i] /= np.linalg.norm(vertex_normals[i])
            else:
                vertex_normals[i] = np.array([0.0, 0.0, 0.0])
        
        #vertex_normals /= np.linalg.norm(vertex_normals, axis=1)[:, np.newaxis]
        self.vertex_normals = vertex_normals

        for i in range(len(self.vertices)):
            #continue
            # rotate 90 degrees around y axis
            self.vertices[i] = np.array([self.vertices[i][2],self.vertices[i][1],-1*self.vertices[i][0]])
            # rotate vertex normal 90degrees around y axis
            self.vertex_normals[i] = np.array([self.vertex_normals[i][2],self.vertex_normals[i][1],-1*self.vertex_normals[i][0]])
            # rotate -90 degrees around x axis
            self.vertices[i] = np.array([self.vertices[i][0],-1*self.vertices[i][2],self.vertices[i][1]])
            # rotate vertex normal -90degrees around x axis
            self.vertex_normals[i] = np.array([self.vertex_normals[i][0],-1*self.vertex_normals[i][2],self.vertex_normals[i][1]])

            #print("vertex:", vertex)
            #print("1:",vertex[0],vertex[1],vertex[2])
            #print("2:",vertex[0],vertex[2],-1*vertex[1])
            #print("3:",vertex[2],vertex[1],-1*vertex[0])
            #print("4:",vertex[2],vertex[0],vertex[1])
            #print("5:",-1*vertex[1],vertex[0],vertex[2])
            #print("6:",-1*vertex[1],vertex[2],-1*vertex[0])
            #print("7:",-1*vertex[0],vertex[1],vertex[2])
            #print("8:",-1*vertex[0],vertex[2],-1*vertex[1])
            #print("9:",-1*vertex[2],vertex[0],vertex[1])
            #print("10:",-1*vertex[2],vertex[1],-1*vertex[0])

        #print(len(self.vertices),len(self.triangles))
        self.generate_gl_list()

    def set_volume(self, volume):
        self.volume = volume
        #print(self.volume.shape)
        max_len = max(self.volume.shape)
        # set max length to 100
        scale_factors = 50.0/max_len

        # Use scipy's zoom function for interpolation
        self.volume = ndimage.zoom(self.volume, scale_factors, order=1)
        #print(self.volume.shape)

    def set_isovalue(self, isovalue):
        self.isovalue = isovalue

    def set_total_volume_box(self, total_volume_box):
        self.total_volume_box = total_volume_box

    def set_roi_volume_box(self, roi_volume_box):
        self.roi_volume_box = roi_volume_box

    def read_images_from_folder(self,folder):
        images = []
        for filename in os.listdir(folder):
            # read images using Pillow
            img = Image.open(os.path.join(folder,filename))
            #img = cv2.imread(os.path.join(folder,filename),0)
            if img is not None:
                images.append(np.array(img))
        return np.array(images)

    def timeout(self):
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
        # left button: rotate
        # right button: zoom
        # middle button: pan

        self.down_x = event.x()
        self.down_y = event.y()
        #print("down_x:", self.down_x, "down_y:", self.down_y)
        if event.buttons() == Qt.LeftButton:
            self.view_mode = ROTATE_MODE
        elif event.buttons() == Qt.RightButton:
            self.view_mode = ZOOM_MODE
        elif event.buttons() == Qt.MiddleButton:
            self.view_mode = PAN_MODE

    def mouseReleaseEvent(self, event):
        import datetime
        self.is_dragging = False
        self.curr_x = event.x()
        self.curr_y = event.y()
        #print("curr_x:", self.curr_x, "curr_y:", self.curr_y)
        if event.button() == Qt.LeftButton:
                self.rotate_x += self.temp_rotate_x
                self.rotate_y += self.temp_rotate_y
                if False: #self.threed_model is not None:
                    #print("rotate_x:", self.rotate_x, "rotate_y:", self.rotate_y)
                    #print("1:",datetime.datetime.now())
                    if self.show_model == True:
                        apply_rotation_to_vertex = True
                    else:
                        apply_rotation_to_vertex = False
                    self.threed_model.rotate(math.radians(self.rotate_x),math.radians(self.rotate_y),apply_rotation_to_vertex)
                    #print("2:",datetime.datetime.now())
                    #self.threed_model.rotate_3d(math.radians(-1*self.rotate_x),'Y')
                    #self.threed_model.rotate_3d(math.radians(self.rotate_y),'X')
                    if self.show_model == True:
                        self.threed_model.generate()
                    #print("3:",datetime.datetime.now())
                #print( "test_obj vert 1 after rotation:", self.test_obj.vertices[0])
                #self.rotate_x = 0
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
        #self.parent.update_status()

    def mouseMoveEvent(self, event):
        #@print("mouse move event",event)
        self.curr_x = event.x()
        self.curr_y = event.y()
        #print("curr_x:", self.curr_x, "curr_y:", self.curr_y)

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
        #print("wheel event", event.angleDelta().y())
        self.dolly -= event.angleDelta().y() / 240.0
        self.updateGL()


    def initializeGL(self):
        #print("initGL")
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_COLOR_MATERIAL)
        #glEnable(GL_BLEND)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glShadeModel(GL_SMOOTH)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

    def resizeGL(self, width, height):
        #print("resizeGL")
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (width / height), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        #print("paintGL")
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
        #glRotatef(90,0.0,1.0,0.0)
        glRotatef(self.rotate_y + self.temp_rotate_y, 1.0, 0.0, 0.0)
        glRotatef(self.rotate_x + self.temp_rotate_x, 0.0, 1.0, 0.0)


        glColor3f( 0.0,0.6,0.0 ) #*COLOR['WIREFRAME'])


        count = 0
        if len(self.triangles) == 0:
            return

        glClearColor(0.2,0.2,0.2, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.gl_list_generated == False:
            self.generate_gl_list()

        self.render_gl_list()

        glColor4f(0.0, 1.0, 0.0, 0.5) 

        '''
        glBegin(GL_LINE_STRIP)
        glVertex3f(-2.0, 0.0, -2.0)
        glVertex3f(2.0, 0.0, -2.0)
        glVertex3f(2.0, 0.0, 2.0)
        glVertex3f(-2.0, 0.0, 2.0)
        glVertex3f(-2.0, 0.0, -2.0)
        glEnd()
        '''

        glBegin(GL_QUADS)
        glVertex3f(-2.0, 0.0, -2.0)
        glVertex3f(2.0, 0.0, -2.0)
        glVertex3f(2.0, 0.0, 2.0)
        glVertex3f(-2.0, 0.0, 2.0)
        glEnd()


        return

        # Render the 3D surface
        glBegin(GL_TRIANGLES)
        
        for triangle in self.triangles:
        #    #print(triangle)
            #count += 1
            for vertex in triangle:
                glNormal3fv(self.vertex_normals[vertex])
                glVertex3fv(self.vertices[vertex])
                #print(self.vertices[vertex])
                #break
            #if count == 10:
            #    break
        #glVertex3fv([1.0,0.0,0.0])
        #glVertex3fv([0.0,1.0,0.0])
        #glVertex3fv([0.0,0.0,1.0])
        glEnd()


    def render_gl_list(self):
        if self.gl_list_generated == False:
            return
        #print("render", self, self.gl_list)
        glCallList(self.gl_list)
        return

    def generate_gl_list(self):
        self.gl_list = glGenLists(1)
        glNewList(self.gl_list, GL_COMPILE)

        # Render the 3D surface
        glBegin(GL_TRIANGLES)
        
        for triangle in self.triangles:
        #    #print(triangle)
            #count += 1
            for vertex in triangle:
                glNormal3fv(self.vertex_normals[vertex])
                glVertex3fv(self.vertices[vertex])
                #print(self.vertices[vertex])
                #break
            #if count == 10:
            #    break
        #glVertex3fv([1.0,0.0,0.0])
        #glVertex3fv([0.0,1.0,0.0])
        #glVertex3fv([0.0,0.0,1.0])
        glEnd()
        glEndList()
        self.gl_list_generated = True

# Define your PyQt main application
class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle("Marching Cubes Visualization")

        # Create the OpenGL widget and add it to the main window
        self.mcube_widget = MCubeWidget(self)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.mcube_widget)
        self.mcube_widget.set_volume( self.mcube_widget.read_images_from_folder( "D:/CT/CO-1/CO-1_Rec/Cropped" ) )
        self.mcube_widget.generate_mesh()
        #self.volume = self.read_images_from_folder( "D:/CT/CO-1/CO-1_Rec/Cropped" ) #np.zeros((10, 10, 10))  # Define the volume to visualize

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