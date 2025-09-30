#!/usr/bin/env python3
"""
PIL/Pillow Performance Test
Tests image loading speed to diagnose performance issues
"""

import time
import os
from PIL import Image
import statistics

def test_pil_performance(image_dir, num_tests=10):
    """Test PIL image loading performance"""

    # Find first few image files
    image_files = []
    for file in os.listdir(image_dir):
        if file.lower().endswith(('.tif', '.tiff', '.bmp', '.png', '.jpg')):
            image_files.append(os.path.join(image_dir, file))
            if len(image_files) >= num_tests:
                break

    if not image_files:
        print(f"No image files found in {image_dir}")
        return

    print(f"Testing PIL performance with {len(image_files)} images...")
    print(f"Directory: {image_dir}")
    print("-" * 60)

    load_times = []

    # Test each file
    for i, filepath in enumerate(image_files):
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB

        # Time the image loading
        start = time.time()
        try:
            img = Image.open(filepath)
            # Force load by accessing size
            _ = img.size
            load_time = (time.time() - start) * 1000  # ms

            load_times.append(load_time)

            print(f"{i+1}. {os.path.basename(filepath)}")
            print(f"   Size: {file_size:.1f} MB")
            print(f"   Mode: {img.mode}, Dimensions: {img.size}")
            print(f"   Load time: {load_time:.1f} ms")

            if load_time > 1000:
                print(f"   ⚠️  SLOW! Over 1 second")

            img.close()

        except Exception as e:
            print(f"   Error: {e}")

        print()

    # Statistics
    if load_times:
        print("-" * 60)
        print("Statistics:")
        print(f"Average load time: {statistics.mean(load_times):.1f} ms")
        print(f"Median load time: {statistics.median(load_times):.1f} ms")
        print(f"Min load time: {min(load_times):.1f} ms")
        print(f"Max load time: {max(load_times):.1f} ms")

        slow_count = sum(1 for t in load_times if t > 1000)
        if slow_count > 0:
            print(f"\n⚠️  {slow_count}/{len(load_times)} images took over 1 second to load!")
            print("This indicates a PIL/system performance issue.")

if __name__ == "__main__":
    # Test with the same directory you're using for thumbnails
    test_dir = input("Enter image directory path (or press Enter for current): ").strip()
    if not test_dir:
        test_dir = "."

    if os.path.exists(test_dir):
        test_pil_performance(test_dir)
    else:
        print(f"Directory not found: {test_dir}")