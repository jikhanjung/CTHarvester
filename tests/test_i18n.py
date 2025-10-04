"""
Tests for config/i18n.py - Internationalization support

Part of Phase 1 quality improvement plan (devlog 072)
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import QCoreApplication, QLocale, QTranslator
from PyQt5.QtWidgets import QApplication

from config.i18n import TranslationManager


@pytest.fixture
def qapp(qapp):
    """Reuse pytest-qt's qapp fixture"""
    return qapp


@pytest.fixture
def translation_manager(qapp):
    """Create a TranslationManager instance for testing"""
    return TranslationManager(qapp)


class TestTranslationManager:
    """Test suite for TranslationManager class"""

    def test_initialization(self, translation_manager, qapp):
        """Test TranslationManager initialization"""
        assert translation_manager.app == qapp
        assert isinstance(translation_manager.translator, QTranslator)
        assert translation_manager.current_language == "en"

    def test_supported_languages(self, translation_manager):
        """Test SUPPORTED_LANGUAGES contains expected languages"""
        assert "en" in TranslationManager.SUPPORTED_LANGUAGES
        assert "ko" in TranslationManager.SUPPORTED_LANGUAGES
        assert TranslationManager.SUPPORTED_LANGUAGES["en"] == "English"
        assert TranslationManager.SUPPORTED_LANGUAGES["ko"] == "한국어"

    def test_load_unsupported_language(self, translation_manager, caplog):
        """Test loading an unsupported language returns False"""
        result = translation_manager.load_language("xyz")
        assert result is False
        assert "Unsupported language" in caplog.text

    @patch("os.path.exists")
    def test_load_language_file_not_found(self, mock_exists, translation_manager, caplog):
        """Test loading language when translation file doesn't exist"""
        mock_exists.return_value = False

        result = translation_manager.load_language("ko")

        assert result is False
        assert "Translation file not found" in caplog.text

    @patch("os.path.exists")
    @patch.object(QTranslator, "load")
    def test_load_language_success(self, mock_load, mock_exists, translation_manager, qapp):
        """Test successful language loading"""
        mock_exists.return_value = True
        mock_load.return_value = True

        result = translation_manager.load_language("ko")

        assert result is True
        assert translation_manager.current_language == "ko"
        mock_load.assert_called_once()

    @patch("os.path.exists")
    @patch.object(QTranslator, "load")
    def test_load_language_load_failed(self, mock_load, mock_exists, translation_manager, caplog):
        """Test language loading when QTranslator.load() fails"""
        mock_exists.return_value = True
        mock_load.return_value = False

        result = translation_manager.load_language("ko")

        assert result is False
        assert "Failed to load translation" in caplog.text

    @patch("os.path.exists")
    @patch.object(QTranslator, "load")
    def test_translator_installation(self, mock_load, mock_exists, translation_manager, qapp):
        """Test that translator is installed to application"""
        mock_exists.return_value = True
        mock_load.return_value = True

        # Mock installTranslator to track calls
        with patch.object(qapp, "installTranslator") as mock_install:
            translation_manager.load_language("ko")
            mock_install.assert_called_once_with(translation_manager.translator)

    @patch("os.path.exists")
    @patch.object(QTranslator, "load")
    def test_translator_removal_on_reload(self, mock_load, mock_exists, translation_manager, qapp):
        """Test that old translator is removed before installing new one"""
        mock_exists.return_value = True
        mock_load.return_value = True

        # Mock removeTranslator to track calls
        with patch.object(qapp, "removeTranslator") as mock_remove, patch.object(
            qapp, "installTranslator"
        ):
            translation_manager.load_language("ko")
            mock_remove.assert_called_once_with(translation_manager.translator)

    def test_get_system_language_korean(self, translation_manager):
        """Test system language detection for Korean locale"""
        with patch.object(QLocale, "system") as mock_system:
            mock_locale = MagicMock()
            mock_locale.name.return_value = "ko_KR"
            mock_system.return_value = mock_locale

            lang_code = translation_manager.get_system_language()
            assert lang_code == "ko"

    def test_get_system_language_english(self, translation_manager):
        """Test system language detection for English locale"""
        with patch.object(QLocale, "system") as mock_system:
            mock_locale = MagicMock()
            mock_locale.name.return_value = "en_US"
            mock_system.return_value = mock_locale

            lang_code = translation_manager.get_system_language()
            assert lang_code == "en"

    def test_get_system_language_unsupported(self, translation_manager):
        """Test system language detection for unsupported locale defaults to English"""
        with patch.object(QLocale, "system") as mock_system:
            mock_locale = MagicMock()
            mock_locale.name.return_value = "fr_FR"
            mock_system.return_value = mock_locale

            lang_code = translation_manager.get_system_language()
            assert lang_code == "en"

    def test_tr_static_method(self, translation_manager):
        """Test static tr() method for translation"""
        # Note: Actual translation requires .qm files, we just test the call
        text = "Test"
        result = TranslationManager.tr(text)
        assert isinstance(result, str)

    def test_tr_with_context(self, translation_manager):
        """Test static tr() method with custom context"""
        text = "Test"
        context = "MyContext"
        result = TranslationManager.tr(text, context=context)
        assert isinstance(result, str)

    def test_get_current_language(self, translation_manager):
        """Test getting current language"""
        assert translation_manager.get_current_language() == "en"

    @patch("os.path.exists")
    @patch.object(QTranslator, "load")
    def test_get_current_language_after_load(self, mock_load, mock_exists, translation_manager):
        """Test getting current language after loading a different language"""
        mock_exists.return_value = True
        mock_load.return_value = True

        translation_manager.load_language("ko")
        assert translation_manager.get_current_language() == "ko"

    def test_get_language_name_current(self, translation_manager):
        """Test getting display name of current language"""
        name = translation_manager.get_language_name()
        assert name == "English"

    def test_get_language_name_specific(self, translation_manager):
        """Test getting display name of specific language"""
        name = translation_manager.get_language_name("ko")
        assert name == "한국어"

    def test_get_language_name_unknown(self, translation_manager):
        """Test getting display name of unknown language"""
        name = translation_manager.get_language_name("xyz")
        assert name == "Unknown"

    def test_translation_file_path(self, translation_manager):
        """Test that translation file path is constructed correctly"""
        # This tests the internal logic for finding translation files
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        expected_path = os.path.join(project_root, "resources", "translations", "CTHarvester_ko.qm")

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False
            result = translation_manager.load_language("ko")

            # Verify the path was checked
            assert result is False
            # The path should have been checked via os.path.exists
            called_path = mock_exists.call_args[0][0]
            assert "CTHarvester_ko.qm" in called_path
            assert "translations" in called_path
