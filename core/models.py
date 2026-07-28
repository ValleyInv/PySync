from dataclasses import dataclass
import os
import datetime

@dataclass
class PackageItem:
    name: str
    relative_path: str        # Relative to Packages folder (e.g. "2026/Manifest.pdf" or "Package_A.zip")
    full_local_path: str      # Local absolute path
    cloud_path: str           # Cloud path (e.g. "/Nor Cal office misc/Packages/2026/Manifest.pdf")
    is_dir: bool
    size: int                 # Bytes
    modified_time: float      # Unix timestamp
    sync_status: str          # "synced", "cloud_only", "local_only", "pending"
    extension: str = ""

    def __post_init__(self):
        if not self.extension and not self.is_dir:
            _, ext = os.path.splitext(self.name)
            self.extension = ext.lower()

    @property
    def formatted_size(self) -> str:
        if self.is_dir:
            return "--"
        num = self.size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(num) < 1024.0:
                return f"{num:3.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} PB"

    @property
    def formatted_date(self) -> str:
        if not self.modified_time:
            return "--"
        dt = datetime.datetime.fromtimestamp(self.modified_time)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def category(self) -> str:
        if self.is_dir:
            return "Folder"
        ext = self.extension
        if ext in [".zip", ".tar", ".gz", ".7z", ".rar", ".pkg", ".deb", ".msi"]:
            return "Packages & Archives"
        elif ext in [".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx", ".json", ".xml", ".log"]:
            return "Documents"
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"]:
            return "Images"
        return "Other Files"
