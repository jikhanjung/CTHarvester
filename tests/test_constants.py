"""Tests for config/constants.py"""

import importlib
import sys


class TestConstants:
    """Test constants module imports and fallbacks"""

    def test_version_import_fallback(self):
        """config.constants falls back to an obviously-unknown version.

        Reloading the module with ``version`` blocked mutates the shared module
        object, and monkeypatch cannot undo that -- it restores ``sys.modules``
        but leaves ``config.constants`` stuck on the fallback value for the rest
        of the session. tests/test_version_consistency.py then asserts the real
        version is re-exported and fails, depending on collection order. Hence
        the explicit reload in ``finally``.
        """
        import config.constants as constants_module

        original = sys.modules.get("version", ...)
        sys.modules["version"] = None  # a None entry makes ``import version`` raise
        try:
            importlib.reload(constants_module)

            assert constants_module.__version__ == "0.0.0+unknown"
            assert constants_module.__version_info__ == (0, 0, 0)
            assert constants_module.PROGRAM_VERSION == "0.0.0+unknown"
        finally:
            if original is ...:
                del sys.modules["version"]
            else:
                sys.modules["version"] = original
            importlib.reload(constants_module)

    def test_version_matches_version_module(self):
        """After the fallback test restores it, the real version is re-exported."""
        import config.constants as constants_module
        import version

        assert constants_module.__version__ == version.__version__
        assert constants_module.PROGRAM_VERSION == version.__version__
