# -*- coding: utf-8 -*-
"""
Created on Thu Mar  9 15:11:01 2023

@author: colbu
"""

from time import sleep
from ctypes import *
import numpy as np
import time as timing

# change the path to match your system.
mcldll = CDLL(r"C:/Program Files/Mad City Labs/NanoDrive/Madlib.dll")
mcldll.MCL_ReleaseHandle.restype = None
mcldll.MCL_SingleReadN.restype = c_double
mcldll.MCL_GetCalibration.restype = c_double

'''
axis corresponds to X=1,Y=2,Z=3
points are how many steps the max for all steps in x y and z is 10000
time is the time it takes to write the waveform which will increase the accuracy 
max dim for x and y is 200
the lagged parameter allows for the repetiiton of values for however many steps you would like to take in the other dimention of the raster scan 
the repeat parameter allows for a file to be written with the same pattern repeating useful for a raster scan
the start coordinate tells you what value you start at in the FOV
'''

def testStageWaveformAccuracy(axis, points, time , file_name, dim, lagged = False, repeat = False):
 
    # Acquire a device handle
    handle = mcldll.MCL_InitHandle()
    print("Handle = ", handle)
    if axis == 1:
        filename = file_name + "X.txt"
    elif axis == 2:
        filename = file_name + "Y.txt"
    else:
        filename = file_name + "Z.txt"

    
    #this function gets the max range of an axis
    axis = c_uint(axis)
    calibration = mcldll.MCL_GetCalibration(axis, handle)
    
    # Create a c_double array type for our waveform data
    datapoints = points
    wavetype = c_double * datapoints
    readwaveform = wavetype()
    loadwaveform = wavetype()
    # Initialize our waveform commands.
    #says that every value in the loadwaveform is the total range (calibration)/1000 so you get 1000 values going from 0-200
    for i in range(0, points, 1):
        loadwaveform[i] = c_double(dim / points * i)
    milliseconds = c_double(time)
    print(list(loadwaveform))
    mcldll.MCL_Setup_LoadWaveFormN(axis, datapoints, milliseconds, loadwaveform, handle)
    mcldll.MCL_Setup_ReadWaveFormN(axis, datapoints, milliseconds, handle)
    mcldll.MCL_TriggerWaveformAcquisition(axis, datapoints, readwaveform, handle)
    print(list(readwaveform))
    # write the waveform doubles to a file, which can be used in a
    # graphing program
    if lagged == True:
        arrayLen = c_double * (len(readwaveform)**2)
        c_doubleArray = arrayLen()
        print(len(c_doubleArray))
        print(len(readwaveform))
        counter = 0
        for i in range(0,len(c_doubleArray)-1,len(readwaveform)):
            counter +=len(readwaveform)
            c_doubleArray[i:i+len(readwaveform)] = [readwaveform[int((counter-10)/(len(readwaveform)))]]*(len(readwaveform))

        file = open(filename, "w")
        for i in range(0, len(c_doubleArray), 1):
            s = repr(c_doubleArray[i]) + "\n"
            file.write(s)
        file.close()
        
    else:
        file = open(filename, "w")
        for i in range(0, points, 1):
            s = repr(readwaveform[i]) + "\n"
            file.write(s)
        file.close()

    #return home
    axisX = c_uint(1)
    posX = c_double(00)
    axisY = c_uint(2)
    posY = c_double(0)
    mcldll.MCL_SingleWriteN(posX, axisX, handle)
    mcldll.MCL_SingleWriteN(posY, axisY, handle)

    mcldll.MCL_ReleaseHandle(handle)


def createLinearWaveform(axis, startCoordinate, points, dim, file_name = 'path',  lagged = False, repeat = False, repeat_inverse = False):
    if axis == 1:
        filename = file_name + "X.txt"
    elif axis == 2:
        filename = file_name + "Y.txt"
    else:
        filename = file_name + "Z.txt"

    targets = np.zeros(points)
    for i in range(points):
        targets[i]=(dim/points)*i
    targets[:] += startCoordinate

    if lagged:
        lagged_targets = np.zeros(points**2)
        for i in range(0,points**2,points):
            lagged_targets[i:i+points] = targets[int(i/points)]
        
        file = open(filename, "w")
        for i in range(0, points**2, 1):
            s = repr(lagged_targets[i]) + "\n"
            file.write(s)
        file.close()
    
    elif repeat:
        repeated_targets = np.zeros(points**2)
        for i in range(0,points**2,points):
            repeated_targets[i:i+points]= targets
        
        file = open(filename, "w")
        for i in range(0, points**2, 1):
            s = repr(repeated_targets[i]) + "\n"
            file.write(s)
        file.close()
    elif repeat_inverse:
        repeated_targets_inv = np.zeros(points**2)
        for i in range(0,points**2,points):
            repeated_targets_inv[i:i+points]= targets
    
        for i in range(0,points//2):
           repeated_targets_inv[i*2*points+points:i*2*points+points*2] = targets[::-1]

        file = open(filename, "w")
        for i in range(0, points**2, 1):
            s = repr(repeated_targets_inv[i]) + "\n"
            file.write(s)
        file.close()
    else:
        file = open(filename, "w")
        for i in range(0, points, 1):
            s = repr(targets[i]) + "\n"
            file.write(s)
        file.close()




def startScanning(fileX = None , fileY = None, fileZ = None, ms= 5, iterations = 1):
    handle = mcldll.MCL_InitHandle()
    print("Initialized ")
    c_arrayX = None
    c_arrayY = None
    c_arrayZ = None
    if fileX:
        waveformX = np.loadtxt(fileX)

        datapointsX = len(waveformX)
        wavetypeX = c_double * datapointsX
        c_arrayX = wavetypeX()

        for i in range(0,len(waveformX)-1,1):
            c_arrayX[i] = c_double(waveformX[i])
    
    if fileY:
        waveformY = np.loadtxt(fileY)

        datapointsY = len(waveformY)
        wavetypeY = c_double * datapointsY
        c_arrayY = wavetypeY()

        for i in range(0,len(waveformY)-1,1):
            c_arrayY[i] = c_double(waveformY[i])

    if fileZ:
        waveformZ = np.loadtxt(fileZ)

        datapointsZ = len(waveformZ)
        wavetypeZ = c_double * datapointsZ
        c_arrayZ = wavetypeZ()

        for i in range(0,len(waveformZ)-1,1):
            c_arrayZ[i] = c_double(waveformZ[i])

    

    datapointsX= len(waveformX)

    milliseconds = c_double(ms)
    iterations = c_ushort(iterations)
    mcldll.MCL_WfmaSetup(c_arrayX, c_arrayY, c_arrayZ, datapointsX , milliseconds, iterations, handle)

    time_start = timing.time()

    mcldll.MCL_WfmaTriggerAndRead(c_arrayX  , c_arrayY, c_arrayZ, handle)

    time_end = timing.time()
    total_time = time_end - time_start
    print('Time elapsed is %4f s' % total_time)
    
    if mcldll.MCL_WfmaTriggerAndRead(c_arrayX  , c_arrayY, c_arrayZ, handle) == 0:
        print('Stage Motion Successful!')
    elif mcldll.MCL_WfmaSetup(c_arrayX, c_arrayY, c_arrayZ, datapointsX , milliseconds, iterations, handle) == -6:
        print('An argument is out of range or a required pointer is equal to NULL. Try reducing the total number of points or time')

    axisX = c_uint(1)
    posX = c_double(00)
    axisY = c_uint(2)
    posY = c_double(0)
    mcldll.MCL_SingleWriteN(posX, axisX, handle)
    mcldll.MCL_SingleWriteN(posY, axisY, handle)

    mcldll.MCL_ReleaseHandle(handle)

