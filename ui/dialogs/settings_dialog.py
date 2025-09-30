"""
Settings Editor Dialog

Provides GUI for editing application settings stored in YAML.
Created during Phase 2.2 settings management improvements.
"""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """
    Settings editor dialog

    Features:
    - Tabbed interface for different setting categories
    - Import/Export settings
    - Reset to defaults
    - Apply/OK/Cancel buttons
    """

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Preferences")
        self.setMinimumSize(700, 500)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()

        # Tab widget
        tabs = QTabWidget()

        # Create tabs
        tabs.addTab(self.create_general_tab(), "General")
        tabs.addTab(self.create_thumbnails_tab(), "Thumbnails")
        tabs.addTab(self.create_processing_tab(), "Processing")
        tabs.addTab(self.create_rendering_tab(), "Rendering")
        tabs.addTab(self.create_advanced_tab(), "Advanced")

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()

        # Import/Export
        import_button = QPushButton("Import Settings...")
        import_button.clicked.connect(self.import_settings)
        button_layout.addWidget(import_button)

        export_button = QPushButton("Export Settings...")
        export_button.clicked.connect(self.export_settings)
        button_layout.addWidget(export_button)

        button_layout.addStretch()

        # Reset to defaults
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_button)

        # Apply/Cancel
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_button)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept_settings)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_general_tab(self):
        """General settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Language
        lang_group = QGroupBox("Language")
        lang_layout = QFormLayout()

        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto (System)", "English", "한국어"])
        lang_layout.addRow("Interface Language:", self.language_combo)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # Theme
        theme_group = QGroupBox("Appearance")
        theme_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        theme_layout.addRow("Theme:", self.theme_combo)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Window
        window_group = QGroupBox("Window")
        window_layout = QVBoxLayout()

        self.remember_position_check = QCheckBox("Remember window position")
        window_layout.addWidget(self.remember_position_check)

        self.remember_size_check = QCheckBox("Remember window size")
        window_layout.addWidget(self.remember_size_check)

        window_group.setLayout(window_layout)
        layout.addWidget(window_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_thumbnails_tab(self):
        """Thumbnail settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        group = QGroupBox("Thumbnail Generation")
        form_layout = QFormLayout()

        # Max size
        self.thumb_max_size_spin = QSpinBox()
        self.thumb_max_size_spin.setRange(100, 2000)
        self.thumb_max_size_spin.setSuffix(" px")
        form_layout.addRow("Max thumbnail size:", self.thumb_max_size_spin)

        # Sample size
        self.thumb_sample_size_spin = QSpinBox()
        self.thumb_sample_size_spin.setRange(10, 100)
        form_layout.addRow("Sample size:", self.thumb_sample_size_spin)

        # Max level
        self.thumb_max_level_spin = QSpinBox()
        self.thumb_max_level_spin.setRange(1, 20)
        form_layout.addRow("Max pyramid level:", self.thumb_max_level_spin)

        # Compression
        self.thumb_compression_check = QCheckBox("Enable compression")
        form_layout.addRow("", self.thumb_compression_check)

        # Format
        self.thumb_format_combo = QComboBox()
        self.thumb_format_combo.addItems(["TIF", "PNG"])
        form_layout.addRow("Format:", self.thumb_format_combo)

        group.setLayout(form_layout)
        layout.addWidget(group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_processing_tab(self):
        """Processing settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        group = QGroupBox("Processing Options")
        form_layout = QFormLayout()

        # Thread count
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(0, 16)
        self.threads_spin.setSpecialValueText("Auto")
        form_layout.addRow("Worker threads:", self.threads_spin)

        # Memory limit
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(1, 64)
        self.memory_limit_spin.setSuffix(" GB")
        form_layout.addRow("Memory limit:", self.memory_limit_spin)

        # Rust module
        self.use_rust_check = QCheckBox("Use high-performance Rust module")
        form_layout.addRow("", self.use_rust_check)

        group.setLayout(form_layout)
        layout.addWidget(group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_rendering_tab(self):
        """Rendering settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        group = QGroupBox("3D Rendering")
        form_layout = QFormLayout()

        # Default threshold
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)
        form_layout.addRow("Default threshold:", self.threshold_spin)

        # Anti-aliasing
        self.antialiasing_check = QCheckBox("Enable anti-aliasing")
        form_layout.addRow("", self.antialiasing_check)

        # FPS display
        self.show_fps_check = QCheckBox("Show FPS counter")
        form_layout.addRow("", self.show_fps_check)

        group.setLayout(form_layout)
        layout.addWidget(group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_advanced_tab(self):
        """Advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Logging
        log_group = QGroupBox("Logging")
        log_layout = QFormLayout()

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_layout.addRow("Log level:", self.log_level_combo)

        self.console_output_check = QCheckBox("Enable console output")
        log_layout.addRow("", self.console_output_check)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Export options
        export_group = QGroupBox("Export")
        export_layout = QFormLayout()

        self.mesh_format_combo = QComboBox()
        self.mesh_format_combo.addItems(["STL", "PLY", "OBJ"])
        export_layout.addRow("Mesh format:", self.mesh_format_combo)

        self.image_format_combo = QComboBox()
        self.image_format_combo.addItems(["TIF", "PNG", "JPG"])
        export_layout.addRow("Image format:", self.image_format_combo)

        self.compression_level_spin = QSpinBox()
        self.compression_level_spin.setRange(0, 9)
        export_layout.addRow("Compression level:", self.compression_level_spin)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def load_settings(self):
        """Load settings values into UI"""
        s = self.settings_manager

        # General
        lang = s.get("application.language", "auto")
        lang_map = {"auto": 0, "en": 1, "ko": 2}
        self.language_combo.setCurrentIndex(lang_map.get(lang, 0))

        theme = s.get("application.theme", "light")
        self.theme_combo.setCurrentIndex(0 if theme == "light" else 1)

        self.remember_position_check.setChecked(s.get("window.remember_position", True))
        self.remember_size_check.setChecked(s.get("window.remember_size", True))

        # Thumbnails
        self.thumb_max_size_spin.setValue(s.get("thumbnails.max_size", 500))
        self.thumb_sample_size_spin.setValue(s.get("thumbnails.sample_size", 20))
        self.thumb_max_level_spin.setValue(s.get("thumbnails.max_level", 10))
        self.thumb_compression_check.setChecked(s.get("thumbnails.compression", True))

        fmt = s.get("thumbnails.format", "tif")
        self.thumb_format_combo.setCurrentIndex(0 if fmt == "tif" else 1)

        # Processing
        threads = s.get("processing.threads", "auto")
        if threads == "auto":
            self.threads_spin.setValue(0)
        else:
            self.threads_spin.setValue(int(threads))

        self.memory_limit_spin.setValue(s.get("processing.memory_limit_gb", 4))
        self.use_rust_check.setChecked(s.get("processing.use_rust_module", True))

        # Rendering
        self.threshold_spin.setValue(s.get("rendering.default_threshold", 128))
        self.antialiasing_check.setChecked(s.get("rendering.anti_aliasing", True))
        self.show_fps_check.setChecked(s.get("rendering.show_fps", False))

        # Advanced
        log_level = s.get("logging.level", "INFO")
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if log_level in levels:
            self.log_level_combo.setCurrentIndex(levels.index(log_level))

        self.console_output_check.setChecked(s.get("logging.console_output", True))

        # Export
        mesh_fmt = s.get("export.mesh_format", "stl").upper()
        mesh_formats = ["STL", "PLY", "OBJ"]
        if mesh_fmt in mesh_formats:
            self.mesh_format_combo.setCurrentIndex(mesh_formats.index(mesh_fmt))

        img_fmt = s.get("export.image_format", "tif").upper()
        img_formats = ["TIF", "PNG", "JPG"]
        if img_fmt in img_formats:
            self.image_format_combo.setCurrentIndex(img_formats.index(img_fmt))

        self.compression_level_spin.setValue(s.get("export.compression_level", 6))

    def save_settings(self):
        """Save settings values from UI"""
        s = self.settings_manager

        # General
        lang_map = {0: "auto", 1: "en", 2: "ko"}
        s.set("application.language", lang_map[self.language_combo.currentIndex()])
        s.set("application.theme", "light" if self.theme_combo.currentIndex() == 0 else "dark")
        s.set("window.remember_position", self.remember_position_check.isChecked())
        s.set("window.remember_size", self.remember_size_check.isChecked())

        # Thumbnails
        s.set("thumbnails.max_size", self.thumb_max_size_spin.value())
        s.set("thumbnails.sample_size", self.thumb_sample_size_spin.value())
        s.set("thumbnails.max_level", self.thumb_max_level_spin.value())
        s.set("thumbnails.compression", self.thumb_compression_check.isChecked())
        s.set("thumbnails.format", "tif" if self.thumb_format_combo.currentIndex() == 0 else "png")

        # Processing
        threads = self.threads_spin.value()
        s.set("processing.threads", "auto" if threads == 0 else threads)
        s.set("processing.memory_limit_gb", self.memory_limit_spin.value())
        s.set("processing.use_rust_module", self.use_rust_check.isChecked())

        # Rendering
        s.set("rendering.default_threshold", self.threshold_spin.value())
        s.set("rendering.anti_aliasing", self.antialiasing_check.isChecked())
        s.set("rendering.show_fps", self.show_fps_check.isChecked())

        # Advanced
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        s.set("logging.level", levels[self.log_level_combo.currentIndex()])
        s.set("logging.console_output", self.console_output_check.isChecked())

        # Export
        mesh_formats = ["stl", "ply", "obj"]
        s.set("export.mesh_format", mesh_formats[self.mesh_format_combo.currentIndex()])

        img_formats = ["tif", "png", "jpg"]
        s.set("export.image_format", img_formats[self.image_format_combo.currentIndex()])

        s.set("export.compression_level", self.compression_level_spin.value())

        s.save()
        logger.info("Settings saved from dialog")

    def apply_settings(self):
        """Apply settings"""
        self.save_settings()
        QMessageBox.information(
            self,
            "Settings Applied",
            "Settings have been applied successfully.\n\nSome changes may require restarting the application.",
        )

    def accept_settings(self):
        """OK button"""
        self.save_settings()
        self.accept()

    def reset_to_defaults(self):
        """Reset to default settings"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.settings_manager.reset()
            self.load_settings()
            QMessageBox.information(self, "Reset Complete", "Settings have been reset to defaults.")

    def import_settings(self):
        """Import settings from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Settings", "", "YAML Files (*.yaml *.yml);;All Files (*)"
        )

        if file_path:
            try:
                self.settings_manager.import_settings(file_path)
                self.load_settings()
                QMessageBox.information(self, "Import Complete", "Settings imported successfully.")
            except Exception as e:
                logger.error(f"Failed to import settings: {e}")
                QMessageBox.critical(self, "Import Failed", f"Failed to import settings:\n{e}")

    def export_settings(self):
        """Export settings to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            "ctharvester_settings.yaml",
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )

        if file_path:
            try:
                self.settings_manager.export(file_path)
                QMessageBox.information(
                    self, "Export Complete", f"Settings exported to:\n{file_path}"
                )
            except Exception as e:
                logger.error(f"Failed to export settings: {e}")
                QMessageBox.critical(self, "Export Failed", f"Failed to export settings:\n{e}")
