from lib.Controller import DataBaseController

databaseController = DataBaseController('test.db')
databaseController.create_testbench_table(True)