#!/usr/bin/env python
"""
Test script to verify that Python and Rust modules generate thumbnails with the same naming pattern.
"""

import os
import sys
from pathlib import Path


def check_thumbnail_naming(thumbnail_dir):
    """Check the naming pattern of thumbnail files in a directory."""
    if not os.path.exists(thumbnail_dir):
        print(f"Directory does not exist: {thumbnail_dir}")
        return None

    files = sorted([f for f in os.listdir(thumbnail_dir) if f.endswith(".tif")])

    if not files:
        print(f"No .tif files found in {thumbnail_dir}")
        return None

    print(f"\nFound {len(files)} files in {thumbnail_dir}")
    print("Sample filenames:")
    for i, f in enumerate(files[:5]):  # Show first 5 files
        print(f"  {i+1}. {f}")

    # Check naming pattern
    uses_rust_pattern = all(f.replace(".tif", "").isdigit() for f in files)

    if uses_rust_pattern:
        print("✓ Uses Rust naming pattern (sequential numbers like 000000.tif)")
    else:
        print("✗ Uses Python legacy naming pattern (includes prefix)")

    return uses_rust_pattern


def main():
    """Main test function."""
    print("=" * 60)
    print("Thumbnail Naming Consistency Test")
    print("=" * 60)

    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = input("Enter the directory containing CT images: ").strip()

    if not os.path.exists(base_dir):
        print(f"Error: Directory '{base_dir}' does not exist")
        return

    thumbnail_base = os.path.join(base_dir, ".thumbnail")

    if not os.path.exists(thumbnail_base):
        print(f"No .thumbnail directory found in {base_dir}")
        print("Please generate thumbnails first")
        return

    # Check all level directories
    print(f"\nChecking thumbnail directories in: {thumbnail_base}")

    all_consistent = True
    for i in range(1, 20):
        level_dir = os.path.join(thumbnail_base, str(i))
        if os.path.exists(level_dir):
            print(f"\n--- Level {i} ---")
            is_rust_pattern = check_thumbnail_naming(level_dir)
            if is_rust_pattern is False:
                all_consistent = False
        else:
            break

    print("\n" + "=" * 60)
    if all_consistent:
        print("✓ SUCCESS: All thumbnail levels use consistent Rust naming pattern")
    else:
        print("✗ INCONSISTENT: Some levels use legacy Python naming pattern")
        print("  This may happen if thumbnails were generated with different versions")
        print("  Consider regenerating thumbnails for consistency")
    print("=" * 60)


if __name__ == "__main__":
    main()
