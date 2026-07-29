import os
import shutil
from typing import List, Tuple, Optional
from config import ConfigManager
from core.models import PackageItem
from core.local_provider import LocalProvider
from core.cloud_provider import CloudProvider

class HybridEngine:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.local_provider = LocalProvider(config.get_effective_target_path())
        self.cloud_provider = CloudProvider(
            access_token=config.get("dropbox_access_token", ""),
            refresh_token=config.get("dropbox_refresh_token", ""),
            app_key=config.get("dropbox_app_key", ""),
            app_secret=config.get("dropbox_app_secret", "")
        )

    def reload_config(self):
        """Reload providers after settings update."""
        self.local_provider = LocalProvider(self.config.get_effective_target_path())
        self.cloud_provider = CloudProvider(
            access_token=self.config.get("dropbox_access_token", ""),
            refresh_token=self.config.get("dropbox_refresh_token", ""),
            app_key=self.config.get("dropbox_app_key", ""),
            app_secret=self.config.get("dropbox_app_secret", "")
        )

    def file_exists(self, dest_sub: str, dest_file_name: str) -> bool:
        """Checks if package file exists either locally or in pure cloud mode."""
        is_pure_cloud = self.config.get("pure_cloud_mode", False) and self.cloud_provider.is_connected()
        if is_pure_cloud:
            cloud_dest = f"{self.config.get_cloud_target_path()}/{dest_sub}/{dest_file_name}".replace("//", "/")
            return self.cloud_provider.file_exists(cloud_dest)
        else:
            return self.local_provider.file_exists(dest_sub, dest_file_name)

    def list_items(self, sub_path: str = "") -> List[PackageItem]:
        """Lists items. If Pure Cloud Mode is active, lists directly via API to save disk space."""
        is_pure_cloud = self.config.get("pure_cloud_mode", False) and self.cloud_provider.is_connected()

        cloud_rel_base = self.config.get_cloud_target_path()
        target_cloud = f"{cloud_rel_base}/{sub_path}".strip("/").replace("//", "/")
        if not target_cloud.startswith("/"):
            target_cloud = "/" + target_cloud

        if is_pure_cloud:
            # PURE CLOUD MODE: Zero disk space used!
            cloud_items, _ = self.cloud_provider.list_items(target_cloud)
            for item in cloud_items:
                item.relative_path = os.path.join(sub_path, item.name).replace("\\", "/")
            return cloud_items

        # HYBRID MODE: Merge local filesystem and cloud API
        local_items = self.local_provider.list_items(sub_path)

        if self.cloud_provider.is_connected():
            cloud_items, _ = self.cloud_provider.list_items(target_cloud)
            if cloud_items:
                local_dict = {item.name: item for item in local_items}

                for c_item in cloud_items:
                    if c_item.name in local_dict:
                        local_dict[c_item.name].sync_status = "synced"
                    else:
                        c_item.relative_path = os.path.join(sub_path, c_item.name).replace("\\", "/")
                        c_item.full_local_path = os.path.join(self.local_provider.target_base_path, c_item.relative_path)
                        local_items.append(c_item)

        local_items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
        return local_items

    def download_to_temp_cache(self, item: PackageItem) -> Tuple[bool, str]:
        """Downloads a cloud-only file on demand to temporary cache without filling local Dropbox storage."""
        if not self.cloud_provider.is_connected():
            return False, "Cloud provider not connected."

        cache_dir = self.config.get_cache_directory()
        cache_path = os.path.join(cache_dir, item.relative_path.replace("/", "_"))

        if os.path.exists(cache_path):
            item.full_local_path = cache_path
            return True, cache_path

        # Check and enforce cache size limits
        self._enforce_cache_limit()

        ok, msg = self.cloud_provider.download_file(item.cloud_path, cache_path)
        if ok:
            item.full_local_path = cache_path
            return True, cache_path
        return False, msg

    def _enforce_cache_limit(self):
        """Purges oldest files in temp cache if total size exceeds max_cache_mb limit."""
        try:
            cache_dir = self.config.get_cache_directory()
            max_bytes = self.config.get("max_cache_mb", 500) * 1024 * 1024
            
            files = []
            total_size = 0
            for f in os.listdir(cache_dir):
                fp = os.path.join(cache_dir, f)
                if os.path.isfile(fp):
                    st = os.stat(fp)
                    files.append((fp, st.st_size, st.st_atime))
                    total_size += st.st_size

            if total_size > max_bytes:
                # Sort by access time (oldest accessed first)
                files.sort(key=lambda x: x[2])
                for fp, size, _ in files:
                    try:
                        os.remove(fp)
                        total_size -= size
                        if total_size <= max_bytes * 0.7:  # Free down to 70% threshold
                            break
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error purging temp cache: {e}")

    def filter_by_category(self, items: List[PackageItem], category: str) -> List[PackageItem]:
        if category == "All":
            return items
        elif category == "Packages":
            return [i for i in items if i.category == "Packages & Archives" or i.is_dir]
        elif category == "Documents":
            return [i for i in items if i.category == "Documents" or i.is_dir]
        elif category == "Images":
            return [i for i in items if i.category == "Images" or i.is_dir]
        return items
