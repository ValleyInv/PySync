from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt

class Sidebar(QWidget):
    category_selected = pyqtSignal(str) # 'All', 'Packages', 'Documents', 'Images'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(230)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(12)

        # Title / Branding
        title_label = QLabel("⚡ PySync")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #5865f2; margin-left: 8px;")
        layout.addWidget(title_label)

        sub_label = QLabel("Dropbox / Nor Cal office misc / Packages")
        sub_label.setWordWrap(True)
        sub_label.setStyleSheet("font-size: 11px; color: #949ba4; margin-left: 8px; margin-bottom: 8px;")
        layout.addWidget(sub_label)

        # Navigation List
        self.nav_list = QListWidget()
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        items = [
            ("📦 All Packages & Files", "All"),
            ("🗜 Packages & Archives", "Packages"),
            ("📄 Documents & Specs", "Documents"),
            ("🖼 Media & Images", "Images"),
        ]

        for text, data in items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.nav_list.addItem(item)

        self.nav_list.setCurrentRow(0)
        self.nav_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.nav_list, 1)

        # Sync Status Box
        self.status_box = QFrame()
        self.status_box.setStyleSheet("""
            QFrame {
                background-color: #1e1f22;
                border: 1px solid #2b2d31;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        status_layout = QVBoxLayout(self.status_box)
        status_layout.setContentsMargins(8, 8, 8, 8)
        status_layout.setSpacing(4)

        status_header = QLabel("STATUS & DISK SAVER")
        status_header.setStyleSheet("font-size: 10px; font-weight: bold; color: #949ba4;")
        status_layout.addWidget(status_header)

        self.mode_lbl = QLabel("💾 Mode: Hybrid Sync")
        self.mode_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #5865f2;")
        status_layout.addWidget(self.mode_lbl)

        self.local_status_lbl = QLabel("🟢 Local Folder: Connected")
        self.local_status_lbl.setStyleSheet("font-size: 11px; color: #57f287;")
        status_layout.addWidget(self.local_status_lbl)

        self.cloud_status_lbl = QLabel("⚪ Cloud API: Local Only")
        self.cloud_status_lbl.setStyleSheet("font-size: 11px; color: #949ba4;")
        status_layout.addWidget(self.cloud_status_lbl)

        layout.addWidget(self.status_box)

    def _on_item_clicked(self, item: QListWidgetItem):
        cat = item.data(Qt.ItemDataRole.UserRole)
        self.category_selected.emit(cat)

    def update_status(self, local_ok: bool, cloud_ok: bool, is_pure_cloud: bool = False, cloud_msg: str = ""):
        if is_pure_cloud and cloud_ok:
            self.mode_lbl.setText("☁ Mode: Pure Cloud (Zero Disk)")
            self.mode_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #57f287;")
        else:
            self.mode_lbl.setText("💾 Mode: Hybrid (Local + Cloud)")
            self.mode_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #5865f2;")

        if local_ok:
            self.local_status_lbl.setText("🟢 Local Folder: Connected")
            self.local_status_lbl.setStyleSheet("font-size: 11px; color: #57f287;")
        else:
            self.local_status_lbl.setText("🔴 Local Folder: Missing")
            self.local_status_lbl.setStyleSheet("font-size: 11px; color: #ed4245;")

        if cloud_ok:
            self.cloud_status_lbl.setText("🟢 Cloud API: Online")
            self.cloud_status_lbl.setStyleSheet("font-size: 11px; color: #57f287;")
        elif cloud_msg:
            self.cloud_status_lbl.setText(f"🟡 Cloud API: {cloud_msg}")
            self.cloud_status_lbl.setStyleSheet("font-size: 11px; color: #fee75c;")
        else:
            self.cloud_status_lbl.setText("⚪ Cloud API: Not Configured")
            self.cloud_status_lbl.setStyleSheet("font-size: 11px; color: #949ba4;")
