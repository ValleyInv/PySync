import os
import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QMessageBox, QFileDialog, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QAction

from config import ConfigManager
from core.hybrid_engine import HybridEngine
from core.dropbox_scanner import DropboxScanner, DropboxPackageItem

class DropboxViewDialog(QDialog):
    def __init__(self, config: ConfigManager, engine: HybridEngine, parent=None):
        super().__init__(parent)
        self.config = config
        self.engine = engine
        self.scanner = DropboxScanner(config, engine)
        self.all_items: List[DropboxPackageItem] = []
        
        self.setWindowTitle("📦 Dropbox Packages (Decrypted & Unmasked View)")
        self.resize(1020, 620)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header Info
        header_hbox = QHBoxLayout()
        title_lbl = QLabel("📦 Decrypted Dropbox Packages")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #5865f2;")
        header_hbox.addWidget(title_lbl)
        header_hbox.addStretch()

        rescan_btn = QPushButton("🔄 Rescan Dropbox")
        rescan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rescan_btn.clicked.connect(self.load_data)
        header_hbox.addWidget(rescan_btn)

        layout.addLayout(header_hbox)

        # Filter Bar
        filter_hbox = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Filter by Customer, Store, or Original File Name...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_table)
        filter_hbox.addWidget(self.search_edit, 1)

        sort_lbl = QLabel("Sort By:")
        sort_lbl.setStyleSheet("font-weight: bold;")
        filter_hbox.addWidget(sort_lbl)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "📅 Date Modified (Newest First)",
            "📅 Date Modified (Oldest First)",
            "🔤 Customer Name (A-Z)",
            "📦 Package File Name (A-Z)",
            "📊 Size (Largest First)"
        ])
        self.sort_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sort_combo.currentIndexChanged.connect(self._filter_table)
        filter_hbox.addWidget(self.sort_combo)

        export_btn = QPushButton("🔓 Export Decrypted Package...")
        export_btn.setObjectName("primaryBtn")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._export_selected)
        filter_hbox.addWidget(export_btn)

        layout.addLayout(filter_hbox)

        # Stats Label
        self.stats_lbl = QLabel("Scanning Dropbox packages...")
        self.stats_lbl.setStyleSheet("color: #949ba4; font-weight: bold;")
        layout.addWidget(self.stats_lbl)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Customer Name", "Store Name", "Original Package Filename",
            "Stored File (Dropbox)", "Status", "Size", "Modified Date"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._export_selected)
        layout.addWidget(self.table, 1)

        # Bottom Buttons
        btn_hbox = QHBoxLayout()
        btn_hbox.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_hbox.addWidget(close_btn)

        layout.addLayout(btn_hbox)

    def load_data(self):
        self.all_items = self.scanner.scan_dropbox_packages()
        self._filter_table()

    def _filter_table(self):
        query = self.search_edit.text().strip().lower()
        filtered = []
        for item in self.all_items:
            if not query or (
                query in item.real_customer_name.lower() or
                query in item.real_store_name.lower() or
                query in item.real_file_name.lower() or
                query in item.stored_file_name.lower() or
                query in item.formatted_date.lower()
            ):
                filtered.append(item)

        # Apply sorting
        sort_mode = self.sort_combo.currentText()
        if "Newest First" in sort_mode:
            filtered.sort(key=lambda x: x.modified_time, reverse=True)
        elif "Oldest First" in sort_mode:
            filtered.sort(key=lambda x: x.modified_time)
        elif "Customer" in sort_mode:
            filtered.sort(key=lambda x: (x.real_customer_name.lower(), x.real_store_name.lower(), x.real_file_name.lower()))
        elif "Package File Name" in sort_mode:
            filtered.sort(key=lambda x: x.real_file_name.lower())
        elif "Size" in sort_mode:
            filtered.sort(key=lambda x: x.size, reverse=True)

        self._display_items(filtered)

    def _display_items(self, items: List[DropboxPackageItem]):
        self.table.setRowCount(0)
        enc_count = sum(1 for i in items if i.is_encrypted)
        anon_count = sum(1 for i in items if i.is_anonymized)

        self.stats_lbl.setText(
            f"Showing {len(items)} package(s) in Dropbox  |  "
            f"🔒 Encrypted: {enc_count}  |  🙈 Anonymized: {anon_count}"
        )

        for row, item in enumerate(items):
            self.table.insertRow(row)

            # Customer Name
            it_cust = QTableWidgetItem(item.real_customer_name)
            it_cust.setToolTip(f"Stored folder: {item.stored_folder_name}")
            self.table.setItem(row, 0, it_cust)

            # Store Name
            it_store = QTableWidgetItem(item.real_store_name)
            self.table.setItem(row, 1, it_store)

            # Original Filename
            it_orig = QTableWidgetItem(item.real_file_name)
            it_orig.setToolTip(f"Real unencrypted filename: {item.real_file_name}")
            self.table.setItem(row, 2, it_orig)

            # Stored Dropbox Filename
            it_stored = QTableWidgetItem(item.stored_file_name)
            it_stored.setForeground(QBrush(QColor("#949ba4")))
            self.table.setItem(row, 3, it_stored)

            # Status Badge
            status_parts = []
            if item.is_encrypted:
                status_parts.append("🔒 Encrypted (AES-256)")
            if item.is_anonymized:
                status_parts.append("🙈 Anonymized")
            if not status_parts:
                status_parts.append("📄 Plaintext")

            status_str = " | ".join(status_parts)
            it_status = QTableWidgetItem(status_str)
            if item.is_encrypted:
                it_status.setForeground(QBrush(QColor("#fee75c")))
            elif item.is_anonymized:
                it_status.setForeground(QBrush(QColor("#57f287")))
            self.table.setItem(row, 4, it_status)

            # Size
            it_size = QTableWidgetItem(item.formatted_size)
            self.table.setItem(row, 5, it_size)

            # Modified
            mtime_str = datetime.datetime.fromtimestamp(item.modified_time).strftime("%Y-%m-%d %H:%M") if item.modified_time else "Unknown"
            it_mtime = QTableWidgetItem(mtime_str)
            self.table.setItem(row, 6, it_mtime)

            # Store item reference
            it_cust.setData(Qt.ItemDataRole.UserRole, item)

        self.table.resizeColumnsToContents()

    def _get_selected_item(self) -> Optional[DropboxPackageItem]:
        row = self.table.currentRow()
        if row < 0:
            return None
        it = self.table.item(row, 0)
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _export_selected(self):
        item = self._get_selected_item()
        if not item:
            QMessageBox.information(self, "No Selection", "Please select a package row to export.")
            return

        suggested_name = item.real_file_name
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Save Decrypted Package File As",
            os.path.join(os.path.expanduser("~\\Desktop"), suggested_name),
            "Titan Package Files (*.tpkj);;All Files (*)"
        )

        if dest_path:
            ok, msg = self.scanner.export_decrypted_package(item, dest_path)
            if ok:
                QMessageBox.information(self, "Export Successful", msg)
            else:
                QMessageBox.warning(self, "Export Failed", msg)

    def _show_context_menu(self, pos):
        item = self._get_selected_item()
        if not item:
            return

        menu = QMenu(self)
        export_act = QAction("🔓 Export Decrypted Package File...", self)
        export_act.triggered.connect(self._export_selected)
        menu.addAction(export_act)

        reveal_act = QAction("📁 Reveal in File Explorer", self)
        reveal_act.triggered.connect(lambda: self.engine.local_provider.reveal_in_explorer(item.full_local_path))
        menu.addAction(reveal_act)

        menu.exec(self.table.viewport().mapToGlobal(pos))
