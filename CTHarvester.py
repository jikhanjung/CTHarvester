import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

# Project modules
from config.constants import (
    COMPANY_NAME,
    DB_BACKUP_DIRECTORY,
    DEFAULT_DB_DIRECTORY,
    DEFAULT_LOG_DIRECTORY,
    DEFAULT_STORAGE_DIRECTORY,
    PROGRAM_NAME,
)
from ui.main_window import CTHarvesterMainWindow
from utils.common import ensure_directories, resource_path

# Try to create directories on import, but don't fail if it doesn't work
try:
    ensure_directories(
        [
            DEFAULT_DB_DIRECTORY,
            DEFAULT_STORAGE_DIRECTORY,
            DEFAULT_LOG_DIRECTORY,
            DB_BACKUP_DIRECTORY,
        ]
    )
except Exception as e:
    # Use print here since logger might not be initialized yet
    print(f"Warning: Directory initialization failed: {e}")
    pass

# Setup logger
from CTLogger import setup_logger

logger = setup_logger(PROGRAM_NAME)


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName(PROGRAM_NAME)
    app.setOrganizationName(COMPANY_NAME)
    app.setOrganizationDomain("github.com/jikhanjung")

    # Set application icon
    app.setWindowIcon(QIcon(resource_path("resources/icons/icon.png")))

    # Initialize application attributes (no longer using QSettings)
    # Settings are now managed by SettingsManager (YAML-based)
    app.remember_geometry = True
    app.remember_directory = True
    app.language = "en"
    app.use_rust_thumbnail = True  # Default to Rust (fast) thumbnail generation

    # Create and show main window
    window = CTHarvesterMainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
