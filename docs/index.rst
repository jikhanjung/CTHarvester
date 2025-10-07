CTHarvester Documentation
=========================

Welcome to CTHarvester's documentation!

CTHarvester is a PyQt5-based application for processing and visualizing CT (Computed Tomography) scan image stacks. It provides tools for thumbnail generation, 3D mesh visualization, and image stack management.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   user_guide
   advanced_features
   troubleshooting
   faq
   developer_guide
   changelog

Features
--------

* **Multi-level Thumbnail Generation**: Automatically generate thumbnail pyramids for fast navigation
* **3D Visualization**: Real-time 3D mesh generation using Marching Cubes algorithm
* **High Performance**: Rust-based thumbnail generation with Python fallback
* **User-Friendly**: Modern UI with progress tracking, keyboard shortcuts, and tooltips
* **Flexible Settings**: YAML-based configuration with import/export functionality
* **Multi-language Support**: English and Korean (한국어) interface

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/yourusername/CTHarvester.git
   cd CTHarvester

   # Install dependencies
   pip install -r requirements.txt

   # Run the application
   python CTHarvester.py

Basic Usage
~~~~~~~~~~~

1. **Open CT Scan Directory**

   Click "Open Directory" to select a folder containing CT scan images.
   The application will automatically generate multi-level thumbnails for fast navigation.

2. **Navigate Through Slices**

   Use the vertical timeline slider to browse through the CT stack.
   The 2D viewer shows the current slice, while the 3D viewer displays the mesh.

3. **Set Region of Interest (ROI)**

   Define the region you want to process by setting the lower and upper bounds:

   - **Set Lower Bound**: Click "Set Bottom" button or press the keyboard shortcut to mark the bottom slice of your ROI
   - **Set Upper Bound**: Click "Set Top" button or press the keyboard shortcut to mark the top slice of your ROI
   - The selected region will be highlighted in the timeline slider
   - You can adjust bounds by moving to a different slice and clicking the buttons again
   - Click "Reset" to clear the ROI selection

4. **Adjust Bounding Box (Optional)**

   Fine-tune the 2D bounding box around your region of interest:

   - The bounding box appears as a red rectangle in the 2D viewer
   - Drag the corners or edges to resize the box
   - The box defines the X-Y crop boundaries for your export
   - Combined with lower/upper bounds, this creates a 3D volume selection

5. **Adjust Visualization**

   - Use the **threshold slider** on the right to modify the isovalue for 3D mesh generation
   - Higher threshold values show denser materials
   - Lower threshold values reveal more internal structures
   - The 3D mesh updates in real-time as you adjust the threshold

6. **Export Your Data**

   Once you've defined your ROI and settings:

   - **Save Cropped Image Stack**: Exports only the selected slices within the bounding box
   - **Export 3D Model**: Saves the 3D mesh as OBJ, STL, or PLY format
   - The exported data includes only the region defined by your ROI settings

**Workflow Example**:

.. code-block:: text

   1. Open directory: /data/ct_scans/sample_001/
   2. Navigate to slice 150 → Click "Set Bottom" (lower bound = 150)
   3. Navigate to slice 300 → Click "Set Top" (upper bound = 300)
   4. Adjust bounding box in 2D viewer to focus on specific area
   5. Set threshold to 128 for optimal visualization
   6. Click "Save cropped image stack" → Exports 151 slices (150-300)
   7. Click "Export 3D Model" → Saves mesh of the selected volume

**Keyboard Shortcuts**:

- ``B`` - Set bottom boundary (lower bound)
- ``T`` - Set top boundary (upper bound)
- ``Ctrl+R`` - Reset ROI selection
- ``Left/Right`` - Navigate slices
- ``Up/Down`` - Adjust threshold
- ``Home/End`` - Jump to first/last slice
- ``Ctrl+Left/Right`` - Jump 10 slices backward/forward

For more detailed instructions, see the :doc:`user_guide`.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
