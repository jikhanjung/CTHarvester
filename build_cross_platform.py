"""Cross-platform build script for CTHarvester.

This script automates the process of building CTHarvester executables for
Windows, macOS, and Linux using PyInstaller.

Usage:
    python build_cross_platform.py [--platform PLATFORM] [--clean]

Arguments:
    --platform: Target platform (windows, macos, linux, or auto)
    --clean: Clean build directories before building

Example:
    python build_cross_platform.py --platform windows --clean
"""

import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def detect_platform():
    """Detect current platform.

    Returns:
        str: Platform name ('windows', 'macos', or 'linux')

    Raises:
        RuntimeError: If platform is not supported
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def clean_build_dirs():
    """Clean build and dist directories."""
    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            logger.info(f"Cleaning {dir_name}/")
            shutil.rmtree(dir_name)

    # Remove spec file
    spec_file = "CTHarvester.spec"
    if os.path.exists(spec_file):
        logger.info(f"Removing {spec_file}")
        os.remove(spec_file)


def get_icon_path(platform_name):
    """Get icon path for platform.

    Args:
        platform_name: Platform name ('windows', 'macos', or 'linux')

    Returns:
        str: Path to icon file
    """
    if platform_name == "windows":
        return "resources/icons/CTHarvester_64.png"  # PyInstaller will convert to .ico
    elif platform_name == "macos":
        return "resources/icons/CTHarvester_64.png"  # PyInstaller will convert to .icns
    else:  # linux
        return "resources/icons/CTHarvester_64.png"


def build_executable(platform_name):
    """Build executable for specified platform.

    Args:
        platform_name: Target platform ('windows', 'macos', or 'linux')

    Returns:
        bool: True if build succeeded, False otherwise
    """
    logger.info(f"Building CTHarvester for {platform_name}...")

    # Base PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=CTHarvester",
        "--windowed" if platform_name in ["windows", "macos"] else "--onefile",
        "--onefile",
        f"--icon={get_icon_path(platform_name)}",
    ]

    # Add data files
    data_files = [
        ("resources/icons/*.png", "resources/icons"),
        ("resources/translations/*.qm", "resources/translations"),
        ("config/settings.yaml", "config"),
    ]

    for src, dst in data_files:
        if platform_name == "windows":
            cmd.append(f"--add-data={src};{dst}")
        else:
            cmd.append(f"--add-data={src}:{dst}")

    # Hidden imports
    hidden_imports = [
        "numpy",
        "PIL",
        "PyQt5",
        "yaml",
        "mcubes",
        "OpenGL",
        "configparser",
    ]

    for module in hidden_imports:
        cmd.append(f"--hidden-import={module}")

    # Platform-specific options
    if platform_name == "macos":
        cmd.extend(
            [
                "--osx-bundle-identifier=com.ctharvester.app",
                "--codesign-identity=-",  # Ad-hoc signing
            ]
        )

    # Entry point
    cmd.append("CTHarvester.py")

    # Run PyInstaller
    logger.info(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Build successful!")
        logger.debug(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Build failed: {e}")
        logger.error(e.stderr)
        return False


def create_distribution_archive(platform_name):
    """Create distribution archive.

    Args:
        platform_name: Platform name

    Returns:
        str: Path to created archive
    """
    import tarfile
    import zipfile

    dist_dir = Path("dist")
    if not dist_dir.exists():
        logger.error("dist/ directory not found")
        return None

    # Find executable
    if platform_name == "windows":
        exe_name = "CTHarvester.exe"
        archive_name = f"CTHarvester-{platform_name}.zip"
    elif platform_name == "macos":
        exe_name = "CTHarvester.app"
        archive_name = f"CTHarvester-{platform_name}.zip"
    else:  # linux
        exe_name = "CTHarvester"
        archive_name = f"CTHarvester-{platform_name}.tar.gz"

    exe_path = dist_dir / exe_name
    if not exe_path.exists():
        logger.error(f"Executable not found: {exe_path}")
        return None

    archive_path = dist_dir / archive_name

    # Create archive
    logger.info(f"Creating distribution archive: {archive_path}")

    if platform_name in ["windows", "macos"]:
        # ZIP for Windows and macOS
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if exe_path.is_dir():  # macOS .app bundle
                for file in exe_path.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(dist_dir)
                        zipf.write(file, arcname)
            else:
                zipf.write(exe_path, exe_name)

            # Add README
            if Path("README.md").exists():
                zipf.write("README.md", "README.md")
    else:
        # TAR.GZ for Linux
        with tarfile.open(archive_path, "w:gz") as tarf:
            tarf.add(exe_path, arcname=exe_name)
            if Path("README.md").exists():
                tarf.add("README.md", arcname="README.md")

    logger.info(f"Distribution archive created: {archive_path}")
    return str(archive_path)


def main():
    """Main build function."""
    parser = argparse.ArgumentParser(description="Build CTHarvester for multiple platforms")
    parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux", "auto"],
        default="auto",
        help="Target platform (default: auto-detect)",
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean build directories before building"
    )
    parser.add_argument(
        "--no-archive", action="store_true", help="Skip creating distribution archive"
    )

    args = parser.parse_args()

    # Detect platform if auto
    if args.platform == "auto":
        platform_name = detect_platform()
        logger.info(f"Auto-detected platform: {platform_name}")
    else:
        platform_name = args.platform

    # Clean if requested
    if args.clean:
        clean_build_dirs()

    # Check PyInstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("PyInstaller not found. Install with: pip install pyinstaller")
        return 1

    # Build executable
    if not build_executable(platform_name):
        logger.error("Build failed")
        return 1

    # Create distribution archive
    if not args.no_archive:
        archive_path = create_distribution_archive(platform_name)
        if not archive_path:
            logger.warning("Failed to create distribution archive")
            return 1

    logger.info("=" * 60)
    logger.info("Build completed successfully!")
    logger.info("=" * 60)
    logger.info(f"Executable: dist/CTHarvester{'.exe' if platform_name == 'windows' else ''}")
    if not args.no_archive:
        logger.info(f"Archive: {archive_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
