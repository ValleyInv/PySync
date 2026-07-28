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
        results: Dict[str, Tuple[int, str, str, int, float]] = {}
        dir_count = 0

        try:
            for root, dirs, files in os.walk(self.base_dir):
                if self._is_cancelled:
                    break

                dir_count += 1
                tpkj_files = []

                for f in files:
                    f_lower = f.lower()
                    m = pattern.search(f)
                    if m:
                        num = int(m.group(2))
                        tpkj_files.append((num, f, os.path.join(root, f)))
                    elif f_lower.endswith('.tpkj'):
                        # Direct .tpkj file without trailing version suffix (treated as v1)
                        tpkj_files.append((1, f, os.path.join(root, f)))
                    elif '.tpkj.' in f_lower:
                        nums = re.findall(r'\d+', f_lower.split('.tpkj.')[-1])
                        num = int(nums[-1]) if nums else 0
                        tpkj_files.append((num, f, os.path.join(root, f)))

                if tpkj_files:
                    # Pick highest version number in this directory
                    tpkj_files.sort(key=lambda x: x[0], reverse=True)
                    highest_num, highest_file, highest_path = tpkj_files[0]

                    try:
                        st = os.stat(highest_path)
                        size = st.st_size
                        mtime = st.st_mtime
                    except Exception:
                        size = 0
                        mtime = 0.0

                    results[root] = (highest_num, highest_file, highest_path, size, mtime)

                if dir_count % 100 == 0:
                    rel_current = os.path.relpath(root, self.base_dir)
                    self.progress_updated.emit(dir_count, len(results), f"Scanning {rel_current}...")

            package_items: List[ScannedPackageItem] = []
            for root, (v_num, fname, full_path, size, mtime) in results.items():
                rel_parts = os.path.relpath(root, self.base_dir).split(os.sep)
                customer = rel_parts[0] if rel_parts else "Unknown"
                store = rel_parts[2] if len(rel_parts) >= 3 else (rel_parts[1] if len(rel_parts) >= 2 else "Main")

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

            # Sort by customer name, store, filename
            package_items.sort(key=lambda x: (x.customer_name.lower(), x.store_name.lower(), x.file_name.lower()))
            self.scan_completed.emit(package_items)

        except Exception as e:
            self.scan_failed.emit(f"Error during scan: {e}")
