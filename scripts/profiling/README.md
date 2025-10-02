# Performance Profiling Tools

Tools for profiling and tracking CTHarvester performance over time.

## =Ë Overview

This directory contains scripts for:
- **CPU Profiling**: Identify performance bottlenecks
- **Memory Profiling**: Track memory usage
- **Performance Metrics**: Benchmark and compare performance over time

## =€ Quick Start

### 1. Install Dependencies (Optional)

```bash
# For detailed system metrics
pip install psutil
```

### 2. Create Sample Data

Run tests to generate sample CT data:

```bash
# Create sample data using pytest fixtures
pytest tests/conftest.py -k sample_ct_directory -v
```

Or create manually:

```bash
mkdir -p tests/fixtures/sample_ct_data
# Add your .tif test images here
```

### 3. Run Profiling

```bash
# Profile all operations
python scripts/profiling/profile_performance.py

# Profile specific operation
python scripts/profiling/profile_performance.py --operation thumbnail_generation

# Use custom sample directory
python scripts/profiling/profile_performance.py --sample-dir /path/to/ct/data
```

### 4. Collect Performance Metrics

```bash
# Collect current metrics
python scripts/profiling/collect_performance_metrics.py

# Save as baseline
python scripts/profiling/collect_performance_metrics.py --save-baseline

# Compare with baseline
python scripts/profiling/collect_performance_metrics.py --compare-baseline
```

## =Ê Scripts

### `profile_performance.py`

Profiles operations using cProfile to identify bottlenecks.

**Features:**
- CPU profiling with cProfile
- Detailed function-level timing
- Saves .prof files for analysis

**Usage:**
```bash
python scripts/profiling/profile_performance.py [OPTIONS]

Options:
  --operation {thumbnail_generation,image_processing,all}
                        Operation to profile (default: all)
  --sample-dir SAMPLE_DIR
                        Directory with sample CT data
  --output OUTPUT       Output file for results (JSON)
```

**Output:**
- `performance_data/thumbnail_generation.prof` - cProfile output
- `performance_data/image_processing.prof` - cProfile output
- `performance_data/profile_results.json` - Summary in JSON

**Example Output:**
```
============================================================
Profiling: Thumbnail Generation
============================================================

 Profiling complete in 12.45s
=Ê Profile saved to: performance_data/thumbnail_generation.prof

Top 20 functions by cumulative time:
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     1000    2.234    0.002   10.234    0.010 thumbnail_generator.py:234(generate_thumbnail)
     1000    1.456    0.001    5.901    0.006 image_utils.py:45(downsample_image)
      500    0.823    0.002    2.123    0.004 {PIL.Image.open}
```

### `collect_performance_metrics.py`

Collects and tracks performance metrics over time.

**Features:**
- Benchmark thumbnail generation speed
- Track memory usage
- Compare with baseline
- Detect performance regressions

**Usage:**
```bash
python scripts/profiling/collect_performance_metrics.py [OPTIONS]

Options:
  --sample-dir SAMPLE_DIR
                        Directory with sample CT data
  --output OUTPUT       Output file for current metrics
  --save-baseline       Save current metrics as baseline
  --compare-baseline    Compare with baseline metrics
```

**Workflow:**

1. **First time - Create baseline:**
```bash
python scripts/profiling/collect_performance_metrics.py --save-baseline
```

2. **After code changes - Compare:**
```bash
python scripts/profiling/collect_performance_metrics.py --compare-baseline
```

**Example Output:**
```
============================================================
Collecting Performance Metrics
============================================================
Benchmarking thumbnail generation...
   Complete in 12.35s
  ¡ Speed: 15.3 images/sec
  =¾ Memory: 45.2 MB

 Metrics saved to: performance_data/current_metrics.json

============================================================
Comparison with Baseline:
============================================================

Thumbnail Generation:
  Current: 15.3 img/s
  Baseline: 14.8 img/s
  Change: +3.4%
   IMPROVEMENT
============================================================
```

## =È Analyzing Results

### View cProfile Results

Use Python's pstats module:

```python
import pstats

# Load profile
stats = pstats.Stats('performance_data/thumbnail_generation.prof')

# Sort by cumulative time
stats.sort_stats('cumulative')

# Show top 20 functions
stats.print_stats(20)

# Show callers of a specific function
stats.print_callers('downsample_image')
```

Or use visualization tools:

```bash
# Install snakeviz
pip install snakeviz

# Visualize profile
snakeviz performance_data/thumbnail_generation.prof
```

### Metrics JSON Structure

```json
{
  "timestamp": "2025-10-02T15:30:00",
  "system": {
    "platform": "Linux",
    "cpu_count": 8,
    "total_memory_gb": 16.0
  },
  "benchmarks": {
    "thumbnail_generation": {
      "success": true,
      "elapsed_time_seconds": 12.35,
      "images_processed": 100,
      "images_per_second": 15.3,
      "memory_used_mb": 45.2
    }
  }
}
```

## <¯ Use Cases

### 1. Find Performance Bottlenecks

```bash
# Profile thumbnail generation
python scripts/profiling/profile_performance.py --operation thumbnail_generation

# Look for functions with high cumulative time
# Optimize those functions
```

### 2. Verify Optimization Impact

```bash
# Before optimization - save baseline
python scripts/profiling/collect_performance_metrics.py --save-baseline

# Make code changes...

# After optimization - compare
python scripts/profiling/collect_performance_metrics.py --compare-baseline
```

### 3. Track Performance Over Time

```bash
# Collect metrics before each commit
python scripts/profiling/collect_performance_metrics.py \
  --output performance_data/metrics_$(git rev-parse --short HEAD).json

# Compare different commits
```

### 4. Regression Detection

```bash
# Set baseline on known-good commit
git checkout v1.0.0
python scripts/profiling/collect_performance_metrics.py --save-baseline

# Test current version
git checkout main
python scripts/profiling/collect_performance_metrics.py --compare-baseline

# Look for "REGRESSION DETECTED" warnings
```

## =Á Output Files

All outputs are saved to `performance_data/`:

- `*.prof` - cProfile binary output (for detailed analysis)
- `current_metrics.json` - Latest metrics
- `baseline_metrics.json` - Baseline for comparison
- `profile_results.json` - Profiling summary

**Note:** `.prof` and `*_metrics.json` files are gitignored.

## =' Troubleshooting

### No sample data found

```bash
# Create sample data manually
mkdir -p tests/fixtures/sample_ct_data
# Copy some test .tif files there

# Or use different directory
python scripts/profiling/profile_performance.py \
  --sample-dir /path/to/your/ct/data
```

### psutil not installed

Most features work without psutil, but for detailed system metrics:

```bash
pip install psutil
```

### Performance seems slow

- **Normal**: First run is slower (cold start, disk cache)
- **Try**: Run profiling 2-3 times and use the best result
- **Check**: Disk I/O (SSD vs HDD makes huge difference)
- **Monitor**: Background processes using system resources

## =Ú Further Reading

- [Python cProfile Documentation](https://docs.python.org/3/library/profile.html)
- [pstats - Statistics object for profilers](https://docs.python.org/3/library/profile.html#pstats.Stats)
- [psutil Documentation](https://psutil.readthedocs.io/)

## <“ Tips

1. **Consistent Environment**: Run profiling on the same machine for accurate comparisons
2. **Multiple Runs**: Run 3 times, use median result
3. **Warm Cache**: Run once to warm up disk cache, then measure
4. **Background Apps**: Close unnecessary applications before profiling
5. **Sample Size**: Use consistent sample data size for comparisons

---

**Part of Phase 3: Performance Profiling Automation**
