import os
from typing import List, Set
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from config import ConfigManager, DEFAULT_SCAN_PATH
from core.scanner import PackageScannerWorker, ScannedPackageItem

MAX_DISPLAY_LIMIT = 500  # Cap table rendering to top 500 items for 60fps responsiveness

class ScannerDialog(QDialog):
    send_packages_requested = pyqtSignal(list) # List[ScannedPackageItem]

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("🔍 Titan Inventory Package Scanner (*.tpkj.*)")
        self.resize(980, 680)
        self.all_items: List[ScannedPackageItem] = []
        self.displayed_items: List[ScannedPackageItem] = []
        self.selected_item_paths: Set[str] = set()
        self.worker = None

        # Debounce timer for search filter
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_filter)

        self.init_ui()
        self.start_scan()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title & Path Picker Section
        header_box = QVBoxLayout()

        title_lbl = QLabel("📦 Highest-Version Package Finder")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #5865f2;")
        header_box.addWidget(title_lbl)

        # Editable Scan Path Controls
        path_layout = QHBoxLayout()

        path_lbl = QLabel("Scan Target Directory:")
        path_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        path_layout.addWidget(path_lbl)

        initial_path = self.config.get("scan_target_path", DEFAULT_SCAN_PATH)
        self.scan_path_edit = QLineEdit(initial_path)
        self.scan_path_edit.setObjectName("searchEdit")
        self.scan_path_edit.setPlaceholderText("Select or enter folder path to scan for *.tpkj.* files...")
        path_layout.addWidget(self.scan_path_edit, 1)

        browse_btn = QPushButton("📁 Browse...")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_scan_path)
        path_layout.addWidget(browse_btn)

        self.rescan_btn = QPushButton("🔄 Scan Target")
        self.rescan_btn.setObjectName("primaryBtn")
        self.rescan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rescan_btn.clicked.connect(self.start_scan)
        path_layout.addWidget(self.rescan_btn)

        header_box.addLayout(path_layout)

        # Quick Preset Buttons
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick Presets:"))

        titan_preset_btn = QPushButton("🏢 Titan Customers")
        titan_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        titan_preset_btn.clicked.connect(lambda: self._set_scan_preset(DEFAULT_SCAN_PATH))
        preset_layout.addWidget(titan_preset_btn)

        desktop_incoming = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "Incoming")
        desktop_preset_btn = QPushButton("📥 Desktop\\Incoming")
        desktop_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        desktop_preset_btn.clicked.connect(lambda: self._set_scan_preset(desktop_incoming))
        preset_layout.addWidget(desktop_preset_btn)

        preset_layout.addStretch()
        header_box.addLayout(preset_layout)

        layout.addLayout(header_box)

        # Progress Indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setRange(0, 0) # Indeterminate while scanning
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Starting directory scan...")
        self.status_lbl.setStyleSheet("color: #fee75c; font-weight: 500;")
        layout.addWidget(self.status_lbl)

        # Search Filter Bar & Selection Tools
        filter_box = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchEdit")
        self.search_input.setPlaceholderText("🔍 Filter by Customer, Store, or Package File Name...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        filter_box.addWidget(self.search_input, 2)

        select_all_btn = QPushButton("☑ Select All Visible")
        select_all_btn.clicked.connect(self._select_all_visible)
        filter_box.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("☐ Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all)
        filter_box.addWidget(deselect_all_btn)

        layout.addLayout(filter_box)

        # Packages Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Select", "Customer", "Store", "Package File", "Highest Version", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)

        # Bottom Action Bar
        bottom_box = QHBoxLayout()

        self.count_lbl = QLabel("Selected: 0 packages")
        self.count_lbl.setStyleSheet("font-weight: bold; color: #dbdee1;")
        bottom_box.addWidget(self.count_lbl)

        bottom_box.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        bottom_box.addWidget(close_btn)

        self.send_btn = QPushButton("🚀 Send Selected Packages to Dropbox")
        self.send_btn.setObjectName("primaryBtn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send_clicked)
        bottom_box.addWidget(self.send_btn)

        layout.addLayout(bottom_box)

    def _browse_scan_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory to Scan for Packages", self.scan_path_edit.text())
        if dir_path:
            self.scan_path_edit.setText(dir_path)
            self.start_scan()

    def _set_scan_preset(self, path: str):
        self.scan_path_edit.setText(path)
        self.start_scan()

    def start_scan(self):
        target_path = self.scan_path_edit.text().strip()
        if not target_path or not os.path.exists(target_path):
            QMessageBox.warning(self, "Invalid Path", f"Target directory does not exist:\n{target_path}")
            return

        self.config.set("scan_target_path", target_path)

        self.table.setRowCount(0)
        self.all_items = []
        self.displayed_items = []
        self.selected_item_paths.clear()
        self.progress_bar.show()
        self.status_lbl.setText(f"Scanning '{target_path}' for *.tpkj.* files...")
        self.rescan_btn.setEnabled(False)

        if self.worker and self.worker.isRunning():
            self.worker.cancel()

        self.worker = PackageScannerWorker(base_dir=target_path)
        self.worker.progress_updated.connect(self._on_scan_progress)
        self.worker.scan_completed.connect(self._on_scan_completed)
        self.worker.scan_failed.connect(self._on_scan_failed)
        self.worker.start()

    def _on_scan_progress(self, dir_count: int, pkg_count: int, msg: str):
        self.status_lbl.setText(f"Scanned {dir_count} directories — Found {pkg_count} highest-version packages...")

    def _on_scan_completed(self, items: List[ScannedPackageItem]):
        self.progress_bar.hide()
        self.rescan_btn.setEnabled(True)
        self.all_items = items
        self._apply_filter()

    def _on_scan_failed(self, err_msg: str):
        self.progress_bar.hide()
        self.rescan_btn.setEnabled(True)
        self.status_lbl.setText(f"🔴 Scan Failed: {err_msg}")
        self.status_lbl.setStyleSheet("color: #ed4245; font-weight: bold;")

    def _on_search_text_changed(self, text: str):
        self.search_timer.start(300)

    def _apply_filter(self):
        query = self.search_input.text().strip().lower()

        if not query:
            filtered = self.all_items
        else:
            filtered = [
                i for i in self.all_items
                if query in i.customer_name.lower()
                or query in i.store_name.lower()
                or query in i.file_name.lower()
                or query in str(i.version_num)
            ]

        self._populate_table(filtered)

    def _populate_table(self, items: List[ScannedPackageItem]):
        self.displayed_items = items
        total_matching = len(items)
        display_items = items[:MAX_DISPLAY_LIMIT]

        if total_matching == 0:
            self.status_lbl.setText("No matching packages found.")
            self.status_lbl.setStyleSheet("color: #fee75c;")
        elif total_matching > MAX_DISPLAY_LIMIT:
            self.status_lbl.setText(f"🟢 Found {total_matching:,} packages (Showing top {MAX_DISPLAY_LIMIT} — type in search box to narrow results).")
            self.status_lbl.setStyleSheet("color: #57f287;")
        else:
            self.status_lbl.setText(f"🟢 Showing {total_matching:,} highest-version *.tpkj.* packages.")
            self.status_lbl.setStyleSheet("color: #57f287;")

        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.setRowCount(len(display_items))

        for row, item in enumerate(display_items):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            is_checked = item.full_path in self.selected_item_paths
            chk_item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            chk_item.setData(Qt.ItemDataRole.UserRole, item)
            self.table.setItem(row, 0, chk_item)

            self.table.setItem(row, 1, QTableWidgetItem(item.customer_name))
            self.table.setItem(row, 2, QTableWidgetItem(item.store_name))
            self.table.setItem(row, 3, QTableWidgetItem(item.file_name))
            v_item = QTableWidgetItem(f"v{item.version_num}")
            v_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, v_item)
            s_item = QTableWidgetItem(item.formatted_size)
            s_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, s_item)

        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)

        self.table.itemChanged.connect(self._on_table_item_changed)
        self._update_selected_count_label()

    def _on_table_item_changed(self, item_widget: QTableWidgetItem):
        if item_widget.column() == 0:
            pkg: ScannedPackageItem = item_widget.data(Qt.ItemDataRole.UserRole)
            if pkg:
                if item_widget.checkState() == Qt.CheckState.Checked:
                    self.selected_item_paths.add(pkg.full_path)
                else:
                    self.selected_item_paths.discard(pkg.full_path)
            self._update_selected_count_label()

    def _select_all_visible(self):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            chk = self.table.item(row, 0)
            if chk:
                chk.setCheckState(Qt.CheckState.Checked)
                pkg: ScannedPackageItem = chk.data(Qt.ItemDataRole.UserRole)
                if pkg:
                    self.selected_item_paths.add(pkg.full_path)
        self.table.blockSignals(False)
        self._update_selected_count_label()

    def _deselect_all(self):
        self.selected_item_paths.clear()
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            chk = self.table.item(row, 0)
            if chk:
                chk.setCheckState(Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self._update_selected_count_label()

    def _update_selected_count_label(self):
        self.count_lbl.setText(f"Selected: {len(self.selected_item_paths)} package(s)")

    def _on_send_clicked(self):
        if not self.selected_item_paths:
            QMessageBox.warning(self, "No Packages Selected", "Please select at least one package to send to Dropbox.")
            return

        selected_items = [i for i in self.all_items if i.full_path in self.selected_item_paths]

        reply = QMessageBox.question(
            self, "Confirm Transfer",
            f"Are you sure you want to send {len(selected_items)} package(s) to your Dropbox folder?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.send_packages_requested.emit(selected_items)
            self.accept()
