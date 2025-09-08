#!/usr/bin/env python
"""
Build script for CTHarvester
Handles PyInstaller build and InnoSetup installer generation
"""

import subprocess
import os
import sys
import platform
import tempfile
from pathlib import Path

# Import version from centralized version file
try:
    from version import __version__ as VERSION
except ImportError:
    # Fallback: extract from version.py file
    import re
    def get_version_from_file():
        with open("version.py", "r") as f:
            content = f.read()
            match = re.search(r'__version__ = "(.*?)"', content)
            if match:
                return match.group(1)
        raise RuntimeError("Unable to find version string")
    VERSION = get_version_from_file()

def run_pyinstaller():
    """Run PyInstaller to build the executable"""
    print(f"Building CTHarvester v{VERSION}")
    
    # Check if spec file exists
    spec_file = "CTHarvester.spec"
    if not Path(spec_file).exists():
        print(f"Error: {spec_file} not found")
        return False
    
    # Run PyInstaller
    cmd = ["pyinstaller", spec_file]
    
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("PyInstaller build completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def prepare_inno_setup_template():
    """Prepare InnoSetup script from template"""
    print("Preparing InnoSetup script from template...")
    
    template_path = Path("InnoSetup/CTHarvester.iss.template")
    if not template_path.exists():
        print(f"[ERROR] Template file {template_path} not found")
        return None
    
    # Read template
    template_content = template_path.read_text()
    
    # Replace version placeholder
    iss_content = template_content.replace("{{VERSION}}", VERSION)
    
    # Create temporary ISS file
    temp_dir = Path(tempfile.gettempdir())
    temp_iss = temp_dir / f"CTHarvester_build_{os.getpid()}.iss"
    
    try:
        temp_iss.write_text(iss_content)
        print(f"[OK] Temporary ISS file created: {temp_iss.name}")
        return str(temp_iss)
    except Exception as e:
        print(f"[ERROR] Error creating temporary ISS file: {e}")
        return None

def build_installer():
    """Build Windows installer using InnoSetup"""
    if platform.system() != "Windows":
        print("[INFO]  Installer build only available on Windows")
        return True
    
    print("Building Windows installer...")
    
    # Prepare ISS from template
    temp_iss_file = prepare_inno_setup_template()
    if not temp_iss_file:
        return False
    
    # Check if InnoSetup is installed
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    
    iscc_path = None
    for path in inno_paths:
        if Path(path).exists():
            iscc_path = path
            break
    
    if not iscc_path:
        print("[WARNING]  InnoSetup not found. Skipping installer build.")
        print("   Install from: https://jrsoftware.org/isdl.php")
        # Clean up temp file
        if Path(temp_iss_file).exists():
            Path(temp_iss_file).unlink()
        return True  # Not a critical error
    
    # Set BUILD_NUMBER environment variable
    build_number = os.environ.get('BUILD_NUMBER', 'local')
    
    cmd = [iscc_path, f"/DBuildNumber={build_number}", temp_iss_file]
    
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("[OK] Installer built successfully")
        
        # Show output location
        installer_name = f"CTHarvester_v{VERSION}_build{build_number}_Installer.exe"
        installer_path = Path(f"InnoSetup/Output/{installer_name}")
        if installer_path.exists():
            print(f"[PACKAGE] Installer: {installer_path}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Installer build failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    finally:
        # Clean up temp file
        if Path(temp_iss_file).exists():
            Path(temp_iss_file).unlink()
            print(f"[CLEANUP] Cleaned up temporary file: {Path(temp_iss_file).name}")

def main():
    """Main build process"""
    print("=" * 60)
    print(f"CTHarvester Build Script")
    print(f"Version: {VERSION}")
    print(f"Platform: {platform.system()}")
    print("=" * 60)
    
    # Set BUILD_NUMBER if provided as argument
    if len(sys.argv) > 1:
        os.environ['BUILD_NUMBER'] = sys.argv[1]
        print(f"BUILD_NUMBER: {sys.argv[1]}")
    elif 'BUILD_NUMBER' not in os.environ:
        os.environ['BUILD_NUMBER'] = 'local'
        print("BUILD_NUMBER: local (default)")
    
    # Step 1: Build executable with PyInstaller
    if not run_pyinstaller():
        print("\n[ERROR] Build failed")
        return 1
    
    # Step 2: Build installer (Windows only)
    if platform.system() == "Windows":
        if not build_installer():
            print("\n[WARNING]  Installer build failed, but executable was built")
            return 0  # Partial success
    
    print("\n[SUCCESS] Build completed successfully!")
    print("\nOutput:")
    print(f"  - Executable: dist/CTHarvester/")
    
    if platform.system() == "Windows":
        build_number = os.environ.get('BUILD_NUMBER', 'local')
        print(f"  - Installer: InnoSetup/Output/CTHarvester_v{VERSION}_build{build_number}_Installer.exe")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())