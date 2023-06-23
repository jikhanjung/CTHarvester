# open tps file

import numpy as np
import re
dataset_name = "Phacops_flat_20230619"
filename = "Phacops_flat_20230619.tps"


def isNumber(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def openTpsFile(filepath):
    f = open(filepath, 'r')
    tpsdata = f.read()
    f.close()

    dataset = {}

    object_count = 0
    landmark_count = 0
    data = []
    key_list = []
    threed = 0
    twod = 0
    objects = {}
    header = ''
    comment = ''
    image_count = 0
    tps_lines = [l.strip() for l in tpsdata.split('\n')]
    found = False
    for line in tps_lines:
        line = line.strip()
        if line == '':
            continue
        if line.startswith("#"):
            continue
        headerline = re.search('^(\w+)(\s*)=(\s*)(\d+)(.*)', line)
        if headerline == None:
            if header == 'lm':
                point = [ float(x) for x in re.split('\s+', line)]
                if len(point) > 2 and isNumber(point[2]):
                    threed += 1
                else:
                    twod += 1

                if len(point)>1:
                    data.append(point)
            continue
        elif headerline.group(1).lower() == "lm":
            if len(data) > 0:
                if comment != '':
                    key = comment
                else:
                    key = dataset_name + "_" + str(object_count + 1)
                objects[key] = data
                key_list.append(key)
                data = []
            header = 'lm'
            object_count += 1
            landmark_count, comment = int(headerline.group(4)), headerline.group(5).strip()
            # landmark_count_list.append( landmark_count )
            # if not found:
            #found = True
        elif headerline.group(1).lower() == "image":
            image_count += 1

    if len(data) > 0:
        if comment != '':
            key = comment
        else:
            key = dataset_name + "_" + str(object_count + 1)
        objects[key] = data
        data = []

    if object_count == 0 and landmark_count == 0:
        return None

    if threed > twod:
        dataset['dimension'] = 3
    else:
        dataset['dimension'] = 2

    dataset['object_count'] = object_count
    dataset['landmark_count'] = landmark_count
    dataset['data'] = objects
    dataset['key_list'] = key_list

    return dataset


dataset = openTpsFile(filename)
key = dataset['key_list'][0]
print(key, dataset['data'][key])
