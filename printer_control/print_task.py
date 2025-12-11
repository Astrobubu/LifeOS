import win32print
import sys
import os

# Ensure we can import sibling scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from task_renderer import generate_task_image
from image_utils import pil_image_to_tspl

PRINTER_NAME = "TSC DA200"
X_OFFSET = 0  # Reverted to user's perfect UI setting
Y_OFFSET = 55  # Reverted to user's perfect UI setting
LABEL_WIDTH_MM = 57
LABEL_HEIGHT_MM = 58

class TaskPrinter:
    def __init__(self, printer_name):
        self.printer_name = printer_name

    def send_raw_bytes(self, raw_data):
        try:
            hPrinter = win32print.OpenPrinter(self.printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Task_Print_Job", None, "RAW"))
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

    def print_task(self, task_text, importance, style="handwritten"):
        print(f"Generating Image (Style: {style})...")
        img_path = generate_task_image(task_text, importance, style)
        
        # Verify Image Size
        from PIL import Image
        with Image.open(img_path) as img:
            print(f"DEBUG: Generated Image Size: {img.size} (Width, Height)")
        
        print("Converting to TSPL...")
        # Get the BITMAP command bytes
        # PLACE AT 0,0 because we use REFERENCE to handle the offset (matching UI logic)
        bitmap_cmd = pil_image_to_tspl(img_path, 0, 0)
        
        # Setup Command with user's perfect settings
        setup_cmd = (
            f"SIZE {LABEL_WIDTH_MM} mm, {LABEL_HEIGHT_MM} mm\r\n"
            "GAP 0,0\r\n"
            "DIRECTION 1\r\n"
            "SET TEAR ON\r\n" # Enable tear/backfeed mechanism
            f"SPEED 2\r\n"      # User-chosen speed
            f"DENSITY 14\r\n"   # User-chosen density
            f"REFERENCE {X_OFFSET},{Y_OFFSET}\r\n" # Added REFERENCE to match UI
            "CLS\r\n"
        ).encode('utf-8')
        
        # End Command with backfeed
        end_cmd = b"\r\nPRINT 1\r\nCUT 1\r\nBACKFEED 180\r\n"
        
        full_command = setup_cmd + bitmap_cmd + end_cmd
        
        print(f"Sending to {self.printer_name}...")
        self.send_raw_bytes(full_command)
        print("Done.")

if __name__ == "__main__":
    printer = TaskPrinter(PRINTER_NAME)
    
    # Default test
    task = "Complete Project Alpha"
    imp = 2
    style = "handwritten"
    
    if len(sys.argv) > 1:
        task = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            imp = int(sys.argv[2])
        except ValueError:
            # If 2nd arg is not int, maybe it's style? Assume imp=2
            style = sys.argv[2]
            
    if len(sys.argv) > 3:
        style = sys.argv[3]
        
    printer.print_task(task, imp, style)
