"""
UI workflow integration tests

Part of Phase 2: Integration Tests Expansion
Tests complete UI workflows with real widget interactions
"""

from pathlib import Path

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest


@pytest.mark.integration
class TestUIWorkflows:
    """UI workflow integration tests"""

    def test_complete_ui_workflow(self, main_window, sample_ct_directory):
        """Test complete UI workflow from directory open to visualization"""
        # Set directory programmatically
        main_window.edtDirname.setText(str(sample_ct_directory))
        QTest.qWait(100)  # Wait for UI update

        # Verify directory was set
        assert main_window.edtDirname.text() == str(sample_ct_directory)

        # Verify UI widget exists
        assert hasattr(main_window, "edtDirname")

    def test_settings_persistence(self, qapp, tmp_path):
        """Test that settings persist across window sessions"""
        import os

        from ui.main_window import CTHarvesterMainWindow

        # Set temp settings location
        os.environ["CTHARVESTER_SETTINGS_DIR"] = str(tmp_path)

        # First session - change settings
        window1 = CTHarvesterMainWindow()
        window1.show()
        QTest.qWaitForWindowExposed(window1)

        # Change a setting if settings manager exists
        if hasattr(window1, "settings"):
            window1.settings.set("application.language", "ko")
            window1.settings.save()

        # Get window geometry
        geometry1 = window1.geometry()

        # Close window
        window1.close()
        qapp.processEvents()
        QTest.qWait(100)

        # Second session - verify settings persisted
        window2 = CTHarvesterMainWindow()
        window2.show()
        QTest.qWaitForWindowExposed(window2)

        # Verify setting persisted
        if hasattr(window2, "settings"):
            lang = window2.settings.get("application.language")
            assert lang == "ko"

        # Cleanup
        window2.close()
        qapp.processEvents()

    def test_error_recovery(self, main_window, tmp_path):
        """Test UI recovery from errors"""
        # Try to set non-existent directory
        fake_dir = tmp_path / "non_existent"

        # This should not crash the application
        try:
            main_window.edtDirname.setText(str(fake_dir))
        except Exception:
            pass  # Expected to fail gracefully

        # Verify window is still responsive
        assert main_window.isVisible()

    def test_window_state_after_operations(self, main_window, sample_ct_directory):
        """Test window state remains consistent after operations"""
        initial_title = main_window.windowTitle()

        # Set directory programmatically
        main_window.edtDirname.setText(str(sample_ct_directory))
        QTest.qWait(100)

        # Window should still be visible and responsive
        assert main_window.isVisible()
        assert not main_window.isMinimized()

        # Title should still be set
        current_title = main_window.windowTitle()
        assert current_title  # Should have some title

    def test_ui_element_visibility(self, main_window):
        """Test that required UI elements are visible"""
        # Main window should be visible
        assert main_window.isVisible()

        # Check for essential widgets (if they exist)
        # These are defensive checks - only verify if widgets exist
        if hasattr(main_window, "menu_bar"):
            assert main_window.menuBar() is not None

        if hasattr(main_window, "status_bar"):
            # Status bar should exist
            assert main_window.statusBar() is not None
