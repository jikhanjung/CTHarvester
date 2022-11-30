import numpy
from PIL import Image, ImageDraw, ImageChops

from os import listdir
from os.path import isfile, join

path_list = [
    "D:/Dropbox/Blender/Estaingia/Estaingia_simulation_rigid_body_flat_surface/",
    "D:/Dropbox/Blender/Estaingia/Estaingia_simulation_rigid_body_tilted_surface/",
    "D:/Dropbox/Blender/Estaingia/Estaingia_simulation_rigid_body_rough_surface/",
    "D:/Dropbox/Blender/Estaingia/Estaingia_simulation_rigid_body_rough_surface/"
]

input_file_list = [ 
    "estaingia_landmark_20221124_rigid_body_flat_surface.txt",
    "estaingia_landmark_20221125_rigid_body_tilted_surface.txt",
    "estaingia_landmark_20221125_rigid_body_rough_surface_1.txt",
    "estaingia_landmark_20221125_rigid_body_rough_surface_2.txt",
]

output_file_list = [ "flat_surface.tps", "tilted_surface.tps", "rough_surface_1.tps", "rough_surface_2.tps" ]

specimen_count = 100
for idx in range(len(input_file_list)):
    with open(path_list[idx]+input_file_list[idx]) as f:
        lines = f.readlines()

    specimen_text = ''
    prev_specimen_name = ''
    landmark_count = 0
    coords_list = []

    for line in lines:
        #print(line)
        specimen_name, x, y, z = line.split("\t")
        #print(x,y,z)
        if specimen_name != prev_specimen_name:
            if prev_specimen_name != '':
                specimen_count += 1
                specimen_text += "lm={}\tEstaingia_{:03d}\n".format(str(len(coords_list)),specimen_count)
                specimen_text += "\n".join(coords_list) + "\n"
                coords_list = []
                landmark_count = 0
        
        landmark_count += 1
        coords = [x,y,z]
        #print(coords)
        coords = [str(int((float(val)+10.0)*1000)/1000.0) for val in coords]
        #print(coords)
        coords_list.append("\t".join(coords))
        prev_specimen_name = specimen_name


    specimen_count += 1
    specimen_text += "lm=" + str(len(coords_list)) + "\t" + "Estaingia_" + str(specimen_count) + "\n"
    #specimen_text += "lm=" + str(len(coords_list)) + "\t" + prev_specimen_name + "\n"
    specimen_text += "\n".join(coords_list) + "\n"

    #print(specimen_text)
    with open("D:/"+output_file_list[idx], 'w') as f:
        f.write(specimen_text)