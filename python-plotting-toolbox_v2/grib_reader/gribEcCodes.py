
# -*- coding: utf-8 -*-

"""
Created on Tue Jan 26 16:35:02 2016

@author: a001592
"""

#from regrot import reg2rot, rot2reg
import eccodes as g
import numpy as np
#from rotuv import rotuv
import os
import time
# helppath = '/media/sf_VBox_common_share/Projekt/Utveckling_Malmo/common'
# sys.path.append(os.path.join(helppath, 'indata', 'grib'))
# sys.path.append(os.path.join(helppath, 'general'))
# import reglambert

"""
Write Grib file
-------------------------------------------------------------------------------
"""     
def write_grib(INPUT,OUTPUT,fields,missingValue=9999):

    fin = open(INPUT)
    fout = open(OUTPUT,'w')
    
    gid = g.codes_grib_new_from_file(fin)
        
    for f in fields.keys():

        field = fields[f]

        fieldvalues = field['values'].flatten()
        fieldvalues = np.where(np.isnan(fieldvalues), missingValue, fieldvalues)

        clone_id = g.codes_clone(gid)

        try:
            for key in field['gribkeys']:
                g.codes_set(clone_id,key,field['gribkeys'][key])
        except KeyError:
            print('No change in metadata')

        g.codes_set_values(clone_id,fieldvalues)

        g.codes_write(clone_id,fout)

    g.codes_release(gid)

    fin.close()
    fout.close()
    #print('GRIB WRITTEN: %s' % OUTPUT)

"""
*******************************************************************************
Nearest neighbour - SID version
Rotated latlon-grid
""" 
def nn(regPoint_lat, 
       regPoint_lon, 
       Ni, 
       Nj,
       latitudeOfFirstGridPointInDegrees,
       latitudeOfLastGridPointInDegrees,
       longitudeOfFirstGridPointInDegrees,
       longitudeOfLastGridPointInDegrees,
       latitudeOfSouthernPoleInDegrees,
       longitudeOfSouthernPoleInDegrees):
    
    # rotate point from regular grid to rotated grid       
    rotPoint_lon, rotPoint_lat = reg2rot(regPoint_lon,regPoint_lat, pxcen = longitudeOfSouthernPoleInDegrees, pycen = latitudeOfSouthernPoleInDegrees)
    
    # make sure point not outside grid
    outSideGrid = False
    if rotPoint_lon > max([longitudeOfFirstGridPointInDegrees,longitudeOfLastGridPointInDegrees]):
        outSideGrid = True
    elif rotPoint_lon < min([longitudeOfFirstGridPointInDegrees,longitudeOfLastGridPointInDegrees]):
        outSideGrid = True
    elif rotPoint_lat > max([latitudeOfFirstGridPointInDegrees,latitudeOfLastGridPointInDegrees]):
        outSideGrid = True
    elif rotPoint_lat < min([latitudeOfFirstGridPointInDegrees,latitudeOfLastGridPointInDegrees]):
        outSideGrid = True
    if outSideGrid:
        print('Point is outside grid lat = '+ str(regPoint_lat) + ' lon = ' + str(regPoint_lon))
        return None
    
    # calculate nearest gribpoint       
    latResolution = abs ((latitudeOfLastGridPointInDegrees - latitudeOfFirstGridPointInDegrees) / (Nj - 1))
    lonResolution = abs ((longitudeOfLastGridPointInDegrees - longitudeOfFirstGridPointInDegrees) / (Ni - 1))
    nearest_lon = round(((rotPoint_lon - longitudeOfFirstGridPointInDegrees) / lonResolution),0)
    nearest_lat = round(((rotPoint_lat - latitudeOfFirstGridPointInDegrees) / latResolution),0)
    index  = nearest_lon+(Ni*nearest_lat)
    
    return int(index)  

"""
*******************************************************************************
Nearest neighbour - SID version
Regular latlon-grid
"""      
def nn_regll(regPoint_lat, 
       regPoint_lon, 
       Ni, 
       Nj,
       latitudeOfFirstGridPointInDegrees,
       latitudeOfLastGridPointInDegrees,
       longitudeOfFirstGridPointInDegrees,
       longitudeOfLastGridPointInDegrees):
           
    # make sure point not outside grid
    outSideGrid = False
    if regPoint_lon > max([longitudeOfFirstGridPointInDegrees,longitudeOfLastGridPointInDegrees]):
        outSideGrid = True
    elif regPoint_lon < min([longitudeOfFirstGridPointInDegrees,longitudeOfLastGridPointInDegrees]):
        outSideGrid = True
    elif regPoint_lat > max([latitudeOfFirstGridPointInDegrees,latitudeOfLastGridPointInDegrees]):
        outSideGrid = True
    elif regPoint_lat < min([latitudeOfFirstGridPointInDegrees,latitudeOfLastGridPointInDegrees]):
        outSideGrid = True
    if outSideGrid:
        print('Point is outside grid lat = '+ str(regPoint_lat) + ' lon = ' + str(regPoint_lon))
        return None
    
    # calculate nearest gribpoint       
    latResolution = abs ((latitudeOfLastGridPointInDegrees - latitudeOfFirstGridPointInDegrees) / (Nj - 1))
    lonResolution = abs ((longitudeOfLastGridPointInDegrees - longitudeOfFirstGridPointInDegrees) / (Ni - 1))
    nearest_lon = round(((regPoint_lon - longitudeOfFirstGridPointInDegrees) / lonResolution),0)
    nearest_lat = round(((regPoint_lat - latitudeOfFirstGridPointInDegrees) / latResolution),0)
    index  = nearest_lon+(Ni*nearest_lat)
    
    return int(index) 
    
def solveLevTypeProblem(lev):
    if lev == 'hl':
        return 'sfc'
    elif lev == 'hmsl':
        return '103'
    else:
        return lev
    
"""
*******************************************************************************
Get data from gribfile
"""   
def getGribWithKeys(fn,wanted=[],names = [], index_keys =["indicatorOfParameter","indicatorOfTypeOfLevel","level"], debug=False, useStepRange=True, indexFile=True):
    
    start = time.time()
    
    data = {}
    gridType = None
    
    first = True
        
    data = {}

    #print('Reading GRIB: %s' % fn)
    
    try:
        if indexFile:
            index_file = '%s.idx' % os.path.split(fn)[-1]
        else:
            index_file = ""
        
        if os.path.exists(index_file):
            iid = g.codes_index_read(index_file)
        else:
            iid = g.codes_index_new_from_file(fn,index_keys)
            if indexFile:
                g.codes_index_write(iid, index_file)
                print('Written index to %s' % index_file)
            
        index_keys = np.array(index_keys)
      
        index_vals = []
     
        for key in index_keys:
     
            key_vals = g.codes_index_get(iid,key)

            if key == 'indicatorOfTypeOfLevel':
                levtypes = list(key_vals)
            # if debug:
            #     print('')
            #     print('DEBUG')
            #     print(' '.join([str(x) for x in key_vals])+' - '+key)
     
            index_vals.append(key_vals)
                    
        for i in range(len(wanted)):
            prod = np.array(wanted[i])
            if "indicatorOfTypeOfLevel" in index_keys:
                index = np.where(index_keys=="indicatorOfTypeOfLevel")
                if prod[index] in levtypes:
                    pass
                else:
                    newLevType = solveLevTypeProblem(prod[index])
                    prod[index] = newLevType
            for j in range(len(index_keys)):
                try:
                    g.codes_index_select(iid,index_keys[j],prod[j])
                except:
                    g.codes_index_select(iid,index_keys[j],int(prod[j]))
     
            while 1:
                gid = g.codes_new_from_index(iid)
                if gid is None: 
                    break
                if first:
                    gridType = g.codes_get(gid,'gridType')
                    if gridType == 'lambert':
                        data['LoVInDegrees'] = g.codes_get(gid,'LoVInDegrees')
                        data['DxInMetres'] = g.codes_get(gid,'DxInMetres')
                        data['DyInMetres'] = g.codes_get(gid,'DyInMetres')
                        data['Latin1InDegrees'] = g.codes_get(gid,'Latin1InDegrees')
                        data['Latin2InDegrees'] = g.codes_get(gid,'Latin2InDegrees')
                    data['Ni'] = g.codes_get(gid,'Ni')
                    data['Nj'] = g.codes_get(gid,'Nj')
                    data['LatFG'] = g.codes_get(gid,'latitudeOfFirstGridPointInDegrees')
                    data['LonFG'] = g.codes_get(gid,'longitudeOfFirstGridPointInDegrees')
                    if not gridType == 'lambert':
                        data['LatLG'] = g.codes_get(gid,'latitudeOfLastGridPointInDegrees')
                        data['LonLG'] = g.codes_get(gid,'longitudeOfLastGridPointInDegrees')
                        try:
                            data['jdir'] = g.codes_get(gid,'jDirectionIncrementInDegrees')
                            data['iDir'] = g.codes_get(gid,'iDirectionIncrementInDegrees')
                        except:
                            pass
                    if gridType == 'rotated_ll':
                        data['SPlat'] = g.codes_get(gid,'latitudeOfSouthernPoleInDegrees')
                        data['SPlon'] = g.codes_get(gid,'longitudeOfSouthernPoleInDegrees')
                    if useStepRange:
                        data['stepRange'] = g.codes_get(gid,'stepRange')                    
                    first = False
                data[names[i]] = g.codes_get_values(gid)
                # if debug:
                #     print('')
                #     print('DEBUG')
                #     print(" ".join(["%s=%s" % (key,g.codes_get(gid,key)) for key in index_keys]))
                g.codes_release(gid)
     
        g.codes_index_release(iid)
    except g.GribInternalError:
        print('Can not open file')
    
    #print('It took %.5f seconds' % (time.time()-start))
    return data, gridType


"""
*******************************************************************************
Find closest gridpoint for grids like lambert
"""      
def closest_gridpoint(latP, lonP, latG, lonG, version = '2d', maxDistInDegrees = 1, n = 1):
    
    # distances between point and every gridpoint    
    dist = np.sqrt((latP-latG)**2+(lonP-lonG)**2)    
    
    # Make sure point not outside grid
    if dist.min() > maxDistInDegrees:
        print('Point is outside grid lat = '+ str(latP) + ' lon = ' + str(lonP))
        return None
     
    # closest gridpoint
    if version == '2d':
        if n == 1:
            closest = np.unravel_index(dist.argmin(), dist.shape)
        else:
            x = dist.flatten().argsort()[:n]
            closest = [np.unravel_index(p, dist.shape) for p in x]
            weights =  1./np.array(dist.flatten()[x])
            weights /= weights.sum(axis=0)
    else:
        dist = np.sqrt((latP-latG)**2+(lonP-lonG)**2)
        if n == 1:
            closest = dist.flatten().argmin()
        else:
            closest = dist.flatten().argsort()[:n]
            weights =  1./np.array(dist.flatten()[x])
            weights /= weights.sum(axis=0)
    
    if n == 1:    
        return closest
    else:
        return closest, weights

"""
*******************************************************************************
Make lat and lon grids
"""    
def get_grid(Ni, Nj, latitudeOfFirstGridPointInDegrees, latitudeOfLastGridPointInDegrees, longitudeOfFirstGridPointInDegrees, longitudeOfLastGridPointInDegrees, sydpol_lon = None, sydpol_lat = None):

    # make grid
    x = np.linspace(longitudeOfFirstGridPointInDegrees, longitudeOfLastGridPointInDegrees, Ni)
    y = np.linspace(latitudeOfFirstGridPointInDegrees, latitudeOfLastGridPointInDegrees, Nj)
    xv, yv = np.meshgrid(x, y)
    
    # rotate grid if neccesary
    if sydpol_lat is not None:
        pxreg, pyreg = rot2reg(xv, yv, sydpol_lon, sydpol_lat)
        return pxreg, pyreg
    else:
        return xv, yv

"""
*******************************************************************************
Turn rotated wind
"""         
def turnwi(u, v, Ni, Nj, latitudeOfFirstGridPointInDegrees, latitudeOfLastGridPointInDegrees, longitudeOfFirstGridPointInDegrees, longitudeOfLastGridPointInDegrees, sydpol_lat, sydpol_lon):

    pxrot, pyrot = get_grid(Ni, Nj, latitudeOfFirstGridPointInDegrees, latitudeOfLastGridPointInDegrees, longitudeOfFirstGridPointInDegrees, longitudeOfLastGridPointInDegrees)
    pxreg, pyreg = rot2reg(pxrot, pyrot, sydpol_lon, sydpol_lat)

    if u.ndim == 1:
        pures, pvres = rotuv(u.reshape(np.shape(pxreg)), v.reshape(np.shape(pxreg)), pyreg, pxreg, sydpol_lat, sydpol_lon)
        return pures.flatten(), pvres.flatten()
    else:
        pures, pvres = rotuv(u, v, pyreg, pxreg, sydpol_lat, sydpol_lon)
        return pures, pvres
 
 
if __name__ == "__main__":

    main()
#     print('main')
    
#     latP = 58.581172
#     lonP = 16.146258
    
#     print('\nTest AROME grib1')
#     fn1 = '/data/dmzshared/24_nb/meps/testdata/MEPS_201909250000+003H00M'
#     print fn1
#     data = getGribWithKeys(fn1,wanted=[(2,11,'sfc')],names = ['t'], index_keys =["level","indicatorOfParameter","indicatorOfTypeOfLevel"], debug=True, useStepRange=True, indexFile=False)
#     print np.amin(data['t'])-273.15, np.mean(data['t'])-273.15, np.amax(data['t'])-273.15
    
#     lonG, latG = reglambert.lambertGrid(data['LatFG'],
#                 data['LonFG'],
#                 data['Ni'],
#                 data['Nj'],
#                 data['LoVInDegrees'],
#                 data['DxInMetres'],
#                 data['DyInMetres'],
#                 data['Latin1InDegrees'],
#                 data['Latin2InDegrees'],
#                 gridInLatlon = True)
    
#     ind = closest_gridpoint(latP, lonP, latG, lonG, version = '2d', maxDistInDegrees = 1, n = 1)
#     print data['t'].reshape(np.shape(latG))[ind]


#     print('\nTest AROME grib2')
#     fn = '/data/dmzshared/24_nb/meps2/testdata/MEPS_201909250000+003H00M'
#     print fn
#     data = getGribWithKeys(fn,wanted=[(2,'2t')],names = ['t'], index_keys =["level","shortNameECMF"], debug=True, useStepRange=True, indexFile=False)
#     print np.amin(data['t'])-273.15, np.mean(data['t'])-273.15, np.amax(data['t'])-273.15
#     print data
    
#     lonG, latG = reglambert.lambertGrid(data['LatFG'],
#                 data['LonFG'],
#                 data['Ni'],
#                 data['Nj'],
#                 data['LoVInDegrees'],
#                 data['DxInMetres'],
#                 data['DyInMetres'],
#                 data['Latin1InDegrees'],
#                 data['Latin2InDegrees'],
#                 gridInLatlon = True)
    
#     ind = closest_gridpoint(latP, lonP, latG, lonG, version = '2d', maxDistInDegrees = 1, n = 1)
#     print data['t'].reshape(np.shape(latG))[ind]
    
    
#     exit()


    
# #    print('\nTest PMP')
# #    fn = '/data/24/valen/data/pmp/PMP_P_201908260300+024H00M'
# #    print fn
# #    data = getGribWithKeys(fn,wanted=[(2,11,'sfc')],names = ['t'], index_keys =["level","indicatorOfParameter","indicatorOfTypeOfLevel"], debug=True, useStepRange=True)
# #    print np.amin(data['t'])-273.15, np.mean(data['t'])-273.15, np.amax(data['t'])-273.15
# #    print data
    
#     print('\nTest MESAN')
#     fn = '/data/24/mesan/MesanA/data/Mesan/MESAN_201909200000+000H00M'
#     print fn
#     data = getGribWithKeys(fn,wanted=[(2,11,'sfc')],names = ['t'], index_keys =["level","indicatorOfParameter","indicatorOfTypeOfLevel"], debug=True, useStepRange=True)
#     print np.amin(data['t'])-273.15, np.mean(data['t'])-273.15, np.amax(data['t'])-273.15
#     print data

# #    print('\nTest EC')
# #    fn = '/data/24/sam/data/data/A/SAMHALLSBYGGNAD/Frysen/ECMWF_201908260000+024H00M'
# #    print fn
# #    data = getGribWithKeys(fn,wanted=[(0,167,'sfc')],names = ['t'], index_keys =["level","indicatorOfParameter","indicatorOfTypeOfLevel"], debug=True, useStepRange=True)
# #    print np.amin(data['t'])-273.15, np.mean(data['t'])-273.15, np.amax(data['t'])-273.15
# #    print data
# #    
# #    print('\nTest AROME')
# #    fn = '/data/24/harmonie/AM25H2/AM25H2_201908280600+012H00M'
# #    print fn
# #    data = getGribWithKeys(fn,wanted=[(2,11,'sfc')],names = ['t'], index_keys =["level","indicatorOfParameter","indicatorOfTypeOfLevel"], debug=True, useStepRange=True)
# #    print np.amin(data['t'])-273.15, np.mean(data['t'])-273.15, np.amax(data['t'])-273.15
# #    print data
    
#     fields = {}
#     #'gribkeys':{'indicatorOfTypeOfLevel':105, 'indicatorOfParameter':101, 'level':0, 'startStep':fh, 'endStep':fh, 'dataDate':int(t[:8]), 'dataTime':int(t[8:])}
#     fields['t'] = {'values':data['t']+10, 'gribkeys':{'indicatorOfParameter':102,'level':10}}
#     write_grib(fn,'warmer.grb',fields,missingValue=9999)
# #    data = getGribWithKeys('warmer.grb',wanted=[(2,11,'sfc')],names = ['t'], index_keys =["level","indicatorOfParameter","indicatorOfTypeOfLevel"], debug=True)
# #    print data
#     print('Done')
    
