from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QMenu,
    QHeaderView, QListWidget, QListWidgetItem, QStackedWidget, QMessageBox, QInputDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon, QAction, QDragEnterEvent, QDropEvent
from core.models import PackageItem

class FileViewWidget(QWidget):
    item_double_clicked = pyqtSignal(PackageItem)
    item_selected = pyqtSignal(PackageItem)
    open_requested = pyqtSignal(PackageItem)
    reveal_requested = pyqtSignal(PackageItem)
    delete_requested = pyqtSignal(PackageItem)
    files_dropped = pyqtSignal(list) # List of local dropped file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.items: List[PackageItem] = []
        self.view_mode = "table"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Table View Widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Type", "Last Modified", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        self.stack.addWidget(self.table)

        # Grid View Widget
        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid.setIconSize(QSize(64, 64))
        self.grid.setGridSize(QSize(120, 110))
        self.grid.setSpacing(10)
        self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._show_context_menu)
        self.grid.itemDoubleClicked.connect(self._on_grid_double_click)
        self.grid.itemSelectionChanged.connect(self._on_grid_selection_changed)

        self.stack.addWidget(self.grid)

    def set_items(self, items: List[PackageItem]):
        self.items = items
        self.table.setRowCount(0)
        self.grid.clear()

        for row, item in enumerate(items):
            # Table Row Populating
            self.table.insertRow(row)

            # Icon & Name
            icon_str = self._get_icon_emoji(item)
            name_item = QTableWidgetItem(f"{icon_str}  {item.name}")
            name_item.setData(Qt.ItemDataRole.UserRole, item)
            self.table.setItem(row, 0, name_item)

            # Size
            size_item = QTableWidgetItem(item.formatted_size)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 1, size_item)

            # Type
            type_item = QTableWidgetItem(item.category)
            self.table.setItem(row, 2, type_item)

            # Date
            date_item = QTableWidgetItem(item.formatted_date)
            self.table.setItem(row, 3, date_item)

            # Sync Status
            status_str = "🟢 Local" if item.sync_status == "synced" else "☁ Cloud Only"
            status_item = QTableWidgetItem(status_str)
            self.table.setItem(row, 4, status_item)

            # Grid Item Populating
            grid_item = QListWidgetItem(f"{icon_str}\n{item.name}")
            grid_item.setData(Qt.ItemDataRole.UserRole, item)
            grid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            grid_item.setToolTip(f"{item.name}\nSize: {item.formatted_size}\nType: {item.category}")
            self.grid.addItem(grid_item)

    def set_view_mode(self, mode: str):
        self.view_mode = mode
        if mode == "grid":
            self.stack.setCurrentWidget(self.grid)
        else:
            self.stack.setCurrentWidget(self.table)

    def get_selected_item(self) -> Optional[PackageItem]:
        if self.view_mode == "grid":
            items = self.grid.selectedItems()
            if items:
                return items[0].data(Qt.ItemDataRole.UserRole)
        else:
            rows = self.table.selectedItems()
            if rows:
                row = self.table.currentRow()
                item_cell = self.table.item(row, 0)
                if item_cell:
                    return item_cell.data(Qt.ItemDataRole.UserRole)
        return None

    def _get_icon_emoji(self, item: PackageItem) -> str:
        if item.is_dir:
            return "📁"
        cat = item.category
        if cat == "Packages & Archives":
            return "📦"
        elif cat == "Documents":
            return "📄"
        elif cat == "Images":
            return "🖼"
        return "📄"

    def _on_table_double_click(self, row: int, col: int):
        item_cell = self.table.item(row, 0)
        if item_cell:
            item: PackageItem = item_cell.data(Qt.ItemDataRole.UserRole)
            self.item_double_clicked.emit(item)

    def _on_grid_double_click(self, grid_item: QListWidgetItem):
        item: PackageItem = grid_item.data(Qt.ItemDataRole.UserRole)
        self.item_double_clicked.emit(item)

    def _on_table_selection_changed(self):
        item = self.get_selected_item()
        if item:
            self.item_selected.emit(item)

    def _on_grid_selection_changed(self):
        item = self.get_selected_item()
        if item:
            self.item_selected.emit(item)

    def _show_context_menu(self, pos):
        item = self.get_selected_item()
        if not item:
            return

        menu = QMenu(self)
        
        open_act = QAction("▶ Open", self)
        open_act.triggered.connect(lambda: self.open_requested.emit(item))
        menu.addAction(open_act)

        reveal_act = QAction("📂 Reveal in Explorer", self)
        reveal_act.triggered.connect(lambda: self.reveal_requested.emit(item))
        menu.addAction(reveal_act)

        menu.addSeparator()

        copy_path_act = QAction("📋 Copy Local Path", self)
        copy_path_act.triggered.connect(lambda: self._copy_to_clipboard(item.full_local_path))
        menu.addAction(copy_path_act)

        menu.addSeparator()

        delete_act = QAction("🗑 Delete", self)
        delete_act.triggered.connect(lambda: self.delete_requested.emit(item))
        menu.addAction(delete_act)

        widget = self.grid if self.view_mode == "grid" else self.table
        menu.exec(widget.mapToGlobal(pos))

    def _copy_to_clipboard(self, text: str):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    # Drag & Drop File Upload Support
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path:
                files.append(local_path)
        if files:
            self.files_dropped.emit(files)
