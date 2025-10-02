#!/usr/bin/env python3
"""
Performance Visualization Script

Creates visualizations of performance data over time.

Usage:
    python scripts/profiling/visualize_performance.py \
        --metrics-dir performance_data \
        --output performance_report.html
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def load_all_metrics(metrics_dir: Path) -> list:
    """Load all metrics JSON files from directory

    Args:
        metrics_dir: Directory containing metrics JSON files

    Returns:
        List of (timestamp, metrics) tuples, sorted by timestamp
    """
    all_metrics = []

    for json_file in metrics_dir.glob("*_metrics*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            timestamp = data.get("timestamp")
            if timestamp:
                all_metrics.append((timestamp, data))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"   Skipping {json_file}: {e}")

    # Sort by timestamp
    all_metrics.sort(key=lambda x: x[0])

    return all_metrics


def generate_ascii_chart(data: list, title: str, width: int = 60) -> str:
    """Generate ASCII bar chart

    Args:
        data: List of (label, value) tuples
        title: Chart title
        width: Chart width in characters

    Returns:
        ASCII chart as string
    """
    if not data:
        return f"{title}\n(No data)"

    max_value = max(v for _, v in data)
    if max_value == 0:
        max_value = 1

    lines = [title, "=" * width]

    for label, value in data:
        bar_length = int((value / max_value) * (width - 25))
        bar = "" * bar_length
        lines.append(f"{label:15s} {bar} {value:.2f}")

    return "\n".join(lines)


def generate_text_report(metrics_history: list) -> str:
    """Generate text-based performance report

    Args:
        metrics_history: List of (timestamp, metrics) tuples

    Returns:
        Text report as string
    """
    if not metrics_history:
        return "No metrics data available"

    report = []
    report.append("=" * 80)
    report.append("Performance Report")
    report.append("=" * 80)
    report.append("")

    # Summary stats
    speeds = []
    times = []
    memories = []

    for timestamp, metrics in metrics_history:
        thumb = metrics.get("benchmarks", {}).get("thumbnail_generation", {})
        if thumb.get("success"):
            speeds.append(thumb.get("images_per_second", 0))
            times.append(thumb.get("elapsed_time_seconds", 0))
            if thumb.get("memory_used_mb"):
                memories.append(thumb["memory_used_mb"])

    if speeds:
        report.append(f"=Ê Summary ({len(speeds)} measurements)")
        report.append("")
        report.append(f"Thumbnail Generation Speed (images/sec):")
        report.append(f"  Current: {speeds[-1]:.2f}")
        report.append(f"  Average: {sum(speeds)/len(speeds):.2f}")
        report.append(f"  Min:     {min(speeds):.2f}")
        report.append(f"  Max:     {max(speeds):.2f}")
        report.append("")

        # Trend
        if len(speeds) > 1:
            trend = speeds[-1] - speeds[0]
            trend_pct = (trend / speeds[0] * 100) if speeds[0] > 0 else 0
            report.append(f"Trend: {trend_pct:+.1f}% from first measurement")
            report.append("")

    # Recent history chart (last 10 measurements)
    if len(speeds) > 0:
        recent_count = min(10, len(speeds))
        recent_data = []

        for i in range(-recent_count, 0):
            timestamp = metrics_history[i][0]
            speed = speeds[i]
            # Parse timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                label = dt.strftime("%m-%d %H:%M")
            except:
                label = f"Entry {len(speeds) + i + 1}"

            recent_data.append((label, speed))

        report.append(
            generate_ascii_chart(
                recent_data, f"=È Recent Performance (last {recent_count} runs)", width=70
            )
        )
        report.append("")

    # Memory usage (if available)
    if memories:
        report.append(f"=¾ Memory Usage (MB):")
        report.append(f"  Current: {memories[-1]:.2f}")
        report.append(f"  Average: {sum(memories)/len(memories):.2f}")
        report.append(f"  Min:     {min(memories):.2f}")
        report.append(f"  Max:     {max(memories):.2f}")
        report.append("")

    report.append("=" * 80)

    return "\n".join(report)


def generate_html_report(metrics_history: list) -> str:
    """Generate HTML performance report

    Args:
        metrics_history: List of (timestamp, metrics) tuples

    Returns:
        HTML report as string
    """
    speeds = []
    timestamps = []

    for timestamp, metrics in metrics_history:
        thumb = metrics.get("benchmarks", {}).get("thumbnail_generation", {})
        if thumb.get("success"):
            speeds.append(thumb.get("images_per_second", 0))
            timestamps.append(timestamp)

    # Simple HTML report (no external dependencies)
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CTHarvester Performance Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .metric-card {{
            background: #f9f9f9;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .metric-card h3 {{
            margin-top: 0;
            color: #555;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #4CAF50;
            color: white;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            color: #777;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>= CTHarvester Performance Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>=Ê Summary</h2>
"""

    if speeds:
        html += f"""
        <div class="metric-card">
            <h3>Thumbnail Generation Performance</h3>
            <p>Current Speed: <span class="metric-value">{speeds[-1]:.2f}</span> images/sec</p>
            <p>Average Speed: <span class="metric-value">{sum(speeds)/len(speeds):.2f}</span> images/sec</p>
            <p>Best: {max(speeds):.2f} images/sec | Worst: {min(speeds):.2f} images/sec</p>
            <p>Total Measurements: {len(speeds)}</p>
        </div>
"""

        # Trend
        if len(speeds) > 1:
            trend = speeds[-1] - speeds[0]
            trend_pct = (trend / speeds[0] * 100) if speeds[0] > 0 else 0
            trend_class = (
                "metric-value" if trend_pct >= 0 else "metric-value" + ' style="color: #f44336"'
            )
            html += f"""
        <div class="metric-card">
            <h3>=È Trend</h3>
            <p>Change from first measurement: <span class="{trend_class}">{trend_pct:+.1f}%</span></p>
        </div>
"""

        # Recent history table
        html += """
        <h2>=Ë Recent History</h2>
        <table>
            <tr>
                <th>Timestamp</th>
                <th>Speed (images/sec)</th>
                <th>Trend</th>
            </tr>
"""

        recent_count = min(20, len(speeds))
        for i in range(-recent_count, 0):
            timestamp = timestamps[i]
            speed = speeds[i]

            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                ts_display = dt.strftime("%Y-%m-%d %H:%M")
            except:
                ts_display = timestamp[:19]

            # Calculate trend from previous
            if i < -1:
                prev_speed = speeds[i - 1]
                trend = ((speed - prev_speed) / prev_speed * 100) if prev_speed > 0 else 0
                trend_str = f"{trend:+.1f}%"
                trend_color = "#4CAF50" if trend >= 0 else "#f44336"
            else:
                trend_str = ""
                trend_color = "#999"

            html += f"""
            <tr>
                <td>{ts_display}</td>
                <td><strong>{speed:.2f}</strong></td>
                <td style="color: {trend_color}"><strong>{trend_str}</strong></td>
            </tr>
"""

        html += """
        </table>
"""

    else:
        html += "<p>No performance data available.</p>"

    html += f"""
        <div class="footer">
            <p>Performance tracking powered by Phase 3 profiling tools</p>
            <p>CTHarvester - CT Scan Processing and Visualization</p>
        </div>
    </div>
</body>
</html>
"""

    return html


def main():
    """Main visualization function"""
    parser = argparse.ArgumentParser(description="Visualize CTHarvester performance metrics")
    parser.add_argument(
        "--metrics-dir",
        type=str,
        default="performance_data",
        help="Directory containing metrics JSON files",
    )
    parser.add_argument(
        "--output", type=str, default="performance_report.html", help="Output file (HTML or TXT)"
    )
    parser.add_argument(
        "--format",
        choices=["html", "text", "auto"],
        default="auto",
        help="Output format (default: auto-detect from extension)",
    )

    args = parser.parse_args()

    # Determine format
    if args.format == "auto":
        if args.output.endswith(".html"):
            output_format = "html"
        else:
            output_format = "text"
    else:
        output_format = args.format

    # Load metrics
    project_root = Path(__file__).parent.parent.parent
    metrics_dir = project_root / args.metrics_dir

    if not metrics_dir.exists():
        print(f"L Metrics directory not found: {metrics_dir}")
        return 1

    print(f"Loading metrics from: {metrics_dir}")
    metrics_history = load_all_metrics(metrics_dir)

    if not metrics_history:
        print("   No metrics files found")
        print(f"   Run: python scripts/profiling/collect_performance_metrics.py")
        return 1

    print(f"Found {len(metrics_history)} metrics files")

    # Generate report
    if output_format == "html":
        report = generate_html_report(metrics_history)
    else:
        report = generate_text_report(metrics_history)

    # Save report
    output_path = project_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(report)

    print(f" Report generated: {output_path}")

    # Also print text summary
    if output_format == "html":
        print("\nPerformance Summary:")
        print(generate_text_report(metrics_history))

    return 0


if __name__ == "__main__":
    sys.exit(main())
