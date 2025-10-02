#!/usr/bin/env python3
"""
Performance Comparison Script

Compares performance metrics between two runs (e.g., current vs baseline).

Usage:
    python scripts/profiling/compare_performance.py \
        --baseline baseline_metrics.json \
        --current current_metrics.json \
        --threshold 20
"""

import argparse
import json
import sys
from pathlib import Path


def load_metrics(file_path: str) -> dict:
    """Load metrics from JSON file"""
    with open(file_path) as f:
        return json.load(f)


def compare_thumbnail_generation(current: dict, baseline: dict) -> dict:
    """Compare thumbnail generation metrics

    Args:
        current: Current metrics
        baseline: Baseline metrics

    Returns:
        Comparison results
    """
    curr = current.get("benchmarks", {}).get("thumbnail_generation", {})
    base = baseline.get("benchmarks", {}).get("thumbnail_generation", {})

    if not curr.get("success") or not base.get("success"):
        return {"success": False, "error": "Missing or failed benchmark data"}

    curr_speed = curr.get("images_per_second", 0)
    base_speed = base.get("images_per_second", 0)
    curr_time = curr.get("elapsed_time_seconds", 0)
    base_time = base.get("elapsed_time_seconds", 0)
    curr_mem = curr.get("memory_used_mb")
    base_mem = base.get("memory_used_mb")

    # Calculate changes
    speed_change = ((curr_speed - base_speed) / base_speed * 100) if base_speed > 0 else 0
    time_change = ((curr_time - base_time) / base_time * 100) if base_time > 0 else 0

    result = {
        "success": True,
        "speed": {
            "current": curr_speed,
            "baseline": base_speed,
            "change_percent": round(speed_change, 2),
            "improved": speed_change > 0,
        },
        "time": {
            "current": curr_time,
            "baseline": base_time,
            "change_percent": round(time_change, 2),
            "improved": time_change < 0,
        },
    }

    if curr_mem is not None and base_mem is not None:
        mem_change = ((curr_mem - base_mem) / base_mem * 100) if base_mem > 0 else 0
        result["memory"] = {
            "current": curr_mem,
            "baseline": base_mem,
            "change_percent": round(mem_change, 2),
            "improved": mem_change < 0,
        }

    return result


def print_comparison(comparison: dict, threshold: float):
    """Print comparison results in human-readable format

    Args:
        comparison: Comparison results
        threshold: Regression threshold percentage (negative means slower)
    """
    if not comparison.get("success"):
        print(f"L Comparison failed: {comparison.get('error', 'Unknown error')}")
        return False

    print("\n" + "=" * 60)
    print("Performance Comparison Results")
    print("=" * 60)

    # Speed comparison
    speed = comparison["speed"]
    print(f"\n=È Throughput (images/sec):")
    print(f"  Current:  {speed['current']:.2f} img/s")
    print(f"  Baseline: {speed['baseline']:.2f} img/s")
    print(f"  Change:   {speed['change_percent']:+.1f}%", end="")

    if speed["improved"]:
        print("  IMPROVEMENT")
    elif speed["change_percent"] < -threshold:
        print(f"    REGRESSION (>{threshold}% slower)")
    else:
        print(" ¡  No significant change")

    # Time comparison
    time = comparison["time"]
    print(f"\nñ  Execution Time (seconds):")
    print(f"  Current:  {time['current']:.2f}s")
    print(f"  Baseline: {time['baseline']:.2f}s")
    print(f"  Change:   {time['change_percent']:+.1f}%", end="")

    if time["improved"]:
        print("  FASTER")
    elif time["change_percent"] > threshold:
        print(f"    SLOWER (>{threshold}%)")
    else:
        print(" ¡  Similar")

    # Memory comparison (if available)
    if "memory" in comparison:
        mem = comparison["memory"]
        print(f"\n=¾ Memory Usage (MB):")
        print(f"  Current:  {mem['current']:.2f} MB")
        print(f"  Baseline: {mem['baseline']:.2f} MB")
        print(f"  Change:   {mem['change_percent']:+.1f}%", end="")

        if mem["improved"]:
            print("  LESS MEMORY")
        elif mem["change_percent"] > threshold:
            print(f"    MORE MEMORY (>{threshold}%)")
        else:
            print(" ¡  Similar")

    print("\n" + "=" * 60)

    # Determine if regression occurred
    regression = speed["change_percent"] < -threshold

    if regression:
        print("\nL REGRESSION DETECTED")
        print(f"   Performance is >{threshold}% slower than baseline")
        return False
    elif speed["improved"]:
        print("\n PERFORMANCE IMPROVED")
        return True
    else:
        print("\n¡  PERFORMANCE STABLE")
        return True


def main():
    """Main comparison function"""
    parser = argparse.ArgumentParser(description="Compare performance metrics between two runs")
    parser.add_argument("--baseline", required=True, help="Baseline metrics JSON file")
    parser.add_argument("--current", required=True, help="Current metrics JSON file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Regression threshold percentage (default: 20%%)",
    )
    parser.add_argument("--output", help="Output comparison results to JSON file")

    args = parser.parse_args()

    # Load metrics
    try:
        baseline = load_metrics(args.baseline)
        current = load_metrics(args.current)
    except FileNotFoundError as e:
        print(f"L Error: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"L Error parsing JSON: {e}")
        return 1

    # Compare
    comparison = compare_thumbnail_generation(current, baseline)

    # Print results
    passed = print_comparison(comparison, args.threshold)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(
                {"threshold": args.threshold, "passed": passed, "comparison": comparison},
                f,
                indent=2,
            )

        print(f"\n=Ä Comparison results saved to: {output_path}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
