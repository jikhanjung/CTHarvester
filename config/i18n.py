"""
Internationalization (i18n) support

Provides translation management for multi-language support.
Created during Phase 1.4 UI/UX improvements.
"""

import logging
import os

from PyQt5.QtCore import QCoreApplication, QLocale, QTranslator

logger = logging.getLogger(__name__)


class TranslationManager:
    """Translation manager for multi-language support"""

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "ko": "한국어",
    }

    def __init__(self, app):
        """
        Initialize translation manager

        Args:
            app: QApplication instance
        """
        self.app = app
        self.translator = QTranslator()
        self.current_language = "en"

    def load_language(self, language_code: str) -> bool:
        """
        Load language translation

        Args:
            language_code: Language code ('en', 'ko')

        Returns:
            True if successful, False otherwise
        """
        if language_code not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language: {language_code}")
            return False

        # Translation file path
        # Look for .qm files in resources/translations/
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qm_file = os.path.join(project_root, "resources", "translations", f"CTHarvester_{language_code}.qm")

        if not os.path.exists(qm_file):
            logger.error(f"Translation file not found: {qm_file}")
            return False

        # Remove existing translator
        self.app.removeTranslator(self.translator)

        # Load new translation
        if self.translator.load(qm_file):
            self.app.installTranslator(self.translator)
            self.current_language = language_code
            logger.info(f"Loaded language: {language_code} from {qm_file}")
            return True
        else:
            logger.error(f"Failed to load translation: {qm_file}")
            return False

    def get_system_language(self) -> str:
        """
        Detect system language

        Returns:
            Language code ('en', 'ko', etc.)
        """
        locale = QLocale.system().name()  # e.g., 'ko_KR', 'en_US'
        language_code = locale.split("_")[0]

        if language_code in self.SUPPORTED_LANGUAGES:
            return language_code
        else:
            return "en"  # Default to English

    @staticmethod
    def tr(text: str, context: str = "Global") -> str:
        """
        Translate text

        Args:
            text: Source text
            context: Translation context (class name, etc.)

        Returns:
            Translated text
        """
        return QCoreApplication.translate(context, text)

    def get_current_language(self) -> str:
        """Get current language code"""
        return self.current_language

    def get_language_name(self, language_code: str = None) -> str:
        """
        Get language display name

        Args:
            language_code: Language code (uses current if None)

        Returns:
            Display name (e.g., 'English', '한국어')
        """
        if language_code is None:
            language_code = self.current_language

        return self.SUPPORTED_LANGUAGES.get(language_code, "Unknown")
