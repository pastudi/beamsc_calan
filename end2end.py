#!/usr/bin/env python

#from vv_calan import vv_calan
#import corr
from __future__ import print_function
import pyvisa as visa
import numpy as np
import time
from sys import exit
from visa_inst import Visa_inst, VNA
import traceback as tr
from datetime import datetime

savepath='/home/pablo/DATA/end2end/'

IP_VNA=         '192.168.1.30'

vna=VNA(IP_VNA)
n_sweep=20001

def set_meas(VNA):
    global n_sweep
    precision=12;
    # n_sweep=20001
    start=60.008
    stop=start
    bw=1000
    n_avg=0
    
    VNA.write('SYST:FPReset')
    VNA.write('DISPlay:WINDow1:STATE ON')
    
    VNA.write('CALCULATE1:PARAMETER:DEFINE:EXTENDED \'DATOS_Are\',\'A,0\'')
    VNA.write('CALCULATE1:PARAMETER:DEFINE:EXTENDED \'DATOS_Aim\',\'A,0\'')
    VNA.write('CALCULATE1:PARAMETER:DEFINE:EXTENDED \'DATOS_Bre\',\'B,0\'')
    VNA.write('CALCULATE1:PARAMETER:DEFINE:EXTENDED \'DATOS_Bim\',\'B,0\'')
    
    VNA.write('DISPLAY:WINDOW1:TRACE1:FEED \'DATOS_Are\' ')
    VNA.write('CALCULATE1:PARAMETER:SELECT \'DATOS_Are\' ')
    VNA.write('CALCULATE1:FORMAT REAL')
    
    VNA.write('DISPLAY:WINDOW1:TRACE2:FEED \'DATOS_Aim\' ')
    VNA.write('CALCULATE1:PARAMETER:SELECT \'DATOS_Aim\' ')
    VNA.write('CALCULATE1:FORMAT IMAG')
    
    VNA.write('DISPLAY:WINDOW1:TRACE3:FEED \'DATOS_Bre\' ')
    VNA.write('CALCULATE1:PARAMETER:SELECT \'DATOS_Bre\' ')
    VNA.write('CALCULATE1:FORMAT REAL')
    
    VNA.write('DISPLAY:WINDOW1:TRACE4:FEED \'DATOS_Bim\' ')
    VNA.write('CALCULATE1:PARAMETER:SELECT \'DATOS_Bim\' ')
    VNA.write('CALCULATE1:FORMAT IMAG')
    
    VNA.query('SENS1:SWE:TYPE CW; *OPC?;')
    
     
    VNA.query('SENS1:FREQ:FIX {:.12f} MHz; *OPC?;'.format(start))
    VNA.query('SENSE1:SWEEP:POINTS {:.12f}; *OPC?; '.format(n_sweep))
    VNA.write('SENSE1:BWID {:.12f} Hz '.format(bw))
    VNA.query('SENSE1:SWE:TIME MIN; *OPC?')

    VNA.write('SENS:AVER OFF')
        
    VNA.write('INIT:CONT OFF')

    VNA.write('*CLS')
    
def exit_clean():
    try:
        # beam_xy.close_all()
        vna.close()
        # lo_source.close()
        # rf_source.close()
    except visa.VisaIOError as e:
        print('exit_clean(): {}'.format(e))
        tr.print_exc()
        pass
    except IOError as e:
        print('exit_clean(): {}'.format(e))
        tr.print_exc()
        pass
    except Exception as e:
        print('exit_clean(): {}'.format(e))
        tr.print_exc()
        pass
    finally:
        print('Program Exit')
        exit(0)
    
def main():
    global n_sweep
    try:
        print('CONNECTING...')
        print('VNA...',end=' ')
        vna.connect()
        print('OK')
    except:
        print('main: Error conecting')
        pass
    
    filename=datetime.now().strftime("%Y%m%d_%H%M%S")
    
    set_meas(vna)
    
    time.sleep(1)
    
    save_buffer=np.zeros((n_sweep,4))
    
    vna.write('*CLS')
    
    while True:
    
        vna.trigger()
    
        if vna.ready(60):
            print("VNA ready")
        else:
            print('main: VNA sweep timeout')
            raise Exception("VNA sweep timeout")
        
        try:
            vna_Are=vna.get_data('Are')
            vna_Aim=vna.get_data('Aim')
            vna_Bre=vna.get_data('Bre')
            vna_Bim=vna.get_data('Bim')
        except visa.VisaIOError, e:
            print('main(): {}'.format(e))
            tr.print_exc()
            pass
        
        save_buffer[:,0]=vna_Are
        save_buffer[:,1]=vna_Aim
        save_buffer[:,2]=vna_Bre
        save_buffer[:,3]=vna_Bim
        
        with open(savepath+filename,'ab') as f:
            np.savetxt(f,save_buffer)
        save_buffer=np.zeros((n_sweep,4))

if __name__=="__main__":
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