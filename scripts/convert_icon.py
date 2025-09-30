#!/usr/bin/env python
"""
Convert PNG image to ICO format for Windows application icon
"""

import sys
from pathlib import Path

from PIL import Image


def convert_png_to_ico(png_path, ico_path):
    """
    Convert PNG image to ICO format

    Args:
        png_path: Path to input PNG file
        ico_path: Path to output ICO file
    """
    try:
        # Open the PNG image
        img = Image.open(png_path)

        # Convert RGBA to RGB if necessary (ICO doesn't always handle transparency well)
        if img.mode == "RGBA":
            # Create a white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Create multiple sizes for the ICO file
        # Windows typically uses these sizes
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

        # Create list of images in different sizes
        ico_images = []
        for size in sizes:
            # Create a copy and resize
            resized = img.copy()
            resized.thumbnail(size, Image.Resampling.LANCZOS)

            # Create a new image with exact size (in case aspect ratio is different)
            new_img = Image.new("RGB", size, (255, 255, 255))
            # Paste the resized image in the center
            x = (size[0] - resized.width) // 2
            y = (size[1] - resized.height) // 2
            new_img.paste(resized, (x, y))

            ico_images.append(new_img)

        # Save as ICO with all sizes
        ico_images[0].save(
            ico_path,
            format="ICO",
            sizes=[(img.width, img.height) for img in ico_images],
            append_images=ico_images[1:],
        )

        print(f"✅ Successfully converted {png_path} to {ico_path}")
        return True

    except Exception as e:
        print(f"❌ Error converting icon: {e}")
        return False


def main():
    # Default paths
    png_file = "CTHarvester_64.png"
    ico_file = "icon.ico"

    # Check if PNG exists
    if not Path(png_file).exists():
        print(f"❌ Error: {png_file} not found")
        sys.exit(1)

    # Convert
    if convert_png_to_ico(png_file, ico_file):
        print(f"✅ Icon created: {ico_file}")

        # Also create copies for other uses
        # Copy for Linux AppImage
        if Path(png_file).exists():
            Path("icon.png").write_bytes(Path(png_file).read_bytes())
            print("✅ Created icon.png for Linux builds")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
