#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 06 15:44:51 2016

@author: a001592
"""

import math as m
import numpy as np

"""
Helpfunctions
"""
def tang(phi):
    return m.tan(m.pi/180.0 *(45.0+phi/2.0))

def sind(phi):
    return m.sin(m.pi/180.0*phi)

def cosd(phi):
    return m.cos(m.pi/180.0*phi)

"""
Calculate regular coordinates to lambert coordinates
Used to calculate Lambert coordinates for lower left corner
"""
def reg2lambert(lon, lat, lat1, lat2, lov):
        
    rearth=6.37122e6
    
    if abs(lat1-lat2) < 1.e-6:
        n=sind(lat1)
    else:
        n=m.log(cosd(lat1)/cosd(lat2))/(m.log(tang(lat2)/tang(lat1)))
    
    F=(cosd(lat1)*tang(lat1)**n)/n
    rho0=rearth*F/(tang(lat1)**n)
    rho=rearth*F/(tang(lat)**n)
    theta=n*(lon-lov)

    alon=rho*sind(theta)
    alat=rho0-rho*cosd(theta)
    
    return alon, alat

"""
Convert from Lambert coordinatates to Latlon
"""
def lambert2reg(x,y,lov,lat1,lat2):
        
    rearth=6.37122e6
    
    rad=m.pi/180.0
    
    if abs(lat1-lat2) < 1.e-6:
        n=sind(lat1)
    else:
        n=m.log(cosd(lat1)/cosd(lat2))/(m.log(tang(lat2)/tang(lat1)))
    
    F=(cosd(lat1)*tang(lat1)**n)/n
    rho0=rearth*F/(tang(lat1)**n)
    
    if n < 0:
        rho0=-rho0

    if n < 0:
        x=-x
        y=-y

    rho=np.sign(n)*np.sqrt(x*x+(rho0-y)*(rho0-y))
    theta=1.0/rad *np.arctan2(x,(rho0-y))

    lon=theta/n+lov
    
    lat=(2*(1.0/rad *np.arctan((rearth*F/rho)**(1/n))))-90.0
            
    return lon, lat

"""
Calculate Latlon coordinates of Lambert grid
IN: Metadata found in GRIB-file
OUT: longrid and latgrid in latlon (np.arrays)
"""    
def lambertGrid(latitudeOfFirstGridPointInDegrees,
                longitudeOfFirstGridPointInDegrees,
                Nx,
                Ny,
                LoVInDegrees,
                DxInMetres,
                DyInMetres,
                Latin1InDegrees,
                Latin2InDegrees,
                gridInLatlon = True):
    
    # calculate Lambert coordinates for lower left corner of grid
    alon, alat = reg2lambert(longitudeOfFirstGridPointInDegrees, latitudeOfFirstGridPointInDegrees, Latin1InDegrees, Latin2InDegrees, LoVInDegrees)

    # create grid in Lambert coordinates    
    xv, yv = np.meshgrid(np.arange(Nx), np.arange(Ny))    
    longrid = alon + DxInMetres*xv.T
    latgrid = alat + DxInMetres*yv.T    
    
    if gridInLatlon:
        # convert from Lambert coordinates to latlon
        lons, lats = lambert2reg(longrid,latgrid,LoVInDegrees,Latin1InDegrees,Latin2InDegrees)    
        return lons.T, lats.T
    else:
        return longrid.T, latgrid.T

if __name__ == '__main__':
    
    """
    Calculate Lambert grid from GRIB-metadata
    Based on reglambert2.f written by Lennart Robertsson 2003
    """

    Nx = 739
    Ny = 949
    latitudeOfFirstGridPointInDegrees = 52.041
    longitudeOfFirstGridPointInDegrees = 1.639
    LoVInDegrees = 15
    DxInMetres = 2500
    DyInMetres = 2500
    Latin1InDegrees = 63
    Latin2InDegrees = 63
    
    lons, lats = lambertGrid(latitudeOfFirstGridPointInDegrees,
                longitudeOfFirstGridPointInDegrees,
                Nx,
                Ny,
                LoVInDegrees,
                DxInMetres,
                DyInMetres,
                Latin1InDegrees,
                Latin2InDegrees)
    
    print('**** CORNERS ****')
    print(lons[0,0],lats[0,0])
    print(lons[-1,0],lats[-1,0])
    print(lons[0,-1],lats[0,-1])
    print(lons[-1,-1],lats[-1,-1])