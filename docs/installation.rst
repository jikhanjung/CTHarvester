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

**Software (for source installation only):**

* Python 3.11 or later
* PyQt5
* NumPy
* PIL/Pillow
* PyMCubes
* PyOpenGL
* Optional: Rust toolchain for high-performance thumbnail generation

Installation Methods
--------------------

Method 1: Binary Installation (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download the pre-built binary from the releases page:

**Windows:**

1. Visit https://github.com/jikhanjung/CTHarvester/releases
2. Download the latest ``CTHarvester-windows.zip``
3. Extract the ZIP file to a folder
4. Run the ``CTHarvester_vX.X.X_Installer.exe`` inside the extracted folder
5. Follow the installation wizard
6. Launch CTHarvester from the Start Menu or Desktop shortcut

**macOS:**

1. Visit https://github.com/jikhanjung/CTHarvester/releases
2. Download the latest ``CTHarvester-macos.dmg``
3. Open the DMG file
4. Drag CTHarvester.app to your Applications folder
5. Launch CTHarvester from Applications

**Linux:**

1. Visit https://github.com/jikhanjung/CTHarvester/releases
2. Download the latest ``CTHarvester-linux.AppImage``
3. Make it executable:

   .. code-block:: bash

      chmod +x CTHarvester-linux.AppImage

4. Run the AppImage:

   .. code-block:: bash

      ./CTHarvester-linux.AppImage

   Or double-click the file in your file manager.

Method 2: From Source
~~~~~~~~~~~~~~~~~~~~~

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

      # Recommended: Install from pyproject.toml
      pip install -e .

      # Or use requirements.txt for backward compatibility
      pip install -r requirements.txt

   **For development:**

   .. code-block:: bash

      # Install with development dependencies
      pip install -e .[dev]

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

Verifying Installation
-----------------------

**Binary Installation:**

Launch CTHarvester from your application menu or desktop shortcut. The application should start and display the main window.

**Source Installation:**

To verify that CTHarvester is installed correctly:

.. code-block:: bash

   python CTHarvester.py --version

You should see output like:

.. code-block:: text

   CTHarvester v0.2.3

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

**Binary Installation:**

1. Download the latest version from the releases page
2. Windows: Run the new installer, it will update the existing installation
3. macOS: Replace the old CTHarvester.app with the new one
4. Linux: Replace the old AppImage with the new one

**Source Installation:**

.. code-block:: bash

   cd CTHarvester
   git pull origin main
   pip install -r requirements.txt --upgrade

Uninstallation
--------------

**Binary Installation:**

* **Windows**: Use "Add or Remove Programs" in Windows Settings, or run the uninstaller from the installation directory
* **macOS**: Drag CTHarvester.app to Trash
* **Linux**: Delete the AppImage file

**Source Installation:**

1. Delete the CTHarvester directory
2. Deactivate and remove the virtual environment

**Configuration Files (all methods):**

To completely remove CTHarvester, also delete configuration files:

* Windows: Delete ``%APPDATA%\\CTHarvester``
* Linux/macOS: Delete ``~/.config/CTHarvester``
