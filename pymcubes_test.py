import os
import numpy as np
import mcubes
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image

# Create a 3D scalar field (for demonstration, you should replace this with your CT scan data)
def scalar_field(x, y, z):
    return x**2 + y**2 + z**2  # Replace with your own scalar field function

# Define the grid dimensions
x, y, z = np.mgrid[-5:5:50j, -5:5:50j, -5:5:50j]
print(x.shape,y.shape,z.shape)
print(x)

# Evaluate the scalar field on the grid
data = scalar_field(x, y, z)
print(data.shape)
print(data)

def read_images_from_folder(folder):
    images = []
    for filename in os.listdir(folder):
        # read images using Pillow
        img = Image.open(os.path.join(folder,filename))
        #img = cv2.imread(os.path.join(folder,filename),0)
        if img is not None:
            images.append(np.array(img))
    return np.array(images)

data = read_images_from_folder( "D:/CT/CO-1/CO-1_Rec/Cropped" )

# Set the isovalue for the isosurface
isovalue = 10.0  # Adjust this to match your data

# Extract the isosurface vertices and triangles using PyMCubes
vertices, triangles = mcubes.marching_cubes(data, isovalue)

# Create a 3D plot for visualization
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot the isosurface
ax.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2], triangles=triangles, cmap='viridis')

# Set axis labels
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')

# Show the plot
plt.show()
