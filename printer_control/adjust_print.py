import tkinter as tk
from tkinter import messagebox
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from print_text import TextPrinter, PRINTER_NAME
from text_renderer import generate_text_image
from image_utils import pil_image_to_tspl
from PIL import Image

class PrintAdjustUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Print Settings Adjuster")
        self.root.geometry("500x600")
        self.root.configure(bg="#1e1e1e")

        tk.Label(root, text="Height Calculation Parameters", bg="#1e1e1e", fg="#FFC107", font=("Arial", 14, "bold")).pack(pady=10)

        params_frame = tk.Frame(root, bg="#1e1e1e")
        params_frame.pack(pady=10, padx=20)

        row = 0

        # Base Height (top padding)
        tk.Label(params_frame, text="Base Height (Top):", bg="#1e1e1e", fg="white", font=("Arial", 11)).grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.base_height = tk.Entry(params_frame, font=("Arial", 11), bg="#2d2d2d", fg="white", insertbackground="white", width=15)
        self.base_height.insert(0, "120")
        self.base_height.grid(row=row, column=1, pady=5, padx=5)
        tk.Label(params_frame, text="px", bg="#1e1e1e", fg="gray", font=("Arial", 10)).grid(row=row, column=2, sticky="w", padx=5)
        row += 1

        # Title Height
        tk.Label(params_frame, text="Title Height:", bg="#1e1e1e", fg="white", font=("Arial", 11)).grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.title_height = tk.Entry(params_frame, font=("Arial", 11), bg="#2d2d2d", fg="white", insertbackground="white", width=15)
        self.title_height.insert(0, "100")
        self.title_height.grid(row=row, column=1, pady=5, padx=5)
        tk.Label(params_frame, text="px", bg="#1e1e1e", fg="gray", font=("Arial", 10)).grid(row=row, column=2, sticky="w", padx=5)
        row += 1

        # Line Height
        tk.Label(params_frame, text="Line Height:", bg="#1e1e1e", fg="white", font=("Arial", 11)).grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.line_height = tk.Entry(params_frame, font=("Arial", 11), bg="#2d2d2d", fg="white", insertbackground="white", width=15)
        self.line_height.insert(0, "60")
        self.line_height.grid(row=row, column=1, pady=5, padx=5)
        tk.Label(params_frame, text="px per line", bg="#1e1e1e", fg="gray", font=("Arial", 10)).grid(row=row, column=2, sticky="w", padx=5)
        row += 1

        # Bottom Padding
        tk.Label(params_frame, text="Bottom Padding:", bg="#1e1e1e", fg="white", font=("Arial", 11)).grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.bottom_padding = tk.Entry(params_frame, font=("Arial", 11), bg="#2d2d2d", fg="white", insertbackground="white", width=15)
        self.bottom_padding.insert(0, "120")
        self.bottom_padding.grid(row=row, column=1, pady=5, padx=5)
        tk.Label(params_frame, text="px", bg="#1e1e1e", fg="gray", font=("Arial", 10)).grid(row=row, column=2, sticky="w", padx=5)
        row += 1

        # Min Height
        tk.Label(params_frame, text="Min Height:", bg="#1e1e1e", fg="white", font=("Arial", 11)).grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.min_height = tk.Entry(params_frame, font=("Arial", 11), bg="#2d2d2d", fg="white", insertbackground="white", width=15)
        self.min_height.insert(0, "400")
        self.min_height.grid(row=row, column=1, pady=5, padx=5)
        tk.Label(params_frame, text="px", bg="#1e1e1e", fg="gray", font=("Arial", 10)).grid(row=row, column=2, sticky="w", padx=5)
        row += 1

        # Separator
        tk.Frame(root, bg="gray", height=2).pack(fill="x", pady=20, padx=20)

        # Test Data Selection
        tk.Label(root, text="Test Print:", bg="#1e1e1e", fg="#FFC107", font=("Arial", 12, "bold")).pack(pady=5)

        test_frame = tk.Frame(root, bg="#1e1e1e")
        test_frame.pack(pady=10)

        tk.Button(
            test_frame,
            text="🎤 Print MIC",
            command=lambda: self.print_test("mic"),
            bg="#2196F3",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
            height=2
        ).pack(side="left", padx=10)

        tk.Button(
            test_frame,
            text="🔊 Print AMP",
            command=lambda: self.print_test("amp"),
            bg="#2196F3",
            fg="white",
            font=("Arial", 11, "bold"),
            width=15,
            height=2
        ).pack(side="left", padx=10)

        # Print Both
        tk.Button(
            root,
            text="🖨️ PRINT BOTH",
            command=self.print_both,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 13, "bold"),
            height=2
        ).pack(pady=20, padx=20, fill="x")

        # Status
        self.status = tk.Label(root, text="Ready", bg="#1e1e1e", fg="#4CAF50", font=("Arial", 11))
        self.status.pack(pady=10)

        # Info
        self.info = tk.Label(root, text="Adjust values and test print immediately", bg="#1e1e1e", fg="gray", font=("Arial", 9))
        self.info.pack(pady=5)

    def print_test(self, test_type):
        try:
            base_h = int(self.base_height.get())
            title_h = int(self.title_height.get())
            line_h = int(self.line_height.get())
            bottom_p = int(self.bottom_padding.get())
            min_h = int(self.min_height.get())

            if test_type == "mic":
                title = "Microphone"
                lines = [
                    "SD  -> IO2",
                    "VDD -> 3V",
                    "GND -> GND",
                    "WS  -> IO42",
                    "SCK -> IO41",
                    "L/R -> empty"
                ]
            else:
                title = "Amplifier"
                lines = [
                    "Vin  -> 5V",
                    "GND  -> GND",
                    "SD   -> empty",
                    "GAIN -> empty",
                    "DIN  -> IO6",
                    "BCLK -> IO7",
                    "LRC  -> IO5"
                ]

            self.status.config(text=f"Printing {test_type.upper()}...", fg="#FFC107")
            self.root.update()

            self.custom_print(lines, title, base_h, title_h, line_h, bottom_p, min_h)

            self.status.config(text=f"{test_type.upper()} Printed!", fg="#4CAF50")

        except Exception as e:
            self.status.config(text=f"Error: {str(e)}", fg="#f44336")
            messagebox.showerror("Error", str(e))

    def print_both(self):
        self.print_test("mic")
        self.print_test("amp")

    def custom_print(self, lines, title, base_height, title_height, line_height, bottom_padding, min_height):
        """Print with custom height parameters"""
        from html2image import Html2Image

        # Calculate height
        total_height = base_height + (title_height if title else 0) + (len(lines) * line_height) + bottom_padding
        total_height = max(total_height, min_height)

        # Build HTML
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template_text.html")
        with open(template_path, "r", encoding="utf-8") as f:
            html_template = f.read()

        title_html = f'<div class="title">{title}</div>' if title else ""
        lines_html = "".join([f'            <div class="line">{line}</div>\n' for line in lines])

        html = html_template.format(height=total_height, title_html=title_html, lines_html=lines_html)

        # Generate image
        hti = Html2Image(output_path=".")
        img_path = "custom_test.png"
        hti.screenshot(html_str=html, save_as=img_path, size=(456, total_height))

        # Print
        with Image.open(img_path) as img:
            img_height = img.size[1]
            print(f"Generated: {img.size[0]}x{img_height}px")

        label_height_mm = max(58, int(img_height / 8) + 10)

        bitmap_cmd = pil_image_to_tspl(img_path, 0, 0)

        setup_cmd = (
            f"SIZE 57 mm, {label_height_mm} mm\r\n"
            "GAP 0,0\r\n"
            "DIRECTION 1\r\n"
            "SET TEAR ON\r\n"
            "SPEED 2\r\n"
            "DENSITY 14\r\n"
            "REFERENCE 0,55\r\n"
            "CLS\r\n"
        ).encode('utf-8')

        end_cmd = b"\r\nPRINT 1\r\nCUT 1\r\nBACKFEED 180\r\n"
        full_command = setup_cmd + bitmap_cmd + end_cmd

        printer = TextPrinter(PRINTER_NAME)
        printer.send_raw_bytes(full_command)

        print(f"Printed! Height calc: {total_height}px -> Label: {label_height_mm}mm")

if __name__ == "__main__":
    root = tk.Tk()
    app = PrintAdjustUI(root)
    root.mainloop()
