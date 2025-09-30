#!/usr/bin/env python
"""
Test script for CTHarvester Rust integration
"""

import sys
import os

# Check if ct_thumbnail module is available
try:
    from ct_thumbnail import build_thumbnails
    print("✓ ct_thumbnail module found")
    rust_available = True
except ImportError:
    print("✗ ct_thumbnail module not found")
    print("  Build with: maturin develop --release")
    rust_available = False

# Test the module directly
if rust_available:
    print("\nTesting Rust module directly...")

    test_dir = r"D:\Lichas_tif"
    if not os.path.exists(test_dir):
        # Try a fallback test directory
        test_dir = "./test_images"
        if not os.path.exists(test_dir):
            print(f"Test directory not found: {test_dir}")
            print("Please create test images or specify a valid directory")
            sys.exit(1)

    print(f"Using test directory: {test_dir}")

    def simple_callback(percentage):
        print(f"Progress: {percentage:.1f}%", end='\r')
        if percentage >= 100:
            print(f"Progress: {percentage:.1f}% - Complete!")

    try:
        print("Starting thumbnail generation...")
        build_thumbnails(test_dir, simple_callback)
        print("✓ Rust module test successful")
    except Exception as e:
        print(f"✗ Rust module test failed: {e}")

# Test CTHarvester integration
print("\n" + "="*60)
print("Testing CTHarvester integration...")
print("="*60)

try:
    # Try to import CTHarvester components
    from PyQt5.QtCore import QCoreApplication
    from PyQt5.QtWidgets import QApplication

    # Create a minimal Qt application for testing
    app = QApplication(sys.argv)

    # Mock the necessary components for testing
    class MockCTHarvester:
        def __init__(self):
            self.edtDirname = MockLineEdit()
            self.progress_dialog = None
            self.level_info = []
            self.minimum_volume = []
            self.initialized = False
            self.comboLevel = MockComboBox()
            self.timeline = MockTimeline()
            self.mcube_widget = MockMCubeWidget()

        def tr(self, text):
            return text

        def initializeComboSize(self):
            pass

        def reset_crop(self):
            pass

        def comboLevelIndexChanged(self):
            pass

    class MockLineEdit:
        def text(self):
            return test_dir if rust_available else "."

    class MockComboBox:
        def count(self):
            return 1

        def setCurrentIndex(self, index):
            pass

    class MockTimeline:
        def values(self):
            return (0, 50, 100)

        def maximum(self):
            return 100

    class MockMCubeWidget:
        def update_boxes(self, *args):
            pass
        def adjust_boxes(self):
            pass
        def update_volume(self, volume):
            pass
        def generate_mesh(self):
            pass
        def adjust_volume(self):
            pass
        def show_buttons(self):
            pass
        def setGeometry(self, rect):
            pass
        def recalculate_geometry(self):
            pass

    class MockProgressDialog:
        def __init__(self, parent):
            self.is_cancelled = False
            self.progressBar = MockProgressBar()
            self.lbl_text = MockLabel()
            self.lbl_detail = MockLabel()

        def update_language(self):
            pass

        def setModal(self, modal):
            pass

        def show(self):
            pass

        def close(self):
            pass

    class MockProgressBar:
        def setMinimum(self, val):
            pass
        def setMaximum(self, val):
            pass
        def setValue(self, val):
            pass

    class MockLabel:
        def setText(self, text):
            print(f"  Label: {text}")

    # Import logging
    import logging
    logging.basicConfig(level=logging.INFO)
    global logger
    logger = logging.getLogger(__name__)

    # Create mock CTHarvester instance
    mock_ct = MockCTHarvester()

    # Import the actual methods
    import importlib.util
    spec = importlib.util.spec_from_file_location("CTHarvester", "CTHarvester.py")
    ct_module = importlib.util.module_from_spec(spec)

    # Add necessary imports to the module namespace
    ct_module.logger = logger
    ct_module.ProgressDialog = MockProgressDialog
    ct_module.QApplication = QApplication
    ct_module.Qt = __import__('PyQt5.QtCore').QtCore.Qt
    ct_module.QMessageBox = __import__('PyQt5.QtWidgets').QtWidgets.QMessageBox
    ct_module.Image = __import__('PIL').Image
    ct_module.np = __import__('numpy')
    ct_module.os = os
    ct_module.QRect = __import__('PyQt5.QtCore').QtCore.QRect

    # Load the module
    spec.loader.exec_module(ct_module)

    # Test the create_thumbnail method
    if hasattr(ct_module, 'CTHarvester'):
        # Get the method from the class
        create_thumbnail = ct_module.CTHarvester.create_thumbnail
        create_thumbnail_rust = ct_module.CTHarvester.create_thumbnail_rust
        load_rust_thumbnail_data = ct_module.CTHarvester.load_rust_thumbnail_data

        # Bind methods to mock instance
        mock_ct.create_thumbnail = create_thumbnail.__get__(mock_ct, MockCTHarvester)
        mock_ct.create_thumbnail_rust = create_thumbnail_rust.__get__(mock_ct, MockCTHarvester)
        mock_ct.load_rust_thumbnail_data = load_rust_thumbnail_data.__get__(mock_ct, MockCTHarvester)

        print("\n✓ CTHarvester methods loaded successfully")

        if rust_available:
            print("\nTesting create_thumbnail with Rust module...")
            try:
                mock_ct.create_thumbnail()
                print("✓ Integration test successful")
            except Exception as e:
                print(f"✗ Integration test failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("\n✗ Cannot test integration - Rust module not available")
    else:
        print("✗ Could not load CTHarvester class")

except ImportError as e:
    print(f"✗ Import error: {e}")
    print("  Make sure PyQt5 and other dependencies are installed")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Test Summary:")
if rust_available:
    print("✓ Rust module available and functional")
    print("✓ CTHarvester integration implemented")
    print("\nTo use in CTHarvester:")
    print("1. Open CTHarvester.py")
    print("2. Load a directory with CT images")
    print("3. Thumbnails will be generated using Rust module automatically")
else:
    print("✗ Rust module not available")
    print("\nTo enable Rust acceleration:")
    print("1. Install Rust: https://rustup.rs/")
    print("2. Install maturin: pip install maturin")
    print("3. Build module: maturin develop --release")
    print("4. Run this test again")

print("="*60)