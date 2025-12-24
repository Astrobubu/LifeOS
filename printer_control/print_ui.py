import tkinter as tk
from tkinter import scrolledtext, messagebox
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from print_text import TextPrinter, PRINTER_NAME

class PrinterUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Thermal Printer Test UI")
        self.root.geometry("700x650")
        self.root.configure(bg="#1e1e1e")

        # Title Frame
        title_frame = tk.Frame(root, bg="#1e1e1e")
        title_frame.pack(pady=10, padx=20, fill="x")

        tk.Label(title_frame, text="Title:", bg="#1e1e1e", fg="white", font=("Arial", 12)).pack(side="left", padx=5)
        self.title_entry = tk.Entry(title_frame, font=("Arial", 12), bg="#2d2d2d", fg="white", insertbackground="white")
        self.title_entry.pack(side="left", fill="x", expand=True, padx=5)

        # Content Frame
        content_frame = tk.Frame(root, bg="#1e1e1e")
        content_frame.pack(pady=10, padx=20, fill="both", expand=True)

        tk.Label(content_frame, text="Content (one line per row):", bg="#1e1e1e", fg="white", font=("Arial", 12)).pack(anchor="w", padx=5)

        self.content_text = scrolledtext.ScrolledText(
            content_frame,
            font=("Courier New", 11),
            bg="#2d2d2d",
            fg="white",
            insertbackground="white",
            height=15
        )
        self.content_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Parameters Frame
        params_frame = tk.Frame(root, bg="#1e1e1e")
        params_frame.pack(pady=10, padx=20, fill="x")

        tk.Label(params_frame, text="Rendering Parameters:", bg="#1e1e1e", fg="#FFC107", font=("Arial", 11, "bold")).pack(anchor="w", pady=5)

        params_grid = tk.Frame(params_frame, bg="#1e1e1e")
        params_grid.pack(fill="x")

        # Base Height
        tk.Label(params_grid, text="Base Height:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.base_height_entry = tk.Entry(params_grid, font=("Arial", 10), bg="#2d2d2d", fg="white", insertbackground="white", width=10)
        self.base_height_entry.insert(0, "100")
        self.base_height_entry.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(params_grid, text="(Top/bottom padding + border)", bg="#1e1e1e", fg="gray", font=("Arial", 9)).grid(row=0, column=2, sticky="w", padx=5, pady=2)

        # Title Height
        tk.Label(params_grid, text="Title Height:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.title_height_entry = tk.Entry(params_grid, font=("Arial", 10), bg="#2d2d2d", fg="white", insertbackground="white", width=10)
        self.title_height_entry.insert(0, "90")
        self.title_height_entry.grid(row=1, column=1, padx=5, pady=2)
        tk.Label(params_grid, text="(Height allocated for title)", bg="#1e1e1e", fg="gray", font=("Arial", 9)).grid(row=1, column=2, sticky="w", padx=5, pady=2)

        # Line Height
        tk.Label(params_grid, text="Line Height:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.line_height_entry = tk.Entry(params_grid, font=("Arial", 10), bg="#2d2d2d", fg="white", insertbackground="white", width=10)
        self.line_height_entry.insert(0, "55")
        self.line_height_entry.grid(row=2, column=1, padx=5, pady=2)
        tk.Label(params_grid, text="(Height per line of content)", bg="#1e1e1e", fg="gray", font=("Arial", 9)).grid(row=2, column=2, sticky="w", padx=5, pady=2)

        # Min Height
        tk.Label(params_grid, text="Min Height:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.min_height_entry = tk.Entry(params_grid, font=("Arial", 10), bg="#2d2d2d", fg="white", insertbackground="white", width=10)
        self.min_height_entry.insert(0, "250")
        self.min_height_entry.grid(row=3, column=1, padx=5, pady=2)
        tk.Label(params_grid, text="(Minimum total height)", bg="#1e1e1e", fg="gray", font=("Arial", 9)).grid(row=3, column=2, sticky="w", padx=5, pady=2)

        # Buttons Frame
        button_frame = tk.Frame(root, bg="#1e1e1e")
        button_frame.pack(pady=10, padx=20, fill="x")

        self.print_btn = tk.Button(
            button_frame,
            text="🖨️ PRINT",
            command=self.print_content,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 14, "bold"),
            cursor="hand2",
            height=2
        )
        self.print_btn.pack(side="left", fill="x", expand=True, padx=5)

        self.clear_btn = tk.Button(
            button_frame,
            text="Clear",
            command=self.clear_content,
            bg="#f44336",
            fg="white",
            font=("Arial", 12),
            cursor="hand2",
            height=2
        )
        self.clear_btn.pack(side="left", fill="x", expand=True, padx=5)

        # Quick presets
        preset_frame = tk.Frame(root, bg="#1e1e1e")
        preset_frame.pack(pady=5, padx=20, fill="x")

        tk.Label(preset_frame, text="Quick Presets:", bg="#1e1e1e", fg="white", font=("Arial", 10)).pack(side="left", padx=5)

        tk.Button(
            preset_frame,
            text="Mic",
            command=self.load_mic_preset,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10),
            cursor="hand2"
        ).pack(side="left", padx=2)

        tk.Button(
            preset_frame,
            text="Amp",
            command=self.load_amp_preset,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10),
            cursor="hand2"
        ).pack(side="left", padx=2)

        # Status Label
        self.status_label = tk.Label(root, text="Ready", bg="#1e1e1e", fg="#4CAF50", font=("Arial", 10))
        self.status_label.pack(pady=5)

    def load_mic_preset(self):
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, "Microphone")

        self.content_text.delete("1.0", tk.END)
        mic_content = """SD  -> IO2
VDD -> 3V
GND -> GND
WS  -> IO42
SCK -> IO41
L/R -> empty"""
        self.content_text.insert("1.0", mic_content)
        self.status_label.config(text="Loaded Microphone Preset", fg="#FFC107")

    def load_amp_preset(self):
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, "Amplifier")

        self.content_text.delete("1.0", tk.END)
        amp_content = """Vin  -> 5V
GND  -> GND
SD   -> empty
GAIN -> empty
DIN  -> IO6
BCLK -> IO7
LRC  -> IO5"""
        self.content_text.insert("1.0", amp_content)
        self.status_label.config(text="Loaded Amplifier Preset", fg="#FFC107")

    def clear_content(self):
        self.title_entry.delete(0, tk.END)
        self.content_text.delete("1.0", tk.END)
        self.status_label.config(text="Cleared", fg="#FFC107")

    def print_content(self):
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", tk.END).strip()

        if not content:
            messagebox.showwarning("Empty Content", "Please enter some content to print!")
            return

        # Split content into lines
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        if not lines:
            messagebox.showwarning("Empty Content", "Please enter some content to print!")
            return

        # Get parameters
        try:
            base_height = int(self.base_height_entry.get())
            title_height = int(self.title_height_entry.get())
            line_height = int(self.line_height_entry.get())
            min_height = int(self.min_height_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Parameters", "Please enter valid numbers for the parameters!")
            return

        try:
            self.status_label.config(text="Printing...", fg="#FFC107")
            self.print_btn.config(state="disabled")
            self.root.update()

            # Print with custom parameters
            printer = TextPrinter(PRINTER_NAME)
            self.print_with_custom_params(printer, lines, title, base_height, title_height, line_height, min_height)

            self.status_label.config(text="Print Complete!", fg="#4CAF50")
            messagebox.showinfo("Success", "Print job sent successfully!")

        except Exception as e:
            self.status_label.config(text="Print Failed", fg="#f44336")
            messagebox.showerror("Print Error", f"Failed to print:\n{str(e)}")

        finally:
            self.print_btn.config(state="normal")

    def print_with_custom_params(self, printer, lines, title, base_height, title_height, line_height, min_height):
        """Print with custom rendering parameters"""
        from text_renderer import generate_text_image
        from image_utils import pil_image_to_tspl
        from PIL import Image

        # Temporarily modify the renderer
        import text_renderer

        # Generate image with custom params
        if isinstance(lines, str):
            lines = lines.split('\n')
        lines = [line for line in lines if line.strip()]

        # Calculate height
        total_height = base_height + (title_height if title else 0) + (len(lines) * line_height)
        total_height = max(total_height, min_height)

        # Manually build HTML
        import os
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template_text.html")
        with open(template_path, "r", encoding="utf-8") as f:
            html_template = f.read()

        title_html = ""
        if title:
            title_html = f'<div class="title">{title}</div>'

        lines_html = ""
        for line in lines:
            lines_html += f'            <div class="line">{line}</div>\n'

        html = html_template.format(
            height=total_height,
            title_html=title_html,
            lines_html=lines_html
        )

        from html2image import Html2Image
        hti = Html2Image(output_path=".")
        img_path = "custom_render.png"
        hti.screenshot(html_str=html, save_as=img_path, size=(456, total_height))

        # Convert and print
        with Image.open(img_path) as img:
            img_width, img_height = img.size
            print(f"DEBUG: Custom Image Size: {img_width}x{img_height}")

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

        print(f"Custom params: base={base_height}, title={title_height}, line={line_height}, min={min_height}")
        print(f"Calculated total height: {total_height}px")
        print(f"Label size: 57mm x {label_height_mm}mm")
        printer.send_raw_bytes(full_command)

if __name__ == "__main__":
    root = tk.Tk()
    app = PrinterUI(root)
    root.mainloop()
