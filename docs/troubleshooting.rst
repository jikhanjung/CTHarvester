Troubleshooting Guide
=====================

This guide provides solutions to common problems and errors you may encounter while using CTHarvester.

.. contents:: Table of Contents
   :local:
   :depth: 2

Installation Issues
-------------------

Python Import Errors
~~~~~~~~~~~~~~~~~~~~

**Problem:** ``ImportError: No module named 'PyQt5'`` or similar module not found errors

**Solution:**

1. Ensure you have installed all dependencies:

   .. code-block:: bash

      pip install -r requirements.txt

2. If using a virtual environment, verify it is activated:

   .. code-block:: bash

      # Windows
      venv\Scripts\activate

      # Linux/macOS
      source venv/bin/activate

3. Try reinstalling the specific missing package:

   .. code-block:: bash

      pip install PyQt5 --upgrade

**Problem:** ``ModuleNotFoundError: No module named 'OpenGL'``

**Solution (Linux):**

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install python3-opengl libglu1-mesa

   # Fedora
   sudo dnf install python3-pyopengl mesa-libGLU

**Solution (Windows/macOS):**

.. code-block:: bash

   pip install PyOpenGL PyOpenGL-accelerate

Rust Module Issues
~~~~~~~~~~~~~~~~~~

**Problem:** Rust module not loading, falling back to Python

**Symptoms:**

* Console message: "Rust thumbnail module not available, using Python fallback"
* Thumbnail generation is very slow (8-10 seconds per image)

**Solution 1: Install Rust toolchain**

.. code-block:: bash

   # Install Rust (if not installed)
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

   # Restart terminal, then verify installation
   rustc --version

**Solution 2: Build the Rust module**

.. code-block:: bash

   # Install maturin (Rust-Python bridge)
   pip install maturin

   # Build and install the module
   cd rust_thumbnail
   maturin develop --release
   cd ..

**Solution 3: Verify module is in correct location**

The compiled Rust module should be in one of these locations:

* Windows: ``rust_thumbnail/target/wheels/*.whl`` or directly in Python site-packages
* Linux/macOS: ``rust_thumbnail/target/wheels/*.whl`` or Python site-packages

**Problem:** Rust module build fails with compiler errors

**Common Causes:**

1. **Outdated Rust version** - Update Rust:

   .. code-block:: bash

      rustup update stable

2. **Missing C/C++ compiler** (Windows):

   * Install Microsoft Visual C++ Build Tools
   * Or install Visual Studio with C++ development tools

3. **Missing build essentials** (Linux):

   .. code-block:: bash

      # Ubuntu/Debian
      sudo apt-get install build-essential

      # Fedora
      sudo dnf install gcc gcc-c++ make

Permission Issues
~~~~~~~~~~~~~~~~~

**Problem:** "Permission denied" when opening directory or saving files

**Windows Solution:**

1. Right-click CTHarvester.exe → "Run as administrator" (not recommended for normal use)
2. Or change folder permissions:

   * Right-click folder → Properties → Security
   * Ensure your user has "Full control"

**Linux/macOS Solution:**

.. code-block:: bash

   # Check permissions
   ls -la /path/to/directory

   # Fix permissions if needed
   chmod -R u+rw /path/to/directory

**Problem:** Settings not saving

**Location of settings files:**

* Windows: ``%APPDATA%\CTHarvester\settings.yaml``
* Linux/macOS: ``~/.config/CTHarvester/settings.yaml``

**Solution:**

1. Check write permissions on the config directory
2. Manually create the directory if it doesn't exist:

   .. code-block:: bash

      # Windows (PowerShell)
      mkdir "$env:APPDATA\CTHarvester"

      # Linux/macOS
      mkdir -p ~/.config/CTHarvester

3. Delete corrupted settings file to regenerate defaults:

   .. code-block:: bash

      # Windows (PowerShell)
      rm "$env:APPDATA\CTHarvester\settings.yaml"

      # Linux/macOS
      rm ~/.config/CTHarvester/settings.yaml

Directory and File Loading Issues
----------------------------------

No Valid Image Files Found
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** "No valid image files found in directory" error when opening a folder

**Possible Causes:**

1. **Incorrect naming pattern**

   CTHarvester expects sequential image files with naming patterns like:

   * ``slice_0001.tif``
   * ``image_001.png``
   * ``CT0001.tif``

   The pattern must include:

   * A prefix (optional)
   * Sequential numbers (required)
   * File extension (.tif, .tiff, .png, .jpg, .bmp)

2. **Unsupported file formats**

   Only these formats are supported:

   * TIF/TIFF (recommended for medical imaging)
   * PNG
   * JPG/JPEG
   * BMP

**Solution:**

1. Check that files follow naming convention:

   * Files must have numeric sequence: ``001``, ``002``, ``003``, etc.
   * Numbers must be zero-padded to same length

2. Rename files if needed:

   .. code-block:: bash

      # Linux/macOS example
      # Rename files to proper format
      count=1
      for file in *.tif; do
          mv "$file" "slice_$(printf '%04d' $count).tif"
          ((count++))
      done

3. Verify file extensions are lowercase or uppercase consistently

**Problem:** Only some images are loaded, not all

**Causes:**

* Non-sequential numbering (gaps in sequence)
* Mixed file extensions in same directory
* Corrupted images breaking the sequence

**Solution:**

1. Ensure sequential numbering with no gaps
2. Place different file types in separate directories
3. Check for corrupted files:

   .. code-block:: bash

      # Test each image (Linux/macOS)
      for file in *.tif; do
          python -c "from PIL import Image; Image.open('$file')" || echo "Corrupted: $file"
      done

Corrupted Image Files
~~~~~~~~~~~~~~~~~~~~~

**Problem:** "Failed to load image" or "Corrupted image file" error

**Symptoms:**

* Application crashes when loading certain slices
* Error dialog about corrupted files
* Some thumbnails show as blank/black

**Solution:**

1. **Identify corrupted files:**

   Check the log files for error messages:

   * Windows: ``%APPDATA%\CTHarvester\logs\``
   * Linux/macOS: ``~/.config/CTHarvester/logs/``

   Look for lines containing "CorruptedImageError" or "Failed to load"

2. **Verify file integrity:**

   .. code-block:: bash

      # Check file size - corrupted files often have 0 bytes
      ls -lh /path/to/images/

3. **Try repairing with ImageMagick:**

   .. code-block:: bash

      # Install ImageMagick
      # Ubuntu: sudo apt-get install imagemagick
      # macOS: brew install imagemagick

      # Attempt repair
      convert corrupted.tif -strip repaired.tif

4. **Replace corrupted files:**

   * If possible, re-export from CT scanner
   * Or remove corrupted files from sequence (may break sequence)

5. **Skip corrupted files:**

   In future versions, CTHarvester will have an option to skip corrupted files automatically.

Invalid Image Format
~~~~~~~~~~~~~~~~~~~~

**Problem:** "Invalid image format" or "Unsupported bit depth" errors

**Cause:** Image has unsupported characteristics:

* 32-bit floating point TIFFs
* 24-bit or 48-bit RGB when grayscale expected
* Compressed formats not supported by PIL

**Solution:**

1. **Convert to supported format:**

   .. code-block:: bash

      # Convert to 8-bit or 16-bit grayscale TIFF
      convert input.tif -depth 16 -colorspace Gray output.tif

2. **Check image properties:**

   .. code-block:: python

      from PIL import Image
      img = Image.open('image.tif')
      print(f"Mode: {img.mode}")  # Should be 'L' or 'I;16'
      print(f"Size: {img.size}")
      print(f"Format: {img.format}")

3. **Supported image modes:**

   * ``L`` - 8-bit grayscale (0-255)
   * ``I;16`` - 16-bit grayscale (0-65535)
   * ``RGB`` - 24-bit color (will be converted to grayscale)

Performance Issues
------------------

Slow Thumbnail Generation
~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Thumbnail generation takes 8-10 seconds per image (extremely slow)

**Expected Performance:**

* **With Rust module:** 0.1-0.5 seconds per image
* **Without Rust (Python):** 1-2 seconds per image (acceptable)
* **Abnormally slow:** 8-10+ seconds per image (problem!)

**Solution 1: Enable Rust module (10-50x speedup)**

See "Rust Module Issues" section above for installation instructions.

**Solution 2: Check disk I/O**

.. code-block:: bash

   # Linux - check disk speed
   sudo hdparm -tT /dev/sda

   # Windows - check in Task Manager → Performance → Disk

**Possible causes:**

* USB 2.0 external drive (slow) - Use USB 3.0+ or internal SSD
* Network drive with high latency - Copy files locally first
* Disk fragmentation (Windows HDD) - Run defragmentation
* Too many threads - Reduce worker threads in settings

**Solution 3: Optimize settings**

1. Open Settings (gear icon ⚙️)
2. Adjust these settings:

   * **Worker threads:** Set to 2-4 (not more than CPU cores)
   * **Max thumbnail size:** Reduce to 300-400 pixels
   * **Sample size:** Reduce to 10-15
   * **Enable compression:** Disable for faster generation

**Solution 4: System performance**

1. Close other applications to free RAM
2. Check background processes (Windows Search, antivirus)
3. Reboot if system has been in sleep mode (Windows-specific issue)

**Problem:** Thumbnail generation was fast before, now suddenly slow

**Possible causes:**

1. **Windows sleep/resume issues:**

   After system sleep/resume, performance may degrade due to:

   * Memory fragmentation
   * SSD not resuming to full performance
   * Driver state issues

   **Solution:** Reboot the computer

2. **Rust module no longer loading:**

   Check console for "Rust thumbnail module not available" message

   **Solution:** Reinstall Rust module (see above)

3. **Disk cache issues:**

   .. code-block:: bash

      # Linux - clear page cache (requires sudo)
      sudo sync && sudo sysctl -w vm.drop_caches=3

Out of Memory Errors
~~~~~~~~~~~~~~~~~~~~

**Problem:** "Out of memory" or "MemoryError" when processing large datasets

**Solution 1: Reduce memory usage**

1. Open Settings → Processing
2. Adjust settings:

   * **Memory limit:** Reduce to 2-3 GB
   * **Worker threads:** Reduce to 1-2
   * **Max thumbnail size:** Reduce to 300 pixels

**Solution 2: Process in smaller batches**

1. Split large datasets into smaller folders
2. Process each folder separately
3. Combine results afterward

**Solution 3: Close other applications**

* Close web browsers (Chrome uses lots of RAM)
* Close unnecessary applications
* Check Task Manager/Activity Monitor for memory usage

**Solution 4: Upgrade RAM**

* 4GB RAM: Can process small datasets (<500 images)
* 8GB RAM: Recommended for medium datasets (<2000 images)
* 16GB+ RAM: For large datasets (5000+ images)

**Problem:** Memory usage keeps increasing over time

**Cause:** Memory leak in image processing

**Solution:**

1. Restart CTHarvester every few hours when processing very large datasets
2. Process in smaller batches
3. Update to latest version (memory leaks are being fixed)

UI freezing during processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Application becomes unresponsive during thumbnail generation

**Expected behavior:** UI should remain responsive with progress updates

**Solution 1: Check if truly frozen**

* Wait 30-60 seconds
* Check if progress bar is moving (slowly)
* Check console output for activity

**Solution 2: Increase responsiveness**

1. Settings → Processing
2. Reduce worker threads to 1 (forces sequential processing)
3. Enable "High priority UI updates" (if available)

**Solution 3: Force quit if truly frozen**

* Windows: Task Manager → End Task
* macOS: Force Quit (Cmd+Option+Esc)
* Linux: ``killall python`` or ``kill -9 <pid>``

**Problem:** Application frozen after clicking "Cancel"

**Cause:** Workers need time to finish current operation

**Solution:** Wait 10-30 seconds for workers to stop gracefully

3D Visualization Issues
-----------------------

3D View Not Updating
~~~~~~~~~~~~~~~~~~~~

**Problem:** 3D mesh not appearing or not updating when threshold changes

**Solution 1: Check threshold value**

1. Try different threshold values (0-255)
2. For dark images: Use lower thresholds (50-100)
3. For bright images: Use higher thresholds (150-200)
4. Enable "Inversion" checkbox if viewing negative scans

**Solution 2: Verify data loaded**

* Ensure enough slices are loaded (minimum ~10-20 for visible mesh)
* Check crop bounds include actual data
* Verify images are not completely black or white

**Solution 3: Reset 3D view**

* Double-click in 3D view area to reset camera
* Try different viewing angles by dragging
* Zoom in/out with scroll wheel

**Problem:** 3D view shows incorrect/garbled mesh

**Cause:** Invalid threshold or corrupted data

**Solution:**

1. Reset threshold to default (128)
2. Check original images for data integrity
3. Try different crop bounds
4. Verify bit depth is correct (8-bit vs 16-bit)

OpenGL Errors
~~~~~~~~~~~~~

**Problem:** "OpenGL error" or "Failed to initialize OpenGL context"

**Linux Solution:**

.. code-block:: bash

   # Install OpenGL libraries
   sudo apt-get install mesa-utils libglu1-mesa-dev freeglut3-dev mesa-common-dev

   # Test OpenGL
   glxinfo | grep "OpenGL version"

**Windows Solution:**

1. Update graphics drivers:

   * NVIDIA: Download from nvidia.com
   * AMD: Download from amd.com
   * Intel: Use Windows Update

2. Try forcing software rendering (slower but works):

   Set environment variable before launching CTHarvester:

   .. code-block:: batch

      set LIBGL_ALWAYS_SOFTWARE=1
      CTHarvester.exe

**macOS Solution:**

1. Update macOS to latest version
2. OpenGL should work out of the box on macOS 10.14+

**Problem:** Low FPS in 3D view (< 10 FPS)

**Solution:**

1. Settings → Rendering
2. Disable "Anti-aliasing"
3. Reduce mesh complexity by using higher threshold
4. Update graphics drivers
5. Check if integrated GPU is being used instead of dedicated GPU

File Export Issues
------------------

Save Cropped Image Stack Fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** "Failed to save image stack" or no images saved

**Solution 1: Check disk space**

.. code-block:: bash

   # Check available space
   # Windows: dir
   # Linux/macOS: df -h

Ensure enough space for output:

* Formula: ``image_count × width × height × bytes_per_pixel``
* Example: 1000 images × 2048 × 2048 × 2 bytes = ~8 GB

**Solution 2: Verify write permissions**

* Try saving to a different directory
* On Windows, avoid "Program Files" directory
* Use Documents or Desktop folder

**Solution 3: Check filename conflicts**

* Remove existing files with same names
* Or choose different output directory

**Problem:** Exported images are black/white/corrupted

**Cause:** Incorrect bit depth conversion or threshold issue

**Solution:**

1. Check original images are not corrupted
2. Verify crop bounds are correct
3. Try exporting small sample first (5-10 images)
4. Check bit depth matches source (8-bit vs 16-bit)

Export 3D Model Fails
~~~~~~~~~~~~~~~~~~~~~

**Problem:** "Failed to export 3D model" or OBJ file is empty

**Solution 1: Check threshold**

* Threshold too high/low may result in empty mesh
* Try different threshold values
* Ensure 3D preview shows visible mesh before export

**Solution 2: Verify mesh generation**

* Look for error messages in console/logs
* Check that marching cubes algorithm completed successfully
* Try with smaller dataset first

**Solution 3: File format issues**

* Ensure file extension is ``.obj``
* Try different export location
* Check disk space and permissions

**Problem:** 3D model is too large to open in other software

**Cause:** High-resolution mesh with millions of polygons

**Solution:**

1. Use higher threshold to reduce mesh complexity
2. Export smaller crop region
3. Use mesh decimation software (MeshLab, Blender) to reduce polygon count
4. Export in chunks and combine later

Settings and Configuration Issues
----------------------------------

Settings Not Persisting
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Settings reset to defaults every time you restart CTHarvester

**Solution 1: Check config file location**

.. code-block:: bash

   # Windows
   dir %APPDATA%\CTHarvester

   # Linux/macOS
   ls ~/.config/CTHarvester

**Solution 2: Fix permissions**

.. code-block:: bash

   # Linux/macOS
   chmod -R u+rw ~/.config/CTHarvester

   # Windows: Use file properties to grant full control

**Solution 3: Delete corrupted config**

.. code-block:: bash

   # This will regenerate default settings
   # Windows
   del %APPDATA%\CTHarvester\settings.yaml

   # Linux/macOS
   rm ~/.config/CTHarvester/settings.yaml

Cannot Import Settings
~~~~~~~~~~~~~~~~~~~~~~

**Problem:** "Failed to import settings" when loading YAML file

**Solution:**

1. Check YAML syntax:

   * Use YAML validator online
   * Ensure proper indentation (spaces, not tabs)
   * Check for special characters

2. Verify file is not corrupted:

   .. code-block:: bash

      # Check if file is valid YAML
      python -c "import yaml; yaml.safe_load(open('settings.yaml'))"

3. Try exporting settings first, then modifying the exported file

Language/Translation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** UI text shows untranslated strings or incorrect language

**Solution:**

1. Settings → General → Language
2. Select desired language
3. Restart CTHarvester

**Problem:** Mixed languages (some English, some Korean)

**Cause:** Incomplete translation coverage

**Solution:**

* Report missing translations as GitHub issue
* Provide English text and location in UI
* Temporary workaround: Use English language setting

Advanced Troubleshooting
-------------------------

Collecting Debug Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When reporting issues, include this information:

1. **System Information:**

   .. code-block:: bash

      # Python version
      python --version

      # OS version
      # Windows: winver
      # macOS: sw_vers
      # Linux: lsb_release -a

2. **CTHarvester version:**

   .. code-block:: bash

      python CTHarvester.py --version

3. **Log files:**

   * Windows: ``%APPDATA%\PaleoBytes\CTHarvester\logs\``
   * Linux/macOS: ``~/.local/share/PaleoBytes/CTHarvester/logs/``

4. **Package versions:**

   .. code-block:: bash

      pip list | grep -E "PyQt5|numpy|pillow|scipy|pymcubes"

Enabling Debug Logging
~~~~~~~~~~~~~~~~~~~~~~~

To get more detailed logs:

1. **Via Settings:**

   * Settings → Advanced → Logging
   * Set "Log level" to "DEBUG"
   * Enable "Console output"

2. **Via Environment Variable:**

   .. code-block:: bash

      # Before launching CTHarvester
      export CTHARVESTER_LOG_LEVEL=DEBUG
      python CTHarvester.py

3. **View logs:**

   * Help menu → "View Logs" (opens log directory)
   * Or manually navigate to log directory (see above)

Running in Safe Mode
~~~~~~~~~~~~~~~~~~~~

To disable all optimizations and run with minimal features:

.. code-block:: bash

   # Disable Rust module
   python CTHarvester.py --no-rust

   # Use single thread
   python CTHarvester.py --threads 1

   # Disable 3D view
   python CTHarvester.py --no-3d

   # Combine options
   python CTHarvester.py --no-rust --threads 1 --no-3d

Common Error Messages
---------------------

"Directory does not exist"
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Selected directory was moved or deleted

**Solution:** Browse to a different directory

"Permission denied"
~~~~~~~~~~~~~~~~~~~

**Cause:** Insufficient file system permissions

**Solution:** See "Permission Issues" section above

"Thumbnail generation failed"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Error during thumbnail processing (disk full, corrupted image, etc.)

**Solution:**

1. Check disk space
2. Verify images are not corrupted
3. Try with smaller sample size
4. Check logs for specific error

"Worker thread crashed"
~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Unexpected error in background thread

**Solution:**

1. Check logs for Python traceback
2. Restart CTHarvester
3. Try processing single-threaded (Settings → Processing → Worker threads: 1)
4. Report as bug with log file

Getting Additional Help
-----------------------

If this guide doesn't solve your problem:

1. **Check GitHub Issues:**

   https://github.com/jikhanjung/CTHarvester/issues

   Search for similar problems - they may already be solved

2. **Create New Issue:**

   Include:

   * Operating system and version
   * Python version (``python --version``)
   * CTHarvester version
   * Error message or description
   * Steps to reproduce
   * Log files (see "Collecting Debug Information" above)

3. **GitHub Discussions:**

   For questions and general discussion:

   https://github.com/jikhanjung/CTHarvester/discussions

4. **Email Support:**

   Contact: jikhanjung@gmail.com

   (Please try GitHub issues first for faster community support)

Known Issues and Limitations
-----------------------------

Current Limitations
~~~~~~~~~~~~~~~~~~~

1. **Maximum Image Resolution:**

   * Tested up to 4096×4096 pixels
   * Larger images may work but require more RAM

2. **File Naming:**

   * Must have sequential numbers
   * No support for non-sequential datasets yet

3. **3D Export Formats:**

   * OBJ, PLY, STL supported
   * No VRML, Collada, or other formats yet

4. **Platform-Specific:**

   * macOS builds not code-signed (requires manual approval)
   * Linux AppImage requires FUSE

5. **GUI Only:**

   * No command-line interface yet
   * Cannot run in headless mode

6. **Memory Usage:**

   * Full dataset not loaded into memory (by design)
   * But thumbnails require disk space

Planned Improvements
~~~~~~~~~~~~~~~~~~~~

See CHANGELOG and GitHub milestones for planned features:

* Command-line interface for batch processing
* Support for DICOM format
* Auto-detection and skipping of corrupted files
* Improved error recovery
* Better memory management for huge datasets
* GPU acceleration for thumbnail generation
* Plugin system for custom workflows

Contributing
------------

Found a bug or have suggestions? Contributions welcome!

* Report bugs: https://github.com/jikhanjung/CTHarvester/issues
* Submit fixes: https://github.com/jikhanjung/CTHarvester/pulls
* Improve docs: Edit this file and submit PR

See CONTRIBUTING.md for detailed contribution guidelines.
