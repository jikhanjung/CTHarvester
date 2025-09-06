'''
from mdstatistics import MdPrincipalComponent2

pca = MdPrincipalComponent2()
datamatrix = []
for obj in self.dataset.object_list:
    datum = []
    for lm in obj.landmark_list:
        datum.extend( lm.coords )
    datamatrix.append(datum)

pca.SetData(datamatrix)
pca.Analyze()
loading_listctrl_initialized = False
coordinates_listctrl_initialized = False

number_of_axes = min(pca.nObservation, pca.nVariable)
'''

# load coordinates file tab separated with header, first column is dataset name second column specimen name, last column is centroid size
# the rest of the columns are coordinates
# the first row is the header
# the first column is the dataset name
# the second column is the specimen name
# the last column is the centroid size
# the rest of the columns are coordinates

# how to open a text file
# https://stackoverflow.com/questions/3277503/how-do-i-read-a-file-line-by-line-into-a-list

import numpy as np

data_matrix = []

filename = "Tf-20230619.x1y1"
with open(filename) as f:
    lines = f.readlines()
    #first line is header
    for i, line in enumerate(lines):
        #if i<10: print(i,line)
        if i == 0:
            continue
        #print(line)
        line = line.strip()
        if line == '':
            continue
        if line.startswith("#"):
            continue
        #print(line)
        tokens = line.split("\t")
        #print(tokens)
        data_matrix.append([float(x) for x in tokens[2:-1]])
        #print(data_matrix)
#exit()
loading_matrix = []
filename = "loading.txt"
# first column is the axis number
with open(filename) as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip()
        if line == '':
            continue
        if line.startswith("#"):
            continue
        tokens = line.split("\t")
        #print(tokens)
        loading_matrix.append([float(x) for x in tokens[1:]])

print(data_matrix[:5])
print(loading_matrix[:5])
#print dimension
print(len(data_matrix))
print(len(data_matrix[0]))
print(len(loading_matrix))
print(len(loading_matrix[0]))

np_data = np.matrix(data_matrix)
np_loading = np.matrix(loading_matrix)

rotated_matrix = np.dot(np_data, np_loading)

print(rotated_matrix[:5])

# save rotated matrix
with open("rotated_matrix.txt", "w") as f:
    for row in rotated_matrix:
        row = [str(x) for x in row.tolist()[0]]
        f.write("\t".join(row) + "\n")

# save rotated matrix

