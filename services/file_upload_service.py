import os
import uuid
from supabase import create_client

# Allowed MIME magic bytes (first bytes of file content)
_MAGIC = {
    b'\xff\xd8\xff':       'jpg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'RIFF':               'webp',   # checked with offset 8 == WEBP
    b'GIF87a':             'gif',
    b'GIF89a':             'gif',
}
_MAX_BYTES = 8 * 1024 * 1024   # 8 MB hard limit per file
_BUCKET    = 'product-images'   # create this bucket in Supabase dashboard


def _detect_mime(header: bytes) -> str | None:
    """Return extension if header matches a known image magic, else None."""
    for magic, ext in _MAGIC.items():
        if header[:len(magic)] == magic:
            # Extra check for WebP: bytes 8-12 must be b'WEBP'
            if ext == 'webp' and header[8:12] != b'WEBP':
                continue
            return ext
    return None


class FileUploadService:
    """
    Uploads files to Supabase Storage and returns public CDN URLs.
    The database stores only the public URL — no local paths.
    """

    def __init__(self):
        self._client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
        )

    # ── Public API ────────────────────────────────────────────

    def save_file(self, file, subfolder: str = 'general') -> str | None:
        """
        Validate, upload to Supabase Storage, and return the public URL.
        Returns None on any failure.

        Args:
            file:      Werkzeug FileStorage object from request.files
            subfolder: Storage path prefix, e.g. 'products/seller-uuid'
        """
        if not file or not file.filename:
            return None

        # CWE-22: reject path traversal in subfolder
        from security import safe_path_component
        if not safe_path_component(subfolder):
            print(f'[FileUpload] Rejected: path traversal attempt in subfolder {subfolder!r}')
            return None

        # Read file bytes once
        data = file.read()
        if not data:
            return None

        # Enforce size limit
        if len(data) > _MAX_BYTES:
            print(f'[FileUpload] Rejected: file exceeds {_MAX_BYTES // 1024 // 1024} MB')
            return None

        # Validate actual content (magic bytes), not just extension
        ext = _detect_mime(data[:12])
        if ext is None:
            print(f'[FileUpload] Rejected: unrecognised image format for {file.filename!r}')
            return None

        # Build a collision-proof storage path
        storage_path = f"{subfolder.strip('/')}/{uuid.uuid4().hex}.{ext}"

        try:
            self._client.storage.from_(_BUCKET).upload(
                path=storage_path,
                file=data,
                file_options={'content-type': f'image/{ext}', 'cache-control': '31536000'},
            )
            return self._public_url(storage_path)
        except Exception as e:
            print(f'[FileUpload] Upload failed: {e}')
            return None

    def delete_file(self, url: str) -> bool:
        """
        Delete a file from Supabase Storage given its public URL.
        Safe to call with legacy local paths — they are ignored.
        """
        if not url or url.startswith('static/'):
            return False   # legacy local path — skip silently
        try:
            path = self._storage_path_from_url(url)
            self._client.storage.from_(_BUCKET).remove([path])
            return True
        except Exception as e:
            print(f'[FileUpload] Delete failed: {e}')
            return False

    def get_public_url(self, path_or_url: str) -> str:
        """
        Normalise any stored value to a usable URL.
        - Already a full URL  → return as-is
        - Legacy local path   → prepend / so Flask can serve it during dev
        """
        if not path_or_url:
            return ''
        if path_or_url.startswith('http'):
            return path_or_url
        # Legacy local path fallback (dev only)
        return path_or_url if path_or_url.startswith('/') else '/' + path_or_url

    # ── Private helpers ───────────────────────────────────────

    def _public_url(self, storage_path: str) -> str:
        res = self._client.storage.from_(_BUCKET).get_public_url(storage_path)
        # supabase-py v1 returns a dict; v2 returns a string
        return res if isinstance(res, str) else res.get('publicURL', '')

    def _storage_path_from_url(self, url: str) -> str:
        """Extract the storage path from a Supabase public URL."""
        # URL format: https://<project>.supabase.co/storage/v1/object/public/<bucket>/<path>
        marker = f'/object/public/{_BUCKET}/'
        idx = url.find(marker)
        if idx == -1:
            return url
        return url[idx + len(marker):]
