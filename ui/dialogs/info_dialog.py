"""
InfoDialog - Application information dialog

Extracted from CTHarvester.py during Phase 4 UI refactoring.
"""

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from config.constants import PROGRAM_VERSION

# Build-time constants (imported from main module)
PROGRAM_COPYRIGHT = "© 2023-2025 Jikhan Jung"


class InfoDialog(QDialog):
    """
    InfoDialog shows application information.
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        # Create layout
        layout = QVBoxLayout()

        # Add title
        title_label = QLabel("<h2>CTHarvester</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Add version info
        version_label = QLabel(self.tr("Version {}").format(PROGRAM_VERSION))
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # Add description
        desc_label = QLabel(self.tr("CT Image Stack Processing Tool"))
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)

        # Add copyright
        copyright_label = QLabel(self.tr(PROGRAM_COPYRIGHT))
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)

        # Add GitHub link
        github_label = QLabel(
            '<a href="https://github.com/jikhanjung/CTHarvester">GitHub Repository</a>'
        )
        github_label.setOpenExternalLinks(True)
        github_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(github_label)

        # Add spacing
        layout.addSpacing(20)

        # Add OK button
        button_layout = QHBoxLayout()
        btn_ok = QPushButton(self.tr("OK"))
        btn_ok.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle(self.tr("About CTHarvester"))
        self.setFixedSize(300, 200)
        self.move(self.parent.pos() + QPoint(150, 150))
