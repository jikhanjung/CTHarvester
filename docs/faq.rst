Frequently Asked Questions (FAQ)
=================================

.. contents:: Table of Contents
   :local:
   :depth: 2

General Questions
-----------------

What is CTHarvester?
~~~~~~~~~~~~~~~~~~~~

CTHarvester is a preprocessing tool for CT (Computed Tomography) image stacks designed for users with limited memory resources. It enables efficient cropping and resampling of large CT datasets without loading entire volumes into memory, using Level of Detail (LoD) techniques for fast preview and navigation.

**Key features:**

* Memory-efficient processing (works on 4GB RAM systems)
* Fast preview using multi-resolution thumbnails
* Interactive crop region selection
* 3D visualization and mesh export
* Batch processing support

Who is CTHarvester for?
~~~~~~~~~~~~~~~~~~~~~~~~

CTHarvester is designed for:

* **Researchers** working with CT imaging data
* **Paleontologists** studying fossil specimens
* **Medical imaging professionals** (for research, not diagnosis)
* **Students** learning about CT data processing
* **Anyone** working with large CT datasets on limited hardware

What makes CTHarvester different from other CT software?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Traditional CT software problems:**

* Requires loading entire dataset into RAM (often 10GB+)
* Slow preview and navigation
* Expensive commercial licenses
* Complex interfaces

**CTHarvester advantages:**

* Level of Detail (LoD) system for instant preview
* Works on low-spec machines (4GB RAM minimum)
* Free and open source (MIT license)
* Streamlined interface focused on cropping/resampling
* Does NOT require loading full dataset into memory

Is CTHarvester suitable for medical diagnosis?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**No.** CTHarvester is a research and preprocessing tool, **not** a medical device. It should not be used for clinical diagnosis, treatment planning, or any medical decision-making.

For medical diagnosis, use FDA-approved DICOM viewers and workstations.

Installation and Setup
----------------------

What are the system requirements?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Minimum Requirements:**

* **OS:** Windows 10+, macOS 10.14+, or Ubuntu 18.04+
* **CPU:** Dual-core processor (2.0 GHz+)
* **RAM:** 4GB minimum
* **Disk:** 500MB for application + space for CT data and thumbnails
* **Display:** 1280×720 resolution

**Recommended Requirements:**

* **CPU:** Quad-core processor (3.0 GHz+)
* **RAM:** 8GB or more
* **Disk:** SSD for best performance
* **Display:** 1920×1080 or higher

How much disk space do thumbnails use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thumbnail disk usage depends on dataset size and settings:

**Formula:** ``~1-5% of original dataset size``

**Examples:**

* 1000 images × 15MB each = 15GB dataset → ~150-750MB thumbnails
* 5000 images × 8MB each = 40GB dataset → ~400MB-2GB thumbnails

**Factors affecting thumbnail size:**

* Number of images
* Max thumbnail size setting (default 500px)
* Number of pyramid levels (default 10)
* Compression enabled/disabled

Can I delete thumbnail files?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes.** Thumbnails are stored in ``.thumbnail/`` subdirectory within your CT scan folder.

* Deleting thumbnails will **not** affect original images
* Thumbnails will be regenerated next time you open that directory
* Regeneration takes time (1-10 minutes depending on dataset)

**When to delete thumbnails:**

* Free up disk space
* Settings changed (thumbnail size, levels, format)
* Thumbnails corrupted or not displaying correctly

How do I install CTHarvester?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Binary Installation (Easiest):**

1. Download from https://github.com/jikhanjung/CTHarvester/releases
2. Windows: Run installer ``CTHarvester_Setup.exe``
3. macOS: Open DMG and drag to Applications
4. Linux: Download AppImage, make executable, and run

**From Source (For Developers):**

.. code-block:: bash

   git clone https://github.com/jikhanjung/CTHarvester.git
   cd CTHarvester
   pip install -r requirements.txt
   python CTHarvester.py

See the Installation Guide for detailed instructions.

Do I need to install Rust?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Optional but highly recommended.**

* **Without Rust:** Thumbnail generation uses Python (slower, 1-2 seconds per image)
* **With Rust:** 10-50x faster thumbnail generation (0.1-0.5 seconds per image)

**Installation:**

.. code-block:: bash

   # Install Rust
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

   # Build Rust module
   pip install maturin
   cd rust_thumbnail
   maturin develop --release

For large datasets (1000+ images), Rust module is strongly recommended.

File Formats and Compatibility
-------------------------------

What file formats are supported?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input Formats:**

* **TIF/TIFF** (8-bit or 16-bit grayscale) - **Recommended**
* **PNG** (8-bit or 16-bit grayscale)
* **JPG/JPEG** (8-bit, converted to grayscale)
* **BMP** (8-bit, converted to grayscale)

**Output Formats:**

* Same as input for image stacks
* **3D Export:** OBJ, PLY, STL

**Recommended:** Use TIF/TIFF for best quality and compatibility with scientific imaging.

Can CTHarvester read DICOM files?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Not currently.** DICOM support is planned for future versions.

**Workaround:**

1. Convert DICOM to TIFF using ImageJ, Fiji, or dcm2niix:

   .. code-block:: bash

      # Using dcm2niix
      dcm2niix -f %f_%p_%t_%s -o output_dir input_dir

2. Import converted TIFF sequence into CTHarvester

Does CTHarvester work with RGB/color images?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Sort of.** CTHarvester is designed for grayscale CT data.

* RGB images are automatically converted to grayscale
* Conversion uses standard formula: ``0.299R + 0.587G + 0.114B``
* Color information is lost

For true color image processing, use ImageJ or similar tools.

Can I process 16-bit images?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes!** CTHarvester fully supports:

* 8-bit grayscale (0-255)
* 16-bit grayscale (0-65535)

16-bit images are preserved during:

* Thumbnail generation
* Cropping
* Resampling
* Export

What file naming pattern is required?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CTHarvester expects **sequential numeric patterns**:

**Valid Patterns:**

* ``slice_0001.tif``, ``slice_0002.tif``, ``slice_0003.tif``
* ``image001.png``, ``image002.png``, ``image003.png``
* ``CT_001.tif``, ``CT_002.tif``, ``CT_003.tif``
* ``0001.tif``, ``0002.tif``, ``0003.tif`` (numbers only, OK)

**Invalid Patterns:**

* ``slice_a.tif``, ``slice_b.tif`` (no letters instead of numbers)
* ``img1.tif``, ``img10.tif``, ``img2.tif`` (not zero-padded, wrong sort order)
* ``scan.tif``, ``scan.tif`` (duplicate names)

**Requirements:**

* Must have sequential numbers
* Numbers must be zero-padded (same length)
* No gaps in sequence

**Renaming files:**

Use batch rename tools:

* Windows: PowerRename (PowerToys)
* macOS: Finder bulk rename
* Linux: ``rename`` command or Thunar bulk rename

Performance and Optimization
-----------------------------

How long does thumbnail generation take?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**With Rust module (recommended):**

* 500 images: 1-2 minutes
* 1000 images: 2-5 minutes
* 2000 images: 5-10 minutes
* 5000 images: 15-25 minutes

**Without Rust module (Python fallback):**

* 500 images: 10-15 minutes
* 1000 images: 20-40 minutes
* 2000 images: 40-80 minutes
* 5000 images: 2-3 hours

**Factors affecting speed:**

* Image resolution (larger = slower)
* Bit depth (16-bit slower than 8-bit)
* Disk speed (SSD vs HDD)
* CPU performance
* Number of worker threads

**Abnormally slow (8-10 sec per image)?**

See Troubleshooting Guide → Performance Issues

Why is thumbnail generation suddenly slow?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Common causes:**

1. **Rust module not loading**

   Check console for: "Rust thumbnail module not available, using Python fallback"

   **Solution:** Reinstall Rust module

2. **System sleep/resume (Windows)**

   After system sleep, performance may degrade

   **Solution:** Reboot computer

3. **Disk issues**

   * USB 2.0 drive (slow I/O)
   * Network drive (high latency)
   * Disk fragmentation

   **Solution:** Use local SSD, run disk check

4. **Background processes**

   * Windows Search indexing
   * Antivirus scanning
   * Windows Updates

   **Solution:** Pause background tasks, close other apps

How much RAM does CTHarvester use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Typical Memory Usage:**

* **Base application:** 100-200 MB
* **Thumbnail generation:** 500 MB - 2 GB (depends on settings)
* **3D visualization:** 200-500 MB (depends on mesh complexity)
* **Total:** 1-3 GB typical, 4-6 GB maximum

**Settings affecting memory:**

* Worker threads (more = more RAM)
* Max thumbnail size (larger = more RAM)
* Memory limit setting (user-configurable)

**Recommendations:**

* 4GB RAM: Set memory limit to 2GB, use 1-2 threads
* 8GB RAM: Default settings work well
* 16GB+ RAM: Can use higher thread counts

Can I process larger datasets faster?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes! Optimization tips:**

1. **Enable Rust module** (10-50x speedup)
2. **Use SSD** instead of HDD
3. **Increase worker threads** (Settings → Processing)

   * Recommended: 2-4 threads
   * Maximum: CPU core count

4. **Adjust thumbnail settings:**

   * Reduce max thumbnail size to 300-400px
   * Reduce sample size to 10-15
   * Disable compression during generation

5. **Close other applications** to free RAM
6. **Process locally** (not over network)

What if I run out of memory?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Solutions:**

1. **Reduce memory limit** (Settings → Processing → Memory limit)
2. **Reduce worker threads** to 1-2
3. **Reduce thumbnail size** to 300px
4. **Process in batches** (split dataset into folders)
5. **Close other applications**
6. **Restart CTHarvester** (to clear memory)

For huge datasets (10,000+ images), use batch processing approach.

Usage and Workflow
------------------

What is the basic workflow?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Step-by-step:**

1. **Open Directory** → Select CT image folder
2. **Wait** for thumbnail generation (first time only)
3. **Navigate** through slices using timeline slider
4. **Set Bottom** → Mark start of region of interest
5. **Set Top** → Mark end of region of interest
6. **Draw ROI** (optional) → Select area within images
7. **Adjust Threshold** → Fine-tune 3D visualization
8. **Save/Export:**

   * Save cropped image stack → Selected slices only
   * Export 3D Model → Generate mesh (OBJ, PLY, STL)

**Total time:** 5-10 minutes for typical workflow

Can I process multiple datasets in parallel?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Currently, no.** CTHarvester processes one dataset at a time.

**Workaround for batch processing:**

1. Process first dataset
2. Close CTHarvester
3. Repeat for each dataset

**Future feature:** Command-line batch processing mode is planned.

What does "Level of Detail (LoD)" mean?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Level of Detail (LoD)** is a multi-resolution pyramid system:

* **Level 0:** Full resolution (slowest to load)
* **Level 1:** 1/2 resolution
* **Level 2:** 1/4 resolution
* **Level 3:** 1/8 resolution
* ... and so on

**Benefits:**

* **Fast navigation** at low levels
* **Smooth scrolling** through large datasets
* **Memory efficient** (only loads current level)
* **Progressive loading** (coarse to fine detail)

**When to use which level:**

* **Initial exploration:** Level 3-5 (fast)
* **Setting boundaries:** Level 2-3 (medium)
* **Fine adjustment:** Level 0-1 (slow but accurate)

How do I select a region of interest (ROI)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Two types of selection:**

1. **Slice range (vertical bounds):**

   * Navigate to bottom slice → Click "Set Bottom"
   * Navigate to top slice → Click "Set Top"
   * Shown as: "Crop indices: 100~200"

2. **Area within slices (horizontal ROI):**

   * Click and drag on image viewer to draw rectangle
   * Adjust by dragging corners
   * Reset button clears ROI

**Both types can be combined:**

* Slice range: Z-axis selection
* ROI area: X-Y plane selection
* Result: 3D bounding box

Can I undo my crop selection?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes:**

* **Reset button** → Clears bottom/top boundaries and ROI rectangle
* **Simply reselect** → Override previous selection
* **Keyboard shortcut:** Ctrl+R

**Note:** Reset does not affect saved/exported files, only current selection.

What does "Inversion" do?
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Inversion checkbox** inverts grayscale values:

* **Normal:** Dark = less dense, Bright = more dense
* **Inverted:** Dark = more dense, Bright = less dense

**When to use inversion:**

* Negative CT scans
* Phase-contrast CT data
* When your specimen appears "inside-out"

**How it works:**

* Mathematically: ``inverted_value = max_value - original_value``
* For 8-bit: ``inverted = 255 - original``
* For 16-bit: ``inverted = 65535 - original``

Output and Export
-----------------

What output does CTHarvester create?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Image Stack Export:**

* Cropped image sequence (same format as input)
* Only includes selected slice range
* Optionally cropped to ROI area
* Sequential numbering (001, 002, 003...)

**3D Model Export:**

* Mesh file (OBJ, PLY, or STL format)
* Generated using marching cubes algorithm
* Includes only visible structures above threshold

**Thumbnails (automatic):**

* Multi-level thumbnail pyramid
* Stored in ``.thumbnail/`` subdirectory
* Used for fast navigation

Can I export at different resolutions?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Planned feature:** Multi-resolution export coming in future version.

**Current workaround:**

1. Export full resolution crop
2. Use ImageJ/Fiji to resample:

   .. code-block::

      Image → Scale → Choose dimensions

3. Or use command-line tools:

   .. code-block:: bash

      # ImageMagick example
      mogrify -resize 50% *.tif

What can I do with the exported 3D model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Software compatible with OBJ/PLY/STL:**

* **3D Viewing:**

  * Blender (free, open source)
  * MeshLab (free, open source)
  * 3D Viewer (Windows built-in)

* **3D Printing:**

  * Cura (free)
  * PrusaSlicer (free)
  * Simplify3D (commercial)

* **Scientific Analysis:**

  * CloudCompare (free)
  * Geomagic (commercial)
  * Avizo (commercial)

* **Further Processing:**

  * Mesh decimation (reduce polygon count)
  * Smoothing and cleanup
  * Measurements and analysis
  * Animation and rendering

Why is my exported 3D model so large?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** High mesh complexity (millions of polygons)

**Factors affecting mesh size:**

* Low threshold → More voxels → More polygons
* High resolution input → More detail → More polygons
* Large crop region → More volume → More polygons

**Solutions:**

1. **Increase threshold** → Fewer polygons
2. **Reduce crop region** → Smaller volume
3. **Decimate mesh** in Blender/MeshLab:

   * Blender: Modifiers → Decimate → Ratio 0.5
   * MeshLab: Filters → Remeshing → Quadric Edge Collapse Decimation

4. **Use STL format** instead of OBJ (more compact)

Can I export only a single slice?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes:**

1. Navigate to desired slice
2. Click "Set Bottom"
3. Stay on same slice (do not navigate away)
4. Click "Set Top"
5. Save cropped image stack

Result: One image file exported

Settings and Customization
---------------------------

What settings should I change?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Most users:** Default settings work fine

**Low-end systems (4GB RAM):**

* Processing → Memory limit: 2 GB
* Processing → Worker threads: 1-2
* Thumbnails → Max size: 300 px

**High-end systems (16GB+ RAM):**

* Processing → Worker threads: 4-8
* Thumbnails → Max size: 800 px
* Enable anti-aliasing (Rendering)

**Network/USB drive:**

* Processing → Worker threads: 1 (avoid contention)
* Thumbnails → Disable compression (faster)

How do I reset settings to defaults?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Method 1: In application**

* Settings dialog → "Reset to Defaults" button
* Confirm → All settings restored

**Method 2: Delete config file**

.. code-block:: bash

   # Windows
   del %APPDATA%\CTHarvester\settings.yaml

   # Linux/macOS
   rm ~/.config/CTHarvester/settings.yaml

Settings will be regenerated with defaults on next launch.

Can I save and share my settings?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes:**

1. Settings dialog → "Export Settings..."
2. Save as ``my_settings.yaml``
3. Share file with colleagues

**To import:**

1. Settings dialog → "Import Settings..."
2. Select YAML file
3. Settings applied immediately

**Use cases:**

* Share lab-wide settings
* Backup settings before upgrade
* Switch between different workflows

Where are logs stored?
~~~~~~~~~~~~~~~~~~~~~~~

**Log locations:**

* **Windows:** ``%APPDATA%\PaleoBytes\CTHarvester\logs\``
* **Linux/macOS:** ``~/.local/share/PaleoBytes/CTHarvester/logs/``

**Access logs:**

* Help menu → "View Logs" (opens directory)
* Or navigate manually to above path

**Log files:**

* Rotating logs (max 5 files × 10MB = 50MB total)
* Named with timestamps: ``ctharvester_YYYYMMDD_HHMMSS.log``

Troubleshooting and Support
----------------------------

Where do I get help?
~~~~~~~~~~~~~~~~~~~~

**Resources (in order):**

1. **This FAQ** - Quick answers to common questions
2. **Troubleshooting Guide** - Detailed problem-solving
3. **GitHub Issues** - Search existing problems/solutions

   https://github.com/jikhanjung/CTHarvester/issues

4. **GitHub Discussions** - Ask questions, share workflows

   https://github.com/jikhanjung/CTHarvester/discussions

5. **Email Support** - jikhanjung@gmail.com

   (Please try above resources first)

How do I report a bug?
~~~~~~~~~~~~~~~~~~~~~~

**GitHub Issues:** https://github.com/jikhanjung/CTHarvester/issues/new

**Include this information:**

1. **System info:**

   * Operating system and version
   * Python version (``python --version``)
   * CTHarvester version

2. **Problem description:**

   * What you were trying to do
   * What actually happened
   * Error message (if any)

3. **Steps to reproduce:**

   1. Open directory...
   2. Click button...
   3. Error appears...

4. **Log files:**

   * Attach relevant log files
   * Location: Help → View Logs

5. **Screenshots** (if UI-related)

**Good bug reports get fixed faster!**

Why does CTHarvester crash?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Common causes:**

1. **Out of memory** → Reduce memory limit, close other apps
2. **Corrupted images** → Check image files, skip corrupted files
3. **Disk full** → Free up space
4. **OpenGL driver issues** → Update graphics drivers
5. **Python package conflicts** → Use virtual environment

**Debugging steps:**

1. Check log files for error messages
2. Try with different dataset (isolate problem)
3. Run with debug logging enabled
4. Report crash with log files attached

See Troubleshooting Guide for detailed solutions.

Is my data sent anywhere?
~~~~~~~~~~~~~~~~~~~~~~~~~~

**No. Absolutely not.**

* All processing is **100% local**
* No internet connection required
* No telemetry or analytics
* Your data never leaves your computer

**Open source = transparent:**

* You can review the source code: https://github.com/jikhanjung/CTHarvester
* No hidden network calls
* MIT license - free to audit

Development and Contributing
-----------------------------

Is CTHarvester open source?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes!**

* **License:** MIT License (permissive)
* **Repository:** https://github.com/jikhanjung/CTHarvester
* **Free to use:** Commercial and non-commercial
* **Free to modify:** Change, extend, redistribute

**This means you can:**

* Use in research (published papers)
* Use in commercial projects
* Modify for your specific needs
* Redistribute (must include license)

Can I contribute to CTHarvester?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Absolutely! Contributions welcome:**

**Ways to contribute:**

1. **Report bugs** - GitHub Issues
2. **Suggest features** - GitHub Discussions
3. **Fix bugs** - Submit Pull Request
4. **Add features** - Submit Pull Request
5. **Improve documentation** - Edit .rst files
6. **Write tutorials** - Share workflows
7. **Translate UI** - Add new languages

**Getting started:**

1. Read CONTRIBUTING.md
2. Fork the repository
3. Make your changes
4. Submit Pull Request

**No contribution is too small!** Even fixing typos helps.

What features are planned?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**v1.0 Roadmap (Current):**

* User documentation improvements ← **Current focus**
* UI polish and accessibility
* Complete internationalization
* Performance benchmarking
* Beta testing program

**v1.1+ (Future):**

* DICOM format support
* Command-line batch processing
* GPU-accelerated thumbnail generation
* Plugin system
* Auto-skip corrupted files
* Non-sequential dataset support
* Volume rendering mode

See GitHub Issues and Milestones for details.

Why is CTHarvester called "CTHarvester"?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Name origin:**

* **CT** = Computed Tomography (the data type)
* **Harvester** = Gathering useful parts (cropping/extracting regions)

Metaphor: Like a farmer harvesting crops, CTHarvester helps you "harvest" the useful regions from large CT datasets.

**Alternative names considered:**

* CTCrop (too simple)
* CTSlicer (confusing with Slicer3D software)
* CTPrep (too generic)

Who develops CTHarvester?
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Primary developer:**

* Jikhan Jung (@jikhanjung)
* Part of PaleoBytes software suite
* Developed for paleontology research

**Contributors:**

* See GitHub contributors page
* Community bug reports and suggestions
* Open source contributions welcome

**Funding/Support:**

* Academic research project
* No commercial backing
* Developed in spare time

Advanced Topics
---------------

Can I use CTHarvester in a publication?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes! Please do.**

**How to cite:**

.. code-block:: bibtex

   @software{ctharvester2024,
     author = {Jung, Jikhan},
     title = {CTHarvester: Memory-Efficient CT Image Preprocessing Tool},
     year = {2024},
     publisher = {GitHub},
     url = {https://github.com/jikhanjung/CTHarvester},
     version = {0.2.3}
   }

**In text:**

"CT images were preprocessed using CTHarvester v0.2.3 (Jung, 2024), an open-source tool for memory-efficient CT data cropping and resampling."

**Please also:**

* Mention the software in Methods section
* Consider citing relevant papers if using specific algorithms

Can I automate CTHarvester with scripts?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Not yet.** GUI only in current version.

**Planned feature:** Command-line interface (CLI) for scripting:

.. code-block:: bash

   # Future CLI (not yet implemented)
   ctharvester process --input ./ct_data --output ./cropped \
                      --bottom 100 --top 200 \
                      --roi 100,100,500,500

**Current workaround:**

* Use Python API directly
* Import modules: ``from core.file_handler import FileHandler``
* Write custom scripts

See developer documentation for API details.

How does the Rust module work?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Architecture:**

* **Python:** UI, file handling, coordination
* **Rust:** Performance-critical thumbnail generation
* **Bridge:** Maturin (Rust-Python bindings)

**Why Rust?**

* 10-50x faster than Python for image processing
* Better memory management
* Parallel processing without GIL limitations
* Still memory-safe (no crashes)

**Technical details:**

* Uses rayon crate for parallelism
* Memory-mapped file I/O
* SIMD optimizations for array operations
* Compiled to native code

**When Rust not available:**

* Automatic fallback to Python implementation
* Same results, just slower
* No functionality lost

What algorithms does CTHarvester use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Core Algorithms:**

1. **Multi-resolution Pyramid:**

   * Progressive downsampling (2x at each level)
   * Box filter or bilinear interpolation
   * Lazy generation (on-demand)

2. **Marching Cubes (3D mesh):**

   * Isosurface extraction
   * Threshold as isovalue
   * Triangle mesh generation

3. **Image Resampling:**

   * Nearest neighbor (fast)
   * Bilinear interpolation (smooth)
   * Preserves bit depth (8/16-bit)

4. **Region of Interest (ROI):**

   * Bounding box intersection
   * Per-slice cropping
   * Boundary adjustment

**Libraries used:**

* NumPy (array operations)
* PyMCubes (marching cubes)
* PIL/Pillow (image I/O)
* SciPy (scientific functions)

Can I run CTHarvester on a server?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Not currently.** CTHarvester requires GUI environment.

**Future feature:** Headless mode for server deployment:

* Command-line batch processing
* No GUI required
* Docker container support

**Current workarounds:**

* Use VNC/Remote Desktop for GUI access
* Or use X11 forwarding over SSH:

  .. code-block:: bash

     ssh -X user@server
     python CTHarvester.py

How do I build CTHarvester from source?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Prerequisites:**

* Python 3.11+
* Rust toolchain (optional, for Rust module)

**Steps:**

.. code-block:: bash

   # 1. Clone repository
   git clone https://github.com/jikhanjung/CTHarvester.git
   cd CTHarvester

   # 2. Install Python dependencies
   pip install -r requirements.txt

   # 3. Build Rust module (optional but recommended)
   pip install maturin
   cd rust_thumbnail
   maturin develop --release
   cd ..

   # 4. Run tests
   pytest tests/ -v

   # 5. Build executable (optional)
   python build.py

See CONTRIBUTING.md for detailed build instructions.

License and Legal
-----------------

Can I use CTHarvester commercially?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes!** MIT License permits:

* **Commercial use** - Use in for-profit projects
* **Modification** - Adapt to your needs
* **Distribution** - Redistribute modified versions
* **Private use** - Use internally without sharing

**Requirements:**

* Include MIT License text
* Include copyright notice

**No warranty:** Software provided "as-is"

Can I sell CTHarvester?
~~~~~~~~~~~~~~~~~~~~~~~

**Technically yes, but discouraged:**

* MIT license allows redistribution
* But software is free on GitHub
* Please don't mislead users

**Better approaches:**

* Offer CTHarvester as part of service (consulting, training)
* Contribute improvements back to project
* Sponsor development (contact maintainer)

What if CTHarvester damages my data?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Disclaimer:**

* Software provided "as-is" (MIT License)
* No warranty of any kind
* **Always backup original data**

**Best practices:**

* Keep original CT data unchanged
* Process copies in separate directory
* Verify results before deleting originals
* Test with small sample first

**In practice:**

* CTHarvester does not modify original files
* Only creates new files (thumbnails, exports)
* Risk is very low with normal use

Still Have Questions?
---------------------

**Check these resources:**

1. **Installation Guide** - Setup and configuration
2. **User Guide** - Detailed usage instructions
3. **Troubleshooting Guide** - Problem-solving
4. **Developer Guide** - Technical details

**Contact:**

* GitHub Issues: https://github.com/jikhanjung/CTHarvester/issues
* Discussions: https://github.com/jikhanjung/CTHarvester/discussions
* Email: jikhanjung@gmail.com

**This FAQ is open source!**

Found an error? Have suggestions? Submit a PR to improve this document.
