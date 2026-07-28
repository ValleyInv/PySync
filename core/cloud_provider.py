import os
import io
from typing import List, Tuple, Optional
from core.models import PackageItem

try:
    import dropbox
    from dropbox.exceptions import ApiError, AuthError
    HAS_DROPBOX_SDK = True
except ImportError:
    HAS_DROPBOX_SDK = False

class CloudProvider:
    def __init__(self, access_token: str = ""):
        self.access_token = access_token.strip()
        self.client = None
        if HAS_DROPBOX_SDK and self.access_token:
            try:
                self.client = dropbox.Dropbox(self.access_token)
            except Exception as e:
                print(f"Error initializing Dropbox client: {e}")

    def is_connected(self) -> bool:
        return self.client is not None

    def test_connection(self) -> Tuple[bool, str]:
        if not HAS_DROPBOX_SDK:
            return False, "Dropbox Python SDK is not installed."
        if not self.access_token:
            return False, "No Access Token configured. Add your token in Settings."
        try:
            self.client = dropbox.Dropbox(self.access_token)
            account = self.client.users_get_current_account()
            return True, f"Connected to Dropbox as {account.name.display_name} ({account.email})"
        except AuthError:
            return False, "Invalid or expired Dropbox Access Token."
        except Exception as e:
            return False, f"Connection failed: {e}"

    def list_items(self, cloud_target_folder: str) -> Tuple[List[PackageItem], str]:
        """Lists items in cloud_target_folder via Dropbox API without local disk usage."""
        if not self.is_connected():
            return [], "Cloud provider not connected."

        items: List[PackageItem] = []
        try:
            folder_path = cloud_target_folder if cloud_target_folder != "/" else ""
            res = self.client.files_list_folder(folder_path)
            
            entries = list(res.entries)
            while res.has_more:
                res = self.client.files_list_folder_continue(res.cursor)
                entries.extend(res.entries)

            for entry in entries:
                is_dir = isinstance(entry, dropbox.files.FolderMetadata)
                size = getattr(entry, "size", 0) if not is_dir else 0
                modified = 0.0
                if hasattr(entry, "client_modified"):
                    modified = entry.client_modified.timestamp()

                rel_path = entry.name
                items.append(PackageItem(
                    name=entry.name,
                    relative_path=rel_path,
                    full_local_path="",
                    cloud_path=entry.path_display,
                    is_dir=is_dir,
                    size=size,
                    modified_time=modified,
                    sync_status="cloud_only"
                ))

            items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
            return items, ""
        except ApiError as e:
            return [], f"Dropbox API Error: {e}"
        except Exception as e:
            return [], f"Error listing cloud files: {e}"

    def get_thumbnail_bytes(self, cloud_path: str) -> Optional[bytes]:
        """Streams thumbnail bytes directly from Dropbox Cloud API without writing file to disk."""
        if not self.is_connected():
            return None
        try:
            _, res = self.client.files_get_thumbnail(
                cloud_path,
                format=dropbox.files.ThumbnailFormat.png,
                size=dropbox.files.ThumbnailSize.w256h256
            )
            return res.content
        except Exception as e:
            print(f"Error fetching thumbnail for '{cloud_path}': {e}")
            return None

    def get_file_content_preview(self, cloud_path: str, max_bytes: int = 8192) -> Optional[str]:
        """Fetches initial text content preview directly from cloud memory without storing file on disk."""
        if not self.is_connected():
            return None
        try:
            metadata, res = self.client.files_download(cloud_path)
            raw_bytes = res.content[:max_bytes]
            return raw_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            print(f"Error downloading content preview for '{cloud_path}': {e}")
            return None

    def upload_file(self, local_path: str, cloud_dest_path: str) -> Tuple[bool, str]:
        """Uploads a file directly to Dropbox Cloud API."""
        if not self.is_connected():
            return False, "Cloud provider not connected."

        try:
            size = os.path.getsize(local_path)
            with open(local_path, "rb") as f:
                if size <= 150 * 1024 * 1024:  # <= 150MB standard upload
                    self.client.files_upload(f.read(), cloud_dest_path, mode=dropbox.files.WriteMode.overwrite)
                else:  # Chunked upload for large files
                    CHUNK_SIZE = 10 * 1024 * 1024
                    upload_session_start_result = self.client.files_upload_session_start(f.read(CHUNK_SIZE))
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=upload_session_start_result.session_id,
                        offset=f.tell()
                    )
                    commit = dropbox.files.CommitInfo(path=cloud_dest_path)

                    while f.tell() < size:
                        if (size - f.tell()) <= CHUNK_SIZE:
                            self.client.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                        else:
                            self.client.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
                            cursor.offset = f.tell()

            return True, "Upload successful"
        except Exception as e:
            return False, f"Upload error: {e}"

    def download_file(self, cloud_path: str, local_dest_path: str) -> Tuple[bool, str]:
        """Downloads cloud file on-demand to local cache path."""
        if not self.is_connected():
            return False, "Cloud provider not connected."

        try:
            os.makedirs(os.path.dirname(local_dest_path), exist_ok=True)
            self.client.files_download_to_file(local_dest_path, cloud_path)
            return True, "Download successful"
        except Exception as e:
            return False, f"Download error: {e}"

    def delete_item(self, cloud_path: str) -> Tuple[bool, str]:
        """Deletes file or folder directly in Dropbox Cloud."""
        if not self.is_connected():
            return False, "Cloud provider not connected."
        try:
            self.client.files_delete_v2(cloud_path)
            return True, "Deleted successfully from cloud"
        except Exception as e:
            return False, f"Cloud delete error: {e}"

    def create_folder(self, cloud_path: str) -> Tuple[bool, str]:
        """Creates folder directly in Dropbox Cloud."""
        if not self.is_connected():
            return False, "Cloud provider not connected."
        try:
            self.client.files_create_folder_v2(cloud_path)
            return True, "Folder created on cloud"
        except Exception as e:
            return False, f"Cloud folder creation error: {e}"
