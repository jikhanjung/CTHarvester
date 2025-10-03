"""Tests for config/shortcuts.py"""

import pytest

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
