import os
import re
from typing import List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFileDialog, QInputDialog, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from config import ConfigManager
from core.hybrid_engine import HybridEngine
from core.models import PackageItem
from core.scanner import ScannedPackageItem

from ui.components.header_bar import HeaderBar
from ui.components.sidebar import Sidebar
from ui.components.file_view import FileViewWidget
from ui.components.detail_panel import DetailPanel
from ui.components.transfer_bar import TransferBar
from ui.components.settings_dialog import SettingsDialog
from ui.components.scanner_dialog import ScannerDialog
from ui.styles import DARK_THEME, LIGHT_THEME

def get_clean_tpkj_filename(filename: str) -> str:
    """Strips trailing .# number from tpkj filenames (e.g., '252425-1-022426.tpkj.2' -> '252425-1-022426.tpkj')."""
    return re.sub(r'(\.tpkj)\.\d+$', r'\1', filename, flags=re.IGNORECASE)

class AsyncLoader(QThread):
    items_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, engine: HybridEngine, sub_path: str):
        super().__init__()
        self.engine = engine
        self.sub_path = sub_path

    def run(self):
        try:
            items = self.engine.list_items(self.sub_path)
            self.items_loaded.emit(items)
        except Exception as e:
            self.error_occurred.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.engine = HybridEngine(self.config)
        self.current_sub_path = ""
        self.current_category = "All"
        self.current_search_query = ""
        self.all_current_items: List[PackageItem] = []
        
        self.setWindowTitle("PySync — Dropbox Packages (Nor Cal Office)")
        self.resize(1150, 700)

        self.init_ui()
        self.apply_theme(self.config.get("theme", "dark"))
        self.load_directory(self.current_sub_path)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_vbox = QVBoxLayout(main_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # Header Bar
        self.header_bar = HeaderBar()
        self.header_bar.search_changed.connect(self._on_search_changed)
        self.header_bar.scan_clicked.connect(self._on_scan_packages_clicked)
        self.header_bar.refresh_clicked.connect(lambda: self.load_directory(self.current_sub_path))
        self.header_bar.upload_clicked.connect(self._on_upload_clicked)
        self.header_bar.new_folder_clicked.connect(self._on_new_folder_clicked)
        self.header_bar.view_mode_changed.connect(self._on_view_mode_changed)
        self.header_bar.settings_clicked.connect(self._on_settings_clicked)
        self.header_bar.path_navigated.connect(self.load_directory)
        main_vbox.addWidget(self.header_bar)

        # Central Split (Sidebar | File View | Detail Panel)
        content_hbox = QHBoxLayout()
        content_hbox.setContentsMargins(0, 0, 0, 0)
        content_hbox.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.category_selected.connect(self._on_category_selected)
        content_hbox.addWidget(self.sidebar)

        # File View Area
        self.file_view = FileViewWidget()
        self.file_view.item_double_clicked.connect(self._on_item_double_clicked)
        self.file_view.item_selected.connect(self._on_item_selected)
        self.file_view.open_requested.connect(self._on_open_requested)
        self.file_view.reveal_requested.connect(self._on_reveal_requested)
        self.file_view.delete_requested.connect(self._on_delete_requested)
        self.file_view.files_dropped.connect(self._on_files_dropped)
        content_hbox.addWidget(self.file_view, 1)

        # Detail Panel
        self.detail_panel = DetailPanel()
        self.detail_panel.open_clicked.connect(self._on_open_requested)
        self.detail_panel.reveal_clicked.connect(self._on_reveal_requested)
        content_hbox.addWidget(self.detail_panel)

        main_vbox.addLayout(content_hbox, 1)

        # Bottom Transfer Bar
        self.transfer_bar = TransferBar()
        main_vbox.addWidget(self.transfer_bar)

    def apply_theme(self, theme_name: str):
        if theme_name == "light":
            QApplication.instance().setStyleSheet(LIGHT_THEME)
        else:
            QApplication.instance().setStyleSheet(DARK_THEME)

    def load_directory(self, sub_path: str = ""):
        self.current_sub_path = sub_path
        self.header_bar.set_sub_path(sub_path)
        self.transfer_bar.set_status("Loading directory items...")
        self.transfer_bar.show_progress(30)

        # Background loader thread
        self.loader = AsyncLoader(self.engine, sub_path)
        self.loader.items_loaded.connect(self._on_items_loaded)
        self.loader.error_occurred.connect(self._on_load_error)
        self.loader.start()

    def _on_items_loaded(self, items: List[PackageItem]):
        self.transfer_bar.hide_progress()
        self.all_current_items = items
        self._filter_and_display()

        # Update Sidebar Status Box
        local_path = self.config.get_effective_target_path()
        local_ok = os.path.exists(local_path)
        cloud_ok = self.engine.cloud_provider.is_connected()
        is_pure_cloud = self.config.get("pure_cloud_mode", False)
        self.sidebar.update_status(local_ok, cloud_ok, is_pure_cloud=is_pure_cloud)

        target_name = os.path.basename(self.config.get_effective_target_path())
        count_str = f"Showing {len(items)} items in {target_name}"
        if self.current_sub_path:
            count_str += f" / {self.current_sub_path}"
        if is_pure_cloud and cloud_ok:
            count_str += " [⚡ Disk Saver Mode: Active]"
        self.transfer_bar.set_status(count_str)

    def _on_load_error(self, err_msg: str):
        self.transfer_bar.hide_progress()
        self.transfer_bar.set_status(f"Error: {err_msg}")

    def _filter_and_display(self):
        items = self.all_current_items

        # Apply category filter
        items = self.engine.filter_by_category(items, self.current_category)

        # Apply search query filter
        if self.current_search_query.strip():
            q = self.current_search_query.lower()
            items = [i for i in items if q in i.name.lower() or q in i.category.lower()]

        self.file_view.set_items(items)
        self.detail_panel.set_item(None)

    def _on_search_changed(self, text: str):
        self.current_search_query = text
        self._filter_and_display()

    def _on_category_selected(self, cat: str):
        self.current_category = cat
        self._filter_and_display()

    def _on_view_mode_changed(self, mode: str):
        self.file_view.set_view_mode(mode)

    def _on_item_selected(self, item: PackageItem):
        self.detail_panel.set_item(item)

    def _on_item_double_clicked(self, item: PackageItem):
        if item.is_dir:
            new_sub = os.path.join(self.current_sub_path, item.name).replace("\\", "/")
            self.load_directory(new_sub)
        else:
            self._on_open_requested(item)

    def _on_open_requested(self, item: PackageItem):
        if item.is_dir:
            self.load_directory(os.path.join(self.current_sub_path, item.name).replace("\\", "/"))
        else:
            if item.full_local_path and os.path.exists(item.full_local_path):
                self.engine.local_provider.open_file_default(item.full_local_path)
            elif self.engine.cloud_provider.is_connected():
                self.transfer_bar.set_status(f"Downloading '{item.name}' on-demand to temp cache...")
                self.transfer_bar.show_progress(50)
                ok, path_or_err = self.engine.download_to_temp_cache(item)
                self.transfer_bar.hide_progress()
                if ok:
                    self.transfer_bar.set_status(f"Opened '{item.name}' from temp cache.")
                    self.engine.local_provider.open_file_default(path_or_err)
                else:
                    QMessageBox.warning(self, "Download Error", f"Could not stream file from Dropbox:\n{path_or_err}")
            else:
                QMessageBox.information(self, "Cloud File", f"File '{item.name}' is cloud-only. Add a Dropbox API Access Token in Settings to stream on-demand.")

    def _on_reveal_requested(self, item: PackageItem):
        path = item.full_local_path or self.engine.local_provider.target_base_path
        self.engine.local_provider.reveal_in_explorer(path)

    def _on_delete_requested(self, item: PackageItem):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{item.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if item.full_local_path and os.path.exists(item.full_local_path):
                self.engine.local_provider.delete_item(item.full_local_path)
            if self.engine.cloud_provider.is_connected() and item.cloud_path:
                self.engine.cloud_provider.delete_item(item.cloud_path)
            self.load_directory(self.current_sub_path)

    def _on_new_folder_clicked(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name.strip():
            sub_name = name.strip()
            if self.config.get("pure_cloud_mode", False) and self.engine.cloud_provider.is_connected():
                cloud_dest = f"{self.config.get_cloud_target_path()}/{self.current_sub_path}/{sub_name}".replace("//", "/")
                self.engine.cloud_provider.create_folder(cloud_dest)
            else:
                self.engine.local_provider.create_folder(self.current_sub_path, sub_name)
            self.load_directory(self.current_sub_path)

    def _on_upload_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Upload into Packages", "", "All Files (*)")
        if files:
            self._on_files_dropped(files)

    def _on_files_dropped(self, file_paths: List[str]):
        count = 0
        is_pure_cloud = self.config.get("pure_cloud_mode", False) and self.engine.cloud_provider.is_connected()

        for src in file_paths:
            orig_name = os.path.basename(src)
            clean_name = get_clean_tpkj_filename(orig_name)

            if is_pure_cloud:
                cloud_dest = f"{self.config.get_cloud_target_path()}/{self.current_sub_path}/{clean_name}".replace("//", "/")
                ok, msg = self.engine.cloud_provider.upload_file(src, cloud_dest)
                if ok:
                    count += 1
            else:
                res = self.engine.local_provider.copy_file_in(src, self.current_sub_path, override_filename=clean_name)
                if res:
                    count += 1
                    if self.engine.cloud_provider.is_connected():
                        cloud_dest = f"{self.config.get_cloud_target_path()}/{self.current_sub_path}/{clean_name}".replace("//", "/")
                        self.engine.cloud_provider.upload_file(res, cloud_dest)

        if count > 0:
            self.load_directory(self.current_sub_path)
            self.transfer_bar.set_status(f"Uploaded {count} file(s) successfully.")

    def _on_scan_packages_clicked(self):
        dlg = ScannerDialog(self.config, self)
        dlg.send_packages_requested.connect(self._on_send_scanned_packages)
        dlg.exec()

    def _on_send_scanned_packages(self, packages: List[ScannedPackageItem]):
        self.transfer_bar.set_status(f"Transferring {len(packages)} package(s) to Dropbox...")
        self.transfer_bar.show_progress(10)

        count = 0
        is_pure_cloud = self.config.get("pure_cloud_mode", False) and self.engine.cloud_provider.is_connected()

        for pkg in packages:
            src = pkg.full_path
            # Strip trailing .# number (e.g., '252425-1-022426.tpkj.2' -> '252425-1-022426.tpkj')
            clean_name = get_clean_tpkj_filename(pkg.file_name)

            if is_pure_cloud:
                cloud_dest = f"{self.config.get_cloud_target_path()}/{self.current_sub_path}/{clean_name}".replace("//", "/")
                ok, msg = self.engine.cloud_provider.upload_file(src, cloud_dest)
                if ok:
                    count += 1
            else:
                res = self.engine.local_provider.copy_file_in(src, self.current_sub_path, override_filename=clean_name)
                if res:
                    count += 1
                    if self.engine.cloud_provider.is_connected():
                        cloud_dest = f"{self.config.get_cloud_target_path()}/{self.current_sub_path}/{clean_name}".replace("//", "/")
                        self.engine.cloud_provider.upload_file(res, cloud_dest)

        self.transfer_bar.hide_progress()
        if count > 0:
            self.load_directory(self.current_sub_path)
            QMessageBox.information(
                self, "Packages Transferred",
                f"Successfully sent {count} package(s) to Dropbox as clean '.tpkj' files!"
            )

    def _on_settings_clicked(self):
        dlg = SettingsDialog(self.config, self)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self):
        self.engine.reload_config()
        self.apply_theme(self.config.get("theme", "dark"))
        self.load_directory(self.current_sub_path)
