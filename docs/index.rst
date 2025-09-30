CTHarvester Documentation
=========================

Welcome to CTHarvester's documentation!

CTHarvester is a PyQt5-based application for processing and visualizing CT (Computed Tomography) scan image stacks. It provides tools for thumbnail generation, 3D mesh visualization, and image stack management.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   user_guide
   api/index
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

1. Click "Open Directory" to select a folder containing CT scan images
2. Wait for thumbnail generation to complete
3. Use the slider to navigate through slices
4. Adjust the threshold slider to modify 3D mesh visualization
5. Click "Save cropped image stack" to export selected slices
6. Click "Export 3D Model" to save the 3D mesh as OBJ format

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`