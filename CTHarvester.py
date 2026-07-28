import sys

from PyQt5.QtGui import QIcon

# Project modules
from config.constants import COMPANY_NAME, PROGRAM_NAME
from ui.ctharvester_app import CTHarvesterApp
from ui.exception_handler import install_global_exception_hook
from ui.main_window import CTHarvesterMainWindow
from utils.common import ensure_directories, resource_path
from utils.paths import user_directories
from version import __version__

# Try to create directories on import, but don't fail if it doesn't work
try:
    ensure_directories(user_directories())
except OSError as e:  # PermissionError is a subclass
    # Use print here since logger might not be initialized yet
    print(f"Warning: Directory initialization failed: {e}")

# Setup logger with rotation and session tracking
from CTLogger import setup_logger

logger, session_id = setup_logger(PROGRAM_NAME)
logger.info(f"CTHarvester version {__version__} starting")


def main():
    """Main application entry point"""
    # --self-test boots the app headless and exits 0, so a packaged build can be
    # launched in CI and proved to start. Everything below -- every heavy import,
    # the Qt/OpenGL stack, the bundled resources, the main window -- runs exactly
    # as it does for a user, which is the whole point: it catches the "works from
    # source, broken when frozen" failures (a PyInstaller data file that was
    # never added, a native library that did not get bundled) that tests run
    # against the source tree cannot reach.
    self_test = "--self-test" in sys.argv
    qt_argv = [arg for arg in sys.argv if arg != "--self-test"]

    app = CTHarvesterApp(qt_argv)

    # Backstop for any code path not covered by @guard_slot: without this an
    # unhandled exception in a slot kills the window with nothing in the log.
    install_global_exception_hook()

    app.setApplicationName(PROGRAM_NAME)
    app.setOrganizationName(COMPANY_NAME)
    app.setOrganizationDomain("github.com/jikhanjung")

    # Set application icon
    app.setWindowIcon(QIcon(resource_path("resources/icons/icon.png")))

    # Application attributes are initialized in CTHarvesterApp.__init__
    # with proper type hints for mypy compatibility
    # Settings are managed by SettingsManager (YAML-based) and loaded in main_window

    # Create and show main window
    window = CTHarvesterMainWindow()
    window.show()

    if self_test:
        # The startup path above has already done the work worth checking. Let
        # the event loop turn over briefly so deferred initialisation runs, then
        # quit. Top-levels are closed first so a stray modal's nested loop
        # cannot outlive quit() and hang the runner.
        from PyQt5.QtCore import QTimer

        def _self_test_exit():
            logger.info("Self-test: main window reached; exiting cleanly")
            for widget in app.topLevelWidgets():
                widget.close()
            app.quit()

        QTimer.singleShot(2000, _self_test_exit)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
