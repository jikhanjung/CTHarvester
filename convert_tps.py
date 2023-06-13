import numpy
from PIL import Image, ImageDraw, ImageChops

from os import listdir
from os.path import isfile, join

surface_type_list = ["flat", "tilted", "irregular"]


path_template = "D:/Dropbox/Blender/{}_simulation/{}/{}_landmark_{}.txt"
output_template = "D:/Dropbox/Blender/{}_simulation/{}/{}_{}.tps"

genus_name = "Phacops"

#input_file_list = [ path_template.format(surface_type, genus_name, surface_type) for surface_type in surface_type_list ]

specimen_count_list = [ 100, 200, 300 ]
for idx, surface_type in enumerate(surface_type_list):
    file_path = path_template.format(genus_name, surface_type, genus_name, surface_type)
    with open(file_path) as f:
        lines = f.readlines()

    specimen_count = specimen_count_list[idx]
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
                specimen_text += "lm={}\t{}_{:03d}\n".format(str(len(coords_list)),genus_name,specimen_count)
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
    specimen_text += "lm=" + str(len(coords_list)) + "\t" + genus_name + "_" + str(specimen_count) + "\n"
    #specimen_text += "lm=" + str(len(coords_list)) + "\t" + prev_specimen_name + "\n"
    specimen_text += "\n".join(coords_list) + "\n"

    #file_path = path_template.format(genus_name, surface_type, genus_name, surface_type)
    #print(specimen_text)
    with open(output_template.format(genus_name, surface_type, genus_name, surface_type), 'w') as f:
        f.write(specimen_text)