"""
Unit tests for UI dialogs

Tests simple information and help dialogs that display static content.
"""

import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QLabel, QMainWindow, QPushButton

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

if PYQT_AVAILABLE:
    from config.constants import PROGRAM_VERSION
    from ui.dialogs.info_dialog import InfoDialog
    from ui.dialogs.shortcut_dialog import ShortcutDialog

    from .test_utils import find_child_widget


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestInfoDialog:
    """Tests for InfoDialog"""

    @pytest.fixture
    def parent_window(self, qtbot):
        """Create parent window for dialog"""
        window = QMainWindow()
        qtbot.addWidget(window)
        window.show()
        return window

    @pytest.fixture
    def dialog(self, qtbot, parent_window):
        """Create InfoDialog instance"""
        dlg = InfoDialog(parent_window)
        qtbot.addWidget(dlg)
        return dlg

    def test_initialization(self, dialog):
        """Should initialize with correct properties"""
        assert dialog is not None
        assert dialog.windowTitle() == "About CTHarvester"
        assert dialog.isModal() is False  # Dialog is not modal by default

    def test_window_size(self, dialog):
        """Should have fixed size"""
        size = dialog.size()
        assert size.width() == 300
        assert size.height() == 200

    def test_title_label_present(self, dialog):
        """Should display title label"""
        labels = dialog.findChildren(QLabel)

        # Find title label (contains "CTHarvester")
        title_labels = [label for label in labels if "CTHarvester" in label.text()]
        assert len(title_labels) > 0

        # Should be HTML formatted
        title_label = title_labels[0]
        assert "<h2>" in title_label.text()

    def test_version_display(self, dialog):
        """Should display version information"""
        labels = dialog.findChildren(QLabel)

        # Find version label
        version_labels = [label for label in labels if "Version" in label.text()]
        assert len(version_labels) > 0

        # Should contain actual version number
        version_label = version_labels[0]
        assert PROGRAM_VERSION in version_label.text()

    def test_description_display(self, dialog):
        """Should display application description"""
        labels = dialog.findChildren(QLabel)

        # Find description label
        desc_labels = [
            label for label in labels if "CT Image Stack Processing Tool" in label.text()
        ]
        assert len(desc_labels) > 0

    def test_copyright_display(self, dialog):
        """Should display copyright information"""
        labels = dialog.findChildren(QLabel)

        # Find copyright label
        copyright_labels = [label for label in labels if "©" in label.text() or "2023" in label.text()]
        assert len(copyright_labels) > 0

        # Should contain year
        copyright_label = copyright_labels[0]
        assert "2023" in copyright_label.text()

    def test_github_link_present(self, dialog):
        """Should display GitHub repository link"""
        labels = dialog.findChildren(QLabel)

        # Find GitHub link label
        github_labels = [label for label in labels if "github" in label.text().lower()]
        assert len(github_labels) > 0

        # Should be a clickable link
        github_label = github_labels[0]
        assert github_label.openExternalLinks() is True
        assert "href" in github_label.text()

    def test_ok_button_present(self, dialog):
        """Should have OK button"""
        buttons = dialog.findChildren(QPushButton)

        ok_buttons = [btn for btn in buttons if "OK" in btn.text()]
        assert len(ok_buttons) > 0

    def test_ok_button_closes_dialog(self, dialog, qtbot):
        """Clicking OK should close dialog"""
        buttons = dialog.findChildren(QPushButton)
        ok_button = [btn for btn in buttons if "OK" in btn.text()][0]

        # Click OK button
        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            qtbot.mouseClick(ok_button, Qt.LeftButton)

    def test_labels_centered(self, dialog):
        """Labels should be center-aligned"""
        labels = dialog.findChildren(QLabel)

        for label in labels:
            # Skip labels that might not be centered (like links)
            if "href" not in label.text():
                alignment = label.alignment()
                # Qt.AlignCenter or Qt.AlignHCenter should be set
                assert (alignment & Qt.AlignHCenter) or (alignment & Qt.AlignCenter)

    def test_dialog_positioning(self, dialog, parent_window):
        """Dialog should be positioned relative to parent"""
        # Dialog position should be calculated from parent
        # We can't test exact position without showing, but verify no crash
        parent_pos = parent_window.pos()
        dialog_pos = dialog.pos()

        # Position should be reasonable (not at 0, 0)
        assert dialog_pos.x() != 0 or dialog_pos.y() != 0


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestShortcutDialog:
    """Tests for ShortcutDialog"""

    @pytest.fixture
    def dialog(self, qtbot):
        """Create ShortcutDialog instance"""
        dlg = ShortcutDialog()
        qtbot.addWidget(dlg)
        return dlg

    def test_initialization(self, dialog):
        """Should initialize with correct properties"""
        assert dialog is not None
        assert dialog.windowTitle() == "Keyboard Shortcuts"

    def test_minimum_size(self, dialog):
        """Should have minimum size set"""
        min_size = dialog.minimumSize()
        assert min_size.width() == 700
        assert min_size.height() == 500

    def test_title_label_present(self, dialog):
        """Should display title"""
        labels = dialog.findChildren(QLabel)

        title_labels = [label for label in labels if label.text() == "Keyboard Shortcuts"]
        assert len(title_labels) > 0

        # Title should have special styling
        title_label = title_labels[0]
        style = title_label.styleSheet()
        assert "font-size" in style or "font-weight" in style

    def test_close_button_present(self, dialog):
        """Should have Close button"""
        buttons = dialog.findChildren(QPushButton)

        close_buttons = [btn for btn in buttons if btn.text() == "Close"]
        assert len(close_buttons) > 0

    def test_close_button_accepts_dialog(self, dialog, qtbot):
        """Clicking Close should accept dialog"""
        buttons = dialog.findChildren(QPushButton)
        close_button = [btn for btn in buttons if btn.text() == "Close"][0]

        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            qtbot.mouseClick(close_button, Qt.LeftButton)

    def test_shortcut_labels_present(self, dialog):
        """Should display shortcut key labels"""
        labels = dialog.findChildren(QLabel)

        # Should have multiple labels (shortcuts, descriptions, categories)
        assert len(labels) > 10

        # Some labels should have monospace styling (keyboard shortcuts)
        monospace_labels = [label for label in labels if "monospace" in label.styleSheet()]
        assert len(monospace_labels) > 0

    def test_category_headers_present(self, dialog):
        """Should display category headers"""
        labels = dialog.findChildren(QLabel)

        # Category headers should have bold styling
        bold_labels = [label for label in labels if "bold" in label.styleSheet().lower()]
        assert len(bold_labels) > 0

    def test_scroll_area_present(self, dialog):
        """Should have scroll area for long content"""
        from PyQt5.QtWidgets import QScrollArea

        scroll_areas = dialog.findChildren(QScrollArea)
        assert len(scroll_areas) > 0

        scroll = scroll_areas[0]
        assert scroll.widgetResizable() is True

    def test_keyboard_shortcuts_display(self, dialog):
        """Should display keyboard shortcut information"""
        labels = dialog.findChildren(QLabel)

        # Should have labels with key sequences (common shortcuts)
        label_texts = [label.text() for label in labels]

        # At least some common modifiers should appear
        # (Ctrl, Shift, etc. in various combinations)
        has_shortcuts = any("Ctrl" in text or "Shift" in text or "Alt" in text for text in label_texts)
        assert has_shortcuts

    def test_shortcut_descriptions_display(self, dialog):
        """Should display descriptions for shortcuts"""
        labels = dialog.findChildren(QLabel)

        # Should have description labels (not just key labels)
        # Description labels don't have monospace style
        desc_labels = [
            label
            for label in labels
            if "monospace" not in label.styleSheet() and len(label.text()) > 5
        ]

        # Should have multiple description labels
        assert len(desc_labels) > 5

    def test_dialog_layout(self, dialog):
        """Should have proper layout structure"""
        layout = dialog.layout()
        assert layout is not None

        # Should have widgets in layout
        assert layout.count() > 0


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt5 not available")
@pytest.mark.qt
class TestDialogIntegration:
    """Integration tests for dialog behavior"""

    def test_info_dialog_can_be_shown_and_closed(self, qtbot):
        """InfoDialog should show and close properly"""
        parent = QMainWindow()
        qtbot.addWidget(parent)

        dialog = InfoDialog(parent)
        qtbot.addWidget(dialog)

        # Show dialog
        dialog.show()
        qtbot.waitExposed(dialog)

        assert dialog.isVisible()

        # Close dialog
        dialog.accept()
        assert not dialog.isVisible() or dialog.result() == dialog.Accepted

    def test_shortcut_dialog_can_be_shown_and_closed(self, qtbot):
        """ShortcutDialog should show and close properly"""
        dialog = ShortcutDialog()
        qtbot.addWidget(dialog)

        # Show dialog
        dialog.show()
        qtbot.waitExposed(dialog)

        assert dialog.isVisible()

        # Close dialog
        dialog.accept()
        assert not dialog.isVisible() or dialog.result() == dialog.Accepted

    def test_multiple_info_dialogs(self, qtbot):
        """Should be able to create multiple InfoDialog instances"""
        parent = QMainWindow()
        qtbot.addWidget(parent)

        dialog1 = InfoDialog(parent)
        dialog2 = InfoDialog(parent)

        qtbot.addWidget(dialog1)
        qtbot.addWidget(dialog2)

        assert dialog1 is not dialog2

    def test_multiple_shortcut_dialogs(self, qtbot):
        """Should be able to create multiple ShortcutDialog instances"""
        dialog1 = ShortcutDialog()
        dialog2 = ShortcutDialog()

        qtbot.addWidget(dialog1)
        qtbot.addWidget(dialog2)

        assert dialog1 is not dialog2

    def test_dialog_escape_key_closes(self, qtbot):
        """Escape key should close dialogs"""
        dialog = ShortcutDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Press Escape
        qtbot.keyClick(dialog, Qt.Key_Escape)

        # Dialog should be rejected (closed)
        # Note: Depending on Qt version, dialog might still be visible but rejected
        assert dialog.result() == dialog.Rejected or not dialog.isVisible()
