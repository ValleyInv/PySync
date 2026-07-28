import os
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QFrame, QHBoxLayout, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QImage
from core.models import PackageItem

class DetailPanel(QWidget):
    open_clicked = pyqtSignal(PackageItem)
    reveal_clicked = pyqtSignal(PackageItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detailPanel")
        self.setFixedWidth(300)
        self.current_item: Optional[PackageItem] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel("Item Information")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #5865f2;")
        layout.addWidget(title_lbl)

        # Preview Container Widget
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("previewArea")
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        # Image Preview Label
        self.image_lbl = QLabel()
        self.image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_lbl.setStyleSheet("background-color: transparent;")
        self.image_lbl.setMinimumHeight(150)
        self.image_lbl.hide()
        preview_layout.addWidget(self.image_lbl)

        # Text Preview Edit
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setStyleSheet("background-color: #18191c; border: none; font-family: 'Consolas', monospace; font-size: 11px;")
        self.text_preview.hide()
        preview_layout.addWidget(self.text_preview)

        # Placeholder Label
        self.placeholder_lbl = QLabel("Select an item to view preview and metadata")
        self.placeholder_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_lbl.setWordWrap(True)
        self.placeholder_lbl.setStyleSheet("color: #949ba4; font-size: 12px; padding: 20px;")
        preview_layout.addWidget(self.placeholder_lbl)

        layout.addWidget(self.preview_frame, 1)

        # Metadata Details Box
        self.meta_box = QFrame()
        meta_layout = QVBoxLayout(self.meta_box)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(6)

        self.name_lbl = QLabel("-")
        self.name_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        self.name_lbl.setWordWrap(True)
        meta_layout.addWidget(self.name_lbl)

        self.size_lbl = QLabel("Size: -")
        self.size_lbl.setStyleSheet("color: #949ba4; font-size: 12px;")
        meta_layout.addWidget(self.size_lbl)

        self.type_lbl = QLabel("Type: -")
        self.type_lbl.setStyleSheet("color: #949ba4; font-size: 12px;")
        meta_layout.addWidget(self.type_lbl)

        self.date_lbl = QLabel("Modified: -")
        self.date_lbl.setStyleSheet("color: #949ba4; font-size: 12px;")
        meta_layout.addWidget(self.date_lbl)

        layout.addWidget(self.meta_box)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.open_btn = QPushButton("▶ Open")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(self._on_open_clicked)
        self.open_btn.setEnabled(False)
        btn_layout.addWidget(self.open_btn)

        self.reveal_btn = QPushButton("📂 Explorer")
        self.reveal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reveal_btn.clicked.connect(self._on_reveal_clicked)
        self.reveal_btn.setEnabled(False)
        btn_layout.addWidget(self.reveal_btn)

        layout.addLayout(btn_layout)

    def set_item(self, item: Optional[PackageItem]):
        self.current_item = item
        if not item:
            self.name_lbl.setText("-")
            self.size_lbl.setText("Size: -")
            self.type_lbl.setText("Type: -")
            self.date_lbl.setText("Modified: -")
            self.image_lbl.hide()
            self.text_preview.hide()
            self.placeholder_lbl.setText("Select an item to view preview and metadata")
            self.placeholder_lbl.show()
            self.open_btn.setEnabled(False)
            self.reveal_btn.setEnabled(False)
            return

        self.name_lbl.setText(item.name)
        self.size_lbl.setText(f"Size: {item.formatted_size}")
        self.type_lbl.setText(f"Type: {item.category}")
        self.date_lbl.setText(f"Modified: {item.formatted_date}")
        self.open_btn.setEnabled(True)
        self.reveal_btn.setEnabled(True)

        # Handle Previews
        if item.is_dir:
            self.image_lbl.hide()
            self.text_preview.hide()
            self.placeholder_lbl.setText(f"📁 Directory: {item.name}\nContains package files and subfolders.")
            self.placeholder_lbl.show()
        elif item.category == "Images" and os.path.exists(item.full_local_path):
            pixmap = QPixmap(item.full_local_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(260, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.image_lbl.setPixmap(scaled)
                self.image_lbl.show()
                self.text_preview.hide()
                self.placeholder_lbl.hide()
            else:
                self._show_text_fallback(item)
        elif item.category == "Documents" and item.extension in [".txt", ".log", ".csv", ".json", ".xml", ".md", ".py", ".php", ".sh", ".bat", ".ini"]:
            self._show_text_fallback(item)
        else:
            self.image_lbl.hide()
            self.text_preview.hide()
            self.placeholder_lbl.setText(f"📄 File: {item.name}\nSize: {item.formatted_size}\nNo visual preview available.")
            self.placeholder_lbl.show()

    def _show_text_fallback(self, item: PackageItem):
        if os.path.exists(item.full_local_path):
            try:
                with open(item.full_local_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = [f.readline() for _ in range(50)]
                    content = "".join(lines)
                    self.text_preview.setPlainText(content)
                    self.text_preview.show()
                    self.image_lbl.hide()
                    self.placeholder_lbl.hide()
                    return
            except Exception as e:
                pass
        self.image_lbl.hide()
        self.text_preview.hide()
        self.placeholder_lbl.setText(f"File stored in cloud or binary format.")
        self.placeholder_lbl.show()

    def _on_open_clicked(self):
        if self.current_item:
            self.open_clicked.emit(self.current_item)

    def _on_reveal_clicked(self):
        if self.current_item:
            self.reveal_clicked.emit(self.current_item)
