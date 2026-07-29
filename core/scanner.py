import os
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from PyQt6.QtCore import QThread, pyqtSignal

DEFAULT_SCAN_PATH = r"C:\ProgramData\AST\Titan_Inventory_Control\_Customers"

@dataclass
class ScannedPackageItem:
    customer_name: str
    store_name: str
    dir_path: str
    file_name: str
    full_path: str
    version_num: int
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

def parse_customer_and_store(root_path: str, base_dir: str, file_name: str) -> Tuple[str, str]:
    """Parses customer name and store name from folder path or package filename."""
    rel_parts = [p for p in os.path.relpath(root_path, base_dir).split(os.sep) if p and p != "."]
    
    if rel_parts and rel_parts[0] != "Unknown":
        customer = rel_parts[0]
        store = rel_parts[2] if len(rel_parts) >= 3 else (rel_parts[1] if len(rel_parts) >= 2 else "Main")
        return customer, store

    # Fallback: Parse from filename if folder is a generic folder like Desktop/Incoming
    clean_name = re.sub(r'(\.tpkj).*$', '', file_name, flags=re.IGNORECASE)
    parts = clean_name.split("-")
    if len(parts) >= 2:
        customer = parts[0].strip()
        store = f"{parts[0]}-{parts[1]}".strip()
        return customer, store
    elif " " in clean_name:
        customer = clean_name.split(" ")[0]
        return customer, "Main"
    
    return "Packages", "Main"

class PackageScannerWorker(QThread):
    progress_updated = pyqtSignal(int, int, str) # scanned_dirs, packages_found, current_status
    scan_completed = pyqtSignal(list) # List[ScannedPackageItem]
    scan_failed = pyqtSignal(str)

    def __init__(self, base_dir: str = DEFAULT_SCAN_PATH):
        super().__init__()
        self.base_dir = base_dir
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if not os.path.exists(self.base_dir):
            self.scan_failed.emit(f"Scan path '{self.base_dir}' does not exist.")
            return

        pattern = re.compile(r'^(.*\.tpkj)\.(\d+)$', re.IGNORECASE)
        # Key: (root_directory, base_package_name) -> (version_num, file_name, full_path, size, mtime)
        results: Dict[Tuple[str, str], Tuple[int, str, str, int, float]] = {}
        dir_count = 0

        try:
            for root, dirs, files in os.walk(self.base_dir):
                if self._is_cancelled:
                    break

                dir_count += 1

                for f in files:
                    f_lower = f.lower()
                    m = pattern.search(f)

                    if m:
                        base_name = m.group(1).lower()
                        num = int(m.group(2))
                    elif f_lower.endswith('.tpkj'):
                        base_name = f_lower
                        num = 1
                    elif '.tpkj.' in f_lower:
                        base_name = f_lower.split('.tpkj.')[0] + '.tpkj'
                        nums = re.findall(r'\d+', f_lower.split('.tpkj.')[-1])
                        num = int(nums[-1]) if nums else 0
                    else:
                        continue

                    full_path = os.path.join(root, f)
                    key = (root, base_name)

                    try:
                        st = os.stat(full_path)
                        size = st.st_size
                        mtime = st.st_mtime
                    except Exception:
                        size = 0
                        mtime = 0.0

                    if key not in results or num > results[key][0]:
                        results[key] = (num, f, full_path, size, mtime)

                if dir_count % 100 == 0:
                    rel_current = os.path.relpath(root, self.base_dir)
                    self.progress_updated.emit(dir_count, len(results), f"Scanning {rel_current}...")

            package_items: List[ScannedPackageItem] = []
            for (root, base_name), (v_num, fname, full_path, size, mtime) in results.items():
                customer, store = parse_customer_and_store(root, self.base_dir, fname)

                package_items.append(ScannedPackageItem(
                    customer_name=customer,
                    store_name=store,
                    dir_path=root,
                    file_name=fname,
                    full_path=full_path,
                    version_num=v_num,
                    size=size,
                    modified_time=mtime
                ))

            # Default sort: newest modified package files first
            package_items.sort(key=lambda x: x.modified_time, reverse=True)
            self.scan_completed.emit(package_items)

        except Exception as e:
            self.scan_failed.emit(f"Error during scan: {e}")
