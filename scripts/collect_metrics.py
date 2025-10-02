#!/usr/bin/env python3
"""
Code Metrics Collection Script

Collects various code quality metrics for CTHarvester project:
- Lines of code (LOC)
- Test coverage
- Code complexity
- Documentation coverage
- Type hint coverage

Usage:
    python scripts/collect_metrics.py
    python scripts/collect_metrics.py --output metrics.json
"""

import argparse
import ast
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def count_lines_of_code(directory: str, extensions: List[str] = [".py"]) -> Dict[str, int]:
    """Count lines of code in directory

    Args:
        directory: Directory to scan
        extensions: File extensions to include

    Returns:
        Dictionary with LOC metrics
    """
    metrics = {"total_lines": 0, "code_lines": 0, "comment_lines": 0, "blank_lines": 0, "files": 0}

    for root, _, files in os.walk(directory):
        # Skip test and build directories
        if any(skip in root for skip in ["test", "build", "dist", ".venv", "__pycache__"]):
            continue

        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, file)
                metrics["files"] += 1

                with open(filepath, encoding="utf-8") as f:
                    for line in f:
                        metrics["total_lines"] += 1
                        stripped = line.strip()

                        if not stripped:
                            metrics["blank_lines"] += 1
                        elif stripped.startswith("#"):
                            metrics["comment_lines"] += 1
                        else:
                            metrics["code_lines"] += 1

    return metrics


def get_test_coverage() -> Dict[str, float]:
    """Get test coverage from pytest-cov

    Returns:
        Dictionary with coverage metrics
    """
    try:
        # Run pytest with coverage
        result = subprocess.run(
            ["pytest", "--cov=.", "--cov-report=json", "--tb=no", "-q"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Read coverage.json if it exists
        if os.path.exists("coverage.json"):
            with open("coverage.json") as f:
                data = json.load(f)
                return {
                    "line_coverage": data["totals"]["percent_covered"],
                    "lines_covered": data["totals"]["covered_lines"],
                    "lines_missing": data["totals"]["missing_lines"],
                }
    except Exception as e:
        print(f"Warning: Could not get coverage: {e}")

    return {"line_coverage": 0, "lines_covered": 0, "lines_missing": 0}


def count_functions_with_docstrings(directory: str) -> Dict[str, int]:
    """Count functions with and without docstrings

    Args:
        directory: Directory to scan

    Returns:
        Dictionary with docstring metrics
    """
    metrics = {
        "total_functions": 0,
        "documented_functions": 0,
        "total_classes": 0,
        "documented_classes": 0,
    }

    for root, _, files in os.walk(directory):
        if any(skip in root for skip in ["test", "build", "dist", ".venv", "__pycache__"]):
            continue

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)

                try:
                    with open(filepath, encoding="utf-8") as f:
                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            metrics["total_functions"] += 1
                            if ast.get_docstring(node):
                                metrics["documented_functions"] += 1
                        elif isinstance(node, ast.ClassDef):
                            metrics["total_classes"] += 1
                            if ast.get_docstring(node):
                                metrics["documented_classes"] += 1
                except Exception:
                    pass

    # Calculate percentages
    if metrics["total_functions"] > 0:
        metrics["function_doc_percentage"] = (
            metrics["documented_functions"] / metrics["total_functions"] * 100
        )
    else:
        metrics["function_doc_percentage"] = 0

    if metrics["total_classes"] > 0:
        metrics["class_doc_percentage"] = (
            metrics["documented_classes"] / metrics["total_classes"] * 100
        )
    else:
        metrics["class_doc_percentage"] = 0

    return metrics


def count_type_hints(directory: str) -> Dict[str, int]:
    """Count type hints usage

    Args:
        directory: Directory to scan

    Returns:
        Dictionary with type hint metrics
    """
    metrics = {"total_functions": 0, "typed_functions": 0, "total_args": 0, "typed_args": 0}

    for root, _, files in os.walk(directory):
        if any(skip in root for skip in ["test", "build", "dist", ".venv", "__pycache__"]):
            continue

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)

                try:
                    with open(filepath, encoding="utf-8") as f:
                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            metrics["total_functions"] += 1

                            # Check return type
                            if node.returns:
                                metrics["typed_functions"] += 1

                            # Check argument types
                            for arg in node.args.args:
                                metrics["total_args"] += 1
                                if arg.annotation:
                                    metrics["typed_args"] += 1
                except Exception:
                    pass

    # Calculate percentages
    if metrics["total_functions"] > 0:
        metrics["function_type_percentage"] = (
            metrics["typed_functions"] / metrics["total_functions"] * 100
        )
    else:
        metrics["function_type_percentage"] = 0

    if metrics["total_args"] > 0:
        metrics["arg_type_percentage"] = metrics["typed_args"] / metrics["total_args"] * 100
    else:
        metrics["arg_type_percentage"] = 0

    return metrics


def collect_all_metrics(directories: List[str]) -> Dict:
    """Collect all metrics for given directories

    Args:
        directories: List of directories to scan

    Returns:
        Complete metrics dictionary
    """
    all_metrics = {"directories": {}, "summary": {}}

    # Collect per-directory metrics
    for directory in directories:
        if not os.path.exists(directory):
            continue

        dir_metrics = {
            "loc": count_lines_of_code(directory),
            "documentation": count_functions_with_docstrings(directory),
            "type_hints": count_type_hints(directory),
        }
        all_metrics["directories"][directory] = dir_metrics

    # Collect global metrics
    all_metrics["summary"]["test_coverage"] = get_test_coverage()

    # Calculate totals
    total_loc = sum(m["loc"]["code_lines"] for m in all_metrics["directories"].values())
    total_files = sum(m["loc"]["files"] for m in all_metrics["directories"].values())

    all_metrics["summary"]["total_code_lines"] = total_loc
    all_metrics["summary"]["total_files"] = total_files

    return all_metrics


def print_metrics(metrics: Dict):
    """Print metrics in human-readable format

    Args:
        metrics: Metrics dictionary
    """
    print("\n" + "=" * 60)
    print("CTHarvester Code Metrics Report")
    print("=" * 60)

    print("\n📊 Lines of Code:")
    for directory, dir_metrics in metrics["directories"].items():
        loc = dir_metrics["loc"]
        print(f"\n  {directory}:")
        print(f"    Files: {loc['files']}")
        print(f"    Code lines: {loc['code_lines']}")
        print(f"    Comment lines: {loc['comment_lines']}")
        print(f"    Blank lines: {loc['blank_lines']}")

    print(f"\n  Total code lines: {metrics['summary']['total_code_lines']}")
    print(f"  Total files: {metrics['summary']['total_files']}")

    print("\n📝 Documentation Coverage:")
    for directory, dir_metrics in metrics["directories"].items():
        doc = dir_metrics["documentation"]
        print(f"\n  {directory}:")
        print(
            f"    Functions: {doc['documented_functions']}/{doc['total_functions']} "
            + f"({doc['function_doc_percentage']:.1f}%)"
        )
        print(
            f"    Classes: {doc['documented_classes']}/{doc['total_classes']} "
            + f"({doc['class_doc_percentage']:.1f}%)"
        )

    print("\n🔤 Type Hint Coverage:")
    for directory, dir_metrics in metrics["directories"].items():
        types = dir_metrics["type_hints"]
        print(f"\n  {directory}:")
        print(
            f"    Functions with return type: {types['typed_functions']}/{types['total_functions']} "
            + f"({types['function_type_percentage']:.1f}%)"
        )
        print(
            f"    Typed arguments: {types['typed_args']}/{types['total_args']} "
            + f"({types['arg_type_percentage']:.1f}%)"
        )

    if "test_coverage" in metrics["summary"]:
        cov = metrics["summary"]["test_coverage"]
        print("\n✅ Test Coverage:")
        print(f"    Line coverage: {cov.get('line_coverage', 0):.1f}%")
        print(f"    Lines covered: {cov.get('lines_covered', 0)}")
        print(f"    Lines missing: {cov.get('lines_missing', 0)}")

    print("\n" + "=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Collect code metrics for CTHarvester")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=["core", "utils", "ui"],
        help="Directories to scan (default: core utils ui)",
    )
    args = parser.parse_args()

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    print("Collecting metrics...")
    metrics = collect_all_metrics(args.dirs)

    # Print to console
    print_metrics(metrics)

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"Metrics saved to: {args.output}")


if __name__ == "__main__":
    main()
