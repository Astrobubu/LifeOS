import os
from html2image import Html2Image
from PIL import Image

def generate_task_image(task_text, importance_level, style="handwritten", output_path="task_render.png"):
    """
    Generates an image from HTML/CSS for a task using a template file.
    style: "handwritten" or "urgent"
    """
    hti = Html2Image(output_path=".")
    
    # Determine Emojis
    emoji_str = "⚡" * importance_level
    
    # Select Template
    if style == "urgent":
        template_filename = "template_urgent.html"
    else:
        template_filename = "template_handwritten.html"
        
    # Read the HTML template
    template_path = os.path.join(os.path.dirname(__file__), template_filename)
    with open(template_path, "r", encoding="utf-8") as f:
        html_template = f.read()

    # Populate the template with actual values (template now has correctly escaped CSS braces)
    html = html_template.format(emoji_str=emoji_str, task_text=task_text)
    
    print("\n--- DEBUG: Final HTML String to be Rendered ---\n")
    print(html)
    print("\n----------------------------------------------\n")
    
    img_path = "temp_render.png"
    
    # Adjust HTML body height to match screenshot height
    # html = html.replace('height: 490px;', 'height: 400px;') # DISABLED dynamic replacement
    # html = html.replace('height: 470px;', 'height: 380px;') # DISABLED dynamic replacement
    
    # 3. Screenshot with the desired height
    hti.screenshot(html_str=html, save_as=output_path, size=(456, 490)) # Capture 490px tall image
    
    # Post-process: specific resize/crop if needed
    return output_path

if __name__ == "__main__":
    generate_task_image("Buy Groceries and clean the house", 3)
