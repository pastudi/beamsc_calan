#!/usr/bin/env python

#from vv_calan import vv_calan
#import corr
from __future__ import print_function
import pyvisa as visa
import numpy as np
import time
from sys import exit
from visa_inst import Visa_inst, VNA
from beamsc import BeamScanner
from beammeas import BeamMeasurement        
import traceback as tr

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
    scan.antenna_aperture=35#mm
    scan.distance=50 #mm
    scan.avg_points=0
    scan.sampl_dist=0.48 #lambda
    scan.plane_size=100 #70 mm
    scan.meas_cut=False
    scan.xcut=True
    filepath='/home/pablo/DATA/beamscanner/'
    logpath='./'
    
    scan.if_freq=.050  # GHz
    scan.ifbw=100    # Hz
    scan.sweep_points=scan.calc_Msize()
    scan.isAsig=True
    scan.rf_power=3.0 #dBm
    scan.lo_power=11.37 #dBm
    
    scan.meas_spd=5   #mm/s
    scan.move_spd=20    #mm/s
    
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
        print('main: Error conecting')
        pass
    beam_xy.set_speed(scan.move_spd,'x')
    beam_xy.set_speed(scan.move_spd,'y')
    beam_xy.move_absolute(0,0)
        
    rf_source.write('FREQ:MULT 1')
    rf_source.write('FREQ {:.9f} GHz; *OPC?'.format(scan.meas_freq/18.0))
    
    lo_source.query('FREQ:MULT 48; *OPC?')
    lo_source.query('FREQ {:.9f} GHz; *OPC?'.format(scan.meas_freq-scan.if_freq))
    
    
        
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
    
    Npoints=scan.calc_Msize()
    Nstep=Npoints-1
    
    data_comp=np.zeros(Npoints**2,dtype=complex)
    data_re=np.zeros(Npoints**2)
    data_im=np.zeros(Npoints**2)
    data_mag=np.zeros(Npoints**2)
    data_phase=np.zeros(Npoints**2)
    
    save_buffer=np.zeros((Npoints,4))
    
    x=np.arange(-Nstep/2,Nstep/2+1)*scan.calc_step()
    x=np.flip(x)
    y=x
    
    Np_vna=scan.sweep_points;
    Ns_vna=Np_vna-1
    step_vna=scan.calc_plane()/(Np_vna-1)
    x_vna=np.linspace(-0.5,0.5,Np_vna)*scan.calc_plane()
    
    data_vna=np.zeros(Npoints*Np_vna,dtype=complex)
    
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
        
        print("Moving to end:\t\t{:.3f}, {:.3f}...".format(x[Npoints-1],y[i]), end='\t')
        beam_xy.move_absolute_trigger(x[Npoints-1],y[i])
        print("Stop")
        
        # Ensure that VNA is ready to read memory
                
        if vna.ready(tline_act*1.1):
            print("VNA ready")
        else:
            print('main: VNA sweep timeout')
            raise Exception("VNA sweep timeout")
        
        # Read data from VNA
        
        try:
            vna_re=vna.get_data('re')
            vna_im=vna.get_data('im')
        except visa.VisaIOError, e:
            print('main(): {}'.format(e))
            tr.print_exc()
            pass

        data_vna[i*Np_vna:(i+1)*Np_vna].real=vna_re
        data_vna[i*Np_vna:(i+1)*Np_vna].imag=vna_im
        data_re[i*Npoints:(i+1)*Npoints]=np.interp(x,x_vna,vna_re)
        data_im[i*Npoints:(i+1)*Npoints]=np.interp(x,x_vna,vna_im)
        
        #Data for plotting
        
        # data_comp[i*Npoints:(i+1)*Npoints].real=data_re[i*Npoints:(i+1)*Npoints]
        # data_comp[i*Npoints:(i+1)*Npoints].imag=data_im[i*Npoints:(i+1)*Npoints]
        
        #data_mag=abs(data_comp)
        #data_phase=np.angle(data_comp)
        
        # Buffering row data to save to disk
        
        save_buffer[:,0]=x
        save_buffer[:,1]=np.ones(Npoints)*y[i]
        save_buffer[:,2]=data_re[i*Npoints:(i+1)*Npoints]
        save_buffer[:,3]=data_im[i*Npoints:(i+1)*Npoints]
        
        try:
            if not scan.meas_cut:
                with open(filepath+scan.get_filepath(),'ab') as f:
                    np.savetxt(f,save_buffer)
                save_buffer=np.zeros((Npoints,4))
        except Exception as e:
            print('main(): {}'.format(e))
            tr.print_exc()
    try:        
        with open(filepath+scan.get_filepath()+'_raw','ab') as f:
            np.savetxt(f,data_vna.real,data_vna.imag)
    except Exception as e:
        print('main(): {}'.format(e))
        tr.print_exc()

def exit_clean():
    try:
        beam_xy.close_all()
        vna.close()
        lo_source.close()
        rf_source.close()
    except visa.VisaIOError as e:
        print('exit_clean(): {}'.format(e))
        tr.print_exc()
        pass
    except IOError as e:
        print('exit_clean(): {}'.format(e))
        tr.print_exc()
    except Exception as e:
        print('exit_clean(): {}'.format(e))
        tr.print_exc()
    finally:
        exit()

if __name__ == "__main__":
    print('Entered main')
    try:
        main()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        exit_clean()
    except Exception as e:
        print('General error: {}'.format(e))
        tr.print_exc()
        exit_clean()
        raise e
    print('Measurement Done')
    exit_clean()
