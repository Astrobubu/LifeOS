import win32print
import sys
import os
import time

# Ensure we can import sibling scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from task_renderer import generate_task_image
from image_utils import pil_image_to_tspl

PRINTER_NAME = "TSC DA200"
X_OFFSET = 0
Y_OFFSET = 50
LABEL_WIDTH_MM = 57
LABEL_HEIGHT_MM = 58

class TaskPrinter:
    def __init__(self, printer_name):
        self.printer_name = printer_name

    def send_raw_bytes(self, raw_data):
        try:
            hPrinter = win32print.OpenPrinter(self.printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Density_Test_Job", None, "RAW"))
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

    def print_test_sample(self, description, density, speed):
        print(f"Printing: {description} (Density: {density}, Speed: {speed})...")
        
        img_path = generate_task_image(f"{description}", 2) # Use description as task text
        bitmap_cmd = pil_image_to_tspl(img_path, X_OFFSET, Y_OFFSET)
        
        # Setup Command - Simple String Concatenation
        setup_cmd_str = f"SIZE {LABEL_WIDTH_MM} mm, {LABEL_HEIGHT_MM} mm\r\n"
        setup_cmd_str += "GAP 0,0\r\n"
        setup_cmd_str += "DIRECTION 1\r\n"
        setup_cmd_str += "SET TEAR OFF\r\n"
        setup_cmd_str += f"SPEED {speed}\r\n"
        setup_cmd_str += f"DENSITY {density}\r\n"
        setup_cmd_str += "CLS\r\n"
        
        setup_cmd = setup_cmd_str.encode('utf-8')
        
        end_cmd = b"\r\nPRINT 1\r\nCUT 1\r\n"
        
        full_command = setup_cmd + bitmap_cmd + end_cmd
        self.send_raw_bytes(full_command)
        time.sleep(2) # Pause between prints

if __name__ == "__main__":
    printer = TaskPrinter(PRINTER_NAME)
    
    # Test A: Low Density
    printer.print_test_sample("DENSITY 6 SPEED 2", 6, 2)
    
    # Test B: Medium Density
    printer.print_test_sample("DENSITY 8 SPEED 2", 8, 2)
    
    # Test C: High Density
    printer.print_test_sample("DENSITY 10 SPEED 2", 10, 2)
    
    # Test D: Higher Density
    printer.print_test_sample("DENSITY 12 SPEED 2", 12, 2)
    
    # Test E: Max Density
    printer.print_test_sample("DENSITY 14 SPEED 2", 14, 2)
    
    # Test F: Fast Speed
    printer.print_test_sample("DENSITY 8 SPEED 4", 8, 4)

    print("All tests sent.")
