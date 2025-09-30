"""
PreferencesDialog - Application preferences dialog

Extracted from CTHarvester.py during Phase 4 UI refactoring.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QRadioButton, QComboBox, QPushButton, QGroupBox, QApplication
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTranslator
import logging


# Get logger (must be set up by main module)
logger = logging.getLogger(__name__)


def value_to_bool(value):
    """Convert string or any value to boolean."""
    return value.lower() == 'true' if isinstance(value, str) else bool(value)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    import sys
    import os
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class PreferencesDialog(QDialog):
    '''
    PreferencesDialog shows preferences.

    Args:
        None

    Attributes:
        well..
    '''
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.m_app = QApplication.instance()

        self.rbRememberGeometryYes = QRadioButton(self.tr("Yes"))
        self.rbRememberGeometryYes.setChecked(self.m_app.remember_geometry)
        self.rbRememberGeometryYes.clicked.connect(self.on_rbRememberGeometryYes_clicked)
        self.rbRememberGeometryNo = QRadioButton(self.tr("No"))
        self.rbRememberGeometryNo.setChecked(not self.m_app.remember_geometry)
        self.rbRememberGeometryNo.clicked.connect(self.on_rbRememberGeometryNo_clicked)

        self.rbRememberDirectoryYes = QRadioButton(self.tr("Yes"))
        self.rbRememberDirectoryYes.setChecked(self.m_app.remember_directory)
        self.rbRememberDirectoryYes.clicked.connect(self.on_rbRememberDirectoryYes_clicked)
        self.rbRememberDirectoryNo = QRadioButton(self.tr("No"))
        self.rbRememberDirectoryNo.setChecked(not self.m_app.remember_directory)
        self.rbRememberDirectoryNo.clicked.connect(self.on_rbRememberDirectoryNo_clicked)

        self.gbRememberGeometry = QGroupBox()
        self.gbRememberGeometry.setLayout(QHBoxLayout())
        self.gbRememberGeometry.layout().addWidget(self.rbRememberGeometryYes)
        self.gbRememberGeometry.layout().addWidget(self.rbRememberGeometryNo)

        self.gbRememberDirectory = QGroupBox()
        self.gbRememberDirectory.setLayout(QHBoxLayout())
        self.gbRememberDirectory.layout().addWidget(self.rbRememberDirectoryYes)
        self.gbRememberDirectory.layout().addWidget(self.rbRememberDirectoryNo)

        self.comboLang = QComboBox()
        self.comboLang.addItem(self.tr("English"))
        self.comboLang.addItem(self.tr("Korean"))
        self.comboLang.currentIndexChanged.connect(self.comboLangIndexChanged)

        # Log level combo box
        self.comboLogLevel = QComboBox()
        self.comboLogLevel.addItem("DEBUG")
        self.comboLogLevel.addItem("INFO")
        self.comboLogLevel.addItem("WARNING")
        self.comboLogLevel.addItem("ERROR")
        self.comboLogLevel.addItem("CRITICAL")
        self.comboLogLevel.setToolTip(self.tr("Set logging level for file and console output"))

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.setLayout(self.main_layout)
        self.form_layout.addRow(self.tr("Remember Geometry"), self.gbRememberGeometry)
        self.form_layout.addRow(self.tr("Remember Directory"), self.gbRememberDirectory)
        self.form_layout.addRow(self.tr("Language"), self.comboLang)
        self.form_layout.addRow(self.tr("Log Level"), self.comboLogLevel)
        self.button_layout = QHBoxLayout()
        self.btnOK = QPushButton(self.tr("OK"))
        self.btnOK.clicked.connect(self.on_btnOK_clicked)
        self.btnCancel = QPushButton(self.tr("Cancel"))
        self.btnCancel.clicked.connect(self.on_btnCancel_clicked)
        self.button_layout.addWidget(self.btnOK)
        self.button_layout.addWidget(self.btnCancel)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.button_layout)
        self.setWindowTitle(self.tr("CTHarvester - Preferences"))
        self.setGeometry(QRect(100, 100, 320, 180))
        self.move(self.parent.pos() + QPoint(100, 100))

        self.read_settings()

    def on_btnOK_clicked(self):
        self.save_settings()
        self.close()

    def on_btnCancel_clicked(self):
        self.close()

    def on_rbRememberGeometryYes_clicked(self):
        self.m_app.remember_geometry = True

    def on_rbRememberGeometryNo_clicked(self):
        self.m_app.remember_geometry = False

    def on_rbRememberDirectoryYes_clicked(self):
        self.m_app.remember_directory = True

    def on_rbRememberDirectoryNo_clicked(self):
        self.m_app.remember_directory = False

    def comboLangIndexChanged(self, index):
        if index == 0:
            self.m_app.language = "en"
        elif index == 1:
            self.m_app.language = "ko"

    def update_language(self):
        translator = QTranslator()
        translator.load(resource_path('CTHarvester_{}.qm').format(self.m_app.language))
        self.m_app.installTranslator(translator)

        self.rbRememberGeometryYes.setText(self.tr("Yes"))
        self.rbRememberGeometryNo.setText(self.tr("No"))
        self.rbRememberDirectoryYes.setText(self.tr("Yes"))
        self.rbRememberDirectoryNo.setText(self.tr("No"))
        self.gbRememberGeometry.setTitle("")
        self.gbRememberDirectory.setTitle("")
        self.comboLang.setItemText(0, self.tr("English"))
        self.comboLang.setItemText(1, self.tr("Korean"))
        self.btnOK.setText(self.tr("OK"))
        self.btnCancel.setText(self.tr("Cancel"))
        self.form_layout.labelForField(self.gbRememberGeometry).setText(self.tr("Remember Geometry"))
        self.form_layout.labelForField(self.gbRememberDirectory).setText(self.tr("Remember Directory"))
        self.form_layout.labelForField(self.comboLang).setText(self.tr("Language"))
        self.form_layout.labelForField(self.comboLogLevel).setText(self.tr("Log Level"))
        self.setWindowTitle(self.tr("CTHarvester - Preferences"))
        self.parent.update_language()
        self.parent.update_status()

    def read_settings(self):
        try:
            self.m_app.remember_geometry = value_to_bool(self.m_app.settings.value("Remember geometry", True))
            self.m_app.remember_directory = value_to_bool(self.m_app.settings.value("Remember directory", True))
            self.m_app.language = self.m_app.settings.value("Language", "en")
            log_level = self.m_app.settings.value("Log Level", "INFO")

            self.rbRememberGeometryYes.setChecked(self.m_app.remember_geometry)
            self.rbRememberGeometryNo.setChecked(not self.m_app.remember_geometry)
            self.rbRememberDirectoryYes.setChecked(self.m_app.remember_directory)
            self.rbRememberDirectoryNo.setChecked(not self.m_app.remember_directory)

            if self.m_app.language == "en":
                self.comboLang.setCurrentIndex(0)
            elif self.m_app.language == "ko":
                self.comboLang.setCurrentIndex(1)

            # Set log level combo box
            log_level_index = self.comboLogLevel.findText(log_level)
            if log_level_index >= 0:
                self.comboLogLevel.setCurrentIndex(log_level_index)
            else:
                self.comboLogLevel.setCurrentIndex(1)  # Default to INFO

            self.update_language()
        except Exception as e:
            logger.error(f"Error reading settings: {e}")
            # Use default values if settings can't be read
            self.m_app.remember_geometry = True
            self.m_app.remember_directory = True
            self.m_app.language = "en"
            self.comboLogLevel.setCurrentIndex(1)  # INFO

    def save_settings(self):
        try:
            self.m_app.settings.setValue("Remember geometry", self.m_app.remember_geometry)
            self.m_app.settings.setValue("Remember directory", self.m_app.remember_directory)
            self.m_app.settings.setValue("Language", self.m_app.language)

            # Save log level
            log_level = self.comboLogLevel.currentText()
            self.m_app.settings.setValue("Log Level", log_level)

            # Apply log level change immediately
            numeric_level = getattr(logging, log_level, logging.INFO)
            logger.setLevel(numeric_level)
            for handler in logger.handlers:
                handler.setLevel(numeric_level)
            logger.info(f"Log level changed to {log_level}")

            self.update_language()
        except Exception as e:
            logger.error(f"Error saving settings: {e}")