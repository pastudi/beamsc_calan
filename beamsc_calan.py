#!/usr/bin/env python

#from vv_calan import vv_calan
#import corr
from __future__ import print_function
import pyvisa as visa
import numpy as np
from datetime import datetime
from os import path,mkdir
import socket
import time, re
from math import ceil
import pathlib2 as pathlib

class Visa_inst:
    def __init__(self,ip,name='inst0'):
        self.addr="TCPIP0::"+ip+"::"+name+"::INSTR"
        
    def connect(self):
        rm=visa.ResourceManager('@py')
        self.resource=rm.open_resource(self.addr)
    
    def close(self):
        self.resource.close()
    
    def write(self,str):
        self.resource.write(str)
    
    def read(self):
        return self.resource.read();
        
    def query(self,str):
        return self.resource.query(str)
        
class BeamScanner:
    def __init__(self,ip='192.168.1.62',type='move x,y'):
        self.socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5)
        self.ip=ip
        self.type=type
        self.unit_conversion=0
        
    def get_resp(self): # listens OK from server
        ans="";
        while ans=="":
            ans=self.socket.recv(1024)
            time.sleep(0.1)
        ans=ans.rstrip()
        #print('get_resp(): {}'.format(ans))
        return ans
    
    def flush(self):
        try:
            while 1:
                ans=self.socket.recv(1024)
        except:
            return
    
    def query(self,cmd):
        tosend='{}\n'.format(cmd)
        self.socket.sendall(tosend)
        #print(tosend)
        return self.get_resp()
    
    def connect(self):
        self.socket.connect((self.ip,9988))
        self.socket.sendall(self.type)
        self.get_resp()
        #self.query(self.type)
        self.unit_conversion=float(self.get_unit_conversion())
    
    def close_all(self):
        self.socket.sendall('close_all\n')
    
    def get_unit_conversion(self):
        return self.query('get_unit_converter')

     
    def set_origin(self):
        return self.query('set_origin')
    
    def set_speed(self,speed,dir):
        return self.query('set_speed {:.3f} {}'.format(speed,dir))
    
    def get_speed(self,dir):
        speed=float(self.query('get_speed {}'.format(dir)))/self.unit_conversion;
        print('Speed is {:.3f} [mm/s]'.format(speed))
        return speed
        
    def query_moving(self):
        ans=int(self.query('query_moving'))
        #print('query_moving: {}'.format(ans))
        return ans != 0
    
    #def move_relative(self,x,y):
    #    self.query('move_relative {:.3f} {:.3f}'.format(x,y))
    
    def move_absolute(self,x,y):
        self.query('move_absolute {:.3f} {:.3f}'.format(x,y))
        #ans=" ";
        ans=self.query_moving()
        while ans:
            #ans=self.get_resp().strip()
            time.sleep(0.1)
            print("move_absolute(): moving")
            ans=self.query_moving()
        print("move_absolute(): ok")
        #print('ok')
        
    def move_absolute_trigger(self,x,y):
        self.query('move_absolute_trigger {:.3f} {:.3f}'.format(x,y))
        ans=self.query_moving()
        while ans:
            time.sleep(0.1)
            print("move_absolute_trigger(): moving")
            ans=self.query_moving()
        print("move_absolute_trigger(): ok")

class VNA(Visa_inst):
    def __init__(self,ip,name='hpib7,16'):
        self.addr="TCPIP0::"+ip+"::"+name+"::INSTR"
    
    #def set_meas(self,start,stop,bw,n_sweep,n_avg=0,isAsig=True):
    def set_meas(self,BeamMeasurement):
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
            param='\'A/B,0\''
        else:
            param='\'B/A,0\''
        
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
    
    def trigger(self):
        self.query(':INITIATE:IMMEDIATE; *OPC?')
    
    def get_data(self,type):
        #self.write('SENS:AVER:CLE')
        #self.write('SENSe1:SWEep:MODE GROUPS ')
        #self.write('SENSe1:SWEep:MODE GROUPS {%d}'.format(n_avg))
        
        #self.query(':INITIATE:IMMEDIATE; *OPC?')
        #self.write('*WAI')
        
        fmt_cmd='CALCULATE1:FORMAT ';
        if type=='re':
            fmt_cmd+='REAL'
        elif type=='im':
            fmt_cmd+='IMAG'
        else:
            print('Data type {} not valid'.format(type))
            return
        
        self.write('CALCULATE1:PARAMETER:SELECT \'DATOS_{}\' '.format(type))
        
        self.write(fmt_cmd)
        self.write('FORMAT ASCII')
        
        self.write('CALCULATE1:DATA? FDATA')
        DATA=self.resource.read_ascii_values(separator=',')
        
        return DATA 
        
    def ready(self,twait):
        #return self.query('TRIG:STAT:READ? AUX1')
        max_count=int(twait/0.1)
        #print("{:d}".format(max_count))
        count=0
        while True:
            ans=int(self.query('STAT:OPER:DEV?'))
            # print('VNA ready: {:d}'.format(ans))
            if ans == 16:
                return True
            if count > max_count:
                return False
            time.sleep(0.1)
            count+=1

class VVM:
    def __init__(self,ip='192.169.1.10',bofname='vv_casper.bof',valon_freq=1080):
        self.ip=ip
        self.bofname=bofname
        self.valon_freq=valon_freq
    
    def connect(self):
        self.resource=corr.katcp_wrapper.FpgaClient(self.ip)
        self.resource.listbof()
    
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
    scan.plane_size=35 #70 mm
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
    
    #roach=VVM()
    #roach=vv_calan.vv_calan(IP_VVM,'vv_casper.bof',1080)
    
    
    #toLog=open(logpath+'beamscanner.log','a')
    #toLog.write('%s: Started\n'%(file_tstamp))
    
    try:
        print('CONNECTING...')
        print('VNA...')
        vna.connect()
        print('OK')
        
        print('RF Source...')
        rf_source.connect()
        print('OK')
        
        print('LO Source...')
        lo_source.connect()
        print('OK')
        
        print('Beam XY...')
        beam_xy.connect()
    except:
        pass
    beam_xy.set_speed(scan.move_spd,'x')
    beam_xy.set_speed(scan.move_spd,'y')
    beam_xy.move_absolute(0,0)
        
    rf_source.write('FREQ:MULT 1')
    #rf_source.write('POW {:.2f} dBm'.format(rf_power))
    rf_source.write('FREQ {:.9f} GHz; *OPC?'.format(scan.meas_freq/18.0))
    
    lo_source.query('FREQ:MULT 48; *OPC?')
    #lo_source.query('POW {:.2f} dBm; *OPC?'.format(lo_power))
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
    
    # Measure loop
    beam_xy.flush()
    for i in range(Npoints):  # start new row
        
        beam_xy.set_speed(scan.move_spd,'x')
        
        # Move to current row
        
        print ("Moving to start: {:.3f}, {:.3f}...".format(x[0],y[i]), end='\t')
        beam_xy.move_absolute(x[0],y[i])
        print("Stop moving")
        beam_xy.set_speed(scan.meas_spd,'x')
        
        # Start moving + isntrument measurement
        
        print("Moving to end: {:.3f}, {:.3f}...".format(x[Npoints-1],y[i]))
        beam_xy.move_absolute_trigger(x[Npoints-1],y[i])
        print("Stop moving")
        
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
    
    beam_xy.close_all()
    vna.close()
    lo_source.close()
    rf_source.close()

if __name__ == "__main__":
    print('Entered main')
    try:
        main()
    except KeyboardInterrupt:
        beam_xy.close_all()
        vna.close()
        lo_source.close()
        rf_source.close()
    except:
        beam_xy.close_all()
        vna.close()
        lo_source.close()
        rf_source.close()
        raise