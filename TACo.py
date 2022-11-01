from datetime import datetime
import os
from typing import List, Tuple
from taco.DatabaseController import DatabaseController
from taco.Testbench import Testbench


class TestbenchAccessController():
    # SETTINGS_FILE = os.path.join(os.environ['LOCALAPPDATA'], '.taco')
    SETTINGS_FILE = '.taco_settings'
    
    def __init__(self):
        self.username: str = os.getlogin()      # Default Username
        self.testbenchJson: str = ''
        self.testbenches: List[Testbench] = []
        self.tb_structure = []
        self.databaseController: DatabaseController = None
        
        self.load_settings()
        
    
    @property
    def databaseFile(self) -> str:
        try:
            return self.databaseController.dbFile
        except AttributeError:
            return ''
        
    
    def set_username(self, username) -> None:
        if username:
            self.username = username
        else:
            self.username = os.getlogin()
        self.save_settings()


    def set_database(self, database, create = False) -> Tuple[bool, str]:
        if not database:
            return (False, 'No database selected')
        
        self.databaseController = DatabaseController(database)
        for tb in self.testbenches:
            try:
                self.get_lock(tb.name)
            except ValueError as err:
                return (False, err)

        self.save_settings()
        return (True, '')
    

    def load_testbench_JSON(self, testbenchJson: str) -> None:
        self.testbenchJson = os.path.abspath(testbenchJson)
        self.testbenches = []
        self.tb_structure = []
        try:
            with open(testbenchJson, 'r') as f:
                json = f.read()
        except (FileNotFoundError, PermissionError):
            json = "{}"
        
        for testbench_list in eval(json):
            self.tb_structure.append({})
            for hostname, data in testbench_list.items():
                self.add_testbench(hostname, data)

        self.save_settings()
           
                
    def add_testbench(self, name: str, data: dict, list_index: int = -1, isChild: bool = False) -> None:
        hostname    = data.get('hostname', '')
        login_name  = data.get('login_name', '')
        self.testbenches.append(Testbench(name, hostname, login_name))

        if self.databaseController is not None:
            self.databaseController.add_testbench(name)

        if not isChild:
            children    = data.get('children', {})
            self.tb_structure[list_index][name] = children.keys()
            for childname, childdata in children.items():
                self.add_testbench(childname, childdata, list_index, isChild = True)
            

    def get_testbench_by_name(self, name: str) -> Testbench:
        try:
            return next(testbench for testbench in self.testbenches if testbench.name == name)
        except StopIteration as err:
            raise ValueError(err)
    

    def get_lock(self, name: str) -> Tuple[str, datetime]:
        if self.databaseController is None:
            return ('', datetime.now())
        
        try:
            return self.databaseController.get_lock(name)
        except ValueError:
            self.databaseController.add_testbench(name)
            return ('', datetime.now())
 
    
    def set_lock(self, name: str) -> None:
        self.databaseController.set_lock(name, self.username)

    
    def unset_lock(self, name: str) -> None:
        self.databaseController.set_lock(name, '')


    def load_settings(self) -> None:
        try:
            with open(self.SETTINGS_FILE, 'r') as f:
                settings = eval(f.read())
        except (IOError, SyntaxError):
            self.save_settings()    # Create new Settings File
            settings = {}
            
        self.set_username(settings.get('Username', ''))
        self.set_database(settings.get('Database', ''))
        self.load_testbench_JSON(settings.get('Testbenchfile', ''))


    def save_settings(self) -> None:
        settings = {}
        settings['Username']        = self.username
        settings['Testbenchfile']   = self.testbenchJson
        try:
            settings['Database']    = self.databaseFile
        except AttributeError:
            settings['Database']    = ''
        
        with open(self.SETTINGS_FILE, 'w') as f:
            f.write(str(settings))