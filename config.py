import os
import json
import tempfile
from pathlib import Path

CONFIG_FILE = Path.home() / ".pysync_config.json"
DEFAULT_REL_PATH = os.path.join("Nor Cal office misc", "Packages")
DEFAULT_SCAN_PATH = r"C:\ProgramData\AST\Titan_Inventory_Control\_Customers"

class ConfigManager:
    def __init__(self):
        self.config_data = {
            "local_dropbox_root": self._detect_dropbox_root(),
            "target_rel_path": DEFAULT_REL_PATH,
            "scan_target_path": DEFAULT_SCAN_PATH,
            "preserve_customer_folders": True, # Automatically organize transfers into Customer subfolders
            "enable_encryption": False,        # Encrypt files with AES-256-CBC before transfer
            "encryption_key": "",              # Secret passphrase for AES-256-CBC
            "custom_local_path": "",
            "dropbox_access_token": "",
            "pure_cloud_mode": False,   # Disk-Saver Pure Cloud API Mode
            "max_cache_mb": 500,        # Max temp cache size before auto purge
            "theme": "dark",
            "view_mode": "table",       # 'table' or 'grid'
            "auto_sync": True
        }
        self.load()

    def _detect_dropbox_root(self) -> str:
        """Detect local Dropbox root directory using Dropbox app info.json or standard locations."""
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            info_json = Path(local_app_data) / "Dropbox" / "info.json"
            if info_json.exists():
                try:
                    with open(info_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Check personal or business accounts
                        for acc_type in ["personal", "business"]:
                            if acc_type in data and "path" in data[acc_type]:
                                path = data[acc_type]["path"]
                                if os.path.exists(path):
                                    return path
                except Exception:
                    pass

        # Standard fallbacks on Windows
        user_home = Path.home()
        candidates = [
            user_home / "Dropbox",
            user_home / "Dropbox (Personal)",
        ]
        for c in candidates:
            if c.exists():
                return str(c)

        return str(user_home / "Dropbox")

    def get_effective_target_path(self) -> str:
        """Returns the full local target path for Packages folder."""
        if self.config_data.get("custom_local_path"):
            return self.config_data["custom_local_path"]
        
        root = self.config_data.get("local_dropbox_root") or self._detect_dropbox_root()
        rel = self.config_data.get("target_rel_path", DEFAULT_REL_PATH)
        return os.path.normpath(os.path.join(root, rel))

    def get_cloud_target_path(self) -> str:
        """Returns Dropbox Cloud API relative path (e.g. /Nor Cal office misc/Packages)."""
        rel = self.config_data.get("target_rel_path", DEFAULT_REL_PATH)
        rel = rel.replace("\\", "/")
        if not rel.startswith("/"):
            rel = "/" + rel
        return rel

    def get_cache_directory(self) -> str:
        """Returns temporary on-demand cache directory."""
        cache_dir = os.path.join(tempfile.gettempdir(), "PySync_Cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.config_data.update(saved)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config_data.get(key, default)

    def set(self, key, value):
        self.config_data[key] = value
        self.save()
