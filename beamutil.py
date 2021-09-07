#!/usr/bin/env python

from __future__ import print_function
import pyvisa as visa
import numpy as np
import time
from datetime import datetime
from sys import exit
from visa_inst import Visa_inst, VNA
from beamsc import BeamScanner
from beammeas import BeamTest       
import traceback as tr
from beamsc_calan import IP_VNA,IP_BEAM_XY,exit_clean
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from Tkinter import *

class VNA2(VNA):
    def set_meas(self,BeamMap):
        # Too lazy to change the variable names
        precision=12;
        n_sweep=BeamMap.sweep_points
        start=BeamMap.if_freq*1000
        stop=start
        bw=BeamMap.ifbw
        n_avg=1 #BeamMap.avg_points
        isAsig=BeamMap.isAsig
        
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
vna=VNA(IP_VNA)
beam_xy=BeamScanner(IP_BEAM_XY)
scan=BeamTest()
tline=0.0

beam_xy.connect()
vna.connect()
scan.load('20201113_132419')

def max_index(a):
    return np.unravel_index(np.argmax(abs(a)),a.shape)

def norm(a,rel_max=0.0):
    if not rel_max:
        max_=a[max_index(a)]
    else:
        max_=rel_max
    return a/max_

def db(a):
    return 20*np.log10(abs(a))

def deg(a,unwrap=False):
    out=np.angle(a)
    if unwrap:
        out=np.unwrap(out)
        out-=np.amax(out)
    return np.rad2deg(out)

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
    
def plot_test(BeamTest,title,db_=True):
    fig=plt.figure(figsize=(10.51,4.52))
    plt.suptitle(title)
    fig.subplots_adjust(bottom=0.1, right=0.98, top=0.9,left=.07,wspace=0.17)
    ax=fig.add_subplot(1,2,1)
    ax1=fig.add_subplot(1,2,2)
    ax.set_xlabel('Distance (mm)')
    ax.set_ylabel('Magnitude')
    # ax1.set_ylabel('Phase [deg]')
    
    ax.grid( color='0.95')
    ax1.grid( color='0.95')
    
    X,DATA=BeamTest.read_data()
    
    for i in range(BeamTest.nlines):
        if db_:
            ax.plot(X[i,:],db(DATA[i,:]))
        else:
            ax.plot(X[i,:],abs(DATA[i,:]))
        # ax1.plot(X[i,:],deg(DATA[i,:],True))
    
    if BeamTest.test_type is 'L':
        offset=get_lin_offset(DATA)
        for i in range(BeamTest.nlines-1):
            # ax1.plot(X[i,:],offset[i,:])
            ax1.plot(db(DATA[0,:]),db(DATA[i+1,:]),'+')
            ax1.plot([0, 1], [0, 1], transform=ax1.transAxes,ls='--',c='black')
            # l,r=xlim()
            # t,b=ylim()
            plt.xlim(-120,-30)
            plt.ylim(-120,-30)
            ax1.set_xlabel('Reference Power [dB]')
            ax1.set_ylabel('Power (dB)')
            ax1.set_aspect('equal', adjustable='box')
            
            # ax.plot([0, 1], [0, 1], transform=ax.transAxes)
    elif BeamTest.test_type is 'R':
        tline,y=get_rep_evol(BeamTest,DATA)
        ax1.plot(tline,y)
        ax1.set_xlabel('Time [seg]')
        ax1.set_ylabel('Magnitude')
    
    fig.show()
    return fig

def get_lin_offset(data):
    off=np.zeros((data.shape[0]-1,data.shape[1]))
    for i in range(data.shape[0]-1):
        off[i,:]=db(data[i,:])-db(data[i+1,:])
    return off

def get_rep_evol(BeamTest,data):
    tline=BeamTest.calc_plane()*(1/BeamTest.meas_spd+1/BeamTest.move_spd)+BeamTest.delay
    t=np.arange(BeamTest.nlines)*tline
    n=(BeamTest.calc_Msize()-1)/2+1
    y=abs(data[:,n])
    return t,y
    
# def get_lin_curve(data):
    # d_db=db(data):
    
    

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
    
    scan.savetxt()
    
    # with open(filename,'a') as f:
        # f.write('# Antenna Name: {}\n'.format(scan.name))
        # f.write('# Frequency (GHz): {:.2f}\n'.format(scan.meas_freq))
        # f.write('# Comment: {}\n'.format(scan.comment))
        # f.write('# Plane size (mm): {:.2f}\n'.format(scan.plane_size))
        # f.write('# Sampling distance (lambda): {:.2f}\n'.format(scan.sampl_dist))
        # Configuracion instrumentos
        # f.write('# IF Freq (GHz): {:.2f}\n'.format(scan.if_freq))
        # f.write('# IF BW (Hz): {:.2f}\n'.format(scan.ifbw))
        # f.write('# Sweep Points: {:d}\n'.format(scan.sweep_points))
        # f.write('# Signal channel A?: {:d}\n'.format(scan.isAsig))
        # f.write('# Measurement Speed: {:.3f}\n'.format(scan.meas_spd))
        # f.write('# Movement Speed: {:.3f}\n'.format(scan.move_spd))
        # f.write('# Number of lines: {:d}\n'.format(N))
        # f.write('# Delay between lines {:.2f}\n'.format(delay))
        # f.write('# Wait for user: {:d}\n'.format(wait_user))
        # f.write('# x [mm] RE[] IM[]\n')
    
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