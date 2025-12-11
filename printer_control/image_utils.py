from PIL import Image, ImageOps
import struct

def pil_image_to_tspl(image_path, x, y):
    """
    Converts an image file to a TSPL BITMAP command.
    """
    # Open and convert to 1-bit monochrome
    img = Image.open(image_path)
    img = img.convert("1")  # Convert to 1-bit pixels, black and white
    
    # Invert image because TSPL usually expects 1=Black, 0=White? 
    # Actually, standard 1-bit bitmaps: 0=Black, 1=White usually.
    # But usually printers print '1's.
    # Let's test standard. If it comes out inverted, we flip it.
    # For many thermal printers: 1 bit = dot burned (black).
    # PIL '1' mode: 0=Black, 1=White.
    # So we might need to invert it so 1=Black.
    
    # Let's ensure 1=Black (Dot) for the printer.
    # In PIL '1' mode, usually 255 (white) becomes 1 and 0 (black) becomes 0.
    # If the printer expects 1 to print, we need to invert.
    
    # However, `ImageOps.invert` only works on RGB/L. 
    # For '1' mode:
    # img = ImageOps.invert(img.convert('L')).convert('1')
    
    width, height = img.size
    width_bytes = (width + 7) // 8
    
    # Get raw bytes
    # We need to construct the rows.
    # PIL tobytes() for mode '1' packs pixels.
    # We need to check if the packing matches TSPL (MSB first vs LSB first).
    # Usually TSPL is Big Endian (MSB first). PIL '1' is also MSB first.
    
    # For TSPL BITMAP:
    # Usually 0 = White (No Dot), 1 = Black (Burn Dot).
    # PIL '1' Mode: 0 = Black, 1 = White.
    # So:
    # PIL Black (0) -> Need 1 (Burn)
    # PIL White (1) -> Need 0 (No Burn)
    #
    # PREVIOUSLY we did: b ^ 0xFF.
    # If PIL White is 1 (00000001?), actually PIL packs pixels.
    # 
    # Let's try standard inversion: ImageOps.invert for 'L' mode before converting to '1'.
    
    # Revert to standard PIL '1' conversion without pre-inversion.
    # If the previous attempt (white background -> 0s) still printed black,
    # then the printer treats 0 as Black(Burn).
    
    # Let's go back to basics:
    # PIL '1' mode: White=1, Black=0.
    # If we want White Background (No Burn), we need to send 0s (if printer treats 0 as No Burn).
    # If printer treats 1 as Burn (Black), then White(1) needs to become 0.
    # So we invert: 1 -> 0.
    
    # BUT, if the previous code (ImageOps.invert) made Background Black(0) -> Text White(1) -> 
    # And we converted that to '1' mode.
    # Background=0.
    # And it printed BLACK.
    # This means the printer treats 0 as BURN (Black).
    
    # So:
    # We want Background to be White (No Burn).
    # Since 0 = Burn, we need to send 1s for the background.
    
    # PIL '1' mode default: White pixels are 1.
    # So if we just take the bytes directly, White Background = 1s.
    # If printer treats 0 as Burn, then 1s should be No Burn (White).
    
    # So, NO INVERSION of bits should be needed if 0=Burn.
    # Revert to standard PIL '1' conversion.
    # User reported "page is black.. again".
    # This implies the previous "Inversion Fix" (ImageOps.invert) made it black.
    
    img = img.convert("1")
    bitmap_data = img.tobytes()
    
    # Sending raw bytes directly.
    return (f"BITMAP {x},{y},{width_bytes},{height},0,".encode('utf-8') + bitmap_data)
