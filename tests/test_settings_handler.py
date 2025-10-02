"""
Tests for WindowSettingsHandler class

Tests the settings management logic extracted from main_window.py
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import QRect

from ui.handlers.settings_handler import WindowSettingsHandler


@pytest.mark.unit
class TestWindowSettingsHandler:
    """Test suite for WindowSettingsHandler"""

    @pytest.fixture
    def mock_app(self):
        """Create a mock QApplication instance"""
        app = MagicMock()
        app.remember_directory = True
        app.default_directory = "."
        app.remember_geometry = True
        app.language = "en"
        app.use_rust_thumbnail = True
        return app

    @pytest.fixture
    def mock_window(self):
        """Create a mock main window"""
        window = MagicMock()
        window.mcube_widget.geometry.return_value = QRect(10, 20, 200, 200)
        window.geometry.return_value = QRect(100, 100, 800, 600)
        window.mcube_geometry = QRect(0, 0, 150, 150)
        return window

    @pytest.fixture
    def mock_settings_manager(self):
        """Create a mock settings manager"""
        manager = MagicMock()
        manager.get = MagicMock(side_effect=lambda key, default=None: default)
        return manager

    @pytest.fixture
    def handler(self, mock_window, mock_settings_manager, mock_app):
        """Create a WindowSettingsHandler instance"""
        with patch("ui.handlers.settings_handler.QApplication.instance", return_value=mock_app):
            return WindowSettingsHandler(mock_window, mock_settings_manager)

    def test_initialization(self, handler, mock_window, mock_settings_manager, mock_app):
        """Test handler initializes correctly"""
        assert handler.window == mock_window
        assert handler.settings == mock_settings_manager
        assert handler.app == mock_app

    def test_read_directory_settings_remember_enabled(self, handler):
        """Test reading directory settings when remember is enabled"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "window.remember_position": True,
            "application.default_directory": "/test/path",
        }.get(key, default)

        handler._read_directory_settings()

        assert handler.app.remember_directory is True
        assert handler.app.default_directory == "/test/path"

    def test_read_directory_settings_remember_disabled(self, handler):
        """Test reading directory settings when remember is disabled"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "window.remember_position": False
        }.get(key, default)

        handler._read_directory_settings()

        assert handler.app.remember_directory is False
        assert handler.app.default_directory == "."

    def test_read_geometry_settings_with_saved_values(self, handler):
        """Test reading geometry with saved values"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "window.remember_size": True,
            "window.main_geometry": {"x": 150, "y": 200, "width": 1024, "height": 768},
            "window.mcube_geometry": {"x": 5, "y": 10, "width": 200, "height": 200},
        }.get(key, default)

        handler._read_geometry_settings()

        assert handler.app.remember_geometry is True
        handler.window.setGeometry.assert_called_once()
        call_args = handler.window.setGeometry.call_args[0][0]
        assert call_args.x() == 150
        assert call_args.y() == 200
        assert call_args.width() == 1024
        assert call_args.height() == 768

        assert handler.window.mcube_geometry.x() == 5
        assert handler.window.mcube_geometry.y() == 10
        assert handler.window.mcube_geometry.width() == 200
        assert handler.window.mcube_geometry.height() == 200

    def test_read_geometry_settings_without_saved_values(self, handler):
        """Test reading geometry without saved values (uses defaults)"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "window.remember_size": True
        }.get(key, default)

        handler._read_geometry_settings()

        # Should use default values
        handler.window.setGeometry.assert_called_once()
        call_args = handler.window.setGeometry.call_args[0][0]
        assert call_args.x() == 100
        assert call_args.y() == 100
        assert call_args.width() == 600
        assert call_args.height() == 550

    def test_read_geometry_settings_remember_disabled(self, handler):
        """Test reading geometry when remember is disabled"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "window.remember_size": False
        }.get(key, default)

        handler._read_geometry_settings()

        assert handler.app.remember_geometry is False
        # Should still set default geometry
        handler.window.setGeometry.assert_called_once()

    def test_read_language_settings(self, handler):
        """Test reading language settings"""
        test_cases = [
            ("en", "en"),
            ("ko", "ko"),
            ("auto", "en"),
            ("unknown", "en"),  # Unknown language defaults to en
        ]

        for lang_code, expected in test_cases:
            handler.settings.get = MagicMock(return_value=lang_code)
            handler._read_language_settings()
            assert handler.app.language == expected

    def test_read_processing_settings_with_checkbox(self, handler):
        """Test reading processing settings when checkbox exists"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "processing.use_rust_module": False
        }.get(key, default)

        handler.window.cbxUseRust = MagicMock()
        handler._read_processing_settings()

        assert handler.app.use_rust_thumbnail is False
        handler.window.cbxUseRust.setChecked.assert_called_once_with(False)

    def test_read_processing_settings_without_checkbox(self, handler):
        """Test reading processing settings when checkbox doesn't exist"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "processing.use_rust_module": True
        }.get(key, default)

        # Remove checkbox attribute
        if hasattr(handler.window, "cbxUseRust"):
            delattr(handler.window, "cbxUseRust")

        # Should not crash
        handler._read_processing_settings()

        assert handler.app.use_rust_thumbnail is True

    def test_read_all_settings_success(self, handler):
        """Test reading all settings successfully"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "window.remember_position": True,
            "application.default_directory": "/test",
            "window.remember_size": True,
            "window.main_geometry": {"x": 100, "y": 100, "width": 800, "height": 600},
            "window.mcube_geometry": {"x": 0, "y": 0, "width": 150, "height": 150},
            "application.language": "ko",
            "processing.use_rust_module": False,
        }.get(key, default)

        handler.read_all_settings()

        # Verify all settings were applied
        assert handler.app.remember_directory is True
        assert handler.app.default_directory == "/test"
        assert handler.app.remember_geometry is True
        assert handler.app.language == "ko"
        assert handler.app.use_rust_thumbnail is False

    def test_read_all_settings_with_error(self, handler):
        """Test reading settings when an error occurs"""
        handler.settings.get.side_effect = Exception("Settings file corrupted")

        # Should not crash, should apply defaults
        handler.read_all_settings()

        # Verify defaults were applied
        assert handler.app.remember_directory is True
        assert handler.app.default_directory == "."
        assert handler.app.remember_geometry is True
        assert handler.app.language == "en"
        assert handler.app.use_rust_thumbnail is True

    def test_apply_defaults(self, handler):
        """Test applying default settings"""
        handler._apply_defaults()

        assert handler.app.remember_directory is True
        assert handler.app.default_directory == "."
        assert handler.app.remember_geometry is True
        assert handler.app.language == "en"
        assert handler.app.use_rust_thumbnail is True

        # Verify window geometry was set
        handler.window.setGeometry.assert_called()
        assert handler.window.mcube_geometry == QRect(0, 0, 150, 150)

    def test_apply_defaults_with_checkbox(self, handler):
        """Test applying defaults when checkbox exists"""
        handler.window.cbxUseRust = MagicMock()
        handler._apply_defaults()

        handler.window.cbxUseRust.setChecked.assert_called_once_with(True)

    def test_save_directory_settings(self, handler):
        """Test saving directory settings"""
        handler.app.default_directory = "/my/custom/path"
        handler._save_directory_settings()

        handler.settings.set.assert_called_once_with(
            "application.default_directory", "/my/custom/path"
        )

    def test_save_geometry_settings(self, handler):
        """Test saving geometry settings"""
        handler.window.geometry.return_value = QRect(150, 200, 1024, 768)
        handler.window.mcube_widget.geometry.return_value = QRect(5, 10, 250, 250)

        handler._save_geometry_settings()

        # Verify main geometry was saved
        calls = handler.settings.set.call_args_list
        assert len(calls) == 2

        # Check main window geometry
        assert calls[0][0][0] == "window.main_geometry"
        assert calls[0][0][1] == {"x": 150, "y": 200, "width": 1024, "height": 768}

        # Check mcube geometry
        assert calls[1][0][0] == "window.mcube_geometry"
        assert calls[1][0][1] == {"x": 5, "y": 10, "width": 250, "height": 250}

    def test_save_processing_settings(self, handler):
        """Test saving processing settings"""
        handler.app.use_rust_thumbnail = False
        handler._save_processing_settings()

        handler.settings.set.assert_called_once_with("processing.use_rust_module", False)

    def test_save_processing_settings_default_value(self, handler):
        """Test saving processing settings when attribute doesn't exist"""
        # Remove attribute
        delattr(handler.app, "use_rust_thumbnail")

        handler._save_processing_settings()

        # Should save True as default
        handler.settings.set.assert_called_once_with("processing.use_rust_module", True)

    def test_save_all_settings_remember_enabled(self, handler):
        """Test saving all settings when remember options are enabled"""
        handler.app.remember_directory = True
        handler.app.remember_geometry = True
        handler.app.default_directory = "/saved/path"
        handler.app.use_rust_thumbnail = False

        handler.save_all_settings()

        # Verify settings were saved
        assert handler.settings.set.call_count >= 3  # directory, main_geom, mcube_geom, processing
        handler.settings.save.assert_called_once()

    def test_save_all_settings_remember_disabled(self, handler):
        """Test saving all settings when remember options are disabled"""
        handler.app.remember_directory = False
        handler.app.remember_geometry = False

        handler.save_all_settings()

        # Only processing settings should be saved
        assert handler.settings.set.call_count == 1  # Only processing settings
        handler.settings.save.assert_called_once()

    def test_save_all_settings_with_error(self, handler, caplog):
        """Test saving settings when an error occurs"""
        import logging

        handler.settings.set.side_effect = Exception("Failed to write settings")

        with caplog.at_level(logging.ERROR):
            handler.save_all_settings()

        # Verify error was logged
        assert any(
            "Error saving main window settings" in record.message for record in caplog.records
        )

    def test_geometry_dict_validation(self, handler):
        """Test geometry settings with invalid dict format"""
        # Test with non-dict geometry
        handler.settings.get.side_effect = lambda key, default=None: {
            "window.remember_size": True,
            "window.main_geometry": "invalid",  # Not a dict
            "window.mcube_geometry": None,  # None value
        }.get(key, default)

        handler._read_geometry_settings()

        # Should fall back to defaults
        handler.window.setGeometry.assert_called_once()
        call_args = handler.window.setGeometry.call_args[0][0]
        assert call_args.x() == 100  # Default values
        assert call_args.y() == 100

    def test_geometry_dict_partial_values(self, handler):
        """Test geometry settings with partial dict values"""
        handler.settings.get.side_effect = lambda key, default=None: {
            "window.remember_size": True,
            "window.main_geometry": {"x": 200},  # Missing y, width, height
            "window.mcube_geometry": {"width": 300, "height": 400},  # Missing x, y
        }.get(key, default)

        handler._read_geometry_settings()

        # Should use defaults for missing values
        call_args = handler.window.setGeometry.call_args[0][0]
        assert call_args.x() == 200  # From saved
        assert call_args.y() == 100  # Default
        assert call_args.width() == 600  # Default
        assert call_args.height() == 550  # Default

        assert handler.window.mcube_geometry.x() == 0  # Default
        assert handler.window.mcube_geometry.y() == 0  # Default
        assert handler.window.mcube_geometry.width() == 300  # From saved
        assert handler.window.mcube_geometry.height() == 400  # From saved


@pytest.mark.integration
class TestWindowSettingsHandlerIntegration:
    """Integration tests for WindowSettingsHandler with real SettingsManager"""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory"""
        # SettingsManager takes a directory, not a file path
        config_dir = tmp_path / "config"
        return str(config_dir)

    @pytest.fixture
    def real_settings_manager(self, temp_config_dir):
        """Create a real SettingsManager instance"""
        from utils.settings_manager import SettingsManager

        return SettingsManager(temp_config_dir)

    @pytest.fixture
    def mock_app_real(self):
        """Create a mock QApplication for integration tests"""
        app = MagicMock()
        return app

    @pytest.fixture
    def mock_window_real(self):
        """Create a mock window for integration tests"""
        window = MagicMock()
        window.mcube_widget.geometry.return_value = QRect(10, 20, 200, 200)
        window.geometry.return_value = QRect(100, 100, 800, 600)
        return window

    @pytest.fixture
    def handler_real(self, mock_window_real, real_settings_manager, mock_app_real):
        """Create a handler with real SettingsManager"""
        with patch(
            "ui.handlers.settings_handler.QApplication.instance", return_value=mock_app_real
        ):
            return WindowSettingsHandler(mock_window_real, real_settings_manager)

    def test_full_save_load_cycle(self, handler_real):
        """Test complete save and load cycle with real settings manager"""
        # Set some values
        handler_real.app.remember_directory = True
        handler_real.app.default_directory = "/integration/test/path"
        handler_real.app.remember_geometry = True
        handler_real.app.use_rust_thumbnail = False
        handler_real.app.language = "ko"

        # Save settings
        handler_real.save_all_settings()

        # Create a new handler with same settings file
        new_app = MagicMock()
        new_window = MagicMock()
        new_window.mcube_widget.geometry.return_value = QRect(10, 20, 200, 200)

        with patch("ui.handlers.settings_handler.QApplication.instance", return_value=new_app):
            new_handler = WindowSettingsHandler(new_window, handler_real.settings)

        # Load settings
        new_handler.read_all_settings()

        # Verify values were persisted
        assert new_app.default_directory == "/integration/test/path"
        assert new_app.use_rust_thumbnail is False

    def test_settings_save_called(self, handler_real):
        """Test that save method is called when saving settings"""
        handler_real.app.remember_directory = True
        handler_real.app.default_directory = "/persistent/path"

        # Mock the save method to verify it's called
        handler_real.settings.save = MagicMock()

        handler_real.save_all_settings()

        # Verify save was called
        handler_real.settings.save.assert_called_once()
