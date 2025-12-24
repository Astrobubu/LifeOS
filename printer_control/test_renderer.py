import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from html2image import Html2Image

class RendererTestUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Renderer Test - NO PRINTING")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e1e1e")

        # Left Panel - Parameters
        left_panel = tk.Frame(root, bg="#1e1e1e", width=400)
        left_panel.pack(side="left", fill="y", padx=10, pady=10)

        tk.Label(left_panel, text="HTML/CSS Parameters", bg="#1e1e1e", fg="#FFC107", font=("Arial", 14, "bold")).pack(pady=10)

        # Container params
        params_frame = tk.Frame(left_panel, bg="#1e1e1e")
        params_frame.pack(fill="x", padx=10)

        row = 0

        # Body width
        tk.Label(params_frame, text="Body Width:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.body_width = tk.Entry(params_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.body_width.insert(0, "456")
        self.body_width.grid(row=row, column=1, padx=5)
        row += 1

        # Container width
        tk.Label(params_frame, text="Container Width:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.container_width = tk.Entry(params_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.container_width.insert(0, "400")
        self.container_width.grid(row=row, column=1, padx=5)
        row += 1

        # Container padding
        tk.Label(params_frame, text="Container Padding:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.container_padding = tk.Entry(params_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.container_padding.insert(0, "20")
        self.container_padding.grid(row=row, column=1, padx=5)
        row += 1

        # Container padding bottom
        tk.Label(params_frame, text="Padding Bottom:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.padding_bottom = tk.Entry(params_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.padding_bottom.insert(0, "30")
        self.padding_bottom.grid(row=row, column=1, padx=5)
        row += 1

        # Container margin bottom
        tk.Label(params_frame, text="Margin Bottom:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.margin_bottom = tk.Entry(params_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.margin_bottom.insert(0, "40")
        self.margin_bottom.grid(row=row, column=1, padx=5)
        row += 1

        # Border width
        tk.Label(params_frame, text="Border Width:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.border_width = tk.Entry(params_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.border_width.insert(0, "4")
        self.border_width.grid(row=row, column=1, padx=5)
        row += 1

        # Font size
        tk.Label(params_frame, text="Content Font Size:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.font_size = tk.Entry(params_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.font_size.insert(0, "28")
        self.font_size.grid(row=row, column=1, padx=5)
        row += 1

        # Line height
        tk.Label(params_frame, text="Line Height:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.line_height = tk.Entry(params_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.line_height.insert(0, "1.8")
        self.line_height.grid(row=row, column=1, padx=5)
        row += 1

        # Separator
        tk.Label(left_panel, text="", bg="#1e1e1e").pack(pady=10)
        tk.Label(left_panel, text="Height Calculation", bg="#1e1e1e", fg="#FFC107", font=("Arial", 12, "bold")).pack()

        calc_frame = tk.Frame(left_panel, bg="#1e1e1e")
        calc_frame.pack(fill="x", padx=10)

        row = 0
        tk.Label(calc_frame, text="Base Height:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.base_height = tk.Entry(calc_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.base_height.insert(0, "120")
        self.base_height.grid(row=row, column=1, padx=5)
        row += 1

        tk.Label(calc_frame, text="Title Height:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.title_height = tk.Entry(calc_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.title_height.insert(0, "100")
        self.title_height.grid(row=row, column=1, padx=5)
        row += 1

        tk.Label(calc_frame, text="Line Height (px):", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.calc_line_height = tk.Entry(calc_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.calc_line_height.insert(0, "60")
        self.calc_line_height.grid(row=row, column=1, padx=5)
        row += 1

        tk.Label(calc_frame, text="Bottom Padding:", bg="#1e1e1e", fg="white", font=("Arial", 10)).grid(row=row, column=0, sticky="w", pady=3)
        self.bottom_padding_calc = tk.Entry(calc_frame, font=("Arial", 10), bg="#2d2d2d", fg="white", width=10)
        self.bottom_padding_calc.insert(0, "120")
        self.bottom_padding_calc.grid(row=row, column=1, padx=5)
        row += 1

        # Generate button
        tk.Button(
            left_panel,
            text="GENERATE PREVIEW",
            command=self.generate_preview,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            height=2
        ).pack(pady=20, fill="x", padx=10)

        # Status
        self.status = tk.Label(left_panel, text="Ready", bg="#1e1e1e", fg="#4CAF50", font=("Arial", 10))
        self.status.pack(pady=5)

        # Right Panel - Preview
        right_panel = tk.Frame(root, bg="#2d2d2d")
        right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        tk.Label(right_panel, text="Preview (Amplifier Test)", bg="#2d2d2d", fg="white", font=("Arial", 12, "bold")).pack(pady=10)

        self.canvas = tk.Canvas(right_panel, bg="white", highlightthickness=1, highlightbackground="gray")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)

        self.photo = None

    def generate_preview(self):
        try:
            self.status.config(text="Generating...", fg="#FFC107")
            self.root.update()

            # Get all parameters
            body_w = int(self.body_width.get())
            container_w = int(self.container_width.get())
            cont_padding = int(self.container_padding.get())
            pad_bottom = int(self.padding_bottom.get())
            mar_bottom = int(self.margin_bottom.get())
            border_w = int(self.border_width.get())
            font_sz = int(self.font_size.get())
            line_h = float(self.line_height.get())

            base_h = int(self.base_height.get())
            title_h = int(self.title_height.get())
            calc_line_h = int(self.calc_line_height.get())
            bottom_pad = int(self.bottom_padding_calc.get())

            # Test data
            title = "AMPLIFIER"
            lines = [
                "Vin  -> 5V",
                "GND  -> GND",
                "SD   -> empty",
                "GAIN -> empty",
                "DIN  -> IO6",
                "BCLK -> IO7",
                "LRC  -> IO5"
            ]

            # Calculate total height
            total_height = base_h + title_h + (len(lines) * calc_line_h) + bottom_pad
            total_height = max(total_height, 400)

            # Build HTML
            html = f"""<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&display=swap" rel="stylesheet">
    <style>
        body {{
            width: {body_w}px;
            height: {total_height}px;
            background-color: white;
            margin: 0;
            padding: 0;
            font-family: 'JetBrains Mono', monospace;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            width: {container_w}px;
            display: flex;
            flex-direction: column;
            border: {border_w}px solid black;
            border-radius: 8px;
            padding: {cont_padding}px;
            padding-bottom: {pad_bottom}px;
            margin-bottom: {mar_bottom}px;
            background-color: white;
            box-sizing: border-box;
        }}
        .title {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid black;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        .content {{
            font-size: {font_sz}px;
            line-height: {line_h};
            font-weight: bold;
        }}
        .line {{
            margin: 8px 0;
            padding: 5px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="title">{title}</div>
        <div class="content">
"""
            for line in lines:
                html += f'            <div class="line">{line}</div>\n'

            html += """        </div>
    </div>
</body>
</html>"""

            # Generate image
            hti = Html2Image(output_path=".")
            img_path = "test_render.png"
            hti.screenshot(html_str=html, save_as=img_path, size=(body_w, total_height))

            # Load and display
            img = Image.open(img_path)

            # Scale to fit canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width > 1 and canvas_height > 1:
                scale = min(canvas_width / img.width, canvas_height / img.height, 1)
                new_width = int(img.width * scale)
                new_height = int(img.height * scale)
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                img_resized = img

            self.photo = ImageTk.PhotoImage(img_resized)
            self.canvas.delete("all")
            self.canvas.create_image(
                self.canvas.winfo_width()//2,
                self.canvas.winfo_height()//2,
                image=self.photo,
                anchor="center"
            )

            self.status.config(text=f"Generated! Height: {total_height}px | Image: {img.width}x{img.height}", fg="#4CAF50")

        except Exception as e:
            self.status.config(text=f"Error: {str(e)}", fg="#f44336")
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = RendererTestUI(root)
    root.mainloop()
