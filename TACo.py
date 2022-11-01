from datetime import datetime
from typing import List, Tuple
from lib.Controller import DataBaseController
from lib.Testbench import Testbench


class TestbenchAccessController():
    def __init__(self, database: str):
        self.testbenches: List[Testbench] = []
        self.tb_structure = []
        self.set_database(database)


    def set_database(self, database) -> Tuple[bool, str]:
        self.databaseController = DataBaseController(database)
        for tb in self.testbenches:
            try:
                self.get_lock(tb.name)
            except ValueError as err:
                return (False, err)
            
        return (True, '')


    def load_testbench_JSON(self, testbenchJson: str):
        self.testbenches = []
        self.tb_structure = []
        with open(testbenchJson, 'r') as f:
            json = f.read()
        
        for testbench_list in eval(json):
            self.tb_structure.append({})
            
            for hostname, data in testbench_list.items():
                self.add_testbench(hostname, data)
           
                
    def add_testbench(self, name: str, data: dict, list_index: int = -1, isChild: bool = False) -> None:
        hostname    = data.get('hostname', '')
        login_name  = data.get('login_name', '')
        self.testbenches.append(Testbench(name, hostname, login_name))
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
        try:
            return self.databaseController.get_lock(name)
        except ValueError:
            self.databaseController.add_testbench(name)
            return ('', datetime.now())
 
    
    def set_lock(self, name: str, lockedBy: str) -> None:
        self.databaseController.set_lock(name, lockedBy)

    
    def is_locked(self, name: str) -> bool:
        return bool(self.get_lock(name)[0])
    

    def unset_lock(self, name: str) -> None:
        self.set_lock(name, '')
