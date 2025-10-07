User Guide
==========

This guide provides comprehensive instructions for using CTHarvester.

Getting Started
---------------

Launching CTHarvester
~~~~~~~~~~~~~~~~~~~~~

**From source:**

.. code-block:: bash

   python CTHarvester.py

**From binary (Windows):**

Double-click ``CTHarvester.exe``

Main Window Overview
~~~~~~~~~~~~~~~~~~~~

The CTHarvester main window consists of several key components:

1. **Top Section**: Directory selection and file information
2. **Center Section**: Image viewer with slider controls
3. **Right Section**: 3D mesh visualization
4. **Bottom Section**: Crop controls and action buttons

Basic Workflow
--------------

Loading CT Scan Images
~~~~~~~~~~~~~~~~~~~~~~~

1. Click the **"Open Directory"** button
2. Navigate to the folder containing your CT scan images
3. Select the folder and click **"Select Folder"**

The application will:

* Scan the directory for image sequences
* Generate multi-level thumbnails for fast navigation
* Display a progress bar during thumbnail generation

.. note::
   First-time loading may take several minutes depending on:

   * Number of images
   * Image resolution
   * Disk speed
   * CPU performance

Navigating Images
~~~~~~~~~~~~~~~~~

**Timeline Slider (Vertical):**

* Drag the slider up/down to navigate through CT slices
* Click above/below the slider for page jumps
* Use keyboard shortcuts:

  * ``Up/Down arrows``: Move one slice
  * ``Page Up/Down``: Jump 10 slices
  * ``Home/End``: Go to first/last slice

**Level Selection:**

* Use the Level dropdown to switch between different thumbnail resolutions
* Level 0: Original resolution (slowest, highest quality)
* Level 1+: Progressively smaller thumbnails (faster navigation)

Setting Crop Bounds
~~~~~~~~~~~~~~~~~~~~

To select a subset of slices for export:

1. Navigate to the bottom slice you want to include
2. Click **"Set Bottom"**
3. Navigate to the top slice
4. Click **"Set Top"**

The status bar shows: ``Crop indices: X~Y``

Drawing Region of Interest (ROI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To select a specific area of each image:

1. Click and drag on the image viewer to draw a rectangle
2. The ROI boundary is shown in red
3. Adjust by dragging the corners
4. Click **"Reset"** to clear the ROI

3D Visualization
~~~~~~~~~~~~~~~~

The 3D mesh view shows a volumetric representation of your CT data:

**Adjusting Threshold:**

* Use the vertical threshold slider (right side)
* Higher values show denser materials
* Lower values show more transparent materials
* The 3D mesh updates in real-time

**3D View Controls:**

* Click and drag to rotate
* Scroll to zoom
* Right-click to pan
* Double-click to reset view

**Inversion:**

* Check **"Inv."** to invert the grayscale values
* Useful for viewing negative scans

Saving and Exporting
---------------------

Saving Cropped Image Stack
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Set crop bounds (top and bottom slices)
2. Draw ROI if needed
3. Check **"Open dir. after"** to open the folder after saving
4. Click **"Save cropped image stack"**
5. Select destination folder
6. Wait for processing to complete

The saved images will:

* Include only slices between bottom and top bounds
* Be cropped to the ROI if defined
* Maintain original bit depth and format
* Use sequential numbering

Exporting 3D Model
~~~~~~~~~~~~~~~~~~

1. Adjust the threshold to your desired level
2. Click **"Export 3D Model"**
3. Choose save location and filename
4. The model is exported as OBJ format

The exported OBJ file can be opened in:

* Blender
* MeshLab
* 3D printing software (Cura, PrusaSlicer)
* Most 3D modeling applications

Settings and Preferences
------------------------

Opening Preferences
~~~~~~~~~~~~~~~~~~~

Click the gear icon (⚙️) at the bottom right to open the Settings dialog.

General Settings
~~~~~~~~~~~~~~~~

**Language:**

* Auto (System): Uses your operating system language
* English: Force English interface
* 한국어: Force Korean interface

**Theme:**

* Light: Default theme
* Dark: Dark mode (future feature)

**Window:**

* Remember window position: Saves window location between sessions
* Remember window size: Saves window dimensions

Thumbnail Settings
~~~~~~~~~~~~~~~~~~

**Max thumbnail size:**

* Range: 100-2000 pixels
* Default: 500
* Larger values use more disk space but provide better quality

**Sample size:**

* Range: 10-100
* Default: 20
* Number of images to sample for initial thumbnails

**Max pyramid level:**

* Range: 1-20
* Default: 10
* Maximum number of thumbnail levels to generate

**Enable compression:**

* Reduces thumbnail file size
* Slightly slower generation

**Format:**

* TIF: Better quality, larger files
* PNG: Good compression, slower

Processing Settings
~~~~~~~~~~~~~~~~~~~

**Worker threads:**

* Auto: Uses CPU core count
* 1-16: Manual thread count
* More threads = faster processing (up to CPU core count)

**Memory limit:**

* Range: 1-64 GB
* Default: 4 GB
* Maximum memory for image processing

**Use high-performance Rust module:**

* Checked: Use Rust (10-50x faster)
* Unchecked: Use Python fallback

Rendering Settings
~~~~~~~~~~~~~~~~~~

**Default threshold:**

* Range: 0-255
* Default: 128
* Initial threshold for 3D mesh generation

**Enable anti-aliasing:**

* Smoother 3D rendering
* Slightly slower performance

**Show FPS counter:**

* Display frames per second in 3D view
* Useful for performance monitoring

Advanced Settings
~~~~~~~~~~~~~~~~~

**Logging:**

* Log level: DEBUG, INFO, WARNING, ERROR
* Console output: Enable/disable console logging

**Export:**

* Mesh format: STL, PLY, OBJ
* Image format: TIF, PNG, JPG
* Compression level: 0-9

Import/Export Settings
~~~~~~~~~~~~~~~~~~~~~~

**Export Settings:**

1. Click **"Export Settings..."**
2. Choose save location
3. Settings saved as ``ctharvester_settings.yaml``

**Import Settings:**

1. Click **"Import Settings..."**
2. Select YAML file
3. Settings applied immediately

**Reset to Defaults:**

1. Click **"Reset to Defaults"**
2. Confirm in dialog
3. All settings restored to defaults

Keyboard Shortcuts
------------------

File Operations
~~~~~~~~~~~~~~~

* ``Ctrl+O``: Open directory
* ``F5``: Reload current directory
* ``Ctrl+S``: Save cropped images
* ``Ctrl+E``: Export 3D mesh
* ``Ctrl+Q``: Quit application

Navigation
~~~~~~~~~~

* ``Left/Right``: Previous/Next slice
* ``Ctrl+Left/Right``: Jump backward/forward 10 slices
* ``Home/End``: First/Last slice

View
~~~~

* ``Ctrl++``: Zoom in
* ``Ctrl+-``: Zoom out
* ``Ctrl+0``: Fit to window
* ``F3``: Toggle 3D view

Crop Region (ROI)
~~~~~~~~~~~~~~~~~

* ``B``: Set bottom boundary (lower bound)
* ``T``: Set top boundary (upper bound)
* ``Ctrl+R``: Reset crop region

Threshold Adjustment
~~~~~~~~~~~~~~~~~~~~

* ``Up/Down``: Increase/Decrease threshold

Tools & Settings
~~~~~~~~~~~~~~~~

* ``Ctrl+T``: Generate thumbnails
* ``Ctrl+,``: Open preferences
* ``F1``: Show keyboard shortcuts help
* ``Ctrl+I``: About CTHarvester

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**"No valid image files found"**

* Ensure images follow naming pattern: ``prefix000001.tif``
* Check file extensions (.tif, .tiff, .png, .jpg, .bmp)
* Verify read permissions on directory

**Slow thumbnail generation**

* Use Rust module if available (10-50x faster)
* Reduce max thumbnail size
* Check disk speed (SSD recommended)
* Close other applications

**3D view not updating**

* Check threshold value (try different values)
* Verify enough images are loaded
* Try resetting view (double-click in 3D view)

**Out of memory errors**

* Reduce memory limit in settings
* Use smaller thumbnail sizes
* Process fewer slices at once
* Close other applications

**Settings not saving**

* Check write permissions on config directory
* Windows: ``%APPDATA%\\CTHarvester``
* Linux/macOS: ``~/.config/CTHarvester``

Getting Help
~~~~~~~~~~~~

If you encounter issues:

1. Check this documentation
2. Review logs in the console or log file
3. Search existing issues on GitHub
4. Create a new issue with:

   * Operating system and version
   * Python version
   * Error message or description
   * Steps to reproduce
   * Log file (if applicable)

Tips and Best Practices
------------------------

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

* Use SSD for best thumbnail generation speed
* Enable Rust module for 10-50x faster thumbnails
* Start with lower thumbnail resolution for initial exploration
* Generate full-resolution thumbnails only when needed
* Close unnecessary applications during processing

File Organization
~~~~~~~~~~~~~~~~~

* Keep CT scan images in dedicated folders
* Use consistent naming conventions
* Include metadata/log files with scans
* Back up original data before processing

3D Visualization
~~~~~~~~~~~~~~~~

* Experiment with different threshold values
* Use inversion for negative scans
* Try different viewing angles for better understanding
* Export models for analysis in specialized 3D software

FAQ
---

**Q: What file formats are supported?**

A: TIF/TIFF, PNG, JPG/JPEG, and BMP. TIF/TIFF recommended for medical imaging.

**Q: Can I process 16-bit images?**

A: Yes, CTHarvester supports both 8-bit and 16-bit images.

**Q: How long does thumbnail generation take?**

A: With Rust module: 1-5 minutes for 1000 images
   Without Rust: 10-50 minutes for 1000 images

   Time varies by image resolution, disk speed, and CPU performance.

**Q: Where are thumbnails stored?**

A: In a ``.thumbnail/`` subdirectory within your CT scan folder.

**Q: Can I delete thumbnail files?**

A: Yes, they will be regenerated when you reopen the directory.

**Q: What's the maximum image size supported?**

A: Tested up to 4096x4096 pixels. Larger images may work but require more memory.

**Q: Can I run CTHarvester on a server without display?**

A: Not currently. CTHarvester requires a GUI environment (X11, Wayland, or Windows display).

**Q: Is my data sent anywhere?**

A: No. CTHarvester processes all data locally. No internet connection required.
