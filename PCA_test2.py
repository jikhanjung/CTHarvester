import math
import numpy
import re
from pathlib import Path

class MdObjectCore:
    def __init__(self):
        self.id = -1
        self.objname = ""
        self.objdesc = ""
        self.scale = 1.0
        self.landmark_str = ""
        self.landmark_list = []
        self.image_list = []
        self.dataset_id = -1
        self.property_list = []
        self.centroid_size = -1

    def pack_landmark(self):
        # error check
        self.landmark_str = "\n".join([",".join([str(x) for x in lm[:lm.dim]]) for lm in self.landmark_list])

    def unpack_landmark(self):
        self.landmark_list = []
        # print "[", self.landmark_str,"]"
        lm_list = self.landmark_str.split("\n")
        for lm in lm_list:
            if lm != "":
                self.landmark_list.append(lm.split(","))


class MdDatasetCore:
    def __init__(self):
        self.id = -1
        self.dsname = ""
        self.dsdesc = ""
        self.dimension = 2
        self.wireframe = ""
        self.baseline = ""
        self.polygons = ""
        self.created_at = ""
        self.modified_at = ""
        self.object_list = []
        self.propertyname_list = []
        self.edge_list = []
        self.baseline_point_list = []
    def pack_wireframe(self, edge_list=None):
        if edge_list is None:
            edge_list = self.edge_list

        for points in edge_list:
            points.sort(key=int)
        edge_list.sort()

        new_edges = []
        for points in edge_list:
            # print points
            if len(points) != 2:
                continue
            new_edges.append("-".join([str(x) for x in points]))
        self.wireframe = ",".join(new_edges)
        return self.wireframe

    def unpack_wireframe(self, wireframe=''):
        if wireframe == '' and self.wireframe != '':
            wireframe = self.wireframe

        self.edge_list = []
        if wireframe == '':
            return []

        # print wireframe
        for edge in wireframe.split(","):
            has_edge = True
            if edge != '':
                #print edge
                verts = edge.split("-")
                int_edge = []
                for v in verts:
                    try:
                        v = int(v)
                    except:
                        has_edge = False
                        #print "Invalid landmark number [", v, "] in wireframe:", edge
                    int_edge.append(v)

                if has_edge:
                    if len(int_edge) != 2:
                        pass  #print "Invalid edge in wireframe:", edge
                    self.edge_list.append(int_edge)

        return self.edge_list

    def pack_polygons(self, polygon_list=None):
        # print polygon_list
        if polygon_list is None:
            polygon_list = self.polygon_list
        for polygon in polygon_list:
            # print polygon
            polygon.sort(key=int)
        polygon_list.sort()

        new_polygons = []
        for polygon in polygon_list:
            #print points
            new_polygons.append("-".join([str(x) for x in polygon]))
        self.polygons = ",".join(new_polygons)
        return self.polygons

    def unpack_polygons(self, polygons=''):
        if polygons == '' and self.polygons != '':
            polygons = self.polygons

        self.polygon_list = []
        if polygons == '':
            return []

        for polygon in polygons.split(","):
            if polygon != '':
                self.polygon_list.append([(int(x)) for x in polygon.split("-")])

        return self.polygon_list

    def get_edge_list(self):
        return self.edge_list

    def pack_baseline(self, baseline_point_list=None):
        if baseline_point_list is None and len(self.baseline_point_list) > 0:
            baseline_point_list = self.baseline_point_list
        # print baseline_points
        self.baseline = ",".join([str(x) for x in baseline_point_list])
        #print self.baseline
        return self.baseline

    def unpack_baseline(self, baseline=''):
        if baseline == '' and self.baseline != '':
            baseline = self.baseline

        self.baseline_point_list = []
        if self.baseline == '':
            return []

        self.baseline_point_list = [(int(x)) for x in self.baseline.split(",")]
        return self.baseline_point_list

    def get_baseline_points(self):
        return self.baseline_point_list

class MdObjectOps:
    def __init__(self,mdobject):
        self.id = mdobject.id
        self.objname = mdobject.objname
        self.objdesc = mdobject.objdesc
        self.scale = mdobject.scale
        self.landmark_str = mdobject.landmark_str
        self.landmark_list = []
        for lm in mdobject.landmark_list:
            self.landmark_list.append(lm)
        self.image_list = mdobject.image_list
        self.dataset_id = mdobject.dataset_id
        self.property_list = mdobject.property_list
        self.centroid_size = -1

    def get_centroid_coord(self):
        c = [0, 0, 0]

        if len(self.landmark_list) == 0 and self.landmark_str != "":
            self.unpack_landmark()

        if len(self.landmark_list) == 0:
            return c
        
        sum_of_x = 0
        sum_of_y = 0
        sum_of_z = 0
        lm_dim = 2
        for lm in ( self.landmark_list ):
            sum_of_x += lm[0]
            sum_of_y += lm[1]
            if len(lm) == 3:
                lm_dim = 3
                sum_of_z += lm[2]
        lm_count = len(self.landmark_list)
        c[0] = sum_of_x / lm_count
        c[1] = sum_of_y / lm_count
        if lm_dim == 3:
            c[2] = sum_of_z / lm_count
        return c

    def get_centroid_size(self, refresh=False):

        if len(self.landmark_list) == 0 and self.landmark_str != "":
            self.unpack_landmark()

        if len(self.landmark_list) == 0:
            return -1
        if ( self.centroid_size > 0 ) and ( refresh == False ):
            return self.centroid_size

        centroid = self.get_centroid_coord()
        # print "centroid:", centroid.xcoord, centroid.ycoord, centroid.zcoord
        sum_of_x_squared = 0
        sum_of_y_squared = 0
        sum_of_z_squared = 0
        sum_of_x = 0
        sum_of_y = 0
        sum_of_z = 0
        lm_count = len(self.landmark_list)
        for lm in self.landmark_list:
            sum_of_x_squared += ( lm[0] - centroid[0]) ** 2
            sum_of_y_squared += ( lm[1] - centroid[1]) ** 2
            if len(lm) == 3:
                sum_of_z_squared += ( lm[2] - centroid[2]) ** 2
            sum_of_x += lm[0] - centroid[0]
            sum_of_y += lm[1] - centroid[1]
            if len(lm) == 3:
                sum_of_z += lm[2] - centroid[2]
        centroid_size = sum_of_x_squared + sum_of_y_squared + sum_of_z_squared
        #centroid_size = sum_of_x_squared + sum_of_y_squared + sum_of_z_squared \
        #              - sum_of_x * sum_of_x / lm_count \
        #              - sum_of_y * sum_of_y / lm_count \
        #              - sum_of_z * sum_of_z / lm_count
        #print centroid_size
        centroid_size = math.sqrt(centroid_size)
        self.centroid_size = centroid_size
        #centroid_size = float( int(  * 100 ) ) / 100
        return centroid_size

    def move(self, x, y, z=0):
        for lm in self.landmark_list:
            lm[0] = lm[0] + x
            lm[1] = lm[1] + y
            if len(lm) == 3:
                lm[2] = lm[2] + z

    def move_to_center(self):
        centroid = self.get_centroid_coord()
        #print("centroid:", centroid[0], centroid[1], centroid[2])
        self.move(-1 * centroid[0], -1 * centroid[1], -1 * centroid[2])

    def rescale(self, factor):
        print("rescale:", factor, self.landmark_list[:5])
        new_landmark_list = []
        for lm in self.landmark_list:
            lm = [x * factor for x in lm]
            new_landmark_list.append(lm)
        self.landmark_list = new_landmark_list
        print("rescale:", factor, self.objname, self.landmark_list[:5])

    def rescale_to_unitsize(self):
        centroid_size = self.get_centroid_size(True)
        
        self.rescale(( 1 / centroid_size ))

    def rotate_2d(self, theta):
        self.rotate_3d(theta, 'Z')
        return

    def rotate_3d(self, theta, axis):
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        r_mx = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        if ( axis == 'Z' ):
            r_mx[0][0] = cos_theta
            r_mx[0][1] = sin_theta
            r_mx[1][0] = -1 * sin_theta
            r_mx[1][1] = cos_theta
        elif ( axis == 'Y' ):
            r_mx[0][0] = cos_theta
            r_mx[0][2] = sin_theta
            r_mx[2][0] = -1 * sin_theta
            r_mx[2][2] = cos_theta
        elif ( axis == 'X' ):
            r_mx[1][1] = cos_theta
            r_mx[1][2] = sin_theta
            r_mx[2][1] = -1 * sin_theta
            r_mx[2][2] = cos_theta
        # print "rotation matrix", r_mx

        for lm in self.landmark_list:
            coords = [0,0,0]
            for j in range(len(lm)):
                coords[j] = lm[j]
            x_rotated = coords[0] * r_mx[0][0] + coords[1] * r_mx[1][0] + coords[2] * r_mx[2][0]
            y_rotated = coords[0] * r_mx[0][1] + coords[1] * r_mx[1][1] + coords[2] * r_mx[2][1]
            z_rotated = coords[0] * r_mx[0][2] + coords[1] * r_mx[1][2] + coords[2] * r_mx[2][2]
            lm = [ x_rotated, y_rotated, z_rotated ]

    def trim_decimal(self, dec=4):
        factor = math.pow(10, dec)

        for lm in self.landmark_list:
            lm = [float(round(x * factor)) / factor for x in lm]

    def print_landmarks(self, text=''):
        print("[", text, "] [", str(self.get_centroid_size()), "]")
        # lm= self.landmarks[0]
        print(self.landmark_list[:5])
        #for lm in self.landmark_list:
        #    print(lm)
            #break
            #lm= self.landmarks[1]
            #print lm.xcoord, ", ", lm.ycoord, ", ", lm.zcoord

    def sliding_baseline_registration(self, baseline):
        csize = self.get_centroid_size()
        self.bookstein_registration(baseline, csize)

    def bookstein_registration(self, baseline, rescale=-1):
        # c = self.get_centroid_coord()
        #print "centroid:", c.xcoord, ", ", c.ycoord, ", ", c.zcoord
        point1 = point2 = point3 = -1
        if len(baseline) == 3:
            point1 = baseline[0]
            point2 = baseline[1]
            point3 = baseline[2]
        elif len(baseline) == 2:
            point1 = baseline[0]
            point2 = baseline[1]
            point3 = None
        point1 = point1 - 1
        point2 = point2 - 1
        if ( point3 != None ):
            point3 = point3 - 1

        #self.print_landmarks("before any processing");

        center = [0, 0, 0]
        center[0] = ( self.landmark_list[point1][0] + self.landmark_list[point2][0] ) / 2
        center[1] = ( self.landmark_list[point1][1] + self.landmark_list[point2][1] ) / 2
        center[2] = ( self.landmark_list[point1][2] + self.landmark_list[point2][2] ) / 2
        self.move(-1 * center[0], -1 * center[1], -1 * center[2])

        #self.print_landmarks("translation");
        #self.scale_to_univsize()
        xdiff = self.landmark_list[point1][0] - self.landmark_list[point2][0]
        ydiff = self.landmark_list[point1][1] - self.landmark_list[point2][1]
        zdiff = self.landmark_list[point1][2] - self.landmark_list[point2][2]
        #print "x, y, z diff: ", xdiff, ",", ydiff, ",", zdiff

        size = math.sqrt(xdiff * xdiff + ydiff * ydiff + zdiff * zdiff)
        #print "size: ", size
        #print "rescale: ", rescale
        if ( rescale < 0 ):
            self.rescale(( 1 / size ))
        elif ( rescale > 0 ):
            self.rescale(( 1 / rescale ))

        #self.print_landmarks("rescaling");

        if ( point3 != None ):
            xdiff = self.landmark_list[point1][0] - self.landmark_list[point2][0]
            ydiff = self.landmark_list[point1][1] - self.landmark_list[point2][1]
            zdiff = self.landmark_list[point1][2] - self.landmark_list[point2][2]
            cos_val = xdiff / math.sqrt(xdiff * xdiff + zdiff * zdiff)
            #print "x, y, z diff: ", xdiff, ",", ydiff, ",", zdiff
            #print "cos val: ", cos_val
            theta = math.acos(cos_val)
            #print "theta: ", theta, ", ", theta * 180/math.pi
            if ( zdiff < 0 ):
                theta = theta * -1
            self.rotate_3d(-1 * theta, 'Y')

        #self.print_landmarks("rotate along xz plane");

        xdiff = self.landmark_list[point1][0] - self.landmark_list[point2][0]
        ydiff = self.landmark_list[point1][1] - self.landmark_list[point2][1]
        zdiff = self.landmark_list[point1][2] - self.landmark_list[point2][2]

        size = math.sqrt(xdiff * xdiff + ydiff * ydiff)
        cos_val = xdiff / size
        #print "x, y, z diff: ", xdiff, ",", ydiff, ",", zdiff
        #print "cos val: ", cos_val
        theta = math.acos(cos_val)
        #print "theta: ", theta, ", ", theta * 180/math.pi
        if ( ydiff < 0 ):
            theta = theta * -1
        self.rotate_2d(-1 * theta)

        if ( point3 != None ):
            xdiff = self.landmark_list[point3][0]
            ydiff = self.landmark_list[point3][1]
            zdiff = self.landmark_list[point3][2]
            size = math.sqrt(ydiff ** 2 + zdiff ** 2)
            cos_val = ydiff / size
            theta = math.acos(cos_val)
            if ( zdiff < 0 ):
                theta = theta * -1
            self.rotate_3d(-1 * theta, 'X')

class MdDatasetOps:
    def __init__(self,dataset):
        self.id = dataset.id
        self.dsname = dataset.dsname
        self.dsdesc = dataset.dsdesc
        self.dimension = dataset.dimension
        self.wireframe = dataset.wireframe
        self.baseline = dataset.baseline
        self.polygons = dataset.polygons
        self.object_list = []
        for mo in dataset.object_list:
            #self.object_list.append(mo.copy())
            self.object_list.append(MdObjectOps(mo))
        if dataset.wireframe != '':
            dataset.unpack_wireframe()
        self.edge_list = dataset.edge_list[:]
        self.propertyname_list = dataset.propertyname_list[:]
        if dataset.polygons != '':
            dataset.unpack_polygons()
        if dataset.baseline != '':
            dataset.unpack_baseline()
        self.baseline_point_list = dataset.baseline_point_list[:]
        #print self
    def set_reference_shape(self, shape):
        self.reference_shape = shape

    def rotate_gls_to_reference_shape(self, object_index):
        num_obj = len(self.object_list)
        if ( num_obj == 0 or num_obj - 1 < object_index  ):
            return

        mo = self.object_list[object_index]
        nlandmarks = len(mo.landmark_list)
        target_shape = numpy.zeros((nlandmarks, 3))
        reference_shape = numpy.zeros((nlandmarks, 3))

        i = 0
        for lm in ( mo.landmark_list ):
            for j in range(len(lm)):
                target_shape[i,j] = lm[j]
            i += 1

        i = 0
        for lm in self.reference_shape.landmark_list:
            for j in range(len(lm)):
                reference_shape[i,j] = lm[j]
            i += 1

        rotation_matrix = self.rotation_matrix(reference_shape, target_shape)
        #print rotation_matrix
        #target_transposed = numpy.transpose( target_shape )
        #print target_transposed
        #print rotation_matrix.shape
        #print target_transposed.shape
        rotated_shape = numpy.transpose(numpy.dot(rotation_matrix, numpy.transpose(target_shape)))

        #print rotated_shape

        i = 0
        new_landmark_list = []
        for i in range( len(mo.landmark_list) ):
            lm = [0,0,0]
            for j in range(3):
                lm[j] = rotated_shape[i,j]
            new_landmark_list.append(lm)
            #lm = [ rotated_shape[i, 0], rotated_shape[i, 1], rotated_shape[i, 2] ]
            #i += 1
        mo.landmark_list = new_landmark_list

    def rotation_matrix(self, ref, target):
        #assert( ref[0] == 3 )
        #assert( ref.shape == target.shape )

        correlation_matrix = numpy.dot(numpy.transpose(ref), target)
        v, s, w = numpy.linalg.svd(correlation_matrix)
        is_reflection = ( numpy.linalg.det(v) * numpy.linalg.det(w) ) < 0.0
        if is_reflection:
            v[-1, :] = -v[-1, :]
        rot_mx = numpy.dot(v, w)
        print("rotation_matrix:",rot_mx)
        return rot_mx

    def get_average_shape(self):

        object_count = len(self.object_list)

        average_shape = MdObjectOps(MdObjectCore())
        average_shape.landmark_list = []

        sum_x = []
        sum_y = []
        sum_z = []

        for mo in self.object_list:
            i = 0
            for lm in mo.landmark_list:
                if len(sum_x) <= i:
                    sum_x.append(0)
                    sum_y.append(0)
                    sum_z.append(0)
                sum_x[i] += lm[0]
                sum_y[i] += lm[1]
                if len( lm ) == 3:
                    sum_z[i] += lm[2]
                i += 1
        for i in range(len(sum_x)):
            lm = [ float(sum_x[i]) / object_count, float(sum_y[i]) / object_count, float(sum_z[i]) / object_count ]
            average_shape.landmark_list.append(lm)
        if self.id:
            average_shape.dataset_id = self.id
        return average_shape

    def check_object_list(self):
        min_number_of_landmarks = 999
        max_number_of_landmarks = 0
        sum_val = 0
        for mo in self.object_list:
            number_of_landmarks = len(mo.landmark_list)
            # print number_of_landmarks
            sum_val += number_of_landmarks
            min_number_of_landmarks = min(min_number_of_landmarks, number_of_landmarks)
            max_number_of_landmarks = max(max_number_of_landmarks, number_of_landmarks)
        #average_number_of_landmarks = float( sum_val ) / len( self.objects )
        #print min_number_of_landmarks, max_number_of_landmarks
        if sum_val > 0 and min_number_of_landmarks != max_number_of_landmarks:
            print("Inconsistent number of landmarks")
            return False
        return True

    def procrustes_superimposition(self):
        print("begin_procrustes")
        if not self.check_object_list():
            print("check_object_list failed")
            return False

        for mo in self.object_list:
            #mo.set_landmarks()
            mo.move_to_center()
            mo.rescale_to_unitsize()
        print("move_to_center and rescale_to_unitsize done")
        print("object",self.object_list[0].landmark_list[:5])

        average_shape = None
        previous_average_shape = None
        i = 0
        while ( True ):
            i += 1
            print("progressing...", i)
            previous_average_shape = average_shape
            average_shape = self.get_average_shape()

            average_shape.print_landmarks("average_shape")

            if ( self.is_same_shape(previous_average_shape, average_shape) and previous_average_shape != None ):
                break
            self.set_reference_shape(average_shape)
            for j in range(len(self.object_list)):
                self.rotate_gls_to_reference_shape(j)
                #self.objects[0].print_landmarks('aa')
                #self.objects[1].print_landmarks('bb')
                #average_shape.print_landmarks('cc')
        print("end procrustes")

    def is_same_shape(self, shape1, shape2):
        if ( shape1 == None or shape2 == None ):
            return False
        sum_coord = 0
        for i in range(len(shape1.landmark_list)):
            sum_coord += ( shape1.landmark_list[i][0] - shape2.landmark_list[i][0]) ** 2
            sum_coord += ( shape1.landmark_list[i][1] - shape2.landmark_list[i][1]) ** 2
            sum_coord += ( shape1.landmark_list[i][2] - shape2.landmark_list[i][2]) ** 2
        #shape1.print_landmarks("shape1")
        #shape2.print_landmarks("shape2")
        sum_coord = math.sqrt(sum_coord)
        #print "diff: ", sum
        if sum_coord < 10 ** -10:
            return True
        return False

    def resistant_fit_superimposition(self):
        if len(self.object_list) == 0:
            print( "No objects to transform!")
            raise 

        for mo in self.object_list:
            mo.move_to_center()
        average_shape = None
        previous_average_shape = None

        i = 0
        while True:
            i += 1
            #print "iteration: ", i
            previous_average_shape = average_shape
            average_shape = self.get_average_shape()
            average_shape.rescale_to_unitsize()
            if self.is_same_shape(previous_average_shape, average_shape) and previous_average_shape is not None:
                break
            self.set_reference_shape(average_shape)
            for j in range(len(self.object_list)):
                self.rotate_resistant_fit_to_reference_shape(j)

    def rotate_vector_2d(self, theta, vec):
        return self.rotate_vector_3d(theta, vec, 'Z')

    def rotate_vector_3d(self, theta, vec, axis):
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        r_mx = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        if ( axis == 'Z' ):
            r_mx[0][0] = cos_theta
            r_mx[0][1] = sin_theta
            r_mx[1][0] = -1 * sin_theta
            r_mx[1][1] = cos_theta
        elif ( axis == 'Y' ):
            r_mx[0][0] = cos_theta
            r_mx[0][2] = sin_theta
            r_mx[2][0] = -1 * sin_theta
            r_mx[2][2] = cos_theta
        elif ( axis == 'X' ):
            r_mx[1][1] = cos_theta
            r_mx[1][2] = sin_theta
            r_mx[2][1] = -1 * sin_theta
            r_mx[2][2] = cos_theta

        x_rotated = vec[0] * r_mx[0][0] + vec[1] * r_mx[1][0] + vec[2] * r_mx[2][0]
        y_rotated = vec[0] * r_mx[0][1] + vec[1] * r_mx[1][1] + vec[2] * r_mx[2][1]
        z_rotated = vec[0] * r_mx[0][2] + vec[1] * r_mx[1][2] + vec[2] * r_mx[2][2]
        vec[0] = x_rotated
        vec[1] = y_rotated
        vec[2] = z_rotated
        return vec

    def rotate_resistant_fit_to_reference_shape(self, object_index):
        num_obj = len(self.object_list)
        if num_obj == 0 or num_obj - 1 < object_index:
            return

        target_shape = self.object_list[object_index]
        nlandmarks = len(target_shape.landmark_list)
        #target_shape = numpy.zeros((nlandmarks,3))
        reference_shape = self.reference_shape

        #rotation_matrix = self.rotation_matrix( reference_shape, target_shape )

        #rotated_shape = numpy.transpose( numpy.dot( rotation_matrix, numpy.transpose( target_shape ) ) )

        # obtain scale factor using repeated median
        landmark_count = len(reference_shape.landmark_list)
        inner_tau_array = []
        outer_tau_array = []
        median_index = -1
        for i in range(landmark_count - 1):
            for j in range(i + 1, landmark_count):
                target_distance = math.sqrt(
                    ( target_shape.landmark_list[i][0] - target_shape.landmark_list[j][0] ) ** 2 + \
                    ( target_shape.landmark_list[i][1] - target_shape.landmark_list[j][1] ) ** 2 + \
                    ( target_shape.landmark_list[i][2] - target_shape.landmark_list[j][2] ) ** 2)
                reference_distance = math.sqrt(
                    ( reference_shape.landmark_list[i][0] - reference_shape.landmark_list[j][0] ) ** 2 + \
                    ( reference_shape.landmark_list[i][1] - reference_shape.landmark_list[j][1] ) ** 2 + \
                    ( reference_shape.landmark_list[i][2] - reference_shape.landmark_list[j][2] ) ** 2)
                tau = reference_distance / target_distance
                inner_tau_array.append(tau)
                median_index = self.get_median_index(inner_tau_array)
            #       print median_index
            #print "tau: ", inner_tau_array
            outer_tau_array.append(inner_tau_array[median_index])
            inner_tau_array = []
        median_index = self.get_median_index(outer_tau_array)
        #print "tau: ", outer_tau_array
        tau_final = outer_tau_array[median_index]

        # rescale to scale factor
        #print "index:", object_index
        #print "scale factor:", tau_final
        #target_shape.print_landmarks("before rescale")
        target_shape.rescale(tau_final)
        #target_shape.print_landmarks("after rescale")
        #exit

        # obtain rotation angle using repeated median
        inner_theta_array = []
        outer_theta_array = []
        inner_vector_array = []
        outer_vector_array = []
        for i in range(landmark_count - 1):
            for j in range(i + 1, landmark_count):
                # get vector
                target_vector = numpy.array([target_shape.landmark_list[i][0] - target_shape.landmark_list[j][0],
                                             target_shape.landmark_list[i][1] - target_shape.landmark_list[j][1],
                                             target_shape.landmark_list[i][2] - target_shape.landmark_list[j][2]])
                reference_vector = numpy.array([reference_shape.landmark_list[i][0] - reference_shape.landmark_list[j][0],
                                             reference_shape.landmark_list[i][1] - reference_shape.landmark_list[j][1],
                                             reference_shape.landmark_list[i][2] - reference_shape.landmark_list[j][2]])
                #       cos_val = ( target_vector[0] * reference_vector[0] + \
                #                   target_vector[1] * reference_vector[1] + \
                #                   target_vector[2] * reference_vector[2] ) \
                #                  / \
                #                  ( math.sqrt( target_vector[0] ** 2 + target_vector[1]**2 + target_vector[2]**2 ) * \
                #                    math.sqrt( reference_vector[0] ** 2 + reference_vector[1]**2 + reference_vector[2]**2 ) )
                #        if( cos_val > 1.0 ):
                #          print "cos_val 1: ", cos_val
                #          print target_vector
                #          print reference_vector
                #          print math.acos( cos_val )
                #          cos_val = 1.0
                cos_val = numpy.vdot(target_vector, reference_vector) / numpy.linalg.norm(
                    target_vector) * numpy.linalg.norm(reference_vector)
                #        if( cos_val > 1.0 ):
                #          print "cos_val 2: ", cos_val
                #          cos_val = 1.0
                #        try:
                #          if( cos_val == 1.0 ):
                #            theta = 0.0
                #          else:
                theta = math.acos(cos_val)
                #        except ValueError:
                #          print "acos value error"
                #          theta = 0.0
                inner_theta_array.append(theta)
                inner_vector_array.append(numpy.array([target_vector, reference_vector]))
                #print inner_vector_array[-1]
            median_index = self.get_median_index(inner_theta_array)
            #      print inner_vector_array[median_index]
            outer_theta_array.append(inner_theta_array[median_index])
            outer_vector_array.append(inner_vector_array[median_index])
            inner_theta_array = []
            inner_vector_array = []
        median_index = self.get_median_index(outer_theta_array)
        # theta_final = outer_theta_array[median_index]
        vector_final = outer_vector_array[median_index]
        #    print vector_final

        target_shape = numpy.zeros((1, 3))
        reference_shape = numpy.zeros((1, 3))
        #print vector_final
        target_shape[0] = vector_final[0]
        reference_shape[0] = vector_final[1]

        rotation_matrix = self.get_vector_rotation_matrix(vector_final[1], vector_final[0])

        #rotation_matrix = self.rotation_matrix( reference_shape, target_shape )
        #print reference_shape
        #print target_shape
        #rotated_shape = numpy.transpose( numpy.dot( rotation_matrix, numpy.transpose( target_shape ) ) )
        #print rotated_shape
        #exit
        target_shape = numpy.zeros((nlandmarks, 3))
        i = 0
        for lm in ( self.object_list[object_index].landmark_list ):
            target_shape[i] = lm
            i += 1

        reference_shape = numpy.zeros((nlandmarks, 3))
        i = 0
        for lm in ( self.reference_shape.landmark_list ):
            reference_shape[i] = lm
            i += 1

        rotated_shape = numpy.transpose(numpy.dot(rotation_matrix, numpy.transpose(target_shape)))

        #print "reference: ", reference_shape[0]
        #print "target: ", target_shape[0], numpy.linalg.norm(target_shape[0])
        #print "rotation: ", rotation_matrix
        #print "rotated: ", rotated_shape[0], numpy.linalg.norm(rotated_shape[0])
        #print "determinant: ", numpy.linalg.det( rotation_matrix )

        i = 0
        for lm in ( self.object_list[object_index].landmark_list ):
            lm = [ rotated_shape[i, 0], rotated_shape[i, 1], rotated_shape[i, 2] ]
            i += 1
        if ( object_index == 0 ):
            pass
            #self.reference_shape.print_landmarks("ref:")
            #self.objects[object_index].print_landmarks(str(object_index))
            #print "reference: ", reference_shape[0]
            #print "target: ", target_shape[0], numpy.linalg.norm(target_shape[0])
            #print "rotation: ", rotation_matrix
            #print "rotated: ", rotated_shape[0], numpy.linalg.norm(rotated_shape[0])
            #print "determinant: ", numpy.linalg.det( rotation_matrix )

    def get_vector_rotation_matrix(self, ref, target):
        ( x, y, z ) = ( 0, 1, 2 )
        #print ref
        #print target
        #print "0 ref", ref
        #print "0 target", target

        ref_1 = ref
        ref_1[z] = 0
        cos_val = ref[x] / math.sqrt(ref[x] ** 2 + ref[z] ** 2)
        theta1 = math.acos(cos_val)
        if ( ref[z] < 0 ):
            theta1 = theta1 * -1
        ref = self.rotate_vector_3d(-1 * theta1, ref, 'Y')
        target = self.rotate_vector_3d(-1 * theta1, target, 'Y')

        #print "1 ref", ref
        #print "1 target", target

        cos_val = ref[x] / math.sqrt(ref[x] ** 2 + ref[y] ** 2)
        theta2 = math.acos(cos_val)
        if ( ref[y] < 0 ):
            theta2 = theta2 * -1
        ref = self.rotate_vector_2d(-1 * theta2, ref)
        target = self.rotate_vector_2d(-1 * theta2, target)

        #print "2 ref", ref
        #print "2 target", target

        cos_val = target[x] / math.sqrt(( target[x] ** 2 + target[z] ** 2 ))
        theta1 = math.acos(cos_val)
        if ( target[z] < 0 ):
            theta1 = theta1 * -1
        target = self.rotate_vector_3d(-1 * theta1, target, 'Y')

        #print "3 ref", ref
        #print "3 target", target

        cos_val = target[x] / math.sqrt(( target[x] ** 2 + target[y] ** 2 ))
        theta2 = math.acos(cos_val)
        if ( target[y] < 0 ):
            theta2 = theta2 * -1
        target = self.rotate_vector_2d(-1 * theta2, target)

        #print "4 ref", ref
        #print "4 target", target

        r_mx1 = numpy.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        r_mx2 = numpy.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        #print "shape:", r_mx1.shape
        #print "r_mx1", r_mx1
        #print "theta1", theta1
        #print "cos theta1", math.cos( theta1 )
        #print "sin theta1", math.sin( theta1 )
        #print "r_mx2", r_mx2
        #print "theta2", theta2
        r_mx1[0][0] = math.cos(theta1)
        r_mx1[0][2] = math.sin(theta1)
        r_mx1[2][0] = math.sin(theta1) * -1
        r_mx1[2][2] = math.cos(theta1)

        #print "r_mx1", r_mx1
        #print "theta1", theta1
        #print "r_mx2", r_mx2
        #print "theta2", theta2

        r_mx2[0][0] = math.cos(theta2)
        r_mx2[0][1] = math.sin(theta2)
        r_mx2[1][0] = math.sin(theta2) * -1
        r_mx2[1][1] = math.cos(theta2)

        #print "r_mx1", r_mx1
        #print "theta1", theta1
        #print "r_mx2", r_mx2
        #print "theta2", theta2

        rotation_matrix = numpy.dot(r_mx1, r_mx2)
        return rotation_matrix


    def get_median_index(self, arr):
        arr.sort()
        len_arr = len(arr)
        if ( len_arr == 0 ):
            return -1
        half_len = int(math.floor(len_arr / 2.0))
        return half_len

class MdPrincipalComponent2:
    def __init__(self):
        # self.datamatrix = []
        return

    def SetData(self, data):
        self.data = data
        self.nObservation = len(data)
        self.nVariable = len(data[0])

    def Analyze(self):
        '''analyze'''
        # print "analyze"
        self.raw_eigen_values = []
        self.eigen_value_percentages = []

        #for d in self.datamatrix :
        #print d

        sums = [0.0 for x in range(self.nVariable)]
        avrs = [0.0 for x in range(self.nVariable)]
        ''' calculate the empirical mean '''
        for i in range(self.nObservation):
            for j in range(self.nVariable):
                sums[j] += float(self.data[i][j])

        for j in range(self.nVariable):
            avrs[j] = float(sums[j]) / float(self.nObservation)

        #print "sum:", sums
        #print "avgs:",avrs
        #return

        for i in range(self.nObservation):
            for j in range(self.nVariable):
                self.data[i][j] -= avrs[j]

                #print self.datamatrix

        log_str = ""

        ''' covariance matrix '''
        np_data = numpy.matrix(self.data)
        self.covariance_matrix = numpy.dot(numpy.transpose(np_data), np_data) / self.nObservation

        #print "covariance_matrix", self.covariance_matrix

        ''' zz '''
        v, s, w = numpy.linalg.svd(self.covariance_matrix)
        #print "v", v
        #print "w", w

        #print "s[",

        self.raw_eigen_values = s
        sum = 0
        for ss in s:
            sum += ss
        for ss in s:
            self.eigen_value_percentages.append(ss / sum)
        cumul = 0
        eigen_values = []
        i = 0
        nSignificantEigenValue = -1
        nEigenValues = -1
        for ss in s:
            cumul += ss
            eigen_values.append(ss)
            #print sum, cumul, ss
            if cumul / sum > 0.95 and nSignificantEigenValue == -1:
                nSignificantEigenValue = i + 1
            if (ss / sum ) < 0.00001 and nEigenValues == -1:
                nEigenValues = i + 1
            i += 1

        self.rotated_matrix = numpy.dot(np_data, v)
        self.rotation_matrix = v
        #print w
        #print self.datamatrix[...,2]
        #print self.rotated_matrix[...,2]
        #print self.rotated_matrix
        self.loading = v
        return

def PerformPCA(dataset):

    pca = MdPrincipalComponent2()
    datamatrix = []
    for obj in dataset.object_list:
        datum = []
        for lm in obj.landmark_list:
            datum.extend( lm )
        datamatrix.append(datum)

    pca.SetData(datamatrix)
    pca.Analyze()
    loading_listctrl_initialized = False
    coordinates_listctrl_initialized = False

    number_of_axes = min(pca.nObservation, pca.nVariable)

    pca_done = True

    return pca




# open tps file
#filename = "Phacops_flat_20230619.tps"
filename = "Estaingia_rough_1.tps"


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


dataset_name = Path(filename).stem
dataset = openTpsFile(filename)
key = dataset['key_list'][0]
#print(key, dataset['data'][key])

object_list = []
for key in dataset['key_list']:
    #print(key, dataset['data'][key])
    obj = MdObjectCore()
    obj.objname = key
    obj.landmark_list = dataset['data'][key]
    #obj.dimension = dataset['dimension']
    object_list.append(obj)

ds_core = MdDatasetCore()
ds_core.dsname = dataset_name
ds_core.object_list = object_list

ds_ops = MdDatasetOps(ds_core)

obj1 = ds_ops.object_list[0]


for obj in ds_ops.object_list[:2]:
    print(obj.objname, obj.landmark_list[:5])
'''
    print("centroid coords:", obj.get_centroid_coord())
    print("centroid size:", obj.get_centroid_size())

for obj in ds_ops.object_list:
    #mo.set_landmarks()
    obj.move_to_center()
    #obj.rescale_to_unitsize()

for obj in ds_ops.object_list[:2]:
    print(obj.objname, obj.landmark_list[:5])
    print("centroid size:", obj.get_centroid_size(True))

for obj in ds_ops.object_list:
    #obj.move_to_center()
    obj.rescale_to_unitsize()

for obj in ds_ops.object_list[:2]:
    print(obj.objname, obj.landmark_list[:5])
    print("centroid size:", obj.get_centroid_size(True))
'''


ds_ops.procrustes_superimposition()
for obj in ds_ops.object_list[:2]:
    print(obj.objname, obj.landmark_list[:5])

pca_result = PerformPCA(ds_ops)
#print(pca_result.loading)
#print(pca_result.data)
print(pca_result.rotated_matrix[:,0:2].tolist())
print(pca_result.raw_eigen_values)
print(pca_result.eigen_value_percentages)
