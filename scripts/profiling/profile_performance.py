#!/usr/bin/env python3
"""
Performance Profiling Script for CTHarvester

This script profiles key operations to identify performance bottlenecks:
- Thumbnail generation (Python and Rust)
- Image processing
- File I/O operations

Usage:
    python scripts/profiling/profile_performance.py [--operation OPERATION]

Operations:
    - thumbnail_generation: Profile thumbnail generation
    - all: Profile all operations (default)
"""

import argparse
import cProfile
import json
import pstats
import sys
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def profile_thumbnail_generation(sample_dir: str) -> dict:
    """Profile thumbnail generation performance

    Args:
        sample_dir: Directory containing sample CT images

    Returns:
        Dictionary with profiling results
    """
    from unittest.mock import MagicMock

    from core.thumbnail_generator import ThumbnailGenerator

    print("=" * 60)
    print("Profiling: Thumbnail Generation")
    print("=" * 60)

    # Create profiler
    profiler = cProfile.Profile()

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.get.side_effect = lambda key, default=None: {
        "thumbnails.max_size": 128,
        "thumbnails.use_rust": False,  # Profile Python implementation
    }.get(key, default)

    mock_threadpool = MagicMock()
    mock_threadpool.maxThreadCount.return_value = 4
    mock_threadpool.activeThreadCount.return_value = 0

    generator = ThumbnailGenerator()

    # Start profiling
    start_time = time.time()
    profiler.enable()

    try:
        result = generator.generate(
            str(sample_dir), mock_settings, mock_threadpool, use_rust_preference=False
        )
        success = result.get("success", False)
    except Exception as e:
        print(f"Error during profiling: {e}")
        success = False

    profiler.disable()
    elapsed = time.time() - start_time

    # Generate statistics
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")

    # Capture top functions
    stream = StringIO()
    stats.stream = stream
    stats.print_stats(20)  # Top 20 functions
    stats_output = stream.getvalue()

    # Save detailed profile
    profile_file = project_root / "performance_data" / "thumbnail_generation.prof"
    stats.dump_stats(str(profile_file))

    print(f"\n✅ Profiling complete in {elapsed:.2f}s")
    print(f"📊 Profile saved to: {profile_file}")
    print(f"\nTop 20 functions by cumulative time:")
    print(stats_output)

    return {
        "operation": "thumbnail_generation",
        "success": success,
        "elapsed_time": elapsed,
        "profile_file": str(profile_file),
        "timestamp": datetime.now().isoformat(),
    }


def profile_image_processing(sample_dir: str) -> dict:
    """Profile image loading and processing

    Args:
        sample_dir: Directory containing sample CT images

    Returns:
        Dictionary with profiling results
    """
    import numpy as np
    from PIL import Image

    print("\n" + "=" * 60)
    print("Profiling: Image Processing")
    print("=" * 60)

    profiler = cProfile.Profile()

    # Get sample images
    image_files = sorted(Path(sample_dir).glob("*.tif"))[:10]

    if not image_files:
        print("⚠️  No .tif files found in sample directory")
        return {"operation": "image_processing", "success": False}

    start_time = time.time()
    profiler.enable()

    try:
        for img_file in image_files:
            with Image.open(img_file) as img:
                # Convert to numpy array
                img_array = np.array(img)
                # Simulate downsample
                downsampled = img_array[::2, ::2]
        success = True
    except Exception as e:
        print(f"Error during profiling: {e}")
        success = False

    profiler.disable()
    elapsed = time.time() - start_time

    # Generate statistics
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")

    # Save profile
    profile_file = project_root / "performance_data" / "image_processing.prof"
    stats.dump_stats(str(profile_file))

    # Print summary
    stream = StringIO()
    stats.stream = stream
    stats.print_stats(15)

    print(f"\n✅ Profiled {len(image_files)} images in {elapsed:.2f}s")
    print(f"📊 Profile saved to: {profile_file}")
    print(f"⚡ Average time per image: {elapsed/len(image_files):.3f}s")

    return {
        "operation": "image_processing",
        "success": success,
        "elapsed_time": elapsed,
        "images_processed": len(image_files),
        "avg_time_per_image": elapsed / len(image_files),
        "profile_file": str(profile_file),
        "timestamp": datetime.now().isoformat(),
    }


def main():
    """Main profiling function"""
    parser = argparse.ArgumentParser(description="Profile CTHarvester performance")
    parser.add_argument(
        "--operation",
        choices=["thumbnail_generation", "image_processing", "all"],
        default="all",
        help="Operation to profile",
    )
    parser.add_argument(
        "--sample-dir",
        type=str,
        default="tests/fixtures/sample_ct_data",
        help="Directory with sample CT data",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="performance_data/profile_results.json",
        help="Output file for results",
    )

    args = parser.parse_args()

    # Verify sample directory exists
    sample_dir = project_root / args.sample_dir
    if not sample_dir.exists():
        print(f"❌ Sample directory not found: {sample_dir}")
        print("💡 Create sample data with: pytest tests/conftest.py::sample_ct_directory")
        return 1

    # Run profiling
    results = []

    if args.operation in ["thumbnail_generation", "all"]:
        result = profile_thumbnail_generation(sample_dir)
        results.append(result)

    if args.operation in ["image_processing", "all"]:
        result = profile_image_processing(sample_dir)
        results.append(result)

    # Save results
    output_file = project_root / args.output
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(
            {
                "profiling_date": datetime.now().isoformat(),
                "sample_directory": str(sample_dir),
                "results": results,
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 60)
    print(f"✅ All profiling complete!")
    print(f"📄 Results saved to: {output_file}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
