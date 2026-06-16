import os
import math
from pathlib import Path
from PIL import Image

# Increase max image pixels to avoid DecompressionBombError for large WSIs
Image.MAX_IMAGE_PIXELS = None

def get_level_sizes(width: int, height: int):
    """
    Generate DZI level sizes.
    Level 0 is 1x1. Level N is the full image.
    """
    sizes = []
    w, h = width, height
    while w > 1 or h > 1:
        sizes.append((w, h))
        w = int(math.ceil(w / 2.0))
        h = int(math.ceil(h / 2.0))
    sizes.append((1, 1))
    sizes.reverse()
    return sizes

def generate_deepzoom_from_image(
    image_path: Path | str,
    output_dir: Path | str,
    tile_size: int = 256,
    overlap: int = 1,
    fmt: str = "jpg"
) -> dict:
    """
    Generates a static Deep Zoom Image (DZI) pyramid for a given image.
    Outputs:
      output_dir/<visual_name>.dzi
      output_dir/<visual_name>_files/<level>/<col>_<row>.<fmt>
    """
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
        
    img_name = image_path.stem
    
    output_dir.mkdir(parents=True, exist_ok=True)
    dzi_path = output_dir / f"{img_name}.dzi"
    files_dir = output_dir / f"{img_name}_files"
    files_dir.mkdir(exist_ok=True)
    
    with Image.open(image_path) as img:
        width, height = img.size
        
        sizes = get_level_sizes(width, height)
        max_level = len(sizes) - 1
        
        # Write DZI XML
        dzi_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<Image TileSize="{tile_size}" Overlap="{overlap}" Format="{fmt}" xmlns="http://schemas.microsoft.com/deepzoom/2008">
    <Size Width="{width}" Height="{height}"/>
</Image>
"""
        dzi_path.write_text(dzi_xml)
        
        # Prepare format arguments
        save_kwargs = {}
        if fmt.lower() in ("jpg", "jpeg"):
            save_kwargs["quality"] = 85
            
        # Build pyramid top-down to optimize resizing
        # Instead of resizing from original every time, resize from the previous level
        current_img = img
        if current_img.mode in ('RGBA', 'P') and fmt.lower() in ("jpg", "jpeg"):
            current_img = current_img.convert('RGB')
            
        for level in range(max_level, -1, -1):
            lw, lh = sizes[level]
            
            level_dir = files_dir / str(level)
            level_dir.mkdir(exist_ok=True)
            
            # If not the max level, downscale from the previous current_img
            if level < max_level:
                current_img = current_img.resize((lw, lh), Image.Resampling.LANCZOS)
                
            cols = int(math.ceil(lw / tile_size))
            rows = int(math.ceil(lh / tile_size))
            
            for row in range(rows):
                for col in range(cols):
                    # Calculate tile bounds with overlap
                    x1 = col * tile_size - (overlap if col > 0 else 0)
                    y1 = row * tile_size - (overlap if row > 0 else 0)
                    x2 = (col + 1) * tile_size + (overlap if col < cols - 1 else 0)
                    y2 = (row + 1) * tile_size + (overlap if row < rows - 1 else 0)
                    
                    # Clamp to image boundaries
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(lw, x2)
                    y2 = min(lh, y2)
                    
                    tile = current_img.crop((x1, y1, x2, y2))
                    tile_path = level_dir / f"{col}_{row}.{fmt}"
                    tile.save(tile_path, **save_kwargs)

    return {
        "dzi_path": str(dzi_path),
        "tiles_dir": str(files_dir),
        "width": width,
        "height": height,
        "tile_size": tile_size,
        "overlap": overlap
    }
