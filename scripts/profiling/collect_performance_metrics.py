#!/usr/bin/env python3
"""
Performance Metrics Collection Script for CTHarvester

Collects and tracks performance metrics over time:
- Thumbnail generation speed (images/sec)
- Memory usage
- CPU utilization
- Disk I/O

Usage:
    python scripts/profiling/collect_performance_metrics.py [--save-baseline]
"""

import argparse
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("   psutil not installed. Install with: pip install psutil")


def collect_system_info() -> dict:
    """Collect system information"""
    info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }

    if HAS_PSUTIL:
        info.update({
            "cpu_count": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        })

    return info


def benchmark_thumbnail_generation(sample_dir: str) -> dict:
    """Benchmark thumbnail generation performance

    Args:
        sample_dir: Directory with sample CT data

    Returns:
        Performance metrics dictionary
    """
    from core.thumbnail_generator import ThumbnailGenerator
    from unittest.mock import MagicMock

    print("Benchmarking thumbnail generation...")

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.get.side_effect = lambda key, default=None: {
        'thumbnails.max_size': 128,
        'thumbnails.use_rust': False
    }.get(key, default)

    mock_threadpool = MagicMock()
    mock_threadpool.maxThreadCount.return_value = 4
    mock_threadpool.activeThreadCount.return_value = 0

    generator = ThumbnailGenerator()

    # Measure performance
    if HAS_PSUTIL:
        process = psutil.Process()
        mem_before = process.memory_info().rss / (1024**2)  # MB

    start_time = time.time()

    try:
        result = generator.generate(
            str(sample_dir),
            mock_settings,
            mock_threadpool,
            use_rust_preference=False
        )
        success = result.get('success', False)
    except Exception as e:
        print(f"Error during benchmark: {e}")
        success = False
        result = {}

    elapsed = time.time() - start_time

    if HAS_PSUTIL:
        mem_after = process.memory_info().rss / (1024**2)  # MB
        mem_used = mem_after - mem_before
    else:
        mem_used = None

    # Get image count if available
    level_info = result.get('level_info', [])
    if level_info and len(level_info) > 0:
        images_count = level_info[0].get('seq_end', 0) - level_info[0].get('seq_begin', 0) + 1
    else:
        images_count = 0

    metrics = {
        "success": success,
        "elapsed_time_seconds": round(elapsed, 3),
        "images_processed": images_count,
        "images_per_second": round(images_count / elapsed, 2) if elapsed > 0 and images_count > 0 else 0,
        "memory_used_mb": round(mem_used, 2) if mem_used else None,
    }

    print(f"   Complete in {elapsed:.2f}s")
    if images_count > 0:
        print(f"  ¡ Speed: {metrics['images_per_second']:.2f} images/sec")
    if mem_used:
        print(f"  =¾ Memory: {mem_used:.2f} MB")

    return metrics


def collect_metrics(sample_dir: str) -> dict:
    """Collect all performance metrics

    Args:
        sample_dir: Directory with sample CT data

    Returns:
        Complete metrics dictionary
    """
    print("=" * 60)
    print("Collecting Performance Metrics")
    print("=" * 60)

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "system": collect_system_info(),
        "benchmarks": {}
    }

    # Benchmark thumbnail generation
    if Path(sample_dir).exists():
        metrics["benchmarks"]["thumbnail_generation"] = benchmark_thumbnail_generation(sample_dir)
    else:
        print(f"   Sample directory not found: {sample_dir}")
        metrics["benchmarks"]["thumbnail_generation"] = {"success": False, "error": "Sample data not found"}

    return metrics


def compare_with_baseline(current: dict, baseline: dict) -> dict:
    """Compare current metrics with baseline

    Args:
        current: Current metrics
        baseline: Baseline metrics

    Returns:
        Comparison results
    """
    comparison = {}

    # Compare thumbnail generation
    curr_thumb = current.get("benchmarks", {}).get("thumbnail_generation", {})
    base_thumb = baseline.get("benchmarks", {}).get("thumbnail_generation", {})

    if curr_thumb.get("success") and base_thumb.get("success"):
        curr_speed = curr_thumb.get("images_per_second", 0)
        base_speed = base_thumb.get("images_per_second", 0)

        if base_speed > 0:
            speed_change = ((curr_speed - base_speed) / base_speed) * 100
            comparison["thumbnail_generation"] = {
                "current_images_per_second": curr_speed,
                "baseline_images_per_second": base_speed,
                "change_percent": round(speed_change, 2),
                "regression": speed_change < -20  # More than 20% slower
            }

    return comparison


def main():
    """Main metrics collection function"""
    parser = argparse.ArgumentParser(description="Collect CTHarvester performance metrics")
    parser.add_argument(
        '--sample-dir',
        type=str,
        default='tests/fixtures/sample_ct_data',
        help='Directory with sample CT data'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='performance_data/current_metrics.json',
        help='Output file for current metrics'
    )
    parser.add_argument(
        '--save-baseline',
        action='store_true',
        help='Save current metrics as baseline'
    )
    parser.add_argument(
        '--compare-baseline',
        action='store_true',
        help='Compare with baseline metrics'
    )

    args = parser.parse_args()

    # Collect metrics
    sample_dir = project_root / args.sample_dir
    metrics = collect_metrics(str(sample_dir))

    # Save results
    output_file = project_root / args.output
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print("\n" + "=" * 60)
    print(f" Metrics saved to: {output_file}")

    # Save as baseline if requested
    if args.save_baseline:
        baseline_file = project_root / "performance_data" / "baseline_metrics.json"
        with open(baseline_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f" Baseline saved to: {baseline_file}")

    # Compare with baseline if requested
    if args.compare_baseline:
        baseline_file = project_root / "performance_data" / "baseline_metrics.json"
        if baseline_file.exists():
            with open(baseline_file) as f:
                baseline = json.load(f)

            comparison = compare_with_baseline(metrics, baseline)

            print("\n" + "=" * 60)
            print("Comparison with Baseline:")
            print("=" * 60)

            if "thumbnail_generation" in comparison:
                thumb_comp = comparison["thumbnail_generation"]
                print(f"\nThumbnail Generation:")
                print(f"  Current: {thumb_comp['current_images_per_second']:.2f} img/s")
                print(f"  Baseline: {thumb_comp['baseline_images_per_second']:.2f} img/s")
                print(f"  Change: {thumb_comp['change_percent']:+.1f}%")

                if thumb_comp['regression']:
                    print(f"     REGRESSION DETECTED (>{-20:.0f}% slower)")
                elif thumb_comp['change_percent'] > 5:
                    print(f"   IMPROVEMENT")
                else:
                    print(f"  ¡  No significant change")
        else:
            print(f"   Baseline file not found: {baseline_file}")
            print(f"   Create baseline with: --save-baseline")

    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
