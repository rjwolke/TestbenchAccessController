import os
import json
from typing import Dict, List, Tuple
from datetime import datetime
from pathlib import Path

import psutil

from taco.DatabaseController import DatabaseController
from taco.Testbench import Testbench


class TestbenchAccessController():
    # SETTINGS_FILE = os.path.join(os.environ['LOCALAPPDATA'], '.taco')
    SETTINGS_FILE       = '.taco_settings'  # Settings file
    LOCK_UPDATE_TIMER   = 10                # Time after which lock data is refreshed
    

    def __init__(self):
        self.database: DatabaseController = None

        self.username: str = os.getlogin()      # Default Username
       
        self.testbenchJson: Path = Path()
        self.testbenches: List[Testbench] = []
        self.tb_structure = []
        
        self.lock_cache: Dict[str, Tuple[str, datetime]] = {}
        self.lock_cache_time: datetime = datetime.min
        
        self.subprocesses: Dict[int, int] = {}
        
        self.load_settings()
        
    
    @property
    def databaseFile(self) -> Path:
        try:
            return Path(self.database.dbFile)
        except AttributeError:
            return Path()
        
        
    @property            
    def lock_cache_age(self) -> int:
        return (datetime.now() - self.lock_cache_time).total_seconds()


    def set_username(self, username) -> None:
        if username:
            self.username = username
        else:
            self.username = os.getlogin()
        self.save_settings()


    def set_database(self, database) -> Tuple[bool, str]:
        if not database:
            return (False, 'No database selected')
        
        self.database = DatabaseController(database)
        for tb in self.testbenches:
            try:
                self.database.add_testbench(tb.hostname)
            except ValueError as err:
                return (False, err)

        self.save_settings()
        return (True, '')
    

    def load_testbench_JSON(self, testbenchJson: str) -> bool:
        self.testbenchJson = Path(testbenchJson)
        self.testbenches = []
        self.tb_structure = []
        try:
            with open(testbenchJson, 'r') as f:
                testbenchdata = json.load(f)
        except (FileNotFoundError, PermissionError):
            testbenchdata = {}
        
        for testbench_list in testbenchdata:
            self.tb_structure.append({})
            for hostname, data in testbench_list.items():
                self.add_testbench(hostname, data)

        self.save_settings()
        return bool(testbenchdata)


    def save_testbench_JSON(self, testbenchJson: str) -> bool:
        def serialize_testbench(id: str, children: List[str] = None) -> Dict[str,str]:
            data = {}
            tb = self.get_testbench(id)
            if tb.hostname != tb.id:
                data['hostname'] = tb.hostname
            if tb.login_name: 
                data['login_name'] = tb.login_name
            if children:
                data['children'] = {child: serialize_testbench(child) for child in children}
            return data
        
        self.testbenchJson = Path(testbenchJson)

        testbenchdata = []
        for tb_block in self.tb_structure:
            testbench_list = {}
            for id, children in tb_block.items():
                testbench_list[id] = serialize_testbench(id, children)
            testbenchdata.append(testbench_list)

        try:
            with open(testbenchJson, 'w') as f:
                json.dump(testbenchdata, f, indent=4)
        except (PermissionError):
            return False
        
        return True
        
                
    def add_testbench(self, id: str, data: dict, isChild: bool = False) -> None:
        hostname    = data.get('hostname', id)
        login_name  = data.get('login_name', '')
        self.testbenches.append(Testbench(id, hostname, login_name))
        self.lock_cache[id] = ('', datetime.now())

        if self.database is not None:
            self.database.add_testbench(hostname)

        if not isChild:
            children    = data.get('children', {})
            self.tb_structure[-1][id] = children.keys()
            for childname, childdata in children.items():
                self.add_testbench(childname, childdata, isChild = True)
            

    def get_testbench(self, id: str) -> Testbench:
        try:
            return next(testbench for testbench in self.testbenches if testbench.id == id)
        except StopIteration as err:
            raise ValueError(err)
        
        
    def update_locks(self) -> None:
        self.lock_cache_time = datetime.now()
        if self.database is None:
            return
        
        self.unlock_by_pid()
        
        hostnames = tuple(tb.hostname for tb in self.testbenches)
        lockDict = self.database.get_lock_multiple(hostnames)
        self.lock_cache.update(lockDict)

            
    def get_lock(self, id: str, forceRefresh: bool = False) -> Tuple[str, datetime]:
        if self.database is None:
            return ('', datetime.now())
        
        if not forceRefresh and self.lock_cache_age >= self.LOCK_UPDATE_TIMER:
            self.update_locks()
        
        hostname = self.get_testbench(id).hostname
        return self.lock_cache[hostname]
 
    
    def __set_lock(self, id: str, username: str) -> None:
        hostname = self.get_testbench(id).hostname
        self.lock_cache[hostname] = (username, datetime.now())
        self.database.set_lock(hostname, username)
        

    def set_lock(self, id: str) -> None:
        return self.__set_lock(id, self.username)

    
    def unset_lock(self, id: str) -> None:
        return self.__set_lock(id, '')

    
    def run_rdp(self, id: str) -> None:
        self.set_lock(id)
        pid = self.get_testbench(id).run_rdp()
        self.subprocesses[id] = pid


    def unlock_by_pid(self):
        for id, pid in self.subprocesses.items():
            if self.lock_cache[id][0] == self.username:
                if not pid in psutil.pids():
                    self.unset_lock(id)


    def load_settings(self) -> None:
        try:
            with open(self.SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except (IOError, SyntaxError):
            self.save_settings()    # Create new Settings File
            settings = {}
            
        self.set_username(settings.get('Username', ''))
        self.set_database(settings.get('Database', ''))
        self.load_testbench_JSON(settings.get('Testbenchfile', ''))


    def save_settings(self) -> None:
        settings = {}
        settings['Username']        = self.username
        settings['Testbenchfile']   = str(self.testbenchJson.absolute())
        settings['Database']        = str(self.databaseFile.absolute())
        
        with open(self.SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
