import os
import shutil
import subprocess
from typing import List, Optional
from core.models import PackageItem

class LocalProvider:
    def __init__(self, target_base_path: str):
        self.target_base_path = os.path.normpath(target_base_path)
        self.ensure_base_directory()

    def ensure_base_directory(self):
        """Creates the local base directory if it doesn't exist."""
        try:
            if not os.path.exists(self.target_base_path):
                os.makedirs(self.target_base_path, exist_ok=True)
        except Exception as e:
            print(f"Error ensuring base directory '{self.target_base_path}': {e}")

    def list_items(self, sub_path: str = "") -> List[PackageItem]:
        """Lists items in target_base_path / sub_path."""
        items: List[PackageItem] = []
        current_dir = os.path.normpath(os.path.join(self.target_base_path, sub_path))

        if not os.path.exists(current_dir):
            return items

        try:
            entries = os.listdir(current_dir)
            for entry in entries:
                full_path = os.path.join(current_dir, entry)
                rel_path = os.path.relpath(full_path, self.target_base_path).replace("\\", "/")
                is_dir = os.path.isdir(full_path)
                
                try:
                    stat = os.stat(full_path)
                    size = stat.st_size if not is_dir else 0
                    modified = stat.st_mtime
                except Exception:
                    size = 0
                    modified = 0.0

                cloud_rel = rel_path.lstrip("/")
                cloud_path = f"/Nor Cal office misc/Packages/{cloud_rel}" if cloud_rel else "/Nor Cal office misc/Packages"

                items.append(PackageItem(
                    name=entry,
                    relative_path=rel_path,
                    full_local_path=full_path,
                    cloud_path=cloud_path,
                    is_dir=is_dir,
                    size=size,
                    modified_time=modified,
                    sync_status="synced"
                ))
        except Exception as e:
            print(f"Error listing local items: {e}")

        # Sort folders first, then by name case-insensitive
        items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
        return items

    def create_folder(self, sub_path: str, folder_name: str) -> bool:
        """Create a subfolder locally."""
        try:
            target = os.path.join(self.target_base_path, sub_path, folder_name)
            os.makedirs(target, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating folder '{folder_name}': {e}")
            return False

    def delete_item(self, local_path: str) -> bool:
        """Deletes a file or directory locally."""
        try:
            if os.path.isdir(local_path):
                shutil.rmtree(local_path)
            elif os.path.exists(local_path):
                os.remove(local_path)
            return True
        except Exception as e:
            print(f"Error deleting '{local_path}': {e}")
            return False

    def file_exists(self, target_sub_path: str, file_name: str) -> bool:
        """Checks if a file exists locally in destination."""
        dest_dir = os.path.join(self.target_base_path, target_sub_path)
        dest_path = os.path.join(dest_dir, file_name)
        return os.path.exists(dest_path)

    def copy_file_in(self, src_file_path: str, target_sub_path: str = "", override_filename: str = "") -> Optional[str]:
        """Copies an external file into the packages folder, with optional filename override."""
        try:
            file_name = override_filename if override_filename else os.path.basename(src_file_path)
            dest_dir = os.path.join(self.target_base_path, target_sub_path)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, file_name)
            shutil.copy2(src_file_path, dest_path)
            return dest_path
        except Exception as e:
            print(f"Error copying file in: {e}")
            return None

    def reveal_in_explorer(self, local_path: str):
        """Reveals file or directory in Windows File Explorer."""
        try:
            norm_path = os.path.normpath(local_path)
            if os.path.exists(norm_path):
                subprocess.Popen(f'explorer.exe /select,"{norm_path}"')
            else:
                subprocess.Popen(f'explorer.exe "{self.target_base_path}"')
        except Exception as e:
            print(f"Error revealing in explorer: {e}")

    def open_file_default(self, local_path: str):
        """Opens file with default Windows registered handler."""
        try:
            norm_path = os.path.normpath(local_path)
            if os.path.exists(norm_path):
                os.startfile(norm_path)
        except Exception as e:
            print(f"Error opening file: {e}")

    def read_text_preview(self, local_path: str, max_lines: int = 50) -> str:
        """Reads text preview from local file."""
        try:
            with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
                return "".join(lines)
        except Exception as e:
            return f"Unable to preview file content: {e}"
