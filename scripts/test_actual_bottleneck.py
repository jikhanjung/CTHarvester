#!/usr/bin/env python3
"""
Test to find the actual bottleneck in CTHarvester
Simulates the exact same operations
"""

import time
import numpy as np
from PIL import Image
import os

def test_full_process(file1_path, file2_path, output_path):
    """Simulate exact CTHarvester thumbnail generation"""

    total_start = time.time()

    # Step 1: Open images (like CTHarvester)
    print("Step 1: Opening images with PIL")
    open_start = time.time()
    img1 = Image.open(file1_path)
    open1_time = (time.time() - open_start) * 1000
    print(f"  img1 open: {open1_time:.1f}ms")

    open_start = time.time()
    img2 = Image.open(file2_path)
    open2_time = (time.time() - open_start) * 1000
    print(f"  img2 open: {open2_time:.1f}ms")

    # Step 2: Convert to numpy arrays (the suspected bottleneck)
    print("\nStep 2: Converting to numpy arrays")
    convert_start = time.time()
    arr1 = np.array(img1, dtype=np.uint16)
    convert1_time = (time.time() - convert_start) * 1000
    print(f"  arr1 = np.array(img1): {convert1_time:.1f}ms")

    convert_start = time.time()
    arr2 = np.array(img2, dtype=np.uint16)
    convert2_time = (time.time() - convert_start) * 1000
    print(f"  arr2 = np.array(img2): {convert2_time:.1f}ms")

    # Step 3: Average arrays
    print("\nStep 3: Averaging arrays")
    avg_start = time.time()
    avg_arr = ((arr1.astype(np.uint32) + arr2.astype(np.uint32)) // 2).astype(np.uint16)
    avg_time = (time.time() - avg_start) * 1000
    print(f"  Average time: {avg_time:.1f}ms")

    # Step 4: Downscale 2x2
    print("\nStep 4: Downscaling")
    downscale_start = time.time()
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
    downscale_time = (time.time() - downscale_start) * 1000
    print(f"  Downscale time: {downscale_time:.1f}ms")
    print(f"  Output shape: {downscaled.shape}")

    # Step 5: Create PIL image and save
    print("\nStep 5: Creating and saving PNG")
    create_start = time.time()
    new_img = Image.fromarray(downscaled, mode='I;16')
    create_time = (time.time() - create_start) * 1000
    print(f"  Image.fromarray time: {create_time:.1f}ms")

    save_start = time.time()
    new_img.save(output_path)
    save_time = (time.time() - save_start) * 1000
    print(f"  Save PNG time: {save_time:.1f}ms")

    total_time = (time.time() - total_start) * 1000

    print("\n" + "="*50)
    print("Summary:")
    print(f"  Open images: {open1_time + open2_time:.1f}ms")
    print(f"  Convert to numpy: {convert1_time + convert2_time:.1f}ms")
    print(f"  Process (avg+resize): {avg_time + downscale_time:.1f}ms")
    print(f"  Save PNG: {create_time + save_time:.1f}ms")
    print(f"  TOTAL: {total_time:.1f}ms")

    # Test multiple runs to check for consistency
    print("\n" + "="*50)
    print("Testing 5 consecutive runs (convert to numpy only):")
    for i in range(5):
        img_test = Image.open(file1_path)
        start = time.time()
        arr_test = np.array(img_test, dtype=np.uint16)
        elapsed = (time.time() - start) * 1000
        print(f"  Run {i+1}: {elapsed:.1f}ms")
        img_test.close()

if __name__ == "__main__":
    test_dir = "D:\\Lichas_tif"
    file1 = os.path.join(test_dir, "Lichas0000.tif")
    file2 = os.path.join(test_dir, "Lichas0001.tif")
    output = "test_thumbnail.png"

    if os.path.exists(file1) and os.path.exists(file2):
        test_full_process(file1, file2, output)
        print(f"\nOutput saved as: {output}")
    else:
        print(f"Files not found in {test_dir}")