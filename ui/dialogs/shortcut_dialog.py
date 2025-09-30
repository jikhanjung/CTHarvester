"""
Keyboard shortcuts help dialog

Displays all available keyboard shortcuts organized by category.
Created during Phase 1.5 UI/UX improvements.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGridLayout
)
from PyQt5.QtCore import Qt

from config.shortcuts import ShortcutManager


class ShortcutDialog(QDialog):
    """
    Keyboard shortcuts help dialog

    Shows all available shortcuts organized by category.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(700, 500)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Title
        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Scrollable area for shortcuts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        # Content widget
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)

        # Get shortcuts by category
        shortcuts = ShortcutManager.get_all_shortcuts()
        categories = ShortcutManager.get_shortcuts_by_category()

        for category, actions in categories.items():
            # Category header
            header = QLabel(category)
            header.setStyleSheet("""
                font-weight: bold;
                font-size: 13pt;
                padding: 5px;
                background-color: #e0e0e0;
                border-radius: 3px;
            """)
            content_layout.addWidget(header)

            # Grid for shortcuts in this category
            grid = QGridLayout()
            grid.setSpacing(10)
            grid.setContentsMargins(10, 5, 10, 5)

            row = 0
            for action in actions:
                if action in shortcuts:
                    shortcut = shortcuts[action]

                    # Key sequence (bold, monospace)
                    key_label = QLabel(shortcut.key)
                    key_label.setStyleSheet("""
                        font-family: monospace;
                        font-weight: bold;
                        font-size: 11pt;
                        padding: 5px 10px;
                        background-color: #f5f5f5;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                    """)
                    key_label.setAlignment(Qt.AlignCenter)
                    key_label.setMinimumWidth(120)

                    # Description
                    desc_label = QLabel(shortcut.description)
                    desc_label.setStyleSheet("font-size: 11pt; padding: 5px;")

                    grid.addWidget(key_label, row, 0)
                    grid.addWidget(desc_label, row, 1)
                    row += 1

            content_layout.addLayout(grid)

        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Close button
        button_layout = QVBoxLayout()
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                font-size: 11pt;
                padding: 8px 30px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button, alignment=Qt.AlignCenter)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)