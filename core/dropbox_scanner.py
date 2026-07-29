import os
import re
import json
import zipfile
import tempfile
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from config import ConfigManager
from core.hybrid_engine import HybridEngine
from core.crypto import decrypt_bytes, derive_aes_key, anonymize_name

INDEX_FILE_NAME = ".pysync_index.json"

@dataclass
class DropboxPackageItem:
    real_customer_name: str
    real_store_name: str
    real_file_name: str
    stored_file_name: str
    stored_folder_name: str
    full_local_path: str
    cloud_path: str
    is_encrypted: bool
    is_anonymized: bool
    size: int
    modified_time: float

    @property
    def formatted_size(self) -> str:
        num = self.size
        for unit in ["B", "KB", "MB", "GB"]:
            if abs(num) < 1024.0:
                return f"{num:3.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} TB"

    @property
    def formatted_date(self) -> str:
        if not self.modified_time:
            return "N/A"
        import datetime
        return datetime.datetime.fromtimestamp(self.modified_time).strftime("%Y-%m-%d %H:%M:%S")

def update_anonymization_index(config: ConfigManager, entries: Dict[str, str]):
    """Appends or updates anonymization index mapping in local Dropbox root."""
    target_dir = config.get_effective_target_path()
    index_path = os.path.join(target_dir, INDEX_FILE_NAME)
    
    current_index: Dict[str, str] = {}
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                current_index = json.load(f)
        except Exception:
            pass

    current_index.update(entries)

    try:
        os.makedirs(target_dir, exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(current_index, f, indent=2)
    except Exception as e:
        print(f"Error updating anonymization index: {e}")

class DropboxScanner:
    def __init__(self, config: ConfigManager, engine: HybridEngine):
        self.config = config
        self.engine = engine

    def load_index(self) -> Dict[str, str]:
        """Loads the anonymization mapping index from Dropbox root."""
        target_dir = self.config.get_effective_target_path()
        index_path = os.path.join(target_dir, INDEX_FILE_NAME)
        
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def scan_dropbox_packages(self) -> List[DropboxPackageItem]:
        """Scans Dropbox Packages directory, resolving encrypted/anonymized information to unencrypted format."""
        target_dir = self.config.get_effective_target_path()
        index_map = self.load_index()
        enc_key = self.config.get("encryption_key", "").strip()

        items: List[DropboxPackageItem] = []
        if not os.path.exists(target_dir):
            return items

        for root, dirs, files in os.walk(target_dir):
            rel_folder = os.path.relpath(root, target_dir)
            folder_name = rel_folder if rel_folder != "." else "Root"

            for fname in files:
                if fname.startswith(".") or fname == INDEX_FILE_NAME:
                    continue

                full_path = os.path.join(root, fname)
                is_tpkj = ".tpkj" in fname.lower()
                if not is_tpkj:
                    continue

                try:
                    st = os.stat(full_path)
                    size = st.st_size
                    mtime = st.st_mtime
                except Exception:
                    size = 0
                    mtime = 0.0

                # Check if content is encrypted
                is_encrypted = False
                decrypted_bytes: Optional[bytes] = None

                try:
                    with open(full_path, "rb") as f:
                        raw_head = f.read(1024)

                    if not raw_head.startswith(b"PK\x03\x04"): # Not plain ZIP
                        if enc_key:
                            dec = decrypt_bytes(raw_head, enc_key)
                            if dec and dec.startswith(b"PK\x03\x04"):
                                is_encrypted = True
                        else:
                            is_encrypted = True
                except Exception:
                    pass

                # Resolve Anonymization / Real Names
                is_anonymized = fname.startswith("PKG_") or folder_name.startswith("CUST_")
                
                # Check index map for exact match
                real_fname = index_map.get(fname, fname)
                real_folder = index_map.get(folder_name, folder_name)

                # Parse Customer & Store name
                clean_real_fname = re.sub(r'(\.tpkj).*$', '.tpkj', real_fname, flags=re.IGNORECASE)
                
                if real_folder and real_folder != "Root" and not real_folder.startswith("CUST_"):
                    customer_name = real_folder
                else:
                    parts = clean_real_fname.replace(".tpkj", "").split("-")
                    customer_name = parts[0].strip() if parts else "Packages"

                parts = clean_real_fname.replace(".tpkj", "").split("-")
                if len(parts) >= 2:
                    store_name = f"{parts[0]}-{parts[1]}".strip()
                else:
                    store_name = customer_name

                items.append(DropboxPackageItem(
                    real_customer_name=customer_name,
                    real_store_name=store_name,
                    real_file_name=clean_real_fname,
                    stored_file_name=fname,
                    stored_folder_name=folder_name,
                    full_local_path=full_path,
                    cloud_path=f"{self.config.get_cloud_target_path()}/{rel_folder}/{fname}".replace("//", "/"),
                    is_encrypted=is_encrypted,
                    is_anonymized=is_anonymized,
                    size=size,
                    modified_time=mtime
                ))

        items.sort(key=lambda x: (x.real_customer_name.lower(), x.real_store_name.lower(), x.real_file_name.lower()))
        return items

    def export_decrypted_package(self, item: DropboxPackageItem, output_dest_path: str) -> Tuple[bool, str]:
        """Decrypts and saves unencrypted package file to local target directory."""
        try:
            if not os.path.exists(item.full_local_path):
                return False, f"Source file '{item.full_local_path}' not found."

            with open(item.full_local_path, "rb") as f:
                data = f.read()

            if item.is_encrypted or not data.startswith(b"PK\x03\x04"):
                enc_key = self.config.get("encryption_key", "").strip()
                if not enc_key:
                    return False, "Encryption key is required to decrypt package contents. Configure key in Settings."

                dec = decrypt_bytes(data, enc_key)
                if not dec or not dec.startswith(b"PK\x03\x04"):
                    return False, "Decryption failed. Please verify the secret encryption key in Settings."
                data = dec

            os.makedirs(os.path.dirname(output_dest_path), exist_ok=True)
            with open(output_dest_path, "wb") as out_f:
                out_f.write(data)

            return True, f"Successfully exported decrypted package to '{output_dest_path}'."
        except Exception as e:
            return False, f"Error exporting decrypted file: {e}"
