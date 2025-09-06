#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy
#from statlib import stats
from numpy import newaxis as nA


class MdManova:
    def __init__(self):
        self.dimension = -1
        self.data = {}  # MdDatamatrix()

    def AddDataset(self, dataset):
        self.data.AddDataset(dataset)
        self.groupinfo_idx = 0
        self.group_list = {}
        i = 0
        for object in self.data.dataset.object_list:
            group_key = object.group_list[self.groupinfo_idx]
            print( group_key)
            if ( not self.group_list.has_key(group_key) ):
                self.group_list[group_key] = []
            self.group_list[group_key].append(i)
            i += 1
        return

    def Analyze(self):
        variable_index = 0
        data = {}
        data['sum'] = [0] * self.data.nVariable
        data['count'] = 0
        self.group_data = {}
        for key in self.group_list.keys():
            self.group_data[key] = {}
            within_group_sum = [0] * self.data.nVariable
            for observation_index in self.group_list[key]:
                for variable_index in range(self.data.nVariable):
                    val = self.data.matrix[variable_index, observation_index]
                    within_group_sum[variable_index] += val
                    data['sum'][variable_index] += val
            self.group_data[key]['sum'] = within_group_sum
            self.group_data[key]['count'] = len(self.group_list[key])
            self.group_data[key]['average'] = []
            for sum in within_group_sum:
                self.group_data[key]['average'].append(sum / float(self.group_data[key]['count']))
            data['count'] += self.group_data[key]['count']
            # print self.group_data[key]

        data['average'] = []
        for sum in data['sum']:
            data['average'].append(sum / float(data['count']))
        W = numpy.zeros(( self.data.nVariable, self.data.nVariable))
        # nGroups = len( self.group_list.keys() )
        B = numpy.zeros(( self.data.nVariable, self.data.nVariable ))
        x = []
        group = []
        for key in self.group_list.keys():
            for variable_index_i in range(self.data.nVariable):
                for variable_index_j in range(self.data.nVariable):
                    val_i = self.group_data[key]['average'][variable_index_i]
                    val_j = self.group_data[key]['average'][variable_index_j]
                    B[variable_index_i, variable_index_j] += self.group_data[key]['count'] * (
                    val_i - data['average'][variable_index_i] ) * ( val_j - data['average'][variable_index_j] )
            print( B)
            for observation_index in self.group_list[key]:
                x.append([])
                group.append(key)
                for variable_index_i in range(self.data.nVariable):
                    x[-1].append(self.data.matrix[variable_index_i, observation_index])
                    for variable_index_j in range(self.data.nVariable):
                        val_i = self.data.matrix[variable_index_i, observation_index]
                        val_j = self.data.matrix[variable_index_j, observation_index]
                        W[variable_index_i, variable_index_j] += (val_i - self.group_data[key]['average'][
                            variable_index_i] ) * ( val_j - self.group_data[key]['average'][variable_index_j] )
            #print W
        #print x
        #print group
        b, w = _BW(numpy.array(x), numpy.array(group))
        #print b
        #print w
        scores, loads, eigs = libpy.chemometrics.cva(numpy.array(x), numpy.array(group), None)
        #print "scores", scores
        #print "loads", loads
        #print "eigs", eigs
        '''
        # so.. I have between group sums of squares and within group sum of squares. now what?
        df1 = ( len( self.group_list.keys() ) - 1 )
        bgms = bgss / df1
        print "bgms", bgms
        df2= ( data['count'] - len( self.group_list.keys() ) )
        wgms = wgss / df2
        print "wgms", wgms
        f = bgms/wgms
        print "F:", f
        prob = stats.fprob(df1,df2,f)
        print "p val", prob
        f, prob = stats.lF_oneway( anova_data[0], anova_data[1] )
        print f, prob
        return
        '''


def _index(y, num):
    """use this to get tuple index for take"""
    idx = []
    for i in range(len(y)):
        if y[i] == num:
            idx.append(int(i))
    return tuple(idx)


def _BW(X, group):
    """Generate B and W matrices for CVA
    Ref. Krzanowski
    """
    mx = numpy.mean(X, 0)[nA, :]
    tgrp = numpy.unique(group)
    for x in range(len(tgrp)):
        idx = _index(group, tgrp[x])
        L = len(idx)
        meani = numpy.mean(numpy.take(X, idx, 0), 0)
        meani = numpy.resize(meani, (len(idx), X.shape[1]))
        A = numpy.mean(numpy.take(X, idx, 0), 0) - mx
        C = numpy.take(X, idx, 0) - meani
        if x == 1:
            Bo = L * numpy.dot(numpy.transpose(A), A)
            Wo = numpy.dot(numpy.transpose(C), C)
        elif x > 1:
            Bo = Bo + L * numpy.dot(numpy.transpose(A), A)
            Wo = Wo + numpy.dot(numpy.transpose(C), C)

    B = (1.0 / (len(tgrp) - 1)) * Bo
    W = (1.0 / (X.shape[0] - len(tgrp))) * Wo

    return B, W


class MdAnova:
    def __init__(self):
        self.dimension = -1
        self.data = {}  # MdDatamatrix()

    def AddDataset(self, dataset):
        self.data.AddDataset(dataset)
        self.groupinfo_idx = 0
        self.group_list = {}
        i = 0
        for object in self.data.dataset.object_list:
            group_key = object.group_list[self.groupinfo_idx]
            print( group_key)
            if ( not self.group_list.has_key(group_key) ):
                self.group_list[group_key] = []
            self.group_list[group_key].append(i)
            i += 1
        return

    def Analyze(self):
        variable_index = 0
        data = {}
        data['sum'] = 0
        data['count'] = 0
        self.group_data = {}
        anova_data = []
        for key in self.group_list.keys():
            anova_data.append([])
            self.group_data[key] = {}
            within_group_sum = 0
            for observation_index in self.group_list[key]:
                val = self.data.matrix[variable_index, observation_index]
                anova_data[len(anova_data) - 1].append(val)
                within_group_sum += val
                data['sum'] += val
            self.group_data[key]['sum'] = within_group_sum
            self.group_data[key]['count'] = len(self.group_list[key])
            self.group_data[key]['average'] = ( self.group_data[key]['sum'] * 1.0 ) / (
            1.0 * self.group_data[key]['count'] )
            data['count'] += self.group_data[key]['count']
            #print self.group_data[key]
        data['average'] = ( data['sum'] * 1.0 ) / ( data['count'] * 1.0 )
        bgss = 0
        wgss = 0
        for key in self.group_list.keys():
            bgss += self.group_data[key]['count'] * ( self.group_data[key]['average'] - data['average'] ) ** 2
            #print key, bgss
            for observation_index in self.group_list[key]:
                val = self.data.matrix[variable_index, observation_index]
                wgss += ( val - self.group_data[key]['average'] ) ** 2
                #print wgss
        df1 = ( len(self.group_list.keys()) - 1 )
        bgms = bgss / df1
        #print "bgms", bgms
        df2 = ( data['count'] - len(self.group_list.keys()) )
        wgms = wgss / df2
        #print "wgms", wgms
        f = bgms / wgms
        #print "F:", f
        prob = stats.fprob(df1, df2, f)
        #print "p val", prob
        f, prob = stats.lF_oneway(anova_data[0], anova_data[1])
        #print f, prob
        return


class MdCanonicalVariate:
    def __init__(self):
        self.dimension = -1
        self.nVariable = 0
        self.nObservation = 0
        # self.datamatrix = []
        return

    def SetData(self, data):
        self.data = data
        self.nObservation = len(data)
        self.nVariable = len(data[0])

    def SetCategory(self, category_list):
        self.category_list = category_list

    def Analyze(self):
        '''analyze'''
        actual_data = self.data
        # actual_data = [ [] for y in range( self.nVariable ) ]
        category_data = self.category_list
        category_set = set(category_data)
        num_category = len(category_set)

        variances = [0.0 for x in range(self.nVariable)]
        total_avg = [0.0 for x in range(self.nVariable)]
        total_sum = [0.0 for x in range(self.nVariable)]
        total_count = self.nObservation

        #print self.nObservation, self.nVariable
        #print category_data

        avg_by_category = {}
        sum_by_category = {}
        count_by_category = {}
        #print "analyze"
        for k in list(category_set):
            count_by_category[k] = 0
            sum_by_category[k] = [0.0 for x in range(self.nVariable)]
            avg_by_category[k] = [0.0 for x in range(self.nVariable)]

        #print "total count:", total_count
        #print "len category_data", len( category_data )
        for i in range(total_count):
            #print i
            k = category_data[i]
            count_by_category[k] += 1
            for j in range(self.nVariable):
                sum_by_category[k][j] += float(actual_data[i][j])
                total_sum[j] += float(actual_data[i][j])

        for k in list(category_set):
            for i in range(self.nVariable):
                avg_by_category[k][i] = sum_by_category[k][i] / count_by_category[k]
                #print k, sum_by_category[k], avg_by_category[k]

        for i in range(self.nVariable):
            total_avg[i] = total_sum[i] * 1.0 / total_count
        #print total_sum, total_avg

        ''' check zero variance variables '''
        for p in range(self.nVariable):
            for idx in range(self.nObservation):
                variances[p] += ( float(actual_data[idx][p]) - total_avg[p] ) ** 2

        covariance_matrix_size = 0
        for p in range(self.nVariable):
            if variances[p] == 0:
                pass
                #print "variance = 0 for ", p, "th variable" 
            else:
                covariance_matrix_size += 1
        #print "covariance_matrix_size", covariance_matrix_size

        covariance_matrix = [[0.0 for x in range(covariance_matrix_size)] for y in range(covariance_matrix_size)]
        p_ = 0
        for p in range(self.nVariable):
            if variances[p] == 0: continue
            q_ = 0
            for q in range(self.nVariable):
                if variances[q] == 0: continue
                for idx in range(self.nObservation):
                    diff_p = float(actual_data[idx][p]) - total_avg[p]
                    diff_q = float(actual_data[idx][q]) - total_avg[q]
                    #print p_, q_
                    covariance_matrix[p_][q_] += diff_p * diff_q / ( total_count - 1 )
                q_ += 1
            p_ += 1

        within_cov = [[0.0 for x in range(covariance_matrix_size)] for y in range(covariance_matrix_size)]
        between_cov = [[0.0 for x in range(covariance_matrix_size)] for y in range(covariance_matrix_size)]

        within_by_category = {}
        between_by_category = {}
        for key in list(category_set):
            within_by_category[key] = [0.0 for x in range(covariance_matrix_size)]
            between_by_category[key] = [0.0 for x in range(covariance_matrix_size)]

        p_ = 0
        for p in range(self.nVariable):
            if variances[p] == 0: continue
            q_ = 0
            for q in range(self.nVariable):
                if variances[q] == 0: continue
                for idx in range(self.nObservation):
                    key = category_data[idx]
                    diff_p = float(actual_data[idx][p]) - avg_by_category[key][p]
                    diff_q = float(actual_data[idx][q]) - avg_by_category[key][q]
                    within_cov[p_][q_] += diff_p * diff_q / ( total_count - len(category_set) )
                q_ += 1
            p_ += 1

        '''
        log_str = ""
        log_str += "within:\n"
        for line in within_cov:
            log_str += "\t".join( [ str( x ) for x in line ] )
            log_str += "\n"
        '''
        #print "within", numpy.matrix( within_cov )

        p_ = 0
        for p in range(self.nVariable):
            if variances[p] == 0: continue
            q_ = 0
            for q in range(self.nVariable):
                if variances[q] == 0: continue
                for key in list(category_set):
                    diff_p = avg_by_category[key][p] - total_avg[p]
                    diff_q = avg_by_category[key][q] - total_avg[q]
                    between_cov[p_][q_] += diff_p * diff_q * count_by_category[key] / len(category_set)
                q_ += 1
            p_ += 1

        #set_printoptions(threshold='nan')
        '''
        log_str += "between:\n"
        for line in between_cov:
            log_str += "\t".join( [ str( x ) for x in line ] )
            log_str += "\n"
        print "between", numpy.matrix( between_cov )
        '''

        w = numpy.matrix(within_cov)
        b = numpy.matrix(between_cov)

        wi = w.getI()
        #print "wi", wi
        x = numpy.dot(wi, b)

        '''
        log_str += "WiB:\n"
        for p in range( covariance_matrix_size ):
            for q in range( covariance_matrix_size ):
                log_str += str( x[p,q] ) 
                log_str += "\t"
            log_str += "\n"
        '''

        #print "x", x

        u, s, v = numpy.linalg.svd(x)

        '''
        log_str += "rotation:\n"
        for p in range( covariance_matrix_size ):
            for q in range( covariance_matrix_size ):
                log_str += str( u[p,q] ) 
                log_str += "\t"
            log_str += "\n"
        '''

        self.raw_eigen_values = s[:]
        s /= sum(s)
        self.eigen_value_percentages = s[:]

        rotation_matrix = numpy.zeros(( self.nVariable, self.nVariable ))

        p_ = 0
        for p in range(self.nVariable):
            q_ = 0
            for q in range(self.nVariable):
                if variances[p] == 0 or variances[q] == 0:
                    rotation_matrix[p, q] = 0.0
                else:
                    rotation_matrix[p, q] = u[p_, q_]
                if variances[q] != 0:
                    q_ += 1
            if variances[p] != 0: p_ += 1

        '''
        log_str += "actual_rotation:\n"
        for p in range( self.nVariable ):
            for q in range( self.nVariable ):
                log_str += str( rotation_matrix[p,q] ) 
                log_str += "\t"
            log_str += "\n"
        '''

        np_data = numpy.zeros(( self.nObservation, self.nVariable ))
        for p in range(self.nObservation):
            for q in range(self.nVariable):
                np_data[p, q] = float(actual_data[p][q])

        '''
        log_str += "data:\n"
        for p in range( self.nObservation ):
            for q in range( self.nVariable ):
                log_str += str( np_data[p,q] ) 
                log_str += "\t"
            log_str += "\n"
        '''
        self.rotation_matrix = rotation_matrix
        #print np_data.shape, rotation_matrix.shape
        #fh = file( "cva_log.txt", 'w' )
        #fh.write( log_str )
        #fh.close()
        self.rotated_matrix = numpy.dot(np_data, rotation_matrix)
        self.loading = rotation_matrix
        return
        #if( i == 2 ) : print object.coords


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


class MdPrincipalComponent:
    def __init__(self):
        self.dimension = -1
        self.data = MdDatamatrix()
        # self.datamatrix = []
        return

    def AddDataset(self, dataset):
        self.data.AddDataset(dataset)

    def Analyze(self):
        '''analyze'''
        # print "analyze"
        self.raw_eigen_values = []
        self.eigen_value_percentages = []

        #for d in self.datamatrix :
        #print d

        sums = []
        avrs = []
        ''' calculate the empirical mean '''
        for i in range(self.data.nVariable):
            sums.append(0)
            for j in range(self.data.nObservation):
                sums[i] += self.data.matrix[i, j]

        for sum in sums:
            avrs.append(float(sum) / float(self.data.nObservation))

        #print "sum:", sums
        #print "avgs:",avrs
        #return

        for i in range(self.data.nVariable):
            for j in range(self.data.nObservation):
                self.data.matrix[i, j] -= avrs[i]

                #print self.datamatrix

        ''' covariance matrix '''
        self.covariance_matrix = numpy.dot(self.data.matrix, numpy.transpose(self.data.matrix)) / self.data.nObservation

        #print self.covariance_matrix

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

            #print nEigenValues, "eigen values obtained,", nSignificantEigenValue, "significant."
            #print eigen_values

            #for i in range( len(s) ):
            #print math.floor( ( s[i] / sum ) * 10000 + 0.5 ) / 100

        #print "s", int( s * 100 )/100
        #print "w", w
        #print v
        for i in range(nSignificantEigenValue):
            k = v[..., i]
            #print i, k, numpy.transpose(k)
            det = numpy.dot(k, numpy.transpose(k))
            #print det
        self.rotated_matrix = numpy.dot(w, self.data.matrix)
        #print w
        #print self.datamatrix[...,2]
        #print self.rotated_matrix[...,2]
        #print self.rotated_matrix
        self.loading = w

        self.new_dataset = self.data.dataset.copy()
        self.new_dataset.object_list = []
        for i in range(self.data.nObservation):
            object = MdObject()
            object.objname = self.data.dataset.object_list[i].objname
            object.coords = self.rotated_matrix[..., i]
            object.group_list[:] = self.data.dataset.object_list[i].group_list[:]
            self.new_dataset.object_list.append(object)
            #if( i == 2 ) : print object.coords
  