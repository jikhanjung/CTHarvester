import numpy
from PIL import Image, ImageDraw, ImageChops

from os import listdir
from os.path import isfile, join

file_path = "D:/Dropbox/Blender/Estaingia/Estaingia_simulation_rigid_body_rough_surface/estaingia_landmark_20221125_rigid_body_rough_surface_2.txt"

with open(file_path) as f:
    lines = f.readlines()

specimen_text = ''
prev_specimen_name = ''
landmark_count = 0
coords_list = []
specimen_count = 100

for line in lines:
    #print(line)
    specimen_name, x, y, z = line.split("\t")
    #print(x,y,z)
    if specimen_name != prev_specimen_name:
        if prev_specimen_name != '':
            specimen_count += 1
            specimen_text += "lm=" + str(len(coords_list)) + "\t" + "Estaingia_" + str(specimen_count) + "\n"
            specimen_text += "\n".join(coords_list) + "\n"
            coords_list = []
            landmark_count = 0
       
    landmark_count += 1
    coords = [x,y,z]
    #print(coords)
    coords = [str(int((float(val)+10.0)*100)/100.0) for val in coords]
    #print(coords)
    coords_list.append("\t".join(coords))
    prev_specimen_name = specimen_name


specimen_count += 1
specimen_text += "lm=" + str(len(coords_list)) + "\t" + "Estaingia_" + str(specimen_count) + "\n"
#specimen_text += "lm=" + str(len(coords_list)) + "\t" + prev_specimen_name + "\n"
specimen_text += "\n".join(coords_list) + "\n"

print(specimen_text)