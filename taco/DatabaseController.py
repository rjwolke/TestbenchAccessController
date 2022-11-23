import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple


class DatabaseController():
    def __init__(self, databaseFile : str) -> None:
        """Initializes the sqlite connection and creates the required table.

        Args:
            databaseFile (str): Path to the database file.
        """
        self.dbFile     = os.path.abspath(databaseFile)
        self.connection = sqlite3.connect(self.dbFile, 
                                          detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.cursor     = self.connection.cursor()
        
        self.create_testbench_table(False)
        
        
    def create_testbench_table(self, forceRecreate: bool = False) -> None:
        """Creates the table "Testbenches".

        Args:
            forceRecreate (bool, optional): Drops the table before creating it. Defaults to False.
        """
        
        table = """CREATE TABLE IF NOT EXISTS Testbenches (
            Name VARCHAR(255) NOT NULL UNIQUE,
            Locked_By CHAR(255),
            Locked_Since TIMESTAMP)
        """
        if forceRecreate:
            self.cursor.execute("DROP TABLE IF EXISTS Testbenches")
            
        self.cursor.execute(table)
        self.connection.commit()
        
        
    def add_testbench(self, hostname: str) -> None:
        """Adds the specified testbench to the table "Testbenches" in the database. The lock data is empty with a timestamp of now().

        Args:
            hostname (str): Hostname of the testbench.

        Raises:
            ValueError: Raised if the table "Testbenches" deviates from the required format.
        """
        try:
            self.cursor.execute("INSERT INTO Testbenches VALUES (?, '', ?)", (hostname, datetime.now()))
        except sqlite3.IntegrityError:
            # Testbench already exists
            return
        except sqlite3.OperationalError as err:
            # Malformed Database
            raise ValueError(err)
        
        self.connection.commit()
        

    def get_lock(self, hostname: str) -> Tuple[str, datetime]:
        """_summary_

        Args:
            hostname (str): hostname of the computer

        Raises:
            ValueError: Raised if the specified hostname is not found in the database

        Returns:
            Tuple[str, datetime]: tuple of locked_by, locked_since
        """
        self.cursor.execute("SELECT Locked_By, Locked_Since FROM Testbenches WHERE Name IS ?", (hostname,))
        
        lockData = self.cursor.fetchone()
        if not lockData:
            raise ValueError(f'Testbench "{hostname}" not found in database "{self.dbFile}".')
        
        return lockData
    
    
    def get_lock_multiple(self, hostnames: Tuple[str] = ()) -> Dict[str, Tuple[str, datetime]]:
        """Get Lock Data for multiple entries in the database.

        Args:
            hostnames (List[str], optional): List of hostnames. Defaults to [], meaning all hosts found in the database.

        Raises:
            ValueError: Raised if any specified hostname is not found in the database

        Returns:
            dict[str, Tuple[str, datetime]]: dictionary linking hostnames to a tuple of locked_by, locked_since
        """
        
        query = "SELECT Name, Locked_By, Locked_Since FROM Testbenches"
        if hostnames:
            query += " WHERE Name IN ({0})".format(", ".join('?' for _ in hostnames))

        self.cursor.execute(query, hostnames)
        lockData = self.cursor.fetchall()
        
        lockDict = {}
        for hostname, lock_user, lock_time in lockData:
            lockDict[hostname] = (lock_user, lock_time)
        
        missingdata = set(hostnames) - set(lockDict.keys())
        if missingdata:
            raise ValueError(f'Testbench(es) "{list(missingdata)}" not found in database "{self.dbFile}".')
       
        return lockDict
    
    
    def set_lock(self, hostname: str, lock_user: str) -> None:
        """Sets a lock in the database for the specified host.

        Args:
            hostname (str): hostname of the computer
            lockedBy (str): name of the user assigned to the lock
        """
        self.cursor.execute("UPDATE Testbenches SET Locked_By = ?, Locked_Since = ? WHERE Name IS ?", (lock_user, datetime.now(), hostname))
        self.connection.commit()
        