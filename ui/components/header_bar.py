from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt

class HeaderBar(QWidget):
    search_changed = pyqtSignal(str)
    refresh_clicked = pyqtSignal()
    scan_clicked = pyqtSignal() # Scan Titan Customer tpkj packages
    upload_clicked = pyqtSignal()
    new_folder_clicked = pyqtSignal()
    view_mode_changed = pyqtSignal(str) # 'table' or 'grid'
    settings_clicked = pyqtSignal()
    path_navigated = pyqtSignal(str) # Navigate to path segment

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerBar")
        self.current_sub_path = ""
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Path Breadcrumbs / Location Label
        self.path_container = QWidget()
        self.path_layout = QHBoxLayout(self.path_container)
        self.path_layout.setContentsMargins(0, 0, 0, 0)
        self.path_layout.setSpacing(4)
        
        self.root_btn = QPushButton("📁 Packages Root")
        self.root_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.root_btn.clicked.connect(lambda: self.path_navigated.emit(""))
        self.path_layout.addWidget(self.root_btn)

        self.path_sub_label = QLabel("")
        self.path_sub_label.setStyleSheet("color: #949ba4; font-weight: bold; font-size: 13px;")
        self.path_layout.addWidget(self.path_sub_label)
        self.path_layout.addStretch()

        layout.addWidget(self.path_container, 2)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchEdit")
        self.search_input.setPlaceholderText("🔍 Search packages & files...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input, 2)

        # Actions
        self.scan_btn = QPushButton("🔍 Scan Packages")
        self.scan_btn.setObjectName("primaryBtn")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self.scan_clicked.emit)
        layout.addWidget(self.scan_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.refresh_btn)

        self.upload_btn = QPushButton("⬆ Upload")
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.clicked.connect(self.upload_clicked.emit)
        layout.addWidget(self.upload_btn)

        self.new_folder_btn = QPushButton("➕ New Folder")
        self.new_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_folder_btn.clicked.connect(self.new_folder_clicked.emit)
        layout.addWidget(self.new_folder_btn)

        # View Mode Switcher
        self.view_combo = QComboBox()
        self.view_combo.addItems(["📋 Table View", "🔲 Grid View"])
        self.view_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_combo.currentIndexChanged.connect(self._on_view_changed)
        layout.addWidget(self.view_combo)

        # Settings
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)

    def set_sub_path(self, sub_path: str):
        self.current_sub_path = sub_path
        if sub_path:
            clean = sub_path.replace("\\", "/").strip("/")
            self.path_sub_label.setText(f"  /  {clean}")
        else:
            self.path_sub_label.setText("")

    def _on_view_changed(self, index: int):
        mode = "table" if index == 0 else "grid"
        self.view_mode_changed.emit(mode)
