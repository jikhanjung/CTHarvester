"""
UI workflow integration tests

Part of Phase 2: Integration Tests Expansion
Tests complete UI workflows with real widget interactions
"""

import contextlib
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

        # The window stays usable afterwards. (`hasattr(main_window,
        # "edtDirname")` used to stand here, two lines after the attribute had
        # already been read twice.)
        assert main_window.isVisible()

    def test_settings_persistence(self, qapp, tmp_path, monkeypatch):
        """A setting written in one session is read back by the next.

        Two things made the previous version assert nothing at all. The
        attribute is `settings_manager`, not `settings`, so both
        `if hasattr(window, "settings")` guards were False and the write and
        the check were skipped together -- a test that could only pass. And the
        isolation used CTHARVESTER_SETTINGS_DIR, a name the application does
        not read, so had the guards been right this would have written the
        developer's real preferences.json instead of tmp_path.
        """
        from ui.main_window import CTHarvesterMainWindow

        monkeypatch.setenv("CTHARVESTER_CONFIG_DIR", str(tmp_path))

        window1 = CTHarvesterMainWindow()
        window1.show()
        QTest.qWaitForWindowExposed(window1)

        assert window1.settings_manager.get_config_file_path().startswith(str(tmp_path))

        window1.settings_manager.set("application.language", "ko")
        window1.settings_manager.save()

        window1.close()
        qapp.processEvents()
        QTest.qWait(100)

        window2 = CTHarvesterMainWindow()
        window2.show()
        QTest.qWaitForWindowExposed(window2)

        assert window2.settings_manager.get("application.language") == "ko"

        window2.close()
        qapp.processEvents()

    def test_error_recovery(self, main_window, tmp_path):
        """Test UI recovery from errors"""
        # Try to set non-existent directory
        fake_dir = tmp_path / "non_existent"

        # This should not crash the application
        # Expected to fail gracefully rather than raise
        with contextlib.suppress(Exception):
            main_window.edtDirname.setText(str(fake_dir))

        # Verify window is still responsive
        assert main_window.isVisible()

    def test_window_state_after_operations(self, main_window, sample_ct_directory):
        """Setting a directory leaves geometry and title untouched.

        The before/after comparison this test is named for was captured into
        `geometry1` and `initial_title` and then never written; the F841 sweep
        removed the unused bindings and left the assertions that survived,
        which only said the window was still visible and had some title.
        """
        initial_geometry = main_window.geometry()
        initial_title = main_window.windowTitle()

        main_window.edtDirname.setText(str(sample_ct_directory))
        QTest.qWait(100)

        assert main_window.isVisible()
        assert not main_window.isMinimized()
        assert main_window.geometry() == initial_geometry
        assert main_window.windowTitle() == initial_title
        assert initial_title

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
