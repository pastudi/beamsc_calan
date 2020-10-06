#from vv_calan import vv_calan
#import corr
import pyvisa as visa
import numpy as np
from datetime import datetime
from os import path,mkdir
import socket
import time, re

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
        
    def get_resp(self):
        ans="";
        while ans=="":
            ans=self.socket.recv(1024)
            time.sleep(0.1)
        print(ans)
        return ans
    
    def connect(self):
        self.socket.connect((self.ip,9988))
        self.socket.sendall(self.type)
        self.get_resp()          # get de OK from server
        self.unit_conversion=float(self.get_unit_conversion())
    
    def get_unit_conversion(self):
        self.socket.sendall('get_unit_converter \n')
        return self.get_resp()
     
    def set_origin(self):
        self.socket.sendall('set_origin \n')
        self.get_resp()
    
    def set_speed(self,speed,dir):
        self.socket.sendall('set_speed {:.3f} {}\n'.format(speed,dir))
        self.get_resp()
    
    def get_speed(self,dir):
        self.socket.sendall('get_speed {}\n'.format(dir))
        speed=float(self.get_resp())/self.unit_conversion;
        print('Speed is {:.3f} [mm/s]'.format(speed))
        return speed
    
    def move_relative(self,x,y):
        self.socket.sendall('move_relative {:.3f} {:.3f}\n'.format(x,y))
        self.get_resp()
    
    def move_absolute(self,x,y):
        self.socket.sendall('move_absolute {:.3f} {:.3f}\n'.format(x,y))
        ans=self.get_resp().strip()
        while ans!="ok":
            ans=self.get_resp().strip()
    

class VNA(Visa_inst):
    def __init__(self,ip,name='hpib7,16'):
        self.addr="TCPIP0::"+ip+"::"+name+"::INSTR"
    
    def set_meas(self,start,stop,bw,n_sweep,n_avg=0,isAsig=True):
        precision=12;
        
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
        
        self.write('SENSE1:SWEEP:POINTS {:.12f} '.format(n_sweep)) 
        self.write('SENSE1:FREQ:START {:.12f} MHz '.format(start))
        self.write('SENSE1:FREQ:STOP {:.12f} MHz '.format(stop))
        self.write('SENSE1:BWID {:.12f} Hz '.format(bw))
        
        if n_avg!=0:
            self.write('SENS:AVER ON')
            self.write('SENS:AVER:MODE POIN')
            self.write('SENSE:AVER:COUN {:d} '.format(n_avg))
        else:
            self.write('SENS:AVER OFF')
        
        self.write('TRIG:SOUR MAN')
        self.write('SENS:SWE:MODE SINGle')
    
    def get_data(self,type):
        #self.write('SENS:AVER:CLE')
        #self.write('SENSe1:SWEep:MODE GROUPS ')
        #self.write('SENSe1:SWEep:MODE GROUPS {%d}'.format(n_avg))
        
        self.query(':INITIATE:IMMEDIATE; *OPC?')
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
        DATA=self.read()
        
        return float(DATA)

class VVM:
    def __init__(self,ip='192.169.1.10',bofname='vv_casper.bof',valon_freq=1080):
        self.ip=ip
        self.bofname=bofname
        self.valon_freq=valon_freq
    
    def connect(self):
        self.resource=corr.katcp_wrapper.FpgaClient(self.ip)
        self.resource.listbof()
    
        

def main():
    meas_start=datetime.now()
    file_tstamp=meas_start.strftime("%Y%m%d_%H%M%S")
    
    meas_freq=296 #GHz
    name='untitled';
    antenna_aperture=35#mm
    distance=108 #mm
    avg_points=40
    sampl_dist=0.48 #lambda
    plane_size=35 #70 mm
    meas_cut=False
    xcut=True
    filepath='./'
    logpath='./'
    
    if_freq=.050  # GHz
    ifbw=400 # Hz
    sweep_points=1
    isAsig=True
    
    
    
    name=raw_input('Enter antenna name (no spaces or special characters): ') or 'test'
    comment=raw_input('Enter comments: ')
    
    if path.exists(filepath+name):
        mkdir(filepath+name)
        mkdir(filepath+name+'/figs')
        
    IP_VNA=         '192.168.1.30'
    IP_RF_SOURCE=   '192.168.1.36'
    IP_BEAM_XY=     '192.168.1.62'
    IP_BEAM_ANGLE=  '192.168.1.62'
    IP_LO_SOURCE=   '192.168.1.31'     # Agilent
    
    #roach=VVM()
    #roach=vv_calan.vv_calan(IP_VVM,'vv_casper.bof',1080)
    vna=VNA(IP_VNA)
    rf_source=Visa_inst(IP_RF_SOURCE)
    lo_source=Visa_inst(IP_LO_SOURCE)
    beam_xy=BeamScanner(IP_BEAM_XY,'move x,y')
    
    toLog=open(logpath+'beamscanner.log','a')
    toLog.write('%s: Started\n'%(file_tstamp))
    
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
    
    beam_xy.set_speed(5,'x')
    beam_xy.set_speed(5,'y')
    beam_xy.move_absolute(0,0)
    
    vna.set_meas(if_freq*1000,if_freq*1000,ifbw,sweep_points,avg_points,isAsig)
    
    rf_source.write('FREQ:MULT 1')
    rf_source.write('POW 6.5 dBm')
    rf_source.write('FREQ {:.9f} GHz; *OPC?'.format(meas_freq/18))
    
    lo_source.query('FREQ:MULT 48; *OPC?')
    lo_source.query('POW 6.5 dBm; *OPC?')
    lo_source.query('FREQ {:.9f} GHz; *OPC?'.format(meas_freq-if_freq))
    

if __name__ == "__main__":
    print('Entered main')
    main()
