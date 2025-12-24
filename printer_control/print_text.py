import win32print
import sys
import os

# Ensure we can import sibling scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from text_renderer import generate_text_image
from image_utils import pil_image_to_tspl
from PIL import Image

PRINTER_NAME = "TSC DA200"
X_OFFSET = 0
Y_OFFSET = 55
LABEL_WIDTH_MM = 57

class TextPrinter:
    def __init__(self, printer_name):
        self.printer_name = printer_name

    def send_raw_bytes(self, raw_data):
        try:
            hPrinter = win32print.OpenPrinter(self.printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Text_Print_Job", None, "RAW"))
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

    def print_long_text(self, text: str, title: str = ""):
        """
        Print text on the thermal printer.
        
        Args:
            text: Raw text content. Newlines preserved, auto-wraps long lines.
            title: Optional title header
        """
        print("Generating image...")
        img_path = generate_text_image(text, title)

        # Get the actual image dimensions
        with Image.open(img_path) as img:
            img_width, img_height = img.size
            print(f"Image: {img_width}x{img_height}")

        # Calculate label height in mm from actual image (8 dots per mm at 203 DPI)
        # Dynamic size with comfortable margin
        label_height_mm = int(img_height / 8) + 8  # 8mm padding for clean cut

        print("Converting to TSPL...")
        bitmap_cmd = pil_image_to_tspl(img_path, 0, 0)

        setup_cmd = (
            f"SIZE {LABEL_WIDTH_MM} mm, {label_height_mm} mm\r\n"
            "GAP 0,0\r\n"
            "DIRECTION 1\r\n"
            "SET TEAR ON\r\n"
            "SPEED 2\r\n"
            "DENSITY 14\r\n"
            f"REFERENCE {X_OFFSET},{Y_OFFSET}\r\n"
            "CLS\r\n"
        ).encode('utf-8')

        end_cmd = b"\r\nPRINT 1\r\nCUT 1\r\nBACKFEED 180\r\n"
        full_command = setup_cmd + bitmap_cmd + end_cmd

        print(f"Sending to {self.printer_name} ({label_height_mm}mm)...")
        self.send_raw_bytes(full_command)
        print("Done.")


def print_long_text(text: str, title: str = ""):
    """Convenience function to print text without instantiating the class."""
    printer = TextPrinter(PRINTER_NAME)
    printer.print_long_text(text, title)


if __name__ == "__main__":
    # Test with natural text
    test_text = """This is a test of the new text printer.
    
It handles newlines properly.
And auto-wraps long lines automatically without any stupid manual splitting."""
    
    print_long_text(test_text, "Test Print")
