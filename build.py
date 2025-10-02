#!/usr/bin/env python
"""
Build script for CTHarvester
Handles PyInstaller build and InnoSetup installer generation
"""

import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Determine project root based on script location (not cwd)
PROJECT_ROOT = Path(__file__).resolve().parent

# Change to project root for reliable operation
os.chdir(PROJECT_ROOT)

# Import version from centralized version file
try:
    from version import __version__ as VERSION
except ImportError:
    # Fallback: extract from version.py file
    import re

    def get_version_from_file():
        version_file = PROJECT_ROOT / "version.py"
        with open(version_file) as f:
            content = f.read()
            match = re.search(r'__version__ = "(.*?)"', content)
            if match:
                return match.group(1)
        raise RuntimeError("Unable to find version string")

    VERSION = get_version_from_file()


def update_build_year():
    """Update BUILD_YEAR in config/constants.py with current year"""
    current_year = datetime.now().year
    print(f"Updating BUILD_YEAR to {current_year}...")

    constants_path = Path("config/constants.py")
    if not constants_path.exists():
        print(f"[ERROR] config/constants.py not found")
        return False

    content = constants_path.read_text(encoding="utf-8")

    # Update BUILD_YEAR line
    import re

    pattern = r"BUILD_YEAR = \d+"
    replacement = f"BUILD_YEAR = {current_year}"

    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        constants_path.write_text(new_content, encoding="utf-8")
        print(f"[OK] BUILD_YEAR updated to {current_year} in config/constants.py")
        return True
    else:
        print(f"[WARNING] BUILD_YEAR pattern not found or already up to date")
        return True


def run_pyinstaller(spec_file="CTHarvester.spec", build_type="onefile"):
    """Run PyInstaller to build the executable

    Args:
        spec_file: Path to the spec file to use (relative to PROJECT_ROOT)
        build_type: Type of build ("onefile" or "onedir")
    """
    print(f"Building CTHarvester v{VERSION} ({build_type})")

    # Resolve spec file path relative to PROJECT_ROOT
    spec_path = PROJECT_ROOT / spec_file
    if not spec_path.exists():
        print(f"Error: {spec_path} not found")
        return False

    # Run PyInstaller with absolute path to spec file
    cmd = ["pyinstaller", str(spec_path), "--clean"]

    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"PyInstaller {build_type} build completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller {build_type} build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def prepare_inno_setup_template():
    """Prepare InnoSetup script from template"""
    print("Preparing InnoSetup script from template...")

    template_path = PROJECT_ROOT / "InnoSetup" / "CTHarvester.iss.template"
    if not template_path.exists():
        print(f"[ERROR] Template file {template_path} not found")
        return None

    # Read template
    template_content = template_path.read_text()

    # Replace version placeholder
    iss_content = template_content.replace("{{VERSION}}", VERSION)

    # Use project root determined from script location
    project_root = PROJECT_ROOT

    # Replace relative paths with absolute paths
    iss_content = iss_content.replace("..\\LICENSE", str(project_root / "LICENSE"))
    iss_content = iss_content.replace(
        "..\\icon.ico", str(project_root / "resources" / "icons" / "icon.ico")
    )
    iss_content = iss_content.replace("..\\dist\\", str(project_root / "dist") + "\\")
    iss_content = iss_content.replace(
        "..\\InnoSetup\\Output", str(project_root / "InnoSetup" / "Output")
    )

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
    build_number = os.environ.get("BUILD_NUMBER", "local")

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

    # Update BUILD_YEAR before building
    if not update_build_year():
        print("[ERROR] Failed to update BUILD_YEAR")
        return 1

    # Parse command line arguments
    build_both = True  # Default: build both versions
    build_onefile = False
    build_onedir = False

    # Check for build type arguments
    args = sys.argv[1:]
    if "--onefile" in args:
        build_both = False
        build_onefile = True
        args.remove("--onefile")
    elif "--onedir" in args:
        build_both = False
        build_onedir = True
        args.remove("--onedir")

    # Set BUILD_NUMBER if provided as argument
    if len(args) > 0:
        os.environ["BUILD_NUMBER"] = args[0]
        print(f"BUILD_NUMBER: {args[0]}")
    elif "BUILD_NUMBER" not in os.environ:
        os.environ["BUILD_NUMBER"] = "local"
        print("BUILD_NUMBER: local (default)")

    # Determine what to build
    if build_both:
        print("Building both onefile and onedir versions...")
        build_onefile = True
        build_onedir = True

    success = True

    # Step 1: Build onefile executable if requested
    if build_onefile:
        print("\n" + "=" * 40)
        print("Building ONEFILE version...")
        print("=" * 40)
        # Try both possible spec file names
        if Path("CTHarvester_onefile.spec").exists():
            success = run_pyinstaller("CTHarvester_onefile.spec", "onefile")
        else:
            success = run_pyinstaller("CTHarvester.spec", "onefile")

        if success and Path("dist/CTHarvester.exe").exists():
            # Rename onefile executable to distinguish it
            Path("dist/CTHarvester.exe").rename("dist/CTHarvester_onefile.exe")
            print("Renamed: dist/CTHarvester.exe -> dist/CTHarvester_onefile.exe")

    # Step 2: Build onedir executable if requested
    if build_onedir and success:
        print("\n" + "=" * 40)
        print("Building ONEDIR version...")
        print("=" * 40)
        success = run_pyinstaller("CTHarvester_onedir.spec", "onedir")

    if not success:
        print("\n[ERROR] Build failed")
        return 1

    # Step 3: Build installer (Windows only)
    if platform.system() == "Windows":
        if not build_installer():
            print("\n[WARNING]  Installer build failed, but executable was built")
            return 0  # Partial success

    print("\n[SUCCESS] Build completed successfully!")
    print("\nOutput:")
    if build_onefile:
        print(f"  - Onefile executable: dist/CTHarvester_onefile.exe")
    if build_onedir:
        print(f"  - Onedir executable: dist/CTHarvester/CTHarvester.exe")

    if platform.system() == "Windows":
        build_number = os.environ.get("BUILD_NUMBER", "local")
        print(
            f"  - Installer: InnoSetup/Output/CTHarvester_v{VERSION}_build{build_number}_Installer.exe"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
