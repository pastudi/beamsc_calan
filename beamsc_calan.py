#!/usr/bin/env python

#from vv_calan import vv_calan
#import corr
from __future__ import print_function
import pyvisa as visa
import numpy as np
# from datetime import datetime
# from os import path,mkdir
# import socket
import time
# from math import ceil
# import pathlib2 as pathlib
from visa_inst import Visa_inst, VNA
from beamsc import BeamScanner
from beammeas import BeamMeasurement

# class VVM:
    # def __init__(self,ip='192.169.1.10',bofname='vv_casper.bof',valon_freq=1080):
        # self.ip=ip
        # self.bofname=bofname
        # self.valon_freq=valon_freq
    
    # def connect(self):
        # self.resource=corr.katcp_wrapper.FpgaClient(self.ip)
        # self.resource.listbof()
    
        

IP_VNA=         '192.168.1.30'
IP_RF_SOURCE=   '192.168.1.36'
IP_BEAM_XY=     '192.168.1.62'
IP_BEAM_ANGLE=  '192.168.1.62'
IP_LO_SOURCE=   '192.168.1.31'     # Agilent

vna=VNA(IP_VNA)
rf_source=Visa_inst(IP_RF_SOURCE)
lo_source=Visa_inst(IP_LO_SOURCE)
beam_xy=BeamScanner(IP_BEAM_XY,'move x,y')
scan=BeamMeasurement()

def main():
    
      # Measurement parameters
    #meas_start=datetime.now()
    #file_tstamp=meas_start.strftime("%Y%m%d_%H%M%S")
    
    scan.meas_freq=296 #GHz
    #scan.name='untitled';
    scan.antenna_aperture=35#mm
    scan.distance=50 #mm
    scan.avg_points=0
    scan.sampl_dist=0.48 #lambda
    scan.plane_size=10 #70 mm
    scan.meas_cut=False
    scan.xcut=True
    filepath='/home/pablo/DATA/beamscanner/'
    logpath='./'
    
    scan.if_freq=.050  # GHz
    scan.ifbw=40 # Hz
    scan.sweep_points=scan.calc_Msize()
    scan.isAsig=True
    scan.rf_power=3.0 #dBm
    scan.lo_power=11.37 #dBm
    
    scan.meas_spd=1   #mm/s
    scan.move_spd=5     #mm/s
    
    scan.name=raw_input('Enter antenna name (no spaces or special characters): ') or 'test'
    scan.comment=raw_input('Enter comments: ')
    
    scan.savetxt(filepath)
    
    try:
        print('CONNECTING...')
        print('VNA...',end=' ')
        vna.connect()
        print('OK')
        
        print('RF Source...',end=' ')
        rf_source.connect()
        print('OK')
        
        print('LO Source...',end=' ')
        lo_source.connect()
        print('OK')
        
        print('Beam XY...',end=' ')
        beam_xy.connect()
        print('OK')
    except:
        pass
    beam_xy.set_speed(scan.move_spd,'x')
    beam_xy.set_speed(scan.move_spd,'y')
    beam_xy.move_absolute(0,0)
        
    rf_source.write('FREQ:MULT 1')
    rf_source.write('FREQ {:.9f} GHz; *OPC?'.format(scan.meas_freq/18.0))
    
    lo_source.query('FREQ:MULT 48; *OPC?')
    lo_source.query('FREQ {:.9f} GHz; *OPC?'.format(scan.meas_freq-scan.if_freq))
    
    Npoints=scan.calc_Msize()
    Nstep=Npoints-1
        
    tmeas_est=scan.calc_plane()/scan.meas_spd
    
    
    print("Estimated time [s]: {:.3f}".format(tmeas_est))
    
    vna.set_meas(scan)
    
    tmeas_act=float(vna.query('SENSE1:SWE:TIME?'))
    
    print("Actual time [s]: {:.3f}".format(tmeas_act))
    
    if tmeas_est>tmeas_act:  # Privilegiar medidas lentas
        vna.write('SENSE1:SWE:TIME {:.3f}'.format(tmeas_est))
        tmeas_act=float(vna.query('SENSE1:SWE:TIME?'))
        print("New actual time [s]: {:.6f}".format(tmeas_act))
    elif tmeas_est<tmeas_act:
        scan.meas_spd=scan.calc_plane/tmeas_act
        beam_xy.set_speed(scan.meas_spd)
        print("New speed: {:.3f}".format(beam_xy.get_speed('x')))
    
    data_comp=np.zeros(Npoints**2,dtype=complex)
    data_re=np.zeros(Npoints**2)
    data_im=np.zeros(Npoints**2)
    data_mag=np.zeros(Npoints**2)
    data_phase=np.zeros(Npoints**2)
    
    save_buffer=np.zeros((Npoints,4))
    
    x=np.arange(-Nstep/2,Nstep/2+1)*scan.calc_step()
    y=x
    
    # Measurement loop
    
    beam_xy.flush()
    for i in range(Npoints):  # start new row
        
        beam_xy.set_speed(scan.move_spd,'x')
        
        # Move to current row
        
        print ("Moving to start:\t{:.3f}, {:.3f}...".format(x[0],y[i]), end='\t')
        beam_xy.move_absolute(x[0],y[i])
        print("Stop")
        beam_xy.set_speed(scan.meas_spd,'x')
        
        # Start moving + isntrument measurement
        
        print("Moving to end:\t{:.3f}, {:.3f}...".format(x[Npoints-1],y[i]), end='\t')
        beam_xy.move_absolute_trigger(x[Npoints-1],y[i])
        print("Stop")
        
        # Ensure that VNA is ready to read memory
        
        if vna.ready(tmeas_act*1.1):
            print("VNA ready")
        else:
            raise Exception("VNA sweep timeout")
        
        # Read data from VNA
        
        data_re[i*Npoints:(i+1)*Npoints]=vna.get_data('re')
        data_im[i*Npoints:(i+1)*Npoints]=vna.get_data('im')
        
        #Data for plotting
        
        data_comp[i*Npoints:(i+1)*Npoints].real=data_re[i*Npoints:(i+1)*Npoints]
        data_comp[i*Npoints:(i+1)*Npoints].imag=data_im[i*Npoints:(i+1)*Npoints]
        
        #data_mag=abs(data_comp)
        #data_phase=np.angle(data_comp)
        
        # Buffering row data to save to disk
        
        save_buffer[:,0]=x
        save_buffer[:,1]=np.ones(Npoints)*y[i]
        save_buffer[:,2]=data_re[i*Npoints:(i+1)*Npoints]
        save_buffer[:,3]=data_im[i*Npoints:(i+1)*Npoints]
            
        if not scan.meas_cut:
            with open(filepath+scan.get_filepath(),'ab') as f:
                np.savetxt(f,save_buffer)
            save_buffer=np.zeros((Npoints,4))

def exit_clean():
    try:
        beam_xy.close_all()
        vna.close()
        lo_source.close()
        rf_source.close()
    except VI_ERROR_TMO:
        print('Timeout while closing')
        pass
    exit(0)

if __name__ == "__main__":
    print('Entered main')
    try:
        main()
    except KeyboardInterrupt:
        exit_clean()
    except:
        exit_clean()
        raise
    print('Measurement Done')
    exit_clean()