import win32print
import sys
import os
import time

# Ensure we can import sibling scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- Printer Settings (DO NOT MODIFY HERE, ADJUST VIA COMMAND LINE OR IN print_task.py) ---
PRINTER_NAME = "TSC DA200"
X_OFFSET = 0  # Fixed as per user's last instruction
LABEL_WIDTH_MM = 57
LABEL_HEIGHT_MM = 58 # To match your paper length, assuming 50mm content + 8mm buffer

# --- Alignment Grid Dimensions (These correspond to the HTML image size) ---
# We are expecting an image that is 440px wide and 400px tall (from task_template.html)
# 440px / 8px_per_mm = 55mm (width of content)
# 400px / 8px_per_mm = 50mm (height of content)
BOX_WIDTH_DOTS = 440
BOX_HEIGHT_DOTS = 400

class TaskPrinter:
    def __init__(self, printer_name):
        self.printer_name = printer_name

    def send_raw_bytes(self, raw_data):
        try:
            hPrinter = win32print.OpenPrinter(self.printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Y_Align_Test_Job", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, raw_data)
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
            return True
        except Exception as e:
            print(f"Error printing: {e}")
            return False

    def print_alignment_grid(self, x_ref, y_ref):
        """Prints a square grid (using the current task_template.html for content)
        to test Y alignment.
        """
        # Generate a dummy image of the task template to use as content
        # We don't care about the text, just the dimensions
        from task_renderer import generate_task_image
        img_path = generate_task_image("ALIGNMENT GRID", 2) # Temp file generated

        # Convert to TSPL BITMAP
        from image_utils import pil_image_to_tspl
        bitmap_cmd = pil_image_to_tspl(img_path, 0, 0) # Place bitmap at 0,0 relative to REFERENCE

        # Setup Command
        # The X_OFFSET and Y_OFFSET will now be controlled by REFERENCE
        setup_cmd_str = f"SIZE {LABEL_WIDTH_MM} mm, {LABEL_HEIGHT_MM} mm\r\n"
        setup_cmd_str += "GAP 0,0\r\n"
        setup_cmd_str += "DIRECTION 1\r\n"
        setup_cmd_str += "SET TEAR OFF\r\n" # Confirmed to stop backfeed
        setup_cmd_str += f"REFERENCE {x_ref},{y_ref}\r\n" # This is where X and Y are set
        setup_cmd_str += "CLS\r\n"
        
        setup_cmd = setup_cmd_str.encode('utf-8')
        
        end_cmd = b"\r\nPRINT 1\r\nCUT 1\r\n"
        
        full_command = setup_cmd + bitmap_cmd + end_cmd
        
        print(f"Sending Alignment Grid with X_OFFSET={x_ref}, Y_OFFSET={y_ref}...")
        self.send_raw_bytes(full_command)
        print("Done.")

if __name__ == "__main__":
    
    current_y = 0 # Default Y for alignment starts at 0, you'll adjust this

    if len(sys.argv) > 1:
        try:
            current_y = int(sys.argv[1])
        except ValueError:
            print("Invalid Y_OFFSET provided. Using default 0.")
            current_y = 0

    printer = TaskPrinter(PRINTER_NAME)
    printer.print_alignment_grid(X_OFFSET, current_y)
