#!/usr/bin/env python

from __future__ import print_function
import pyvisa as visa
import time

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

class VNA(Visa_inst):
    def __init__(self,ip='192.168.1.30',name='hpib7,16'):
        self.addr="TCPIP0::"+ip+"::"+name+"::INSTR"
        
    def get_swtime1pt(self):   #Asuming previous call to set_meas()
        self.query('SENS1:SWE:POIN 1; *OPC?')
        return float(self.query('SENS1:SWE:TIME?'))
    
    def set_swpoints(self,t_line,t_sw1pt):
        # t_line=BeamMeasurement.calc_plane()/BeamMeasurement.meas_spd
        # t_swe1pt=self.get_swtime1pt()
        Np= int(t_line/t_sw1pt)+1
        self.query('SENS1:SWE:POIN {:d}; *OPC?'.format(Np))
        return Np
        
    def get_cycletime(self,BeamScanner,BeamMeasurement):
        # self.set_swpoints(BeamMeasurement)
        self.write('*CLS')
        start=time.time()   
        BeamScanner.launch_trigger(1,1000)
        if self.ready(60):
            return time.time()-start
        else:
            print('get_cycletime: Timeout')
    
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