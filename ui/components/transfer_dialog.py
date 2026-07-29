import os
import time
import queue
import tempfile
from typing import List, Union, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

from config import ConfigManager
from core.hybrid_engine import HybridEngine
from core.scanner import ScannedPackageItem
from core.crypto import encrypt_file_to_bytes, anonymize_name
from core.dropbox_scanner import update_anonymization_index

def get_clean_tpkj_filename(filename: str) -> str:
    """Strips trailing .# number from tpkj filenames (e.g., '252425-1-022426.tpkj.2' -> '252425-1-022426.tpkj')."""
    import re
    return re.sub(r'(\.tpkj)\.\d+$', r'\1', filename, flags=re.IGNORECASE)

class FileConflictDialog(QDialog):
    def __init__(self, file_name: str, folder_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠️ Package File Conflict Detected")
        self.setFixedWidth(540)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.choice = "cancel"  # Default fallback if window closed

        self.init_ui(file_name, folder_name)

    def init_ui(self, file_name: str, folder_name: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        header_lbl = QLabel("⚠️ Package File Already Exists in Dropbox")
        header_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #fee75c;")
        layout.addWidget(header_lbl)

        target_folder_display = folder_name if folder_name else "Root Packages"
        msg = (
            f"The package file <b>{file_name}</b> already exists in your Dropbox "
            f"destination under <b>{target_folder_display}</b>.<br><br>"
            f"How would you like to handle this duplicate file?"
        )
        msg_lbl = QLabel(msg)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("font-size: 12px; color: #dbdee1;")
        layout.addWidget(msg_lbl)

        layout.addSpacing(4)

        # 5 Conflict Choice Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        # Skip
        skip_btn = QPushButton("⏭ Skip  (Skip this package)")
        skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_btn.clicked.connect(lambda: self._select("skip"))
        btn_layout.addWidget(skip_btn)

        # Replace
        replace_btn = QPushButton("🔄 Replace  (Overwrite existing package file)")
        replace_btn.setObjectName("primaryBtn")
        replace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replace_btn.clicked.connect(lambda: self._select("replace"))
        btn_layout.addWidget(replace_btn)

        # Skip All
        skip_all_btn = QPushButton("⏭ All (Skip All)  (Automatically skip all existing packages)")
        skip_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_all_btn.clicked.connect(lambda: self._select("skip_all"))
        btn_layout.addWidget(skip_all_btn)

        # Replace All
        replace_all_btn = QPushButton("🔄 All (Replace All)  (Automatically overwrite all existing packages)")
        replace_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replace_all_btn.clicked.connect(lambda: self._select("replace_all"))
        btn_layout.addWidget(replace_all_btn)

        # Cancel
        cancel_btn = QPushButton("⏹ Cancel Transfer  (Stop transferring remaining queue)")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #da373c;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #a1282c;
            }
        """)
        cancel_btn.clicked.connect(lambda: self._select("cancel"))
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _select(self, choice: str):
        self.choice = choice
        self.accept()


class PackageTransferWorker(QThread):
    progress_updated = pyqtSignal(int, int, str, str) # current_idx, total, package_name, status_msg
    conflict_requested = pyqtSignal(str, str, object) # dest_file_name, dest_sub, response_queue
    transfer_finished = pyqtSignal(int, dict, bool)   # count_sent, index_updates, is_cancelled

    def __init__(
        self,
        config: ConfigManager,
        engine: HybridEngine,
        packages: List[Union[ScannedPackageItem, str]],
        current_sub_path: str = ""
    ):
        super().__init__()
        self.config = config
        self.engine = engine
        self.packages = packages
        self.current_sub_path = current_sub_path
        self._is_cancelled = False
        self.global_conflict_action = None  # None, 'skip_all', 'replace_all'

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total_pkgs = len(self.packages)
        count = 0
        is_pure_cloud = self.config.get("pure_cloud_mode", False) and self.engine.cloud_provider.is_connected()
        preserve_folders = self.config.get("preserve_customer_folders", True)
        use_crypto = self.config.get("enable_encryption", False)
        use_anon = self.config.get("anonymize_filenames", False)
        enc_key = self.config.get("encryption_key", "").strip()

        index_updates = {}

        for idx, pkg_item in enumerate(self.packages):
            if self._is_cancelled:
                break

            if isinstance(pkg_item, ScannedPackageItem):
                src = pkg_item.full_path
                orig_file_name = pkg_item.file_name
                cust_name = pkg_item.customer_name
            else:
                src = str(pkg_item)
                orig_file_name = os.path.basename(src)
                cust_name = "Packages"

            clean_name = get_clean_tpkj_filename(orig_file_name)

            if use_anon:
                cust_folder = anonymize_name(cust_name, prefix="CUST")
                dest_file_name = anonymize_name(clean_name, prefix="PKG") + ".tpkj"
                index_updates[cust_folder] = cust_name
                index_updates[dest_file_name] = clean_name
            else:
                cust_folder = cust_name
                dest_file_name = clean_name

            if preserve_folders and cust_folder and cust_folder != "Unknown":
                dest_sub = f"{self.current_sub_path}/{cust_folder}".strip("/").replace("//", "/")
            else:
                dest_sub = self.current_sub_path

            # --- Check if file already exists in Dropbox ---
            if self.engine.file_exists(dest_sub, dest_file_name):
                if self.global_conflict_action == "skip_all":
                    self.progress_updated.emit(idx + 1, total_pkgs, dest_file_name, "⏭ Skipped (File exists)")
                    continue
                elif self.global_conflict_action == "replace_all":
                    pass  # Overwrite
                else:
                    # Request conflict choice from user on GUI main thread
                    resp_queue = queue.Queue()
                    self.conflict_requested.emit(dest_file_name, dest_sub, resp_queue)
                    
                    # Block worker thread waiting for user input
                    user_choice = resp_queue.get()

                    if user_choice == "skip":
                        self.progress_updated.emit(idx + 1, total_pkgs, dest_file_name, "⏭ Skipped by user")
                        continue
                    elif user_choice == "skip_all":
                        self.global_conflict_action = "skip_all"
                        self.progress_updated.emit(idx + 1, total_pkgs, dest_file_name, "⏭ Skipped (Skip All set)")
                        continue
                    elif user_choice == "replace_all":
                        self.global_conflict_action = "replace_all"
                    elif user_choice == "cancel":
                        self._is_cancelled = True
                        break

            src_to_send = src
            temp_enc_file = None

            status_text = f"Preparing '{dest_file_name}'..."
            self.progress_updated.emit(idx + 1, total_pkgs, dest_file_name, status_text)

            if use_crypto and enc_key:
                status_text = f"🔒 Encrypting '{dest_file_name}' with AES-256-CBC..."
                self.progress_updated.emit(idx + 1, total_pkgs, dest_file_name, status_text)
                enc_bytes = encrypt_file_to_bytes(src, enc_key)
                if enc_bytes:
                    temp_enc_file = os.path.join(tempfile.gettempdir(), f"enc_{dest_file_name}")
                    with open(temp_enc_file, "wb") as ef:
                        ef.write(enc_bytes)
                    src_to_send = temp_enc_file

            if self._is_cancelled:
                if temp_enc_file and os.path.exists(temp_enc_file):
                    try:
                        os.remove(temp_enc_file)
                    except Exception:
                        pass
                break

            if is_pure_cloud:
                cloud_dest = f"{self.config.get_cloud_target_path()}/{dest_sub}/{dest_file_name}".replace("//", "/")
                
                def _status_cb(msg):
                    self.progress_updated.emit(idx + 1, total_pkgs, dest_file_name, msg)

                _status_cb(f"☁ Uploading '{dest_file_name}' to Dropbox Cloud...")
                ok, msg = self.engine.cloud_provider.upload_file(src_to_send, cloud_dest, status_callback=_status_cb)
                if ok:
                    count += 1
                time.sleep(0.2)
            else:
                status_text = f"📁 Copying '{dest_file_name}' into local Dropbox packages..."
                self.progress_updated.emit(idx + 1, total_pkgs, dest_file_name, status_text)
                res = self.engine.local_provider.copy_file_in(src_to_send, dest_sub, override_filename=dest_file_name)
                if res:
                    count += 1

            if temp_enc_file and os.path.exists(temp_enc_file):
                try:
                    os.remove(temp_enc_file)
                except Exception:
                    pass

        if index_updates:
            update_anonymization_index(self.config, index_updates)

        self.transfer_finished.emit(count, index_updates, self._is_cancelled)


class TransferProgressDialog(QDialog):
    def __init__(
        self,
        config: ConfigManager,
        engine: HybridEngine,
        packages: List[Union[ScannedPackageItem, str]],
        current_sub_path: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.config = config
        self.engine = engine
        self.packages = packages
        self.total_count = len(packages)
        self.transferred_count = 0
        self.was_cancelled = False

        self.setWindowTitle("🚀 Transferring Packages to Dropbox")
        self.setFixedWidth(540)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # Prevent user from closing with X without triggering cancel logic
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        self.init_ui()

        self.worker = PackageTransferWorker(config, engine, packages, current_sub_path)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.conflict_requested.connect(self._on_conflict_requested)
        self.worker.transfer_finished.connect(self._on_transfer_finished)
        self.worker.start()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Title / Subtitle
        self.title_lbl = QLabel("🚀 Sending Packages to Dropbox...")
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #5865f2;")
        layout.addWidget(self.title_lbl)

        # Package Counter Label
        self.pkg_counter_lbl = QLabel(f"Package 0 of {self.total_count} (0%)")
        self.pkg_counter_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #dbdee1;")
        layout.addWidget(self.pkg_counter_lbl)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Detail Status Text (Current package filename & operation detail)
        self.detail_lbl = QLabel("Initializing transfer queue...")
        self.detail_lbl.setStyleSheet("color: #949ba4; font-size: 12px;")
        self.detail_lbl.setWordWrap(True)
        layout.addWidget(self.detail_lbl)

        # Bottom Button Box
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.cancel_btn = QPushButton("⏹ Cancel Transfer")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #da373c;
                color: white;
                font-weight: bold;
                padding: 6px 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #a1282c;
            }
            QPushButton:disabled {
                background-color: #4f545c;
                color: #8e9297;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_box.addWidget(self.cancel_btn)

        layout.addLayout(btn_box)

    def _on_progress_updated(self, current_idx: int, total: int, pkg_name: str, status_msg: str):
        pct = int((current_idx / total) * 100)
        self.progress_bar.setValue(pct)
        self.pkg_counter_lbl.setText(f"Package {current_idx} of {total} ({pct}%)")
        self.detail_lbl.setText(f"📦 File: {pkg_name}\nStatus: {status_msg}")

    def _on_conflict_requested(self, file_name: str, folder_name: str, response_queue: queue.Queue):
        dlg = FileConflictDialog(file_name, folder_name, parent=self)
        dlg.exec()
        response_queue.put(dlg.choice)

    def _on_cancel_clicked(self):
        reply = QMessageBox.question(
            self,
            "Confirm Cancellation",
            "Are you sure you want to cancel the transfer?\nPackages already transferred will remain in Dropbox.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("Cancelling...")
            self.detail_lbl.setText("⏹ Cancelling transfer queue... Cleaning up current package...")
            self.worker.cancel()

    def _on_transfer_finished(self, count: int, index_updates: dict, is_cancelled: bool):
        self.transferred_count = count
        self.was_cancelled = is_cancelled
        self.accept()
