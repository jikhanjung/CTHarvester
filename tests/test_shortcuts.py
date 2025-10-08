"""Tests for config/shortcuts.py and shortcuts setup"""

import pytest
from PyQt5.QtWidgets import QMainWindow

from config.shortcuts import Shortcut, ShortcutManager


class TestShortcutManager:
    """Test ShortcutManager class"""

    def test_get_existing_shortcut(self):
        """Test getting an existing shortcut"""
        shortcut = ShortcutManager.get_shortcut("open_directory")
        assert shortcut is not None
        assert isinstance(shortcut, Shortcut)
        assert shortcut.key == "Ctrl+O"
        assert shortcut.description == "Open directory"

    def test_get_nonexistent_shortcut(self):
        """Test getting a nonexistent shortcut returns None"""
        shortcut = ShortcutManager.get_shortcut("nonexistent_action")
        assert shortcut is None

    def test_get_all_shortcuts(self):
        """Test getting all shortcuts"""
        shortcuts = ShortcutManager.get_all_shortcuts()
        assert isinstance(shortcuts, dict)
        assert len(shortcuts) > 0
        assert "open_directory" in shortcuts
        assert all(isinstance(s, Shortcut) for s in shortcuts.values())

    def test_all_shortcuts_count(self):
        """Verify we have 24 shortcuts defined"""
        shortcuts = ShortcutManager.get_all_shortcuts()
        assert len(shortcuts) == 24, f"Expected 24 shortcuts, got {len(shortcuts)}"

    def test_no_duplicate_keys(self):
        """Verify no duplicate key sequences"""
        shortcuts = ShortcutManager.get_all_shortcuts()
        key_sequences = {}

        for action_name, shortcut in shortcuts.items():
            key = shortcut.key
            if key in key_sequences:
                pytest.fail(f"Duplicate key '{key}': {action_name} and {key_sequences[key]}")
            key_sequences[key] = action_name

    def test_shortcuts_by_category(self):
        """Test shortcuts grouped by category"""
        categories = ShortcutManager.get_shortcuts_by_category()

        # Verify expected categories
        expected = [
            "File",
            "Thumbnails",
            "View",
            "Navigation",
            "Crop",
            "Threshold",
            "Help",
            "Settings",
        ]
        for category in expected:
            assert category in categories, f"Category {category} missing"


class TestShortcutSetup:
    """Test shortcuts setup infrastructure"""

    def test_shortcuts_setup_import(self):
        """Test that shortcuts_setup module can be imported"""
        from ui.setup.shortcuts_setup import setup_shortcuts

        assert callable(setup_shortcuts)


class TestTooltipManager:
    """Test TooltipManager functionality"""

    def test_tooltip_manager_import(self):
        """Test TooltipManager can be imported"""
        from config.tooltips import TooltipManager

        assert TooltipManager is not None

    def test_get_tooltip(self):
        """Test getting tooltip text"""
        from config.tooltips import TooltipManager

        tooltip = TooltipManager.get_tooltip("open_directory")
        assert tooltip
        assert "Open Directory" in tooltip
        assert "Ctrl+O" in tooltip

    def test_get_status_tip(self):
        """Test getting status tip text"""
        from config.tooltips import TooltipManager

        status = TooltipManager.get_status_tip("open_directory")
        assert status
        assert len(status) > 0

    def test_nonexistent_tooltip(self):
        """Test getting nonexistent tooltip returns empty string"""
        from config.tooltips import TooltipManager

        tooltip = TooltipManager.get_tooltip("nonexistent")
        assert tooltip == ""

        status = TooltipManager.get_status_tip("nonexistent")
        assert status == ""
