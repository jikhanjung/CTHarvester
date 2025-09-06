import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import():
    """Test that the main module can be imported"""
    try:
        import CTHarvester
        assert True
    except ImportError:
        assert False, "Failed to import CTHarvester module"

def test_requirements():
    """Test that required packages are installed"""
    required_packages = [
        'PyQt5',
        'PIL',
        'numpy',
        'scipy',
        'pymcubes'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            assert False, f"Required package {package} is not installed"
    
    assert True