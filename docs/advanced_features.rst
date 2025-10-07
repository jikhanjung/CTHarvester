Advanced Features Guide
=======================

This guide covers advanced features and techniques for power users of CTHarvester.

.. contents:: Table of Contents
   :local:
   :depth: 2

Performance Optimization
------------------------

Rust Module for High-Speed Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Rust thumbnail generation module provides 10-50x speedup over Python.

**Installation:**

.. code-block:: bash

   # Install Rust toolchain
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source $HOME/.cargo/env

   # Install maturin (Python-Rust bridge)
   pip install maturin

   # Build and install the Rust module
   cd rust_thumbnail
   maturin develop --release
   cd ..

**Verification:**

Check console output when starting CTHarvester:

.. code-block:: text

   [INFO] Rust thumbnail module loaded successfully

If you see "Rust thumbnail module not available, using Python fallback", the module is not loaded.

**Troubleshooting:**

.. code-block:: bash

   # Check if Rust is installed
   rustc --version

   # Rebuild module
   cd rust_thumbnail
   cargo clean
   maturin develop --release --verbose

**Performance comparison:**

+---------------+------------------+-------------------+
| Dataset Size  | Python (seconds) | Rust (seconds)    |
+===============+==================+===================+
| 500 images    | 500-1000         | 50-100            |
+---------------+------------------+-------------------+
| 1000 images   | 1200-2400        | 120-300           |
+---------------+------------------+-------------------+
| 2000 images   | 2400-4800        | 300-600           |
+---------------+------------------+-------------------+
| 5000 images   | 6000-12000       | 900-1500          |
+---------------+------------------+-------------------+

Multi-Threading Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CTHarvester uses multi-threading for parallel thumbnail generation.

**Optimal thread count:**

* **2-4 cores:** 2 threads
* **4-8 cores:** 4 threads
* **8+ cores:** 4-6 threads (diminishing returns beyond 6)

**Configuration:**

1. Settings → Processing → Worker threads
2. Select thread count
3. Restart thumbnail generation for changes to take effect

**Thread count trade-offs:**

+--------+-------------------+------------------+--------------------+
| Threads| Speed             | Memory Usage     | Disk I/O           |
+========+===================+==================+====================+
| 1      | Baseline (1.0x)   | Low (1x)         | Sequential         |
+--------+-------------------+------------------+--------------------+
| 2      | 1.7-1.9x faster   | Medium (1.8x)    | Moderate           |
+--------+-------------------+------------------+--------------------+
| 4      | 3.0-3.5x faster   | High (3.5x)      | High contention    |
+--------+-------------------+------------------+--------------------+
| 8      | 3.5-4.0x faster   | Very high (7x)   | Severe contention  |
+--------+-------------------+------------------+--------------------+

**Best practices:**

* Use 1 thread for network drives or USB 2.0 devices
* Use 2-4 threads for local SSDs
* Use 1-2 threads on low-RAM systems (4GB)
* Monitor system during generation to find optimal setting

Memory Management Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Settings affecting memory usage:**

1. **Memory limit** (Settings → Processing)

   * Soft limit for image processing
   * Default: 4GB
   * Recommended: 50-70% of available RAM

2. **Worker threads**

   * Each thread requires memory for image buffers
   * Formula: ``total_memory ≈ base (200MB) + threads × image_size × 2``

3. **Max thumbnail size**

   * Larger thumbnails = more memory per thread
   * 300px: ~3MB per thread
   * 500px: ~8MB per thread
   * 800px: ~20MB per thread

**Memory optimization for large datasets:**

.. code-block:: python

   # Configuration for 4GB RAM system
   {
       "memory_limit_gb": 2,
       "worker_threads": 1,
       "max_thumbnail_size": 300,
       "sample_size": 10,
       "enable_compression": False  # Faster, uses less CPU
   }

   # Configuration for 8GB RAM system
   {
       "memory_limit_gb": 4,
       "worker_threads": 2,
       "max_thumbnail_size": 500,
       "sample_size": 20,
       "enable_compression": True
   }

   # Configuration for 16GB+ RAM system
   {
       "memory_limit_gb": 8,
       "worker_threads": 4,
       "max_thumbnail_size": 800,
       "sample_size": 30,
       "enable_compression": True
   }

**Monitoring memory usage:**

* Windows: Task Manager → Performance → Memory
* macOS: Activity Monitor → Memory
* Linux: ``htop`` or ``free -h``

Disk I/O Optimization
~~~~~~~~~~~~~~~~~~~~~

**Best practices for maximum throughput:**

1. **Use local SSD**

   * Sequential read: 500-7000 MB/s
   * vs HDD: 100-200 MB/s
   * vs USB 2.0: 35 MB/s
   * vs Network (1Gbps): 125 MB/s

2. **Copy to local drive first**

   .. code-block:: bash

      # Better: copy to local, then process
      cp -r /network/ct_scans/sample/ /local/temp/
      # Process /local/temp/sample/

      # Worse: process directly from network
      # Process /network/ct_scans/sample/

3. **Disable real-time antivirus temporarily**

   * Add CTHarvester directory to exclusions
   * Or temporarily disable real-time scanning
   * **Re-enable after processing**

4. **TRIM/Defrag maintenance**

   .. code-block:: bash

      # Windows: Optimize drives
      defrag C: /O

      # Linux: TRIM SSD
      sudo fstrim -av

Advanced Thumbnail Configuration
---------------------------------

Multi-Level Pyramid System
~~~~~~~~~~~~~~~~~~~~~~~~~~~

CTHarvester generates a multi-resolution pyramid for efficient navigation.

**Pyramid levels:**

* Level 0: Full resolution
* Level 1: 1/2 resolution (width/2, height/2)
* Level 2: 1/4 resolution
* Level 3: 1/8 resolution
* ... up to configured maximum

**Configuration:**

Settings → Thumbnails:

* **Max pyramid level:** 1-20 (default: 10)
* **Max thumbnail size:** 100-2000 px (default: 500)
* **Sample size:** 10-100 images (default: 20)

**Level calculation:**

.. code-block:: python

   def calculate_pyramid_levels(image_width, max_thumbnail_size, max_levels):
       """Calculate number of pyramid levels"""
       levels = 0
       current_size = image_width

       while current_size > max_thumbnail_size and levels < max_levels:
           current_size //= 2
           levels += 1

       return levels + 1  # Include level 0

**Example:**

* Image: 2048×2048 px
* Max thumbnail: 500 px
* Levels generated:

  * Level 0: 2048×2048 (full resolution)
  * Level 1: 1024×1024
  * Level 2: 512×512 ✓ (below max_thumbnail_size)
  * Level 3: 256×256 ✓
  * Level 4: 128×128 ✓

**Disk space calculation:**

.. code-block:: python

   # Approximate disk usage formula
   total_size = sum(
       image_count × (original_width / (2**level))² × bytes_per_pixel
       for level in range(num_levels)
   )

   # Example: 1000 images, 2048×2048, 16-bit, 3 levels
   level_0 = 1000 × 2048² × 2 = ~8 GB
   level_1 = 1000 × 1024² × 2 = ~2 GB
   level_2 = 1000 × 512² × 2 = ~500 MB
   total = ~10.5 GB

Custom Sampling Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The sample size parameter controls how many images are used to generate initial thumbnails.

**Sampling strategy:**

.. code-block:: python

   def select_sample_indices(total_images, sample_size):
       """Evenly distributed sample"""
       if sample_size >= total_images:
           return list(range(total_images))

       step = total_images / sample_size
       indices = [int(i * step) for i in range(sample_size)]
       return indices

**Use cases:**

* **Small sample (10-15):** Quick preview for large datasets
* **Medium sample (20-30):** Balanced speed/quality
* **Large sample (50-100):** High quality preview, slower

**When to use large sample size:**

* Highly variable dataset (different structures per slice)
* Quality preview needed before full processing
* Sufficient time for thumbnail generation

**When to use small sample size:**

* Quick exploration
* Homogeneous dataset (similar structures throughout)
* Limited time or disk space

Thumbnail Format Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Supported formats:**

1. **TIF (default)**

   * Pros: Lossless, preserves bit depth, fast
   * Cons: Larger file size
   * Best for: Quality-critical workflows

2. **PNG**

   * Pros: Lossless, good compression
   * Cons: Slower encoding/decoding
   * Best for: Disk-space-constrained systems

**Compression settings:**

.. code-block:: python

   # TIF compression options
   {
       "compression": "lzw",  # or "deflate", "jpeg", None
       "quality": 95          # for JPEG compression
   }

   # PNG compression level
   {
       "compression_level": 6  # 0-9, higher = smaller but slower
   }

**Benchmark (1000 images, 512×512, 8-bit):**

+--------------------+------------+------------------+--------------------+
| Format             | Size       | Write Speed      | Read Speed         |
+====================+============+==================+====================+
| TIF (uncompressed) | 250 MB     | 200 MB/s         | 500 MB/s           |
+--------------------+------------+------------------+--------------------+
| TIF (LZW)          | 150 MB     | 100 MB/s         | 200 MB/s           |
+--------------------+------------+------------------+--------------------+
| PNG                | 120 MB     | 50 MB/s          | 100 MB/s           |
+--------------------+------------+------------------+--------------------+

3D Visualization Techniques
----------------------------

Threshold Tuning for Different Materials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The threshold parameter acts as the isovalue for marching cubes algorithm.

**Material-specific thresholds:**

+---------------------+-----------------+---------------------+
| Material            | Typical Range   | Notes               |
+=====================+=================+=====================+
| Air/Void            | 0-30            | Background          |
+---------------------+-----------------+---------------------+
| Soft tissue         | 30-80           | Low density         |
+---------------------+-----------------+---------------------+
| Muscle              | 80-120          | Medium density      |
+---------------------+-----------------+---------------------+
| Bone (trabecular)   | 120-180         | Medium-high density |
+---------------------+-----------------+---------------------+
| Bone (cortical)     | 180-255         | High density        |
+---------------------+-----------------+---------------------+

**Finding optimal threshold:**

1. Start at 128 (midpoint)
2. Increase threshold until:

   * Internal structures disappear
   * Only outer shell visible

3. Decrease threshold until:

   * Noise appears
   * Too much detail obscures structure

4. Fine-tune in range where structure is clear

**Multi-threshold visualization:**

For complex specimens, visualize multiple thresholds:

.. code-block:: python

   # Export multiple meshes at different thresholds
   thresholds = [50, 100, 150, 200]
   for threshold in thresholds:
       # Set threshold in UI
       # Export as mesh_threshold_XXX.obj

**Inversion mode:**

For negative CT scans (phase-contrast, certain staining):

* Check "Inv." checkbox
* Threshold interpretation reversed:

  * Low threshold → high density
  * High threshold → low density

Advanced Mesh Export Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Export formats:**

1. **OBJ (Wavefront)**

   * Pros: Universal compatibility, readable text format
   * Cons: Large file size, no color
   * Best for: General 3D software (Blender, Maya, MeshLab)

2. **PLY (Polygon File Format)**

   * Pros: Supports color and vertex attributes
   * Cons: Less universal than OBJ
   * Best for: CloudCompare, scientific visualization

3. **STL (Stereolithography)**

   * Pros: Compact binary, 3D printing standard
   * Cons: No color, less readable
   * Best for: 3D printing (Cura, PrusaSlicer)

**Post-processing workflow:**

.. code-block:: text

   CTHarvester → Export OBJ → MeshLab → Decimate/Smooth → Export STL → Print

**Mesh cleanup in MeshLab:**

.. code-block:: text

   1. Import OBJ file
   2. Filters → Cleaning → Remove Duplicate Vertices
   3. Filters → Cleaning → Remove Unreferenced Vertices
   4. Filters → Remeshing → Quadric Edge Collapse Decimation
      - Target faces: 50% of original
   5. Filters → Smoothing → Laplacian Smooth
      - Iterations: 3-5
   6. File → Export Mesh As → STL

**Blender workflow:**

.. code-block:: text

   1. File → Import → Wavefront (.obj)
   2. Select mesh → Object → Shade Smooth
   3. Add Modifier → Decimate
      - Ratio: 0.5 (50% reduction)
      - Apply modifier
   4. File → Export → STL
      - Binary format
      - Scene Unit
   5. Print or further process

OpenGL Rendering Customization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Settings → Rendering:**

* **Anti-aliasing:** Smooth edges, slower rendering
* **Backface culling:** Faster, may hide internal structures
* **Wireframe mode:** View mesh topology
* **FPS counter:** Monitor performance

**Performance optimization:**

.. code-block:: python

   # Low-end GPU (integrated graphics)
   {
       "anti_aliasing": False,
       "backface_culling": True,
       "max_polygon_count": 100000
   }

   # High-end GPU (dedicated graphics)
   {
       "anti_aliasing": True,
       "backface_culling": False,
       "max_polygon_count": 1000000
   }

**Keyboard shortcuts for 3D view:**

* Click+Drag: Rotate
* Shift+Click+Drag: Pan
* Scroll: Zoom
* Double-click: Reset view
* ``F3``: Toggle 3D view
* ``W``: Toggle wireframe mode
* ``B``: Toggle backface culling

Batch Processing Workflows
---------------------------

Processing Multiple Datasets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Current limitation:** CTHarvester processes one dataset at a time.

**Workaround for batch processing:**

.. code-block:: bash

   #!/bin/bash
   # batch_process.sh - Process multiple CT datasets

   DATASETS=(
       "/data/ct_scans/sample_001"
       "/data/ct_scans/sample_002"
       "/data/ct_scans/sample_003"
   )

   for dataset in "${DATASETS[@]}"; do
       echo "Processing $dataset..."

       # Generate thumbnails (manual step for now)
       # Open CTHarvester, load directory, wait for thumbnails

       # User performs cropping/export interactively

       read -p "Press Enter when done with $dataset..."
   done

**Future CLI support (planned):**

.. code-block:: bash

   # Future command-line interface (not yet implemented)
   ctharvester process \
       --input /data/ct_scans/sample_001 \
       --output /data/processed/sample_001 \
       --bottom 100 \
       --top 200 \
       --roi 100,100,500,500 \
       --threshold 128 \
       --export-mesh sample_001.obj \
       --export-images

Scripting with Python API
~~~~~~~~~~~~~~~~~~~~~~~~~~

For advanced automation, use CTHarvester modules directly:

.. code-block:: python

   #!/usr/bin/env python
   """
   Example: Batch thumbnail generation
   """
   import sys
   from pathlib import Path
   from core.file_handler import FileHandler
   from core.thumbnail_manager import ThumbnailManager

   def process_dataset(directory):
       """Generate thumbnails for a dataset"""
       handler = FileHandler()

       try:
           # Open directory
           result = handler.open_directory(directory)
           print(f"Loaded {result['image_count']} images")

           # Initialize thumbnail manager
           manager = ThumbnailManager(handler)

           # Generate thumbnails
           print("Generating thumbnails...")
           manager.generate_thumbnails(
               max_size=500,
               levels=5,
               sample_size=20,
               use_rust=True
           )

           print(f"✓ Completed {directory}")

       except Exception as e:
           print(f"✗ Error processing {directory}: {e}")

   if __name__ == "__main__":
       datasets = [
           "/data/ct_scans/sample_001",
           "/data/ct_scans/sample_002",
           "/data/ct_scans/sample_003",
       ]

       for dataset in datasets:
           process_dataset(dataset)

**Automated cropping and export:**

.. code-block:: python

   #!/usr/bin/env python
   """
   Example: Automated batch cropping
   """
   from core.file_handler import FileHandler
   from utils.file_utils import save_cropped_stack

   def crop_and_export(directory, bottom, top, output_dir):
       """Crop and export image stack"""
       handler = FileHandler()
       handler.open_directory(directory)

       # Get file list
       files = handler.get_file_list()[bottom:top+1]

       # Save cropped stack
       save_cropped_stack(
           files,
           output_dir,
           roi=(100, 100, 500, 500),  # x, y, width, height
           bit_depth=16
       )

       print(f"Exported {len(files)} slices to {output_dir}")

   # Batch configuration
   jobs = [
       {"dir": "/data/ct_scans/sample_001", "bottom": 100, "top": 200},
       {"dir": "/data/ct_scans/sample_002", "bottom": 150, "top": 250},
       {"dir": "/data/ct_scans/sample_003", "bottom": 80, "top": 180},
   ]

   for job in jobs:
       output = f"/data/processed/{Path(job['dir']).name}"
       crop_and_export(job["dir"], job["bottom"], job["top"], output)

Settings Management
-------------------

Configuration File Format
~~~~~~~~~~~~~~~~~~~~~~~~~

CTHarvester settings are stored in YAML format.

**Location:**

* Windows: ``%APPDATA%\CTHarvester\settings.yaml``
* Linux/macOS: ``~/.config/CTHarvester/settings.yaml``

**Example settings.yaml:**

.. code-block:: yaml

   # General settings
   general:
     language: "en"  # or "ko" for Korean
     theme: "light"
     remember_window_geometry: true
     remember_last_directory: true

   # Thumbnail generation
   thumbnails:
     max_size: 500
     sample_size: 20
     max_pyramid_level: 10
     enable_compression: true
     format: "tif"  # or "png"

   # Processing
   processing:
     worker_threads: 4
     memory_limit_gb: 4
     use_rust_module: true
     priority: "normal"  # or "high", "low"

   # Rendering
   rendering:
     default_threshold: 128
     enable_antialiasing: true
     show_fps: false
     backface_culling: false
     wireframe_mode: false

   # Export
   export:
     mesh_format: "obj"  # or "ply", "stl"
     image_format: "tif"  # or "png", "jpg"
     compression_level: 6

   # Advanced
   advanced:
     log_level: "INFO"  # or "DEBUG", "WARNING", "ERROR"
     console_output: true
     auto_save_settings: true

Bulk Settings Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Export settings for team:**

.. code-block:: bash

   # Export settings
   # Settings → Export Settings... → save as team_settings.yaml

   # Distribute to team
   cp team_settings.yaml /shared/ctharvester/

**Import settings for team:**

.. code-block:: bash

   # Each team member imports
   # Settings → Import Settings... → select team_settings.yaml

**Programmatic settings update:**

.. code-block:: python

   #!/usr/bin/env python
   """
   Update settings for batch processing
   """
   import yaml
   from pathlib import Path

   settings_path = Path.home() / ".config" / "CTHarvester" / "settings.yaml"

   # Load existing settings
   with open(settings_path) as f:
       settings = yaml.safe_load(f)

   # Update for batch processing
   settings["processing"]["worker_threads"] = 1  # Sequential
   settings["processing"]["memory_limit_gb"] = 2  # Low memory
   settings["thumbnails"]["max_size"] = 300  # Smaller thumbs
   settings["advanced"]["log_level"] = "DEBUG"  # Detailed logs

   # Save updated settings
   with open(settings_path, "w") as f:
       yaml.dump(settings, f, default_flow_style=False)

   print(f"Settings updated: {settings_path}")

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Control CTHarvester behavior via environment variables:

**Log level:**

.. code-block:: bash

   export CTHARVESTER_LOG_LEVEL=DEBUG
   python CTHarvester.py

**Console log level (separate from file log):**

.. code-block:: bash

   export CTHARVESTER_CONSOLE_LEVEL=WARNING
   python CTHarvester.py

**Custom log directory:**

.. code-block:: bash

   export CTHARVESTER_LOG_DIR=/custom/log/path
   python CTHarvester.py

**Disable Rust module:**

.. code-block:: bash

   export CTHARVESTER_NO_RUST=1
   python CTHarvester.py

**Force single-threaded:**

.. code-block:: bash

   export CTHARVESTER_THREADS=1
   python CTHarvester.py

**Combined example:**

.. code-block:: bash

   #!/bin/bash
   # Debug mode with maximum logging

   export CTHARVESTER_LOG_LEVEL=DEBUG
   export CTHARVESTER_CONSOLE_LEVEL=DEBUG
   export CTHARVESTER_LOG_DIR=/tmp/ctharvester_debug
   export CTHARVESTER_THREADS=1
   export CTHARVESTER_NO_RUST=1

   python CTHarvester.py

Integration with Other Tools
-----------------------------

ImageJ/Fiji Integration
~~~~~~~~~~~~~~~~~~~~~~~

**Export for ImageJ:**

1. Save cropped image stack (TIF format recommended)
2. Open in ImageJ: File → Import → Image Sequence
3. Select first file in sequence
4. ImageJ automatically loads all files

**ImageJ macro for batch import:**

.. code-block:: javascript

   // ImageJ macro: Import CTHarvester stack
   dir = getDirectory("Choose CTHarvester output directory");
   run("Image Sequence...", "open=" + dir + " sort");
   run("Z Project...", "projection=[Max Intensity]");

**CTHarvester → ImageJ → Analysis workflow:**

.. code-block:: text

   1. CTHarvester: Crop region of interest
   2. Export as TIF sequence
   3. ImageJ: Import sequence
   4. Process:
      - Enhance contrast
      - Measure features
      - Segment structures
   5. Save results

Blender Integration
~~~~~~~~~~~~~~~~~~~

**Import CTHarvester mesh:**

.. code-block:: text

   1. Blender → File → Import → Wavefront (.obj)
   2. Navigate to exported mesh
   3. Import options:
      - ✓ Split by Object
      - ✓ Split by Group
      - ✗ Y Forward, Z Up (use defaults)

**Blender Python script for batch import:**

.. code-block:: python

   import bpy
   import os

   # Clear existing objects
   bpy.ops.object.select_all(action='SELECT')
   bpy.ops.object.delete()

   # Import multiple meshes
   mesh_dir = "/data/processed/"
   for filename in os.listdir(mesh_dir):
       if filename.endswith(".obj"):
           filepath = os.path.join(mesh_dir, filename)
           bpy.ops.import_scene.obj(filepath=filepath)

   # Set up lighting and camera
   bpy.ops.object.light_add(type='SUN', location=(10, 10, 10))
   bpy.ops.object.camera_add(location=(15, -15, 10))

**Render animation:**

.. code-block:: python

   # Blender: Rotate mesh for 360° animation
   import bpy
   import math

   obj = bpy.context.active_object
   for frame in range(0, 360, 5):
       obj.rotation_euler[2] = math.radians(frame)
       obj.keyframe_insert(data_path="rotation_euler", frame=frame)

   # Set render settings
   bpy.context.scene.render.image_settings.file_format = 'PNG'
   bpy.context.scene.render.filepath = "/output/animation/frame_"

   # Render animation
   bpy.ops.render.render(animation=True)

CloudCompare Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

**Import CTHarvester mesh into CloudCompare:**

.. code-block:: text

   1. CloudCompare → File → Open → Select .ply or .obj
   2. Mesh loaded as point cloud
   3. Analysis tools available:
      - Measure dimensions
      - Compute normals
      - Compare to reference
      - Export sections

**Command-line CloudCompare:**

.. code-block:: bash

   # Compute mesh normals
   CloudCompare -O mesh.obj -COMPUTE_NORMALS -SAVE_MESHES FILE "output.obj"

   # Measure distances
   CloudCompare -O mesh1.obj -O mesh2.obj -C2C_DIST -SAVE_CLOUDS

Python/NumPy Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

**Load CTHarvester images for custom processing:**

.. code-block:: python

   import numpy as np
   from PIL import Image
   from pathlib import Path

   def load_stack(directory, start_idx, end_idx):
       """Load image stack as 3D NumPy array"""
       files = sorted(Path(directory).glob("*.tif"))
       selected = files[start_idx:end_idx+1]

       # Load first image to get dimensions
       img = np.array(Image.open(selected[0]))
       height, width = img.shape
       depth = len(selected)

       # Pre-allocate 3D array
       stack = np.zeros((depth, height, width), dtype=img.dtype)

       # Load all slices
       for i, file in enumerate(selected):
           stack[i] = np.array(Image.open(file))

       return stack

   # Custom analysis
   stack = load_stack("/data/processed/sample_001", 100, 200)
   print(f"Stack shape: {stack.shape}")
   print(f"Mean intensity: {stack.mean():.2f}")
   print(f"Max projection:\n{stack.max(axis=0)}")

**3D morphological operations:**

.. code-block:: python

   from scipy import ndimage

   # Load stack from CTHarvester export
   stack = load_stack("/data/processed/sample_001", 100, 200)

   # Apply 3D median filter
   filtered = ndimage.median_filter(stack, size=3)

   # Binary thresholding
   threshold = 128
   binary = stack > threshold

   # Morphological closing (fill holes)
   structure = np.ones((3, 3, 3))
   closed = ndimage.binary_closing(binary, structure=structure)

   # Label connected components
   labeled, num_features = ndimage.label(closed)
   print(f"Found {num_features} separate structures")

Custom Analysis Pipelines
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Example: Automated porosity analysis**

.. code-block:: python

   #!/usr/bin/env python
   """
   Automated porosity analysis pipeline

   CTHarvester → Export → NumPy → Analysis → Report
   """
   import numpy as np
   from PIL import Image
   from pathlib import Path
   import json

   def calculate_porosity(stack, threshold):
       """Calculate 3D porosity from thresholded stack"""
       binary = stack < threshold  # Pores are dark
       porosity = binary.sum() / binary.size
       return porosity * 100  # As percentage

   def analyze_sample(directory, sample_name, threshold=80):
       """Analyze single sample"""
       files = sorted(Path(directory).glob("*.tif"))
       stack = np.array([np.array(Image.open(f)) for f in files])

       porosity = calculate_porosity(stack, threshold)

       return {
           "sample": sample_name,
           "slice_count": len(files),
           "porosity_percent": round(porosity, 2),
           "mean_intensity": float(stack.mean()),
           "std_intensity": float(stack.std())
       }

   # Batch analysis
   samples = [
       ("/data/processed/sample_001", "Sample A"),
       ("/data/processed/sample_002", "Sample B"),
       ("/data/processed/sample_003", "Sample C"),
   ]

   results = [analyze_sample(dir, name) for dir, name in samples]

   # Export results
   with open("porosity_results.json", "w") as f:
       json.dump(results, f, indent=2)

   print("Analysis complete:")
   for result in results:
       print(f"  {result['sample']}: {result['porosity_percent']}% porosity")

Debugging and Diagnostics
--------------------------

Advanced Logging
~~~~~~~~~~~~~~~~

**Enable debug logging:**

.. code-block:: bash

   # Via environment variable
   export CTHARVESTER_LOG_LEVEL=DEBUG
   python CTHarvester.py

   # Or via settings
   # Settings → Advanced → Log level: DEBUG

**View logs in real-time:**

.. code-block:: bash

   # Linux/macOS
   tail -f ~/.local/share/PaleoBytes/CTHarvester/logs/ctharvester_*.log

   # Windows PowerShell
   Get-Content -Path "$env:APPDATA\PaleoBytes\CTHarvester\logs\ctharvester_*.log" -Wait

**Parse logs for errors:**

.. code-block:: bash

   # Find all errors
   grep "ERROR" ~/.local/share/PaleoBytes/CTHarvester/logs/*.log

   # Find memory-related issues
   grep -i "memory\|oom\|malloc" ~/.local/share/PaleoBytes/CTHarvester/logs/*.log

   # Find file I/O errors
   grep -i "permission\|not found\|corrupted" ~/.local/share/PaleoBytes/CTHarvester/logs/*.log

Performance Profiling
~~~~~~~~~~~~~~~~~~~~~

**Profile thumbnail generation:**

.. code-block:: python

   #!/usr/bin/env python
   """
   Profile thumbnail generation performance
   """
   import time
   import psutil
   from core.file_handler import FileHandler
   from core.thumbnail_manager import ThumbnailManager

   def profile_thumbnail_generation(directory):
       """Profile thumbnail generation with detailed metrics"""
       handler = FileHandler()
       manager = ThumbnailManager(handler)

       # System metrics before
       process = psutil.Process()
       mem_before = process.memory_info().rss / 1024 / 1024  # MB

       # Time the operation
       start = time.time()
       handler.open_directory(directory)
       manager.generate_thumbnails()
       elapsed = time.time() - start

       # System metrics after
       mem_after = process.memory_info().rss / 1024 / 1024  # MB

       # Calculate stats
       image_count = handler.get_image_count()
       time_per_image = elapsed / image_count * 1000  # ms

       print(f"Performance Profile:")
       print(f"  Images: {image_count}")
       print(f"  Total time: {elapsed:.2f} seconds")
       print(f"  Time per image: {time_per_image:.2f} ms")
       print(f"  Memory before: {mem_before:.1f} MB")
       print(f"  Memory after: {mem_after:.1f} MB")
       print(f"  Memory increase: {mem_after - mem_before:.1f} MB")

   profile_thumbnail_generation("/data/ct_scans/sample_001")

**Memory profiling:**

.. code-block:: python

   # Install memory_profiler
   # pip install memory-profiler

   from memory_profiler import profile

   @profile
   def memory_intensive_operation():
       """Function decorated with @profile shows line-by-line memory usage"""
       handler = FileHandler()
       handler.open_directory("/data/ct_scans/sample_001")
       # ... rest of operation

   memory_intensive_operation()

Safe Mode and Recovery
~~~~~~~~~~~~~~~~~~~~~~

**Run in safe mode (minimal features):**

.. code-block:: bash

   # Disable all optimizations
   python CTHarvester.py --safe-mode

   # Or individual options
   python CTHarvester.py --no-rust --threads 1 --no-3d

**Reset to factory settings:**

.. code-block:: bash

   # Delete config file
   # Windows
   del %APPDATA%\CTHarvester\settings.yaml

   # Linux/macOS
   rm ~/.config/CTHarvester/settings.yaml

   # Launch CTHarvester - settings regenerated with defaults

**Clear thumbnail cache:**

.. code-block:: bash

   # Delete all cached thumbnails
   find /data/ct_scans/ -name ".thumbnail" -type d -exec rm -rf {} +

**Database repair (if using internal database):**

.. code-block:: bash

   # Check for corrupted database
   sqlite3 ~/.config/CTHarvester/cache.db "PRAGMA integrity_check;"

   # Rebuild if corrupted
   rm ~/.config/CTHarvester/cache.db
   # CTHarvester will regenerate on next launch

Tips and Tricks
---------------

Keyboard Power User Shortcuts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beyond basic shortcuts, these advanced combinations increase efficiency:

**Quick navigation:**

* ``Ctrl+Home``: Jump to first slice
* ``Ctrl+End``: Jump to last slice
* ``Ctrl+Left/Right``: Jump 10 slices
* ``Shift+Left/Right``: Jump 100 slices (if dataset large enough)

**Rapid ROI setting:**

.. code-block:: text

   1. Navigate to approximate bottom → Press B
   2. Use arrow keys to fine-tune → Press B again
   3. Navigate to approximate top → Press T
   4. Fine-tune → Press T again

**Threshold shortcuts:**

* ``Up/Down arrows``: Adjust threshold (fine control)
* ``Shift+Up/Down``: Adjust threshold (coarse steps)
* ``Ctrl+0``: Reset threshold to default (128)

**View management:**

* ``F3``: Toggle 3D view
* ``F11``: Fullscreen mode
* ``Ctrl+W``: Toggle wireframe in 3D view
* ``Ctrl+B``: Toggle bounding box visibility

Hidden Features
~~~~~~~~~~~~~~~

**Double-click behaviors:**

* Double-click thumbnail: Jump to that slice
* Double-click 3D view: Reset camera
* Double-click status bar: Copy current slice info to clipboard

**Middle-click actions:**

* Middle-click slider: Jump to that position
* Middle-click 3D view: Toggle orthographic/perspective

**Right-click context menus:**

* Right-click file list: Show file in Explorer/Finder
* Right-click thumbnail: Regenerate individual thumbnail
* Right-click 3D view: Export current view as image

**Drag-and-drop:**

* Drag folder onto window: Open that directory
* Drag image onto window: Jump to that slice (if in current set)

Workflow Optimization
~~~~~~~~~~~~~~~~~~~~~

**Efficient large dataset exploration:**

.. code-block:: text

   1. Open directory (generates low-res preview)
   2. Level 3-5: Quick scan entire dataset
   3. Identify interesting region
   4. Level 1-2: Examine region in detail
   5. Set ROI boundaries
   6. Level 0: Fine-tune boundaries
   7. Export

**Multi-stage processing:**

.. code-block:: text

   Stage 1: Quick exploration
     - Use Python fallback (no Rust needed)
     - Small thumbnails (300px)
     - Quick decisions

   Stage 2: Detailed analysis
     - Install Rust module
     - Larger thumbnails (800px)
     - Precise ROI definition

   Stage 3: Final export
     - Full resolution
     - Multiple outputs (images + mesh)

**Dataset organization:**

.. code-block:: text

   project/
   ├── 01_raw/           # Original CT scans (never modify)
   ├── 02_reviewed/      # Reviewed datasets (thumbnails generated)
   ├── 03_processed/     # Cropped/exported data
   ├── 04_analysis/      # Analysis results (measurements, renders)
   └── 05_final/         # Publication-ready outputs

Further Resources
-----------------

**Documentation:**

* Installation Guide: Detailed setup instructions
* User Guide: Basic usage and workflow
* Troubleshooting Guide: Problem-solving
* FAQ: Common questions

**Community:**

* GitHub Discussions: Ask questions, share workflows
* GitHub Issues: Report bugs, request features

**Development:**

* Developer Guide: Architecture and API
* CONTRIBUTING.md: Contribution guidelines
* GitHub Repository: Source code and releases

**Contact:**

* Email: jikhanjung@gmail.com
* GitHub: @jikhanjung
