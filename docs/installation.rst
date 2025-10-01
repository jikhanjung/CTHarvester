Installation Guide
==================

System Requirements
-------------------

**Operating Systems:**

* Windows 10 or later
* macOS 10.14 (Mojave) or later
* Linux (Ubuntu 18.04 or later, or equivalent)

**Hardware:**

* CPU: Multi-core processor recommended for thumbnail generation
* RAM: 4GB minimum, 8GB recommended
* Disk Space: 500MB for application + space for CT data
* Display: 1280x720 minimum resolution

**Software:**

* Python 3.11 or later
* PyQt5
* NumPy
* PIL/Pillow
* PyMCubes
* PyOpenGL
* Optional: Rust toolchain for high-performance thumbnail generation

Installation Methods
--------------------

Method 1: From Source (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Clone the repository:**

   .. code-block:: bash

      git clone https://github.com/jikhanjung/CTHarvester.git
      cd CTHarvester

2. **Create a virtual environment (recommended):**

   .. code-block:: bash

      # Windows
      python -m venv venv
      venv\\Scripts\\activate

      # Linux/macOS
      python3 -m venv venv
      source venv/bin/activate

3. **Install Python dependencies:**

   .. code-block:: bash

      pip install -r requirements.txt

4. **Optional: Install Rust module for faster thumbnail generation:**

   .. code-block:: bash

      # Install Rust if not already installed
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

      # Build the Rust module
      cd rust_thumbnail
      cargo build --release
      cd ..

5. **Run the application:**

   .. code-block:: bash

      python CTHarvester.py

Method 2: Using pip (if published to PyPI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install ctharvester

Method 3: Binary Installation (Windows/macOS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download the pre-built binary from the releases page:

1. Visit https://github.com/yourusername/CTHarvester/releases
2. Download the appropriate binary for your platform
3. Extract the archive
4. Run CTHarvester.exe (Windows) or CTHarvester.app (macOS)

Verifying Installation
-----------------------

To verify that CTHarvester is installed correctly:

.. code-block:: bash

   python CTHarvester.py --version

You should see output like:

.. code-block:: text

   CTHarvester v0.2.3-beta.1

Troubleshooting
---------------

**ImportError: No module named 'PyQt5'**

   Install PyQt5:

   .. code-block:: bash

      pip install PyQt5

**OpenGL errors on Linux**

   Install required OpenGL libraries:

   .. code-block:: bash

      # Ubuntu/Debian
      sudo apt-get install python3-opengl

      # Fedora
      sudo dnf install python3-pyopengl

**Rust module not working**

   The application will automatically fall back to Python-based thumbnail generation.
   To enable Rust module:

   1. Verify Rust is installed: ``rustc --version``
   2. Rebuild the module: ``cd rust_thumbnail && cargo build --release``
   3. Ensure the compiled library is in the correct location

Configuration
-------------

CTHarvester stores its configuration in platform-specific locations:

**Windows:**
  ``%APPDATA%\\CTHarvester\\settings.yaml``

**Linux/macOS:**
  ``~/.config/CTHarvester/settings.yaml``

You can customize settings through the Preferences dialog (gear icon) in the application.

Updating
--------

To update CTHarvester to the latest version:

**From Source:**

.. code-block:: bash

   cd CTHarvester
   git pull origin main
   pip install -r requirements.txt --upgrade

**From pip:**

.. code-block:: bash

   pip install --upgrade ctharvester

Uninstallation
--------------

**From Source:**

1. Delete the CTHarvester directory
2. Remove configuration files:

   * Windows: Delete ``%APPDATA%\\CTHarvester``
   * Linux/macOS: Delete ``~/.config/CTHarvester``

**From pip:**

.. code-block:: bash

   pip uninstall ctharvester