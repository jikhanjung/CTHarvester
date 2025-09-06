import numpy
from PIL import Image, ImageDraw, ImageChops

from os import listdir
from os.path import isfile, join

surface_type_list = ["flat", "tilted", "irregular"]


path_template = "D:/Dropbox/Blender/{}_simulation/{}/{}_landmark_{}.txt"
output_template = "D:/Dropbox/Blender/{}_simulation/{}/{}_{}_20230619.tps"

genus_name = "Taebaeksaukia"

#input_file_list = [ path_template.format(surface_type, genus_name, surface_type) for surface_type in surface_type_list ]

specimen_count_list = [ 100, 200, 300 ]
for idx, surface_type in enumerate(surface_type_list):
    file_path = path_template.format(genus_name, surface_type, genus_name, surface_type)
    with open(file_path) as f:
        lines = f.readlines()

    specimen_count = specimen_count_list[idx]
    specimen_text = ''
    specimen_id = ''
    prev_specimen_id = ''
    landmark_count = 0
    coords_list = []

    for line in lines:
        #print(line)
        specimen_name, x, y, z = line.split("\t")
        if "." in specimen_name:
            prefix, seq = specimen_name.split(".")
            specimen_id = "{}{}-{:03d}".format(genus_name[0],surface_type[0],int(seq))
        else:
            specimen_id = "{}{}-{:03d}".format(genus_name[0],surface_type[0],int(0))
            #continue
        #print(x,y,z)
        if specimen_id != prev_specimen_id:
            if prev_specimen_id != '':
                specimen_count += 1
                specimen_text += "lm={}\t{}\n".format(str(len(coords_list)),prev_specimen_id)
                specimen_text += "\n".join(coords_list) + "\n"
                coords_list = []
                landmark_count = 0
        
        landmark_count += 1
        coords = [x,y,z]
        #print(coords)
        coords = [str(int((float(val)+10.0)*1000)/1000.0) for val in coords]
        #print(coords)
        coords_list.append("\t".join(coords))
        prev_specimen_id = specimen_id


    specimen_count += 1
    specimen_text += "lm=" + str(len(coords_list)) + "\t" + specimen_id + "\n"
    #specimen_text += "lm=" + str(len(coords_list)) + "\t" + prev_specimen_name + "\n"
    specimen_text += "\n".join(coords_list) + "\n"

    #file_path = path_template.format(genus_name, surface_type, genus_name, surface_type)
    #print(specimen_text)
    with open(output_template.format(genus_name, surface_type, genus_name, surface_type), 'w') as f:
        f.write(specimen_text)