import subprocess as sp
import os
import socket
from typing import Dict
from datetime import datetime


class Testbench():
    def __init__(self, id: str, hostname: str = '', login_name: str = '') -> None:
        self.id         = id
        self.hostname   = hostname if hostname else id
        self.login_name = login_name
   
        
    def __repr__(self) -> str:
        return f'{self.id} ({self.hostname})'
    

    def run_rdp(self) -> int:       
        rdp_file = self.create_rdp_file()   # Create RDP file
        process = sp.Popen(['mstsc.exe', rdp_file])   # Open Remote Desktop Connection without waiting for a return
        return process.pid
    
    
    def get_ip_address(self) -> str:
        try:
            return socket.gethostbyname(self.hostname)
        except socket.gaierror:
            return ''
    
    def create_rdp_file(self) -> str:
        rdpSettings = []
        rdpSettings.append(f'full address:s:{self.get_ip_address()}\n') # Target Computer
        rdpSettings.append(f'username:s:{self.login_name}\n')           # Login Name
        rdpSettings.append('screen mode id:i:2\n')                      # Full Screen
        rdpSettings.append('use multimon:i:0\n')                        # Single Monitor
        
        path = os.path.join(os.environ['TEMP'], f'RDP_{self.id}.rdp')
        with open(path, 'w') as rdpfile:
            rdpfile.writelines(rdpSettings)
            
        return path
    