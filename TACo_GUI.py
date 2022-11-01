import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta

from taco.Testbench import Testbench
from TACo import TestbenchAccessController


class TACo_GUI(tk.Tk):
    TREEVIEW_UPDATE_TIMER = 10000
    COLOR_TREEVIEW_ITEM_FREE = "DarkBlue"
    COLOR_TREEVIEW_ITEM_LOCKED = "Red"
    COLOR_TREEVIEW_POPUP_FREE = "DeepSkyBlue"
    COLOR_TREEVIEW_POPUP_LOCKED = "Salmon"
    
    def __init__(self):
        super().__init__()
        
        self.taco = TestbenchAccessController()
        self.user = tk.StringVar(value = self.taco.username)
        
        self.draw_GUI()
        
        # Load Database if not present
        if self.taco.databaseController is None:
            self.set_database_file()
        
        # Load Testbench Config
        if not self.taco.testbenches:
            self.load_testbench_json()

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
        filemenu.add_command(label="Load Testbench-Config", command=self.load_testbench_json)
        filemenu.add_command(label="Select Database", command=self.set_database_file)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=lambda:sys.exit(0))

        menubar.add_command(label="About")

        self.config(menu=menubar)


    def draw_userbar(self):
        frame = tk.Frame()
        
        label = tk.Label(frame, text='Username')
        entry = tk.Entry(frame, textvariable=self.user)
        entry.bind('<FocusOut>', self.set_username)
        
        label.pack(side=tk.LEFT)
        entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        frame.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)
                

    def draw_testbench_treeview(self):
        """
        Function for drawing the testbench treeview with scrollbar
        """
        style = ttk.Style()
        style.theme_use('vista')
        style.configure("Treeview", foreground=self.COLOR_TREEVIEW_ITEM_FREE)

        frame = tk.Frame(self)

        # Create Treeview
        self.tree = ttk.Treeview(frame, columns=['User'], show="tree", selectmode="browse")
        self.tree.heading("#0", text="Testbench")
        self.tree.heading("User", text="User")
        self.tree.column("#0", minwidth=80, width=180)
        self.tree.column("User", minwidth=30, width=120)
        
        self.tree.tag_configure("locked", foreground=self.COLOR_TREEVIEW_ITEM_LOCKED)

        treeScroll = ttk.Scrollbar(frame)
        treeScroll.configure(command=self.tree.yview)
        self.tree.configure(yscrollcommand=treeScroll.set)

        treeScroll.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.tree.pack(fill=tk.BOTH, expand=True)
        frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.update_testbench_treeview()


        def show_context_menu(event):
            """
            Display the context menu for the treeview item
            """
            
            # Create Menu
            self.contextmenu = tk.Menu(self, tearoff=0)
            self.contextmenu.add_command(label="Remote Desktop", command=self.run_rdp)
            self.contextmenu.add_separator()
            self.contextmenu.add_command(label="Set Lock", command=self.lock_testbench)
            self.contextmenu.add_command(label="Remove Lock", command=self.unlock_testbench)

            selected_row = self.tree.identify_row(event.y)
            try:
                self.selected_testbench = self.taco.get_testbench_by_name(selected_row)
            except ValueError:
                # Only show popup on testbenches
                return               

            self.tree.selection_set(selected_row)   # Update Selection
            self.update_testbench(self.selected_testbench.name)

            # Popup-Header
            headerlines = []
            headerlines.append(f'{self.selected_testbench.name} ({self.selected_testbench.hostname})')
            bgcolor = self.COLOR_TREEVIEW_POPUP_FREE

            lock_user, locked_since = self.taco.get_lock(self.selected_testbench.name)
            def get_lock_time_string(deltatime):
                days = deltatime.days
                hours, remainder = divmod(deltatime.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                lock_str = f'{minutes:02d}m{seconds:02d}s'
                if hours or days: lock_str = f'{hours:02d}h' + lock_str
                if days: lock_str = f'{days}d' + lock_str
                return lock_str
                
            lock_str = get_lock_time_string(datetime.now()-locked_since)        # Calculate Deltatime
            if lock_user:
                bgcolor = self.COLOR_TREEVIEW_POPUP_LOCKED                      # Set BGColor
                headerlines.append(f'Locked by {lock_user} for {lock_str}')
            else:
                headerlines.append(f'Free for {lock_str}')
                
            self.contextmenu.insert_separator(0)
            for i, line in enumerate(headerlines):
                self.contextmenu.insert_command(i, label=line, command=lambda:show_context_menu(event), background=bgcolor)


            # Post popup
            try:
                self.contextmenu.post(event.x_root, event.y_root)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.contextmenu.grab_release()
                
        def run_rdp(event):
            selected_row = self.tree.identify_row(event.y)
            try:
                self.selected_testbench = self.taco.get_testbench_by_name(selected_row)
            except ValueError:
                # Only show popup on testbenches
                return
            self.run_rdp()

        self.tree.bind("<Button-3>", show_context_menu)
        self.tree.bind("<Double-Button-1>", run_rdp)
        
        
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
        self.selected_testbench.run_rdp()

    
    def lock_testbench(self):
        self.taco.set_lock(self.selected_testbench.name)
        self.update_testbench(self.selected_testbench.name)
    

    def unlock_testbench(self):
        self.taco.unset_lock(self.selected_testbench.name)
        self.update_testbench(self.selected_testbench.name)
        
        
    def set_database_file(self):
        # Save Dialog to allow for the creation of a new Database
        dbfile = filedialog.asksaveasfilename(title='Select Database File', defaultextension='db', filetypes=[('sqlite database', '.db'), ('All Files', '*')], confirmoverwrite=False)    
        if not dbfile:
            return

        old_dbfile = self.taco.databaseFile
        result, err = self.taco.set_database(dbfile)
        if not result:
            # Revert to previous database
            messagebox.showerror('Error loading Database', f'Failed to load database located at {dbfile}: {err}')
            self.taco.set_database(old_dbfile)
            
        self.update_testbench_treeview()
            
            
    def load_testbench_json(self):
        jsonfile = filedialog.askopenfilename(title='Select Testbench Config JSON', filetypes=[('Testbench Config', '.json'), ('All Files', '*')])
        if not jsonfile: 
            return
        
        self.taco.load_testbench_JSON(jsonfile)
        self.update_testbench_treeview(clear = True)
        
        
    def set_username(self, *args):
        self.taco.set_username(self.user.get())
        self.taco.save_settings()

        
if __name__ == '__main__':
    TACo_GUI()