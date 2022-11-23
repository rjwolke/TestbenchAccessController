import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font
from datetime import datetime, timedelta
import webbrowser

from taco.Testbench import Testbench
from TACo import TestbenchAccessController


class TACo_GUI(tk.Tk):
    TREEVIEW_UPDATE_TIMER = 2000
    COLOR_TREEVIEW_ITEM_FREE = "DarkBlue"
    COLOR_TREEVIEW_ITEM_LOCKED = "Red"
    COLOR_TREEVIEW_POPUP_FREE = "DeepSkyBlue"
    COLOR_TREEVIEW_POPUP_LOCKED = "Salmon"
    
    def __init__(self):
        super().__init__()
        
        self.taco = TestbenchAccessController()
        self.user = tk.StringVar(value = self.taco.username)

        self.selected_testbench: Testbench = None
        self.images = {}
        
        self.draw_GUI()
        
        # Load Database if not present
        if self.taco.database is None:
            self.set_database_file()
        
        # Load Testbench Config
        if not self.taco.testbenches:
            self.load_testbench_json()

        self.mainloop()


    def draw_GUI(self):
        self.title("TACo")
        self.iconphoto(True, tk.PhotoImage(file='./icons/taco_16px.png'))
        self.minsize(200, 400)
        self.draw_main_menu()
        self.draw_userbar()
        self.draw_testbench_treeview()


    def draw_main_menu(self):
        self.menubar = tk.Menu(self)
        self.menubar.icon_add_testbench = tk.PhotoImage(file = 'icons/computer_add.png')
        self.menubar.icon_load_config   = tk.PhotoImage(file = 'icons/table_go.png')
        self.menubar.icon_save_config   = tk.PhotoImage(file = 'icons/table_save.png')
        self.menubar.icon_database      = tk.PhotoImage(file = 'icons/database_connect.png')
        filemenu = tk.Menu(self.menubar, tearoff=False)
        
        self.menubar.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label= "Add Testbench", 
                             image= self.menubar.icon_add_testbench, 
                             compound=tk.LEFT,
                             command=self.add_testbench)
        filemenu.add_command(label= "Load Testbench List", 
                             image= self.menubar.icon_load_config, 
                             compound=tk.LEFT,
                             command=self.load_testbench_json)
        filemenu.add_command(label= "Save Testbench List", 
                             image= self.menubar.icon_save_config, 
                             compound=tk.LEFT,
                             command=self.save_testbench_json)
        filemenu.add_separator()
        filemenu.add_command(label="Select Database", 
                             image=self.menubar.icon_database, 
                             compound = tk.LEFT, 
                             command=self.set_database_file)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=lambda:sys.exit(0))

        self.menubar.add_command(label="About", command=lambda: AboutWindow(self))

        self.config(menu=self.menubar)


    def draw_userbar(self):
        frame = tk.Frame()
        
        label = ttk.Label(frame, text='Username')
        entry = ttk.Entry(frame, textvariable=self.user)
        entry.bind('<FocusOut>', self.set_username)
        
        label.pack(side=tk.LEFT)
        entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        frame.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)
                

    def draw_testbench_treeview(self):
        """
        Function for drawing the testbench treeview with scrollbar
        """
        style = ttk.Style()
        style.theme_use('xpnative')

        frame = tk.Frame(self)

        # Create Treeview
        self.tree = ttk.Treeview(frame, columns=['User'], show="tree", selectmode="browse")
        self.tree.heading("#0", text="Testbench")
        self.tree.heading("User", text="User")
        self.tree.column("#0", minwidth=80, width=180)
        self.tree.column("User", minwidth=30, width=120)
        
        self.tree.icon_free = tk.PhotoImage(file='icons/computer.png')
        self.tree.icon_locked = tk.PhotoImage(file='icons/computer_delete.png')
        self.tree.icon_error = tk.PhotoImage(file='icons/computer_error.png')
        
        self.tree.tag_configure("free", foreground=self.COLOR_TREEVIEW_ITEM_FREE, image=self.tree.icon_free)
        self.tree.tag_configure("locked", foreground=self.COLOR_TREEVIEW_ITEM_LOCKED, image=self.tree.icon_locked)
        self.tree.tag_configure("error", foreground=self.COLOR_TREEVIEW_ITEM_FREE, image=self.tree.icon_error)

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
            
            selected_row = self.tree.identify_row(event.y)
            try:
                self.selected_testbench = self.taco.get_testbench(selected_row)
            except ValueError:
                # Only show popup on testbenches
                return               

            self.tree.selection_set(selected_row)   # Update Selection
            self.update_testbench(self.selected_testbench.id, forceLockRefresh=True)
            lock_user, lock_time = self.taco.get_lock(self.selected_testbench.id)
            
            # Create Menu
            self.contextmenu = tk.Menu(self, tearoff=False)
            self.contextmenu.add_command(label="Remote Desktop", command=lambda:self.taco.run_rdp(self.selected_testbench.id))
            self.contextmenu.add_separator()
            self.contextmenu.add_command(label="Set Lock", command=self.lock_testbench)
            self.contextmenu.add_command(label="Remove Lock", command=self.unlock_testbench, state=('normal' if lock_user else 'disabled'))

            # Add Popup-Header
            headerlines = []
            headerlines.append(f'{self.selected_testbench.id} ({self.selected_testbench.hostname})')
            bgcolor = self.COLOR_TREEVIEW_POPUP_FREE

            lock_user, lock_time = self.taco.get_lock(self.selected_testbench.id)
            def get_lock_time_string(deltatime):
                days = deltatime.days
                hours, remainder = divmod(deltatime.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                lock_str = f'{minutes:02d}m{seconds:02d}s'
                if hours or days: lock_str = f'{hours:02d}h' + lock_str
                if days: lock_str = f'{days}d' + lock_str
                return lock_str
                
            lock_str = get_lock_time_string(datetime.now()-lock_time)       # Calculate Deltatime
            if lock_user:
                bgcolor = self.COLOR_TREEVIEW_POPUP_LOCKED                  # Set BGColor
                headerlines.append(f'Locked by {lock_user} for {lock_str}')
            else:
                headerlines.append(f'Free for {lock_str}')
            
            # Insert Header at top
            self.contextmenu.insert_separator(0)
            for i, line in enumerate(headerlines):
                self.contextmenu.insert_command(i, label=line, command=lambda:show_context_menu(event), background=bgcolor)

            # Post popup
            try:
                self.contextmenu.post(event.x_root, event.y_root)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self.contextmenu.grab_release()

                
        # def run_rdp(event):
        #     selected_row = self.tree.identify_row(event.y)
        #     try:
        #         self.selected_testbench = self.taco.get_testbench_by_name(selected_row)
        #     except ValueError:
        #         # Only show popup on testbenches
        #         return
        #     self.run_rdp()

        self.tree.bind("<Button-3>", show_context_menu)
        
        
    def update_testbench(self, id, parent = "", forceLockRefresh: bool = False) -> None:
        lock_user = self.taco.get_lock(id, forceRefresh=forceLockRefresh)[0]
        
        # Add Testbench to Treeview if not yet present
        if not self.tree.exists(id):
            testbench = self.taco.get_testbench(id)
            self.tree.insert(parent, tk.END, iid = id, text = str(testbench))
        
        self.tree.item(id, values=(lock_user,), tags=("locked",) if lock_user else ("free",))

    
    def update_testbench_treeview(self, clear: bool = False) -> None:
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
        self.taco.run_rdp(self.selected_testbench.id)

    
    def lock_testbench(self):
        self.taco.set_lock(self.selected_testbench.id)
        self.update_testbench(self.selected_testbench.id)
    

    def unlock_testbench(self):
        self.taco.unset_lock(self.selected_testbench.id)
        self.update_testbench(self.selected_testbench.id)
        
        
    def set_database_file(self):
        # Save Dialog to allow for the creation of a new Database
        dbfile = filedialog.asksaveasfilename(title='Select Database File', 
                                              defaultextension='db', 
                                              initialdir=self.taco.databaseFile.parent,
                                              initialfile=self.taco.databaseFile.name,
                                              filetypes=[('sqlite database', '.db'), ('All Files', '*')], confirmoverwrite=False)    
        if not dbfile:
            return

        old_dbfile = self.taco.databaseFile
        result, err = self.taco.set_database(dbfile)
        if not result:
            # Revert to previous database
            messagebox.showerror('Error loading Database', f'Failed to load database located at {dbfile}: {err}')
            self.taco.set_database(old_dbfile)
            
        self.update_testbench_treeview()
            
            
    def load_testbench_json(self) -> None:
        jsonfile = filedialog.askopenfilename(title='Load Testbench List', 
                                              initialdir=self.taco.testbenchJson.parent, 
                                              filetypes=[('Testbench Config', '.json'), ('All Files', '*')])
        if not jsonfile: 
            return
        
        self.taco.load_testbench_JSON(jsonfile)
        self.update_testbench_treeview(clear = True)


    def save_testbench_json(self) -> None:
        jsonfile = filedialog.asksaveasfilename(title='Save Testbench List', 
                                                initialdir=self.taco.testbenchJson.parent,
                                                initialfile=self.taco.testbenchJson.name,
                                                filetypes=[('Testbench Config', '.json'), ('All Files', '*')])
        if not jsonfile:
            return

        self.taco.save_testbench_JSON(jsonfile)


    def add_testbench(self): pass
        # TODO: Implement adding testbench into GUI        
        
    def set_username(self, *args):
        self.taco.set_username(self.user.get())
        self.taco.save_settings()


class AboutWindow(tk.Toplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.title("About")
        self.resizable(height = False, width = False)

        self.img_taco_large = tk.PhotoImage(file = 'icons/taco_64px.png')
        self.img_cc_by_3 = tk.PhotoImage(file = 'icons/CC_BY_icon.png')
        
        tk.Label(self, image=self.img_taco_large).pack()
        tk.Label(self, text='TestbenchAccessController (TACo)', font=font.Font(size=11, weight='bold')).pack()
        tk.Label(self, text='Copyright 2022 Robert J. Wolke, Licensed under GPLv3').pack()
        
        url = 'https://github.com/rjwolke/TestbenchAccessController'
        github_link   = tk.Label(self, text=url, fg="blue", cursor="hand2")
        github_link.bind('<Button-1>', lambda _: webbrowser.open_new_tab(url))
        github_link.pack()

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(pady=5, fill=tk.X)

        # Attributions       
        tk.Label(self, text='Attributions', font=font.Font(size=11, weight='bold')).pack(anchor=tk.W, padx=5)                
        self.creative_commons_attribution('Silk Icons', 'Mark James', 'http://www.famfamfam.com/lab/icons/silk/')
        self.creative_commons_attribution('Food, mexican, snack icon', 'Chanut is Industries', 'https://www.iconfinder.com/icons/5626998/')

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(pady=5, fill=tk.X)

        # Close Button
        closeButton = tk.Button(self, text='Close', command=lambda: self.withdraw(), width=15)
        closeButton.pack(side=tk.BOTTOM, padx=5, pady=5, anchor='se')

        
    def creative_commons_attribution(self, name, author, url) -> None:
        frame = tk.Frame(self)
        frame.columnconfigure(0, weight=1)
        frame.pack(padx=5, fill=tk.X)
        
        title = tk.Label(frame, text=f'"{name}" By {author}')
        title.grid(row=0, column=0, sticky="w")

        link = tk.Label(frame, text=url, fg="blue", cursor="hand2")
        link.bind('<Button-1>', lambda _: webbrowser.open_new_tab(url))
        link.grid(row=1, column=0, sticky="w")

        image = tk.Label(frame, image=self.img_cc_by_3, cursor="hand2")
        image.bind('<Button-1>', lambda _: webbrowser.open_new_tab('https://creativecommons.org/licenses/by/3.0/'))
        image.grid(row=0, column=1, rowspan=2, sticky="e")
        

if __name__ == '__main__':
    TACo_GUI()