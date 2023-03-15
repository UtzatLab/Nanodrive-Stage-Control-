from time import sleep
from ctypes import *
import numpy as np
import time as timing
import TimeTagger as tt
import multiprocessing as mp
import threading
from queue import Queue
import time
import matplotlib.pyplot as plt
import ctypes
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
#this function allows for the pause of steps less than .01 s which is what sleep() is limited to. 
#use the functin time.perf_counter_ns()  instead of time.time() if you want to test accuracy
# can get microsecond pauses doesnt quite get 1 us but if you input 1 us it pauses for around 4 us. the larget the number the better the accuracy 


def sleep_us(microseconds):
    start_time = time.perf_counter_ns()
    while True:
        elapsed_time = time.perf_counter_ns() - start_time
        remaining_time = microseconds - elapsed_time /1000
        if remaining_time <= 0:
            break

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

#this function is a bit of a general function that allows you do make 3d waveforms, this can be done with a different below
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

#this makes 2-d waveform and spits it into a text file
def createScanPoints(x_start, y_start, nx_pix, ny_pix, x_end, y_end, file_name, square_raster = False):
    filenameX = file_name + "X.txt" 
    filenameY = file_name + "Y.txt"

    motion_arrayY = np.zeros((ny_pix,nx_pix))  
    motion_arrayX = np.zeros((ny_pix,nx_pix))  
    for y in range(ny_pix):    
        for x in range(nx_pix):
            motion_arrayY[y,x] = (y_end-y_start)/(ny_pix)*y

    motion_listY = motion_arrayY.reshape(1,-1)
    for y in range(ny_pix):    
        for x in range(nx_pix):
            motion_arrayX[y,x] = (x_end-x_start)/nx_pix*x
        if square_raster == True:
            if y%2 ==1: 
                motion_arrayX[y,:] = motion_arrayX[y,::-1]
    motion_listX = motion_arrayX.reshape(1,-1) 
   
    file = open(filenameY, "w")
    for i in range(0, nx_pix*ny_pix, 1):
        s = repr(motion_listY[0,i]) + "\n"
        file.write(s)
    file.close()

    file = open(filenameX, "w")
    for i in range(0, nx_pix*ny_pix, 1):
        s = repr(motion_listX[0,i]) + "\n"
        file.write(s)
    file.close()
    
  
#This scans through using the MCL waveform function
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

    print(waveformX)
    print(waveformY)

    datapointsX= len(waveformX)

    milliseconds = c_double(ms)
    iterations = c_ushort(iterations)
    mcldll.MCL_WfmaSetup(c_arrayX, c_arrayY, c_arrayZ, datapointsX , milliseconds, iterations, handle)
    mcldll.MCL_IssBindClockToAxis(1, 3, 1, handle)
    time_start = timing.time()

    mcldll.MCL_WfmaTriggerAndRead(c_arrayX  , c_arrayY, c_arrayZ, handle)

    time_end = timing.time()
    total_time = time_end - time_start
    print('Time elapsed is for stage motion %4f s' % total_time)
    
    #this takes as much time to run as the stage motion, only use for troubleshooting
    #if mcldll.MCL_WfmaTriggerAndRead(c_arrayX  , c_arrayY, c_arrayZ, handle) == 0:
       # print('Stage Motion Successful!')
        
    if mcldll.MCL_WfmaSetup(c_arrayX, c_arrayY, c_arrayZ, datapointsX , milliseconds, iterations, handle) == -6:
        print('An argument is out of range or a required pointer is equal to NULL. Try reducing the total number of points or time')
        

    axisX = c_uint(1)
    posX = c_double(00)
    axisY = c_uint(2)
    posY = c_double(0)
    mcldll.MCL_SingleWriteN(posX, axisX, handle)
    mcldll.MCL_SingleWriteN(posY, axisY, handle)

    mcldll.MCL_ReleaseHandle(handle)

   #this scans using a loop and absolute movements 
def startScanningWithoutWaveform(fileX = None , fileY = None, fileZ = None, dwell_time= 0, iterations = 1):
    sleep(.1)
    handle = mcldll.MCL_InitHandle()
    start = timing.time()
    if fileX:
        waveformX = np.loadtxt(fileX)
    if fileY:
        waveformY = np.loadtxt(fileY)
    if fileZ:
        waveformZ = np.loadtxt(fileZ)
    
    
    mcldll.MCL_IssBindClockToAxis(1, 3, 1, handle)
    start = timing.time()
    for j in range(iterations):
        for i in range(len(waveformX)):
            axisX = c_uint(1)
            posX = c_double(waveformX[i])
            
            axisY = c_uint(2)
            posY = c_double(waveformY[i])

            mcldll.MCL_SingleWriteN(posX, axisX, handle)
            mcldll.MCL_SingleReadN(axisX, handle)

            mcldll.MCL_SingleWriteN(posY, axisY, handle)
            sleep_us(dwell_time)
            #timing.sleep(dwell_time)

    end = timing.time()

    
    mcldll.MCL_SingleWriteN(c_double(00), axisX, handle)
    mcldll.MCL_SingleWriteN(c_double(00), axisY, handle)
    
    print(f'total time = {end-start}')
    mcldll.MCL_ReleaseHandle(handle)

    
    #this runs the scan and collects the data at the same time

if __name__ == '__main__':
    square_raster = True
    iterations  = 3
    nx_pix =100
    ny_pix = 100
    n_pixels = nx_pix*ny_pix 
    dwell_time = 1e2

    createScanPoints(x_start = 20, y_start = 0, nx_pix = nx_pix, ny_pix = ny_pix, x_end = 50, y_end = 100, file_name = 'path', square_raster = square_raster)


    
    tagger = tt.createTimeTagger()
    tagger.setTestSignal(1, True)

    img = np.zeros((ny_pix, nx_pix))
    for i in range(iterations):
        
        delay_signal = tt.DelayedChannel(tagger, 3, dwell_time * 1e6)
        delay_ch = delay_signal.getChannel()


        cbm = tt.CountBetweenMarkers(tagger, 1, 3, delay_ch, nx_pix*ny_pix )
        p1 = mp.Process(target = startScanningWithoutWaveform, args = ('pathX.txt' , 'pathY.txt', None, dwell_time, 1))#the args are (input pos for x, input pos for y, input pos for z, dwell time , iteratoins)
        
        p1.start()
        
    
        while 1:
            counts = cbm.getData()
            current_img = np.reshape(counts, (ny_pix, nx_pix))
            print(counts)
            for i in range(ny_pix):
                if i%2 == 1 and square_raster:
                    current_img[i,:] = current_img[i,::-1]

            mask = current_img !=0
            img[mask]=current_img[mask]
            
            plt.imshow(img)
            plt.pause(.001)
            if np.all(counts) == True:
                break
        print(counts)
      
        p1.join()
    
        
    tt.freeTimeTagger(tagger) 
    
   
