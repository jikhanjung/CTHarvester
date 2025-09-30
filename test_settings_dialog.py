"""
Test script for SettingsDialog

Run this to test the settings dialog without running the full application.
"""
import sys
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel

from utils.settings_manager import SettingsManager
from ui.dialogs.settings_dialog import SettingsDialog


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings Dialog Test")
        self.setGeometry(100, 100, 400, 200)

        # Initialize settings manager
        self.settings_manager = SettingsManager()

        layout = QVBoxLayout()

        # Info label
        info = QLabel(
            f"Settings file location:\n{self.settings_manager.get_config_file_path()}\n\n"
            "Click the button below to open the settings dialog."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Button to open settings dialog
        btn = QPushButton("Open Settings Dialog")
        btn.clicked.connect(self.open_settings)
        layout.addWidget(btn)

        # Button to show current settings
        show_btn = QPushButton("Show Current Settings")
        show_btn.clicked.connect(self.show_settings)
        layout.addWidget(show_btn)

        self.setLayout(layout)

    def open_settings(self):
        dialog = SettingsDialog(self.settings_manager, self)
        result = dialog.exec_()

        if result:
            print("Settings dialog accepted (OK clicked)")
            print("Current settings:")
            self.print_settings()
        else:
            print("Settings dialog rejected (Cancel clicked)")

    def show_settings(self):
        print("\n=== Current Settings ===")
        self.print_settings()

    def print_settings(self):
        settings = self.settings_manager.get_all()
        import yaml
        print(yaml.dump(settings, default_flow_style=False, allow_unicode=True))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())