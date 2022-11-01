import subprocess as sp
import os
import socket
from typing import List


class Testbench():
    def __init__(self, name: str, hostname: str = '', login_name: str = '') -> None:
        self.name       = name
        self.hostname   = hostname if hostname else name
        self.login_name = login_name
        
        # try:
        #     self.ip_address = socket.gethostbyname(self.hostname)
        # except socket.gaierror:
        #     self.ip_address = ''
        self.ip_address = '127.0.0.1'
        
        
    def __repr__(self) -> str:
        return f'{self.name} ({self.hostname})'
       

    def run_rdp(self) -> None:       
        rdp_file = self.create_rdp_file()   # Create RDP file
        sp.Popen(['mstsc.exe', rdp_file])   # Open Remote Desktop Connection without waiting for a return
    
    
    def create_rdp_file(self) -> str:
        rdpSettings = []
        rdpSettings.append(f'full address:s:{self.ip_address}\n')   # Target Computer
        rdpSettings.append(f'username:s:{self.login_name}\n')       # Login Name
        rdpSettings.append('screen mode id:i:2\n')                  # Full Screen
        rdpSettings.append('use multimon:i:0\n')                    # Single Monitor
        
        path = os.path.join(os.environ['TEMP'], f'RDP_{self.name}.rdp')
        with open(path, 'w') as rdpfile:
            rdpfile.writelines(rdpSettings)
            
        return path