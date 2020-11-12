#!/usr/bin/env python

from __future__ import print_function
import pyvisa as visa
import numpy as np
import time
from datetime import datetime
from sys import exit
from visa_inst import Visa_inst, VNA
from beamsc import BeamScanner
from beammeas import BeamMeasurement        
import traceback as tr
from beamsc_calan import IP_VNA,IP_BEAM_XY,exit_clean

class VNA2(VNA):
    def set_meas(self,BeamMeasurement):
        # Too lazy to change the variable names
        precision=12;
        n_sweep=BeamMeasurement.sweep_points
        start=BeamMeasurement.if_freq*1000
        stop=start
        bw=BeamMeasurement.ifbw
        n_avg=BeamMeasurement.avg_points
        isAsig=BeamMeasurement.isAsig
        
        self.write('SYST:FPReset')
        self.write('DISPlay:WINDow1:STATE ON')
        
        if isAsig:
            param='\'A,0\''
        else:
            param='\'B,0\''
        
        self.write('CALCULATE1:PARAMETER:DEFINE:EXTENDED \'DATOS_re\','+ param +' ')
        self.write('CALCULATE1:PARAMETER:DEFINE:EXTENDED \'DATOS_im\','+ param +' ')
        
        self.write('DISPLAY:WINDOW1:TRACE1:FEED \'DATOS_re\' ')
        self.write('CALCULATE1:PARAMETER:SELECT \'DATOS_re\' ')
        self.write('CALCULATE1:FORMAT REAL')
        
        self.write('DISPLAY:WINDOW1:TRACE2:FEED \'DATOS_im\' ')
        self.write('CALCULATE1:PARAMETER:SELECT \'DATOS_im\' ')
        self.write('CALCULATE1:FORMAT IMAG')
        
        self.query('SENS1:SWE:TYPE CW; *OPC?;')
        
         
        #self.write('SENSE1:FREQ:START {:.12f} MHz '.format(start))
        #self.write('SENSE1:FREQ:STOP {:.12f} MHz '.format(stop))
        self.query('SENS1:FREQ:FIX {:.12f} MHz; *OPC?;'.format(start))
        self.query('SENSE1:SWEEP:POINTS {:.12f}; *OPC?; '.format(n_sweep))
        self.write('SENSE1:BWID {:.12f} Hz '.format(bw))
        self.query('SENSE1:SWE:TIME MIN; *OPC?')
        
        if n_avg!=0:
            self.write('SENS:AVER ON')
            self.write('SENS:AVER:MODE POIN')
            self.write('SENSE:AVER:COUN {:d} '.format(n_avg))
        else:
            self.write('SENS:AVER OFF')
        
        self.write('TRIG:SOUR EXTernal')
        #self.write('TRIG:TYPE EDGE')
        #self.write('TRIG:SLOP NEGative')
        #self.write('SENS:SWE:MODE CHANnel')
        self.write('CONT:SIGN BNC1,TIENEGATIVE')
        self.write('CONT:SIGN AUXT,INACTIVE')
        
        self.write('*CLS')
        
parampath='/home/pablo/DATA/beamscanner/ccat_spline_horn1/20201103_170228'
filepath='/home/pablo/DATA/beamscanner/sys_eval/'
vna=VNA2(IP_VNA)
beam_xy=BeamScanner(IP_BEAM_XY,'move x,y')
scan=BeamMeasurement()
tline=0.0

beam_xy.connect()
vna.connect()
scan.load(parampath)

def conf_vna():

    global scan,vna,beam_xy
    
    vna.set_meas(scan)
    
    tline_est=scan.calc_plane()/scan.meas_spd
    print("Estimated time [s]: {:.3f}".format(tline_est))
    vna.set_meas(scan)
    t1=vna.get_swtime1pt()
    scan.sweep_points=vna.set_swpoints(tline_est,t1)
    beam_xy.launch_trigger(1,1)
    
    if vna.ready(10):
        pass
    
    tline_act=vna.get_cycletime(beam_xy,scan)
    print('Actual time [s]: {:.3f}'.format(tline_act))
    print('Swe pts: {:d}'.format(scan.sweep_points))
    scan.sweep_points=int(scan.sweep_points*tline_est/tline_act)
    print('Swe pts: {:d}'.format(scan.sweep_points))
    vna.set_meas(scan)
    
    return tline_act

def stability_measurement(N=10,delay=0.0,wait_user=False):

    global scan
    
    scan.meas_start=datetime.now()
    
    filename=filepath+scan.meas_start.strftime("%Y%m%d_%H%M%S")
    
    beam_xy.set_speed(scan.move_spd,'x')
    beam_xy.set_speed(scan.move_spd,'y')
    
    Npoints=scan.calc_Msize()
    
    x=scan.space_array()
    data_re=np.zeros(Npoints*N)
    data_im=np.zeros(Npoints*N)
    
    save_buffer=np.zeros((Npoints,3))
    
    Np_vna=scan.sweep_points;
    Ns_vna=Np_vna-1
    step_vna=scan.calc_plane()/(Np_vna-1)
    x_vna=np.linspace(-0.5,0.5,Np_vna)*scan.calc_plane()
    
    scan.name=raw_input('Enter antenna name (no spaces or special characters): ') or 'test'
    scan.comment=raw_input('Enter comments: ')
    
    with open(filename,'a') as f:
        f.write('# Antenna Name: {}\n'.format(scan.name))
        f.write('# Frequency (GHz): {:.2f}\n'.format(scan.meas_freq))
        f.write('# Comment: {}\n'.format(scan.comment))
        f.write('# Plane size (mm): {:.2f}\n'.format(scan.plane_size))
        f.write('# Sampling distance (lambda): {:.2f}\n'.format(scan.sampl_dist))
        #Configuracion instrumentos
        f.write('# IF Freq (GHz): {:.2f}\n'.format(scan.if_freq))
        f.write('# IF BW (Hz): {:.2f}\n'.format(scan.ifbw))
        f.write('# Sweep Points: {:d}\n'.format(scan.sweep_points))
        f.write('# Signal channel A?: {:d}\n'.format(scan.isAsig))
        f.write('# Measurement Speed: {:.3f}\n'.format(scan.meas_spd))
        f.write('# Movement Speed: {:.3f}\n'.format(scan.move_spd))
        f.write('# Number of lines: {:d}\n'.format(N))
        f.write('# Delay between lines {:.2f}\n'.format(delay))
        f.write('# Wait for user: {:d}\n'.format(wait_user))
        f.write('# x [mm] RE[] IM[]\n')
    
    for i in range(N):
        
        print ("Moving to start:\t{:.3f}, {:.3f}...".format(x[0],0), end='\t')
        beam_xy.move_absolute(x[0],0)
        print("Stop")
        beam_xy.set_speed(scan.meas_spd,'x')
        
        if wait_user:
            raw_input('Press Enter to measure')
        
        print("Moving to end:\t\t{:.3f}, {:.3f}...".format(x[-1],0), end='\t')
        beam_xy.move_absolute_trigger(x[-1],0)
        print("Stop")
        
        if vna.ready(tline*1.1):
            print("VNA ready")
        else:
            print('main: VNA sweep timeout')
            raise Exception("VNA sweep timeout")
        
        try:
            vna_re=vna.get_data('re')
            vna_im=vna.get_data('im')
        except visa.VisaIOError, e:
            print('main(): {}'.format(e))
            tr.print_exc()
            pass
            
        data_re[i*Npoints:(i+1)*Npoints]=np.interp(x,x_vna,vna_re)
        data_im[i*Npoints:(i+1)*Npoints]=np.interp(x,x_vna,vna_im)
        
        save_buffer[:,0]=x
        save_buffer[:,1]=data_re[i*Npoints:(i+1)*Npoints]
        save_buffer[:,2]=data_im[i*Npoints:(i+1)*Npoints]
        
        try:
            with open(filename,'ab') as f:
                np.savetxt(f,save_buffer)
            save_buffer=np.zeros((Npoints,3))
        except Exception as e:
            print('main(): {}'.format(e))
            tr.print_exc()
            
        if delay != 0.0:
            time.sleep(delay)
            
        beam_xy.set_speed(scan.move_spd,'x')