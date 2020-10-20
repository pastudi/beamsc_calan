#!/usr/bin/env python

from __future__ import print_function
import socket
import time

class BeamScanner:
    def __init__(self,ip='192.168.1.62',type='move x,y'):
        self.socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5)
        self.ip=ip
        self.type=type
        self.unit_conversion=0
        
    def get_resp(self): # listens OK from server
        ans=""
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
        speed=float(self.query('get_speed {}'.format(dir)))/self.unit_conversion
        print('Speed is {:.3f} [mm/s]'.format(speed))
        return speed
        
    def query_moving(self):
        ans=int(self.query('query_moving'))
        #print('query_moving: {}'.format(ans))
        return ans != 0
    
    #def move_relative(self,x,y):
    #    self.query('move_relative {:.3f} {:.3f}'.format(x,y))
    
    def launch_trigger(self,niter,width):
        self.query('launch_trigger {:d} {:.3f}'.format(niter,width))
    
    def __move_listener(self):
        ans=self.query_moving()
        while ans:
            #ans=self.get_resp().strip()
            time.sleep(0.1)
            #print("move_absolute(): moving")
            ans=self.query_moving()
    
    def move_absolute(self,x,y):
        self.query('move_absolute {:.3f} {:.3f}'.format(x,y))
        self.__move_listener()
        #print("move_absolute(): ok")
        #print('ok')
        
    def move_absolute_trigger(self,x,y):
        self.query('move_absolute_trigger {:.3f} {:.3f}'.format(x,y))
        self.__move_listener()
        #print("move_absolute_trigger(): ok")