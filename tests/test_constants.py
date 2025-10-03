"""Tests for config/constants.py"""

import sys
from pathlib import Path

import pytest


class TestConstants:
    """Test constants module imports and fallbacks"""

    def test_version_import_fallback(self, monkeypatch):
        """Test fallback when version.py import fails"""
        # Remove version module if already imported
        if "version" in sys.modules:
            monkeypatch.setitem(sys.modules, "version", None)

        # Force reimport of constants to trigger ImportError path
        import importlib

        import config.constants as constants_module

        importlib.reload(constants_module)

        # Check fallback values are set
        assert hasattr(constants_module, "__version__")
        assert hasattr(constants_module, "__version_info__")
        assert isinstance(constants_module.__version__, str)
        assert isinstance(constants_module.__version_info__, tuple)
