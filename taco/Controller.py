import sqlite3
from datetime import datetime
from typing import Tuple


class DataBaseController():
    def __init__(self, databaseFile : str) -> None:
        self.dbFile     = databaseFile
        self.connection = sqlite3.connect(self.dbFile, 
                                          detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.cursor     = self.connection.cursor()
        
        
    def create_testbench_table(self, recreate = False) -> None:
        table = """ CREATE TABLE Testbenches (
                    Name VARCHAR(255) NOT NULL UNIQUE,
                    Locked_By CHAR(255),
                    Locked_Since TIMESTAMP)
        """
        if recreate:
            self.cursor.execute('DROP TABLE Testbenches')
            
        self.cursor.execute(table)
        self.connection.commit()
        
        
    def add_testbench(self, name) -> None:
        try:
            query = 'INSERT INTO Testbenches VALUES (?, "", ?)'
            self.cursor.execute(query, (name, datetime.now()))
        except sqlite3.IntegrityError:
            # Testbench already exists
            return
        except sqlite3.OperationalError as err:
            # Malformed Database
            raise ValueError(err)
        
        self.connection.commit()
        

    def get_lock(self, name: str) -> Tuple[str, datetime]:
        self.cursor.execute('SELECT Locked_By, Locked_Since FROM Testbenches WHERE Name IS ?', (name,))
        lockData = self.cursor.fetchone()
        if not lockData:
            raise ValueError(f'Testbench "{name}" not found in database "{self.dbFile}"')
        
        return lockData
    
    
    def set_lock(self, name: str, lockedBy: str) -> None:
        self.cursor.execute('UPDATE Testbenches SET Locked_By = ?, Locked_Since = ? WHERE Name IS ?', (lockedBy, datetime.now(), name))
        self.connection.commit()
        