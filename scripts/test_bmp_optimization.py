#!/usr/bin/env python3
"""
Test BMP optimization strategies
"""

import time
import numpy as np
from PIL import Image
import cv2
import os

def test_bmp_methods(file_path):
    print(f"Testing BMP loading methods for: {file_path}")
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    print(f"File size: {file_size:.1f} MB\n")

    # Method 1: PIL + np.array (current)
    print("Method 1: PIL + np.array")
    start = time.time()
    img = Image.open(file_path)
    open_time = (time.time() - start) * 1000

    start = time.time()
    arr = np.array(img)
    convert_time = (time.time() - start) * 1000
    print(f"  Image.open: {open_time:.1f}ms")
    print(f"  np.array: {convert_time:.1f}ms")
    print(f"  Total: {open_time + convert_time:.1f}ms")
    print(f"  Shape: {arr.shape}, dtype: {arr.dtype}\n")

    # Method 2: PIL getdata()
    print("Method 2: PIL getdata()")
    start = time.time()
    img = Image.open(file_path)
    open_time = (time.time() - start) * 1000

    start = time.time()
    arr = np.array(img.getdata(), dtype=np.uint8).reshape(img.size[::-1])
    convert_time = (time.time() - start) * 1000
    print(f"  Image.open: {open_time:.1f}ms")
    print(f"  getdata + reshape: {convert_time:.1f}ms")
    print(f"  Total: {open_time + convert_time:.1f}ms\n")

    # Method 3: OpenCV (if available)
    try:
        print("Method 3: OpenCV imread")
        start = time.time()
        arr = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
        total_time = (time.time() - start) * 1000
        print(f"  cv2.imread: {total_time:.1f}ms")
        print(f"  Shape: {arr.shape}, dtype: {arr.dtype}\n")
    except Exception:
        print("  OpenCV not available\n")

    # Method 4: PIL load() to force pixel access
    print("Method 4: PIL load() first")
    start = time.time()
    img = Image.open(file_path)
    open_time = (time.time() - start) * 1000

    start = time.time()
    img.load()  # Force load pixels
    load_time = (time.time() - start) * 1000

    start = time.time()
    arr = np.array(img)
    convert_time = (time.time() - start) * 1000
    print(f"  Image.open: {open_time:.1f}ms")
    print(f"  img.load(): {load_time:.1f}ms")
    print(f"  np.array: {convert_time:.1f}ms")
    print(f"  Total: {open_time + load_time + convert_time:.1f}ms\n")

if __name__ == "__main__":
    # Test with BMP file
    test_path = input("Enter BMP file path (or directory to find one): ").strip()

    if os.path.isdir(test_path):
        # Find first BMP file
        for f in os.listdir(test_path):
            if f.lower().endswith('.bmp'):
                test_path = os.path.join(test_path, f)
                break

    if os.path.exists(test_path) and test_path.lower().endswith('.bmp'):
        test_bmp_methods(test_path)
    else:
        print("No BMP file found. Testing with any image...")
        # Fallback to any image
        test_bmp_methods(test_path)