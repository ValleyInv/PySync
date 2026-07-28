from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QComboBox, QCheckBox, QMessageBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from config import ConfigManager
from core.cloud_provider import CloudProvider

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("⚙ PySync Settings & Security Options")
        self.setFixedWidth(580)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Local Dropbox Path Section
        local_group = QGroupBox("Local Dropbox Directory")
        local_layout = QVBoxLayout(local_group)
        local_layout.setSpacing(8)

        lbl = QLabel("Dropbox Root Directory:")
        local_layout.addWidget(lbl)

        path_hbox = QHBoxLayout()
        self.local_path_edit = QLineEdit(self.config.get("local_dropbox_root"))
        path_hbox.addWidget(self.local_path_edit)

        browse_btn = QPushButton("📁 Browse...")
        browse_btn.clicked.connect(self._browse_local_path)
        path_hbox.addWidget(browse_btn)

        local_layout.addLayout(path_hbox)

        effective_path = self.config.get_effective_target_path()
        self.lbl_effective = QLabel(f"Full Path: {effective_path}")
        self.lbl_effective.setStyleSheet("color: #5865f2; font-size: 11px; font-weight: bold;")
        self.lbl_effective.setWordWrap(True)
        local_layout.addWidget(self.lbl_effective)

        layout.addWidget(local_group)

        # Security & Encryption Section
        crypto_group = QGroupBox("Security & Package Encryption (AES-256-CBC)")
        crypto_layout = QVBoxLayout(crypto_group)
        crypto_layout.setSpacing(8)

        self.enable_crypto_chk = QCheckBox("🔒 Encrypt package contents before sending to Dropbox")
        self.enable_crypto_chk.setChecked(self.config.get("enable_encryption", False))
        self.enable_crypto_chk.setStyleSheet("font-weight: bold; color: #fee75c;")
        crypto_layout.addWidget(self.enable_crypto_chk)

        key_hbox = QHBoxLayout()
        key_hbox.addWidget(QLabel("Encryption Key / Secret Passphrase:"))
        self.crypto_key_edit = QLineEdit(self.config.get("encryption_key", ""))
        self.crypto_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.crypto_key_edit.setPlaceholderText("Shared Secret Passphrase (for PHP decryption)...")
        key_hbox.addWidget(self.crypto_key_edit, 1)
        crypto_layout.addLayout(key_hbox)

        crypto_desc = QLabel("Packages are encrypted with AES-256-CBC & 16-byte random IV. Fully decryptable in Laravel PHP via standard openssl_decrypt().")
        crypto_desc.setStyleSheet("color: #949ba4; font-size: 11px;")
        crypto_desc.setWordWrap(True)
        crypto_layout.addWidget(crypto_desc)

        layout.addWidget(crypto_group)

        # Package Transfer & Organization Options Section
        transfer_group = QGroupBox("Package Transfer & Subfolder Organization")
        transfer_layout = QVBoxLayout(transfer_group)
        transfer_layout.setSpacing(8)

        self.preserve_folders_chk = QCheckBox("📁 Organize packages into Customer subfolders in Dropbox (Recommended)")
        self.preserve_folders_chk.setChecked(self.config.get("preserve_customer_folders", True))
        self.preserve_folders_chk.setStyleSheet("font-weight: bold; color: #5865f2;")
        transfer_layout.addWidget(self.preserve_folders_chk)

        folder_desc = QLabel("Organizes transferred packages as 'Packages / <Customer_Name> / <Package_Name>.tpkj', keeping Dropbox clean and fast to browse.")
        folder_desc.setStyleSheet("color: #949ba4; font-size: 11px;")
        folder_desc.setWordWrap(True)
        transfer_layout.addWidget(folder_desc)

        layout.addWidget(transfer_group)

        # Cloud API & Disk Saver Section
        cloud_group = QGroupBox("Dropbox Cloud API & Disk Saver Mode")
        cloud_layout = QVBoxLayout(cloud_group)
        cloud_layout.setSpacing(10)

        token_header_layout = QHBoxLayout()
        cloud_info = QLabel("Enter your Dropbox Access Token:")
        cloud_info.setStyleSheet("font-weight: bold;")
        token_header_layout.addWidget(cloud_info)

        help_btn = QPushButton("🔑 How to get a Token?")
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        help_btn.clicked.connect(self._show_token_help)
        token_header_layout.addWidget(help_btn)

        cloud_layout.addLayout(token_header_layout)

        token_hbox = QHBoxLayout()
        self.token_edit = QLineEdit(self.config.get("dropbox_access_token"))
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("Paste Dropbox Access Token here...")
        token_hbox.addWidget(self.token_edit)

        test_btn = QPushButton("🔌 Test Token")
        test_btn.clicked.connect(self._test_cloud_token)
        token_hbox.addWidget(test_btn)

        cloud_layout.addLayout(token_hbox)

        # Disk Saver Checkbox
        self.pure_cloud_chk = QCheckBox("⚡ Enable Pure Cloud Mode (Zero Disk Space Usage)")
        self.pure_cloud_chk.setChecked(self.config.get("pure_cloud_mode", False))
        self.pure_cloud_chk.setStyleSheet("font-weight: bold; color: #57f287;")
        cloud_layout.addWidget(self.pure_cloud_chk)

        cloud_desc = QLabel("In Pure Cloud Mode, file lists and previews are fetched directly via Cloud API without downloading files to local disk storage.")
        cloud_desc.setStyleSheet("color: #949ba4; font-size: 11px;")
        cloud_desc.setWordWrap(True)
        cloud_layout.addWidget(cloud_desc)

        # Cache Limit Setting
        cache_hbox = QHBoxLayout()
        cache_hbox.addWidget(QLabel("Max Temp Cache Limit (MB):"))
        self.cache_mb_edit = QLineEdit(str(self.config.get("max_cache_mb", 500)))
        self.cache_mb_edit.setFixedWidth(80)
        cache_hbox.addWidget(self.cache_mb_edit)
        cache_hbox.addStretch()
        cloud_layout.addLayout(cache_hbox)

        layout.addWidget(cloud_group)

        # Preferences Section
        pref_group = QGroupBox("Preferences")
        pref_layout = QVBoxLayout(pref_group)

        theme_hbox = QHBoxLayout()
        theme_hbox.addWidget(QLabel("UI Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Mode", "Light Mode"])
        current_theme = self.config.get("theme", "dark")
        self.theme_combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        theme_hbox.addWidget(self.theme_combo)
        pref_layout.addLayout(theme_hbox)

        layout.addWidget(pref_group)

        # Dialog Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save Settings")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save_settings)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _browse_local_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Dropbox Root Directory", self.local_path_edit.text())
        if dir_path:
            self.local_path_edit.setText(dir_path)
            self._update_effective_label()

    def _update_effective_label(self):
        root = self.local_path_edit.text().strip()
        rel = self.config.get("target_rel_path")
        eff = os.path.normpath(os.path.join(root, rel))
        self.lbl_effective.setText(f"Full Path: {eff}")

    def _show_token_help(self):
        help_text = (
            "How to Generate a Dropbox Access Token (1 Minute Step-by-Step):\n\n"
            "1. Go to https://www.dropbox.com/developers/apps\n"
            "2. Click 'Create App' -> Choose 'Scoped Access' and 'Full Dropbox' or 'App Folder'.\n"
            "3. Under the 'Permissions' tab, check: files.metadata.read, files.content.read, files.content.write.\n"
            "4. Click 'Submit' / 'Save'.\n"
            "5. Under the 'Settings' tab, scroll down to 'Generated access token' and click 'Generate'.\n"
            "6. Copy the generated token string and paste it into the field here!\n\n"
            "Once saved, Pure Cloud Mode will stream all package files without consuming disk space."
        )
        QMessageBox.information(self, "Generate Dropbox Access Token", help_text)

    def _test_cloud_token(self):
        token = self.token_edit.text().strip()
        provider = CloudProvider(token)
        ok, msg = provider.test_connection()
        if ok:
            QMessageBox.information(self, "Dropbox API Connection", f"Success!\n{msg}")
        else:
            QMessageBox.warning(self, "Dropbox API Connection", f"Connection Failed:\n{msg}")

    def _save_settings(self):
        self.config.set("local_dropbox_root", self.local_path_edit.text().strip())
        self.config.set("dropbox_access_token", self.token_edit.text().strip())
        self.config.set("pure_cloud_mode", self.pure_cloud_chk.isChecked())
        self.config.set("preserve_customer_folders", self.preserve_folders_chk.isChecked())
        self.config.set("enable_encryption", self.enable_crypto_chk.isChecked())
        self.config.set("encryption_key", self.crypto_key_edit.text().strip())
        try:
            val = int(self.cache_mb_edit.text().strip())
            self.config.set("max_cache_mb", val)
        except ValueError:
            pass

        theme_val = "dark" if self.theme_combo.currentIndex() == 0 else "light"
        self.config.set("theme", theme_val)
        self.settings_saved.emit()
        self.accept()
