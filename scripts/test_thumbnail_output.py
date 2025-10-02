#!/usr/bin/env python
"""
Test to verify thumbnail output dimensions
"""

import os
import sys
from pathlib import Path

from PIL import Image


def check_thumbnail_dimensions(base_dir):
    """Check dimensions of thumbnail files"""
    thumbnail_dir = Path(base_dir) / ".thumbnail"

    if not thumbnail_dir.exists():
        print(f"No .thumbnail directory found in {base_dir}")
        return

    print(f"\nChecking thumbnails in: {thumbnail_dir}")
    print("=" * 60)

    # Check original images first
    orig_files = list(Path(base_dir).glob("*.tif")) + list(Path(base_dir).glob("*.bmp"))
    if orig_files:
        with Image.open(orig_files[0]) as first_orig:
            orig_w, orig_h = first_orig.size
            print(f"Original image size: {orig_w} x {orig_h}")
    else:
        print("No original images found")
        orig_w = orig_h = 0

    # Check each level
    for level in range(1, 10):
        level_dir = thumbnail_dir / str(level)
        if not level_dir.exists():
            break

        print(f"\n--- Level {level} ---")

        # Get first few thumbnails
        thumb_files = sorted(list(level_dir.glob("*.tif")))[:5]

        if not thumb_files:
            print("No thumbnails found")
            continue

        # Expected dimensions
        expected_w = orig_w // (2**level)
        expected_h = orig_h // (2**level)

        for thumb_file in thumb_files:
            img = Image.open(thumb_file)
            actual_w, actual_h = img.size

            # Check if dimensions are correct
            if actual_h == expected_h * 2:
                status = "❌ VERTICALLY STACKED (height doubled!)"
            elif actual_w != expected_w or actual_h != expected_h:
                status = f"❌ WRONG SIZE (expected {expected_w}x{expected_h})"
            else:
                status = "✓ OK"

            print(f"  {thumb_file.name}: {actual_w}x{actual_h} {status}")

            # If first file has problems, show pixel values to debug
            if "❌" in status and thumb_file == thumb_files[0]:
                import numpy as np

                arr = np.array(img)
                print(f"    Shape: {arr.shape}")
                print(f"    dtype: {arr.dtype}")

                # Check if top and bottom halves are different (indicates stacking)
                if arr.shape[0] > 10:
                    mid = arr.shape[0] // 2
                    top_half = arr[:mid]
                    bottom_half = arr[mid : mid * 2] if arr.shape[0] >= mid * 2 else arr[mid:]

                    if top_half.shape == bottom_half.shape:
                        diff = np.abs(top_half.astype(np.float32) - bottom_half.astype(np.float32))
                        avg_diff = np.mean(diff)
                        print(
                            f"    Average difference between top and bottom halves: {avg_diff:.2f}"
                        )
                        if avg_diff > 10:
                            print("    ⚠️  Top and bottom halves are different - likely stacked!")


def main():
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = input("Enter the directory containing CT images: ").strip()

    if not os.path.exists(base_dir):
        print(f"Directory does not exist: {base_dir}")
        return

    check_thumbnail_dimensions(base_dir)


if __name__ == "__main__":
    main()
