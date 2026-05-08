"""
Demo storage backend — stores files on local disk under /tmp/securedoc_storage/
Import this BEFORE starting the app to override the storage service.

WARNING: Must only be used in development mode (APP_ENV=development).
"""
import asyncio
from pathlib import Path
from app.config import settings as _settings
from app.services import storage as _mod

if _settings.app_env != "development":
    raise RuntimeError(
        "demo_storage_patch.py must not be imported in production. "
        "Use real S3/R2 storage via STORAGE_* environment variables."
    )

STORE_DIR = Path("/tmp/securedoc_storage")
STORE_DIR.mkdir(parents=True, exist_ok=True)


class DemoStorageService:
    def _path(self, key: str) -> Path:
        p = STORE_DIR / key.replace("/", "_")
        return p

    async def upload_file(self, file_bytes: bytes, storage_key: str, content_type: str = "application/pdf") -> str:
        self._path(storage_key).write_bytes(file_bytes)
        return storage_key

    async def download_bytes(self, storage_key: str) -> bytes:
        p = self._path(storage_key)
        if p.exists():
            return p.read_bytes()
        # Return a placeholder WebP if file not found
        from PIL import Image
        import io
        img = Image.new("RGB", (595, 842), color=(240, 240, 240))
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        return buf.getvalue()

    async def generate_presigned_url(self, storage_key: str, expires_in_seconds: int = 60) -> str:
        return f"http://localhost:8000/demo-storage/{storage_key}"

    async def delete_file(self, storage_key: str) -> None:
        p = self._path(storage_key)
        if p.exists():
            p.unlink()

    async def list_keys_with_prefix(self, prefix: str) -> list:
        prefix_flat = prefix.replace("/", "_")
        return [
            str(f.name).replace("_", "/", 1)
            for f in STORE_DIR.iterdir()
            if f.name.startswith(prefix_flat)
        ]


_demo_svc = DemoStorageService()

def get_demo_storage():
    return _demo_svc

# Monkey-patch the module
_mod.get_storage_service = get_demo_storage
_mod._storage_service = _demo_svc
print("[demo] Storage patched to local disk at /tmp/securedoc_storage/")
