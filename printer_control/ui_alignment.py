import tkinter as tk
from tkinter import ttk
import win32print
import threading

# --- DEFAULTS ---
DEFAULT_PRINTER = "TSC DA200"
DEF_X = 0
DEF_Y = 50
DEF_WIDTH = 57
DEF_HEIGHT = 58
DEF_SPEED = 1
DEF_DENSITY = 8
DEF_BACKFEED_VAL = 120
DEF_BACKFEED_ON = False  # Start OFF for safety

class TSCPrinter:
    def __init__(self, printer_name):
        self.printer_name = printer_name

    def send_command(self, tspl_command):
        try:
            hPrinter = win32print.OpenPrinter(self.printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("TSC_Ultimate_Tool", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    if isinstance(tspl_command, str):
                        tspl_command = tspl_command.encode('utf-8')
                    win32print.WritePrinter(hPrinter, tspl_command)
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
            return True
        except Exception as e:
            print(f"Print Error: {e}")
            return False

class UltimatePrinterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TSC DA200 Ultimate Control Panel")
        self.root.geometry("600x650")
        
        self.printer = TSCPrinter(DEFAULT_PRINTER)
        
        # --- UI Styles ---
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#333")
        
        # --- Layout Frames ---
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(main_frame, text="Printer Settings & Calibration", style="Header.TLabel").pack(pady=(0, 20))

        # --- GRID SETTINGS ---
        
        # Row 1: Dimensions
        row1 = ttk.Frame(main_frame)
        row1.pack(fill=tk.X, pady=5)
        self.width_var = self.create_input(row1, "Label Width (mm):", DEF_WIDTH, 0)
        self.height_var = self.create_input(row1, "Label Height (mm):", DEF_HEIGHT, 1)

        # Row 2: Offsets
        row2 = ttk.Frame(main_frame)
        row2.pack(fill=tk.X, pady=5)
        self.x_var = self.create_input(row2, "X Offset (dots):", DEF_X, 0)
        self.y_var = self.create_input(row2, "Y Offset (dots):", DEF_Y, 1)

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # --- QUALITY SETTINGS ---
        
        # Speed
        q_frame = ttk.Frame(main_frame)
        q_frame.pack(fill=tk.X, pady=5)
        ttk.Label(q_frame, text="Print Speed (1-4):", style="Bold.TLabel").pack(anchor=tk.W)
        self.speed_var = tk.IntVar(value=DEF_SPEED)
        speed_scale = tk.Scale(q_frame, from_=1, to=4, orient=tk.HORIZONTAL, variable=self.speed_var, showvalue=1)
        speed_scale.pack(fill=tk.X)

        # Density
        d_frame = ttk.Frame(main_frame)
        d_frame.pack(fill=tk.X, pady=10)
        ttk.Label(d_frame, text="Print Density (0-15):", style="Bold.TLabel").pack(anchor=tk.W)
        self.density_var = tk.IntVar(value=DEF_DENSITY)
        density_scale = tk.Scale(d_frame, from_=0, to=15, orient=tk.HORIZONTAL, variable=self.density_var, showvalue=1)
        density_scale.pack(fill=tk.X)

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # --- MEDIA HANDLING ---
        
        m_frame = ttk.Frame(main_frame)
        m_frame.pack(fill=tk.X, pady=5)
        
        # Backfeed Toggle
        self.backfeed_enabled = tk.BooleanVar(value=DEF_BACKFEED_ON)
        bf_check = ttk.Checkbutton(m_frame, text="Enable Backfeed (Pull Back)", variable=self.backfeed_enabled, command=self.toggle_backfeed)
        bf_check.pack(anchor=tk.W)

        # Backfeed Slider
        self.bf_frame = ttk.Frame(main_frame)
        self.bf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.bf_frame, text="Backfeed Distance (dots):").pack(anchor=tk.W)
        self.backfeed_val = tk.IntVar(value=DEF_BACKFEED_VAL)
        self.bf_scale = tk.Scale(self.bf_frame, from_=0, to=1000, orient=tk.HORIZONTAL, variable=self.backfeed_val, showvalue=1)
        self.bf_scale.pack(fill=tk.X)
        
        if not DEF_BACKFEED_ON:
            self.bf_frame.pack_forget() # Hide initially if off

        # --- ACTION BUTTONS ---
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=30)
        
        self.print_btn = tk.Button(btn_frame, text="PRINT TEST GRID", bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), height=2, command=self.run_print)
        self.print_btn.pack(fill=tk.X)
        
        self.status_lbl = ttk.Label(main_frame, text="Ready", foreground="#555")
        self.status_lbl.pack(pady=10)

    def create_input(self, parent, label_text, default_val, col):
        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Label(frame, text=label_text).pack(anchor=tk.W)
        var = tk.IntVar(value=default_val)
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(fill=tk.X)
        return var

    def toggle_backfeed(self):
        if self.backfeed_enabled.get():
            self.bf_frame.pack(fill=tk.X, pady=5, after=self.print_btn.master) # Should place it correctly
            # Actually easier to just repack in order or not hide, but enable/disable
            self.bf_scale.config(state=tk.NORMAL)
        else:
            self.bf_scale.config(state=tk.DISABLED)

    def run_print(self):
        # Gather all values
        width = self.width_var.get()
        height = self.height_var.get()
        x_off = self.x_var.get()
        y_off = self.y_var.get()
        speed = self.speed_var.get()
        density = self.density_var.get()
        use_backfeed = self.backfeed_enabled.get()
        bf_dist = self.backfeed_val.get()

        self.status_lbl.config(text="Sending print job...", foreground="blue")
        self.root.update()

        threading.Thread(target=self._send_print_job, args=(width, height, x_off, y_off, speed, density, use_backfeed, bf_dist)).start()

    def _send_print_job(self, w, h, x, y, spd, den, use_bf, bf_dist):
        # Construct TSPL Command
        # 1. Setup
        cmd = f"SIZE {w} mm, {h} mm\r\n"
        cmd += "GAP 0,0\r\n"
        cmd += "DIRECTION 1\r\n"
        cmd += f"SPEED {spd}\r\n"
        cmd += f"DENSITY {den}\r\n"
        
        if use_bf:
            # If backfeed is enabled, we usually DON'T want 'SET TEAR OFF' because that disables it.
            # OR we want 'SET TEAR ON'.
            # Actually, BACKFEED command works regardless usually, BUT 'SET TEAR OFF' might disable auto-backfeed.
            cmd += "SET TEAR ON\r\n" 
        else:
            cmd += "SET TEAR OFF\r\n" # Disable auto mechanics
            
        cmd += f"REFERENCE {x},{y}\r\n"
        cmd += "CLS\r\n"
        
        # 2. Content (The Alignment Grid Box)
        # Using a simple box drawing for instant feedback without image generation overhead
        box_w = 440
        box_h = 380
        center_x = box_w // 2
        center_y = box_h // 2
        
        cmd += f"BOX 0,0,{box_w},{box_h},4\r\n"
        cmd += f"BAR {center_x},0,2,{box_h}\r\n"
        cmd += f"BAR 0,{center_y},{box_w},2\r\n"
        cmd += f'TEXT 10,10,"ROMAN.TTF",0,12,12,"X:{x} Y:{y}"\r\n'
        cmd += f'TEXT 10,40,"ROMAN.TTF",0,10,10,"S:{spd} D:{den}"\r\n'
        
        # 3. End / Cut / Backfeed
        cmd += "PRINT 1\r\n"
        cmd += "CUT 1\r\n"
        
        if use_bf:
            cmd += f"BACKFEED {bf_dist}\r\n"

        success = self.printer.send_command(cmd)
        
        if success:
            self.root.after(0, lambda: self.status_lbl.config(text="Print Sent Successfully!", foreground="green"))
        else:
            self.root.after(0, lambda: self.status_lbl.config(text="Print Failed.", foreground="red"))

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimatePrinterApp(root)
    root.mainloop()
