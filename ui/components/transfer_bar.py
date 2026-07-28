from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QProgressBar
)
from PyQt6.QtCore import pyqtSignal, Qt

class TransferBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(36)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        self.status_lbl = QLabel("Ready")
        layout.addWidget(self.status_lbl, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

    def set_status(self, text: str):
        self.status_lbl.setText(text)

    def show_progress(self, val: int = 0):
        self.progress_bar.setValue(val)
        self.progress_bar.show()

    def hide_progress(self):
        self.progress_bar.hide()
