import win32print
import sys

# ==========================================
#  PRINTER ALIGNMENT CONFIGURATION
#  Edit these values to shift your print
# ==========================================
PRINTER_NAME = "TSC DA200"

# Horizontal Start Position (X Reference)
# Increase to shift RIGHT, Decrease to shift LEFT
X_OFFSET = 10 

# Vertical Start Position (Y Reference)
# Increase to shift DOWN, Decrease to shift UP
Y_OFFSET = 50

# Label Size (Width, Height in mm)
LABEL_WIDTH_MM = 57
LABEL_HEIGHT_MM = 60

# Box Dimensions (in dots)
# 1mm approx 8 dots (203 DPI) or 12 dots (300 DPI)
# Assuming 203 DPI: 57mm is ~456 dots.
BOX_WIDTH_DOTS = 440
BOX_HEIGHT_DOTS = 400

# ==========================================

class TSCPrinter:
    def __init__(self, printer_name):
        self.printer_name = printer_name

    def send_command(self, command):
        try:
            hPrinter = win32print.OpenPrinter(self.printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("TSC_Align_Job", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    if isinstance(command, str):
                        command = command.encode('utf-8')
                    win32print.WritePrinter(hPrinter, command)
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
            return True
        except Exception as e:
            print(f"Error printing to {self.printer_name}: {e}")
            return False

    def print_alignment_grid(self, x_ref, y_ref):
        """Prints a square grid to test alignment."""
        
        # Calculate centers for the crosshairs
        center_x = BOX_WIDTH_DOTS // 2
        center_y = BOX_HEIGHT_DOTS // 2
        
        # Construct TSPL Command
        tspl_command = (
            f"SIZE {LABEL_WIDTH_MM} mm, {LABEL_HEIGHT_MM} mm\r\n"
            "GAP 0,0\r\n"
            f"REFERENCE {x_ref},{y_ref}\r\n"
            "DIRECTION 1\r\n"
            "CLS\r\n"
            # Draw Main Box
            f"BOX 0,0,{BOX_WIDTH_DOTS},{BOX_HEIGHT_DOTS},4\r\n"
            # Draw Center Vertical Bar
            f"BAR {center_x},0,2,{BOX_HEIGHT_DOTS}\r\n"
            # Draw Center Horizontal Bar
            f"BAR 0,{center_y},{BOX_WIDTH_DOTS},2\r\n"
            # Corner Labels
            'TEXT 10,10,"ROMAN.TTF",0,8,8,"TL"\r\n'
            f'TEXT {BOX_WIDTH_DOTS - 40},10,"ROMAN.TTF",0,8,8,"TR"\r\n'
            f'TEXT 10,{BOX_HEIGHT_DOTS - 40},"ROMAN.TTF",0,8,8,"BL"\r\n'
            f'TEXT {BOX_WIDTH_DOTS - 40},{BOX_HEIGHT_DOTS - 40},"ROMAN.TTF",0,8,8,"BR"\r\n'
            # Center Label
            f'TEXT {center_x - 30},{center_y - 20},"ROMAN.TTF",0,10,10,"CENTER"\r\n'
            "PRINT 1\r\n"
            "CUT 1\r\n"
        )
        
        print(f"Sending Alignment Grid to {self.printer_name}...")
        print(f"Settings -> X_OFFSET: {x_ref}, Y_OFFSET: {y_ref}")
        
        if self.send_command(tspl_command):
            print("Command sent.")
        else:
            print("Failed.")

if __name__ == "__main__":
    # Allow command line overrides: python tsc_printer.py [x_offset] [y_offset]
    
    current_x = X_OFFSET
    current_y = Y_OFFSET
    
    if len(sys.argv) > 1:
        try:
            current_x = int(sys.argv[1])
        except ValueError:
            pass
            
    if len(sys.argv) > 2:
        try:
            current_y = int(sys.argv[2])
        except ValueError:
            pass

    printer = TSCPrinter(PRINTER_NAME)
    printer.print_alignment_grid(current_x, current_y)
