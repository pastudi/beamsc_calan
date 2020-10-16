#!/usr/bin/env python

from __future__ import print_function
from datetime import datetime
from os import path,mkdir
import pathlib2 as pathlib
from math import ceil

class BeamMeasurement:
    def __init__(self):
        # Datos generales
        self.meas_freq=0.0
        self.meas_start=datetime.now()
        self.name="untitled"
        self.comment=""
        # Plano medicion
        self.antenna_aperture=0.0
        self.sampl_dist=0.0
        self.distance=0.0
        self.plane_size=0.0
        #Configuracion instrumentos
        #VNA
        self.if_freq=0.0
        self.ifbw=0.0
        self.sweep_points=0.0
        self.isAsig=True
        self.avg_points=0
        #RF Source
        self.rf_power=0.0
        self.lo_power=0.0
        #Tipo de medicion
        self.meas_cut=False
        self.xcut=False
        
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
            f.write('Frequency (GHz): {:.2f}\n'.format(self.meas_freq))
            f.write('Comment: {}\n'.format(self.comment))
            #Plano medicion
            f.write('DUT Aperture (mm): {:.2f}\n'.format(self.antenna_aperture))
            f.write('DUT Distance (mm): {:.2f}\n'.format(self.distance))
            #Configuracion instrumentos
            f.write('IF Freq (GHz): {:.2f}\n'.format(self.if_freq))
            f.write('IF BW (Hz): {:d}\n'.format(self.ifbw))
            f.write('Sweep Points: {:d}\n'.format(self.sweep_points))
            f.write('Signal channel A?: {:d}\n'.format(self.isAsig))
            f.write('RF Power (dBm): {:.2f}\n'.format(self.rf_power))
            f.write('LO Power (dBm): {:.2f}\n'.format(self.lo_power))
            f.write('Measurement Speed: {:.3f}\n'.format(self.meas_spd))
            f.write('Movement Speed: {:.3f}\n'.format(self.move_spd))
