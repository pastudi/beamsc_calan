#!/usr/bin/env python

from __future__ import print_function
from datetime import datetime
from os import path,mkdir
import pathlib2 as pathlib
from math import ceil
import numpy as np

class BeamMeasurement(object):
    def __init__(self):
        # Datos generales
        self.meas_freq=0.0
        self.meas_start=datetime.now()
        self.name="untitled"
        self.comment=""
        # Plano medicion
        self.sampl_dist=0.0
        self.distance=0.0
        self.plane_size=0.0
        #Configuracion instrumentos
        #VNA
        self.if_freq=0.0
        self.ifbw=0.0
        self.sweep_points=0
        self.avg_points=0
        self.isAsig=True
        
        self.meas_spd=0.0
        self.move_spd=0.0
    
    def calc_step(self):    # En mm
        c=299792458
        lam=c/(self.meas_freq*1e9)*1000.0
        return lam*self.sampl_dist
        
    def calc_Msize(self):   # Calculates number of points
        n_points=ceil(self.plane_size/self.calc_step())+1.0;
        if n_points % 2 ==0:  # Always odd to include center point
            n_points+=1
        return int(n_points)
        
    def calc_plane(self):
        return (self.calc_Msize()-1)*self.calc_step()
    
    def space_array(self):
        Npoints=self.calc_Msize()
        Nstep=Npoints-1
        x=np.arange(-Nstep/2,Nstep/2+1)*self.calc_step()
        
        return np.flip(x)

class BeamMap(BeamMeasurement,object):
    def __init__(self):
        super(BeamMap,self).__init__()
        self.antenna_aperture=0.0
        # self.avg_points=0
        #RF Source
        self.rf_power=0.0
        self.lo_power=0.0
        #Tipo de medicion
        self.meas_cut=False
        self.xcut=False
        
    def get_filepath(self):
        return self.name+'/'+self.meas_start.strftime("%Y%m%d_%H%M%S")

    def savetxt(self,filepath):
        filepath_=filepath+self.name+'/'
        if not path.exists(filepath_):
            print("Creating... "+filepath_)
            pathlib.Path(filepath_).mkdir(parents=True, exist_ok=True) 
            pathlib.Path(filepath_+'figs/').mkdir(parents=True, exist_ok=True) 
        filename=self.get_filepath()
        print("Saving on... "+filepath+filename)
        with open(filepath+filename,'a') as f:
            #Datos generales
            f.write('# Frequency (GHz): {:.2f}\n'.format(self.meas_freq))
            f.write('# Comment: {}\n'.format(self.comment))
            #Plano medicion
            f.write('# DUT Aperture (mm): {:.2f}\n'.format(self.antenna_aperture))
            f.write('# DUT Distance (mm): {:.2f}\n'.format(self.distance))
            f.write('# Plane size (mm): {:.2f}\n'.format(self.plane_size))
            f.write('# Sampling distance (lambda): {:.2f}\n'.format(self.sampl_dist))
            #Configuracion instrumentos
            f.write('# IF Freq (GHz): {:.2f}\n'.format(self.if_freq))
            f.write('# IF BW (Hz): {:.2f}\n'.format(self.ifbw))
            f.write('# Sweep Points: {:d}\n'.format(self.sweep_points))
            f.write('# Signal channel A?: {:d}\n'.format(self.isAsig))
            f.write('# RF Power (dBm): {:.2f}\n'.format(self.rf_power))
            f.write('# LO Power (dBm): {:.2f}\n'.format(self.lo_power))
            f.write('# Measurement Speed: {:.3f}\n'.format(self.meas_spd))
            f.write('# Movement Speed: {:.3f}\n'.format(self.move_spd))
    
    def load(self,filepath):
        with open(filepath,'r') as f:
            #all_data= [line.strip() for line in f.readlines()]
            param=[0]*14
            for i in range (14):
                line=f.readline()
                line=line.split(': ')
                # print(line)
                param[i]=line[1]
        self.meas_freq       =float(param[0])
        i=2
        self.antenna_aperture=float(param[i])
        i+=1
        self.distance        =float(param[i])
        i+=1
        self.plane_size      =float(param[i])
        i+=1
        self.sampl_dist      =float(param[i])
        i+=1
        self.if_freq         =float(param[i])
        i+=1
        self.ifbw            =float(param[i])
        i+=1
        self.sweep_points    =int(param[i])
        i+=1
        self.isAsig          =int(param[i])
        i+=1
        self.rf_power        =float(param[i])
        i+=1
        self.lo_power        =float(param[i])
        i+=1
        self.meas_spd        =float(param[i])
        i+=1
        self.move_spd        =float(param[i])
        # return param

class BeamTest(BeamMeasurement,object):
    path='/home/pablo/DATA/beamscanner/sys_eval/'
    def __init__(self):
        super(BeamTest,self).__init__()
        self.nlines=0
        self.delay=0
        self.wait_user=0
        self.filename=''
        self.test_type='R'  #R: Repeatability, #L: linearity
    
    def savetxt(self):
        filename=self.path+self.meas_start.strftime("%Y%m%d_%H%M%S")
        print("Saving on... "+filename)
        with open(filename,'a') as f:
            f.write('# Antenna Name: {}\n'.format(self.name))
            f.write('# Frequency (GHz): {:.2f}\n'.format(self.meas_freq))
            f.write('# Comment: {}\n'.format(self.comment))
            f.write('# Plane size (mm): {:.2f}\n'.format(self.plane_size))
            f.write('# Sampling distance (lambda): {:.2f}\n'.format(self.sampl_dist))
            #Configuracion instrumentos
            f.write('# IF Freq (GHz): {:.2f}\n'.format(self.if_freq))
            f.write('# IF BW (Hz): {:.2f}\n'.format(self.ifbw))
            f.write('# Sweep Points: {:d}\n'.format(self.sweep_points))
            f.write('# Signal channel A?: {:d}\n'.format(self.isAsig))
            f.write('# Measurement Speed: {:.3f}\n'.format(self.meas_spd))
            f.write('# Movement Speed: {:.3f}\n'.format(self.move_spd))
            # Test parameters
            f.write('# Test type: {}\n'.format(self.test_type))
            f.write('# Number of lines: {:d}\n'.format(self.nlines))
            f.write('# Delay between lines: {:.2f}\n'.format(self.delay))
            f.write('# Wait for user: {:d}\n'.format(self.wait_user))
            f.write('# x [mm] RE[] IM[]\n')
    
    def load(self,filename):
        self.filename=filename
        with open(self.path+filename,'r') as f:
            #all_data= [line.strip() for line in f.readlines()]
            param=[0]*15
            for i in range (15):
                line=f.readline()
                line=line.split(': ')
                # print(line)
                try:
                    param[i]=line[1].rstrip('\n')
                except IndexError as e:
                    print(e)
                    print('Header line #{:d}'.format(i))
                    print(line)
        self.name           =param[0]
        i=1
        self.meas_freq      =float(param[i])
        i+=2
        self.plane_size     =float(param[i])
        i+=1
        self.sampl_dist     =float(param[i])
        i+=1
        self.if_freq        =float(param[i])
        i+=1
        self.ifbw           =float(param[i])
        i+=1
        # self.avg_points     =int(param[i])
        # i+=1
        self.sweep_points   =int(param[i])
        i+=1
        self.isAsig         =int(param[i])
        i+=1
        self.meas_spd       =float(param[i])
        i+=1
        self.move_spd       =float(param[i])
        i+=1
        self.test_type      =param[i]
        i+=1
        self.nlines         =int(param[i])
        i+=1
        self.delay          =float(param[i])
        i+=1
        self.wait_user      =int(param[i])
        
    def read_data(self):
        # filepath='/home/pablo/DATA/beamscanner/sys_eval/'
        x,re,im=np.loadtxt(self.path+self.filename,unpack=True)

        data_comp=np.zeros(int(len(x)),dtype=complex)
        N=self.calc_Msize()
        M=self.nlines

        data_comp.real=re
        data_comp.imag=im

        data_comp=data_comp.reshape((M,N))
        x=x.reshape((M,N))
        
        return x,data_comp