#!/usr/bin/env python3
"""
Test PIL's native 16-bit image handling vs NumPy conversion
"""

import time
import numpy as np
from PIL import Image, ImageChops
import os

def test_methods(file1_path, file2_path):
    print(f"Testing with:\n  {file1_path}\n  {file2_path}\n")

    # Method 1: PIL native operations (if supported)
    print("Method 1: PIL native ImageChops")
    try:
        start = time.time()
        img1 = Image.open(file1_path)
        img2 = Image.open(file2_path)
        load_time = (time.time() - start) * 1000
        print(f"  Load time: {load_time:.1f}ms")

        start = time.time()
        # Try ImageChops.add on 16-bit images
        result = ImageChops.add(img1, img2, scale=2.0)
        avg_time = (time.time() - start) * 1000
        print(f"  ImageChops.add time: {avg_time:.1f}ms")

        start = time.time()
        result = result.resize((img1.width // 2, img1.height // 2))
        resize_time = (time.time() - start) * 1000
        print(f"  Resize time: {resize_time:.1f}ms")

        print(f"  Total: {load_time + avg_time + resize_time:.1f}ms")
        print(f"  Result mode: {result.mode}, size: {result.size}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\nMethod 2: NumPy conversion")
    try:
        start = time.time()
        img1 = Image.open(file1_path)
        img2 = Image.open(file2_path)
        load_time = (time.time() - start) * 1000
        print(f"  Load time: {load_time:.1f}ms")

        start = time.time()
        arr1 = np.array(img1, dtype=np.uint16)
        arr2 = np.array(img2, dtype=np.uint16)
        convert_time = (time.time() - start) * 1000
        print(f"  Convert to numpy time: {convert_time:.1f}ms")

        start = time.time()
        avg_arr = ((arr1.astype(np.uint32) + arr2.astype(np.uint32)) // 2).astype(np.uint16)
        avg_time = (time.time() - start) * 1000
        print(f"  NumPy average time: {avg_time:.1f}ms")

        start = time.time()
        h, w = avg_arr.shape
        new_h, new_w = h // 2, w // 2
        avg_arr_32 = avg_arr.astype(np.uint32)
        downscaled = (
            avg_arr_32[0:2*new_h:2, 0:2*new_w:2] +
            avg_arr_32[0:2*new_h:2, 1:2*new_w:2] +
            avg_arr_32[1:2*new_h:2, 0:2*new_w:2] +
            avg_arr_32[1:2*new_h:2, 1:2*new_w:2]
        ) // 4
        downscaled = downscaled.astype(np.uint16)
        resize_time = (time.time() - start) * 1000
        print(f"  NumPy resize time: {resize_time:.1f}ms")

        print(f"  Total: {load_time + convert_time + avg_time + resize_time:.1f}ms")
    except Exception as e:
        print(f"  Error: {e}")

    # Method 3: Try using PIL blend
    print("\nMethod 3: PIL Image.blend")
    try:
        start = time.time()
        img1 = Image.open(file1_path)
        img2 = Image.open(file2_path)
        load_time = (time.time() - start) * 1000
        print(f"  Load time: {load_time:.1f}ms")

        start = time.time()
        result = Image.blend(img1, img2, 0.5)
        blend_time = (time.time() - start) * 1000
        print(f"  Blend time: {blend_time:.1f}ms")

        start = time.time()
        result = result.resize((img1.width // 2, img1.height // 2))
        resize_time = (time.time() - start) * 1000
        print(f"  Resize time: {resize_time:.1f}ms")

        print(f"  Total: {load_time + blend_time + resize_time:.1f}ms")
        print(f"  Result mode: {result.mode}, size: {result.size}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    # Test with actual TIFF files
    test_dir = input("Enter directory with TIFF files (or press Enter for D:\\Lichas_tif): ").strip()
    if not test_dir:
        test_dir = "D:\\Lichas_tif"

    file1 = os.path.join(test_dir, "Lichas0000.tif")
    file2 = os.path.join(test_dir, "Lichas0001.tif")

    if os.path.exists(file1) and os.path.exists(file2):
        test_methods(file1, file2)
    else:
        print(f"Files not found in {test_dir}")