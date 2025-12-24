import os
from html2image import Html2Image
from PIL import Image

def generate_text_image(text: str, title: str = "", output_path: str = "text_render.png") -> str:
    """
    Generate a print-ready image from text.
    
    Args:
        text: Raw text content. Can include newlines for explicit breaks.
              Text will auto-wrap to fit the label width.
        title: Optional title header
        output_path: Where to save the image
    
    Returns:
        Path to generated image
    """
    hti = Html2Image(output_path=".")
    
    # Escape HTML entities and convert newlines to <br>
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html_content = safe_text.replace("\n", "<br>")
    
    # Calculate approximate height
    # - Count actual line breaks
    # - Estimate wrapped lines based on ~20 chars per line at our font size
    explicit_lines = text.count("\n") + 1
    avg_chars_per_line = 20
    estimated_wrapped_lines = max(len(text) // avg_chars_per_line, explicit_lines)
    
    line_height_px = 50  # Approximate height per line
    title_height = 100 if title else 0
    padding = 100  # Top + bottom padding
    
    total_height = title_height + (estimated_wrapped_lines * line_height_px) + padding
    total_height = max(total_height, 300)  # Minimum height
    
    # Build HTML with proper word-wrap
    title_html = f'<div class="title">{title}</div>' if title else ''
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            width: 456px;
            min-height: {total_height}px;
            background: white;
            font-family: 'JetBrains Mono', monospace;
            padding: 25px;
        }}
        .container {{
            border: 4px solid black;
            border-radius: 10px;
            padding: 20px;
            width: 100%;
        }}
        .title {{
            font-size: 24px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 3px solid black;
            padding-bottom: 12px;
            margin-bottom: 15px;
            text-align: center;
        }}
        .content {{
            font-size: 28px;
            font-weight: 500;
            line-height: 1.4;
            word-wrap: break-word;
            overflow-wrap: break-word;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="container">
        {title_html}
        <div class="content">{html_content}</div>
    </div>
</body>
</html>'''
    
    # Generate screenshot with larger height initially
    hti.screenshot(html_str=html, save_as=output_path, size=(456, total_height + 200))
    
    # Crop to actual content - find where content ends
    with Image.open(output_path) as img:
        # Convert to grayscale for easier analysis
        gray = img.convert('L')
        pixels = gray.load()
        
        # Scan from bottom up to find last non-white row
        content_bottom = img.height
        for y in range(img.height - 1, 0, -1):
            row_has_content = False
            for x in range(img.width):
                if pixels[x, y] < 250:  # Not white
                    row_has_content = True
                    break
            if row_has_content:
                content_bottom = y + 25  # Add small padding
                break
        
        # Crop and save
        content_bottom = min(content_bottom, img.height)
        cropped = img.crop((0, 0, 456, content_bottom))
        cropped.save(output_path)
        actual_height = cropped.height
    
    print(f"📄 Text: {len(text)} chars → {actual_height}px")
    return output_path


if __name__ == "__main__":
    # Test with various inputs
    test1 = "This is a simple single line"
    test2 = "Line one\nLine two\nLine three"
    test3 = "This is a much longer piece of text that should automatically wrap to multiple lines without any manual intervention because the CSS handles it properly."
    
    generate_text_image(test1, "Short", "test1.png")
    generate_text_image(test2, "Multi-line", "test2.png")
    generate_text_image(test3, "Auto-wrap", "test3.png")
    print("Tests complete!")
