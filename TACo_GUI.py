import json
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta

from lib.Testbench import Testbench
from TACo import TestbenchAccessController


class TACo_GUI(tk.Tk):
    TREEVIEW_UPDATE_TIMER = 10000
    COLOR_TREEVIEW_ITEM_FREE = "DarkBlue"
    COLOR_TREEVIEW_ITEM_LOCKED = "Red"
    COLOR_TREEVIEW_POPUP_FREE = "DeepSkyBlue"
    COLOR_TREEVIEW_POPUP_LOCKED = "Salmon"
    
    def __init__(self):
        super().__init__()
        
        self.taco = TestbenchAccessController("test.db")
        self.taco.load_testbench_JSON("testbenches.json")
        
        self.user = tk.StringVar(value = 'Testuser')
        
        self.draw_GUI()
        self.mainloop()


    def draw_GUI(self):
        self.title("TACo")
        self.minsize(200, 400)
        self.draw_main_menu()
        self.draw_userbar()
        self.draw_testbench_treeview()


    def draw_main_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        
        menubar.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label="Load Testbench-Config", command=self.load_json)
        filemenu.add_command(label="Set Database", command=self.set_database_file)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=lambda:sys.exit(0))

        menubar.add_command(label="About")

        self.config(menu=menubar)


    def draw_userbar(self):
        frame = tk.Frame()
        
        label = tk.Label(frame, text='Username')
        entry = tk.Entry(frame, textvariable=self.user)
        
        label.pack(side=tk.LEFT)
        entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        frame.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)
                

    def draw_testbench_treeview(self):
                
        style = ttk.Style()
        style.theme_use('vista')
        style.configure("Treeview", foreground=self.COLOR_TREEVIEW_ITEM_FREE)

        frame = tk.Frame(self)

        # Create Treeview
        treeScroll = ttk.Scrollbar(frame)
        treeScroll.pack(side=tk.RIGHT, fill=tk.BOTH)
        
        self.tree = ttk.Treeview(frame, columns=['User'], show="tree", selectmode="browse")
        self.tree.column("#0", minwidth=80, width=180)
        self.tree.heading("#0", text="Testbench")
        # self.tree.heading("Hostname", text="Hostname")
        # self.tree.column("Hostname", minwidth=30)
        self.tree.heading("User", text="User")
        self.tree.column("User", minwidth=30, width=120)
        
        self.tree.tag_configure("locked", foreground=self.COLOR_TREEVIEW_ITEM_LOCKED)

        treeScroll.configure(command=self.tree.yview)
        self.tree.configure(yscrollcommand=treeScroll.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.update_testbench_treeview()


        def show_context_menu(event):
            '''
                Display the context menu for the treeview item
            '''
            
            # Create Menu
            self.popup = tk.Menu(self, tearoff=0)
            self.popup.add_command(label="Remote Desktop", command=self.run_rdp)
            self.popup.add_separator()
            self.popup.add_command(label="Set Lock", command=self.lock_testbench)
            self.popup.add_command(label="Remove Lock", command=self.unlock_testbench)

            selected_row = self.tree.identify_row(event.y)
            try:
                self.popup.testbench = self.taco.get_testbench_by_name(selected_row)
            except ValueError:
                # Only show popup on testbenches
                return               

            self.tree.selection_set(selected_row)   # Update Selection
            self.update_testbench(self.popup.testbench.name)

            # Popup-Header
            headerlines = []
            headerlines.append(f'{self.popup.testbench.name} ({self.popup.testbench.hostname})')
            bgcolor = self.COLOR_TREEVIEW_POPUP_FREE

            lock_user, locked_since = self.taco.get_lock(self.popup.testbench.name)
            if lock_user:
                bgcolor = self.COLOR_TREEVIEW_POPUP_LOCKED                          # Set BGColor
                lock_delta = datetime.now()-locked_since                            # Calculate Deltatime
                lock_delta -= timedelta(microseconds = lock_delta.microseconds)     # Remove microseconds
                headerlines.append(f'Locked by {lock_user} since {lock_delta}')
                
            self.popup.insert_separator(0)
            for i, line in enumerate(headerlines):
                self.popup.insert_command(i, label=line, command=lambda:show_context_menu(event), background=bgcolor)

            try:
                # Post
                self.popup.post(event.x_root, event.y_root)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.popup.grab_release()

        self.tree.bind("<Button-3>", show_context_menu)
        
        
    def update_testbench(self, name, parent = ""):
        testbench = self.taco.get_testbench_by_name(name)
        lock_user = self.taco.get_lock(name)[0]
        
        # Add Testbench to Treeview if not yet present
        if not self.tree.exists(name):
            self.tree.insert(parent, tk.END, iid = name, text = str(testbench))
        
        self.tree.item(name, values=(lock_user,), tags=("locked") if lock_user else ())

    
    def update_testbench_treeview(self, clear = False):
        if clear:
            for child in self.tree.get_children():
                self.tree.delete(child)
            
        for testbench_block in self.taco.tb_structure:
            for root, children in testbench_block.items():
                self.update_testbench(root)
                for child in children:
                    self.update_testbench(child, parent = root)

        # Update-Loop
        self.after(self.TREEVIEW_UPDATE_TIMER, lambda: self.update_testbench_treeview())        
    
        
    def run_rdp(self):
        self.lock_testbench()
        self.popup.testbench.run_rdp()

    
    def lock_testbench(self):
        self.taco.set_lock(self.popup.testbench.name, self.user.get())
        self.update_testbench(self.popup.testbench.name)
    

    def unlock_testbench(self):
        self.taco.unset_lock(self.popup.testbench.name)
        self.update_testbench(self.popup.testbench.name)
        
        
    def set_database_file(self):
        dbfile = filedialog.askopenfilename(filetypes=[('sqlite database', 'db')])
        if not dbfile:
            return

        old_dbfile = self.taco.databaseController.dbFile        
        result, err = self.taco.set_database(dbfile)
        if not result:
            messagebox.showerror('Error loading Database', f'Failed to load database located at {dbfile}: {err}')
            self.taco.set_database(old_dbfile)


    def load_json(self):
        jsonfile = filedialog.askopenfilename(filetypes=[('Testbench Structure', 'json')])
        if not jsonfile:
            return
        
        self.taco.load_testbench_JSON(jsonfile)
        self.update_testbench_treeview(True)

        
if __name__ == '__main__':
    TACo_GUI()