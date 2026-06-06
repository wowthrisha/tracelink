"""
Storage service — S3/R2-compatible document asset store.

Wraps boto3 S3 client calls in asyncio executor calls so they do not block
the async event loop.  Uses a dedicated bounded thread pool (_STORAGE_EXECUTOR)
separate from the default asyncio pool to prevent S3 network waits from
competing with CPU-bound tasks (e.g. watermarking).

Phase 8 additions:
  - file_exists() method for safe pre-existence checks
  - storage_path_style config support (MinIO, some Cloudflare R2 configs)
  - Consistent use of _STORAGE_EXECUTOR for all S3 operations
  - StorageBackend abstract base for testability / future backends

Cloudflare R2 compatibility:
  - Set STORAGE_ENDPOINT_URL to your R2 endpoint
    (e.g. https://<account-id>.r2.cloudflarestorage.com)
  - Set STORAGE_ACCESS_KEY_ID / STORAGE_SECRET_ACCESS_KEY to R2 API tokens
  - Leave STORAGE_PATH_STYLE=false (R2 uses virtual-hosted style by default)
  - Set STORAGE_REGION to "auto"
"""
import asyncio
import concurrent.futures
import io
from abc import ABC, abstractmethod
from functools import partial
from typing import Optional
import boto3
import boto3.exceptions
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError
from app.config import settings

# Dedicated bounded thread pool for S3/R2 I/O operations.
# Keeping storage I/O separate from the default asyncio executor prevents
# S3 network waits from competing with CPU-bound tasks (e.g. watermarking)
# that share the default thread pool.
# 16 threads: comfortably handles burst page / thumbnail fetches under load.
_STORAGE_EXECUTOR: concurrent.futures.ThreadPoolExecutor = (
    concurrent.futures.ThreadPoolExecutor(
        max_workers=16, thread_name_prefix="storage-io"
    )
)

# Fail fast: 2 attempts, 30 s connect, 60 s read.  Without this boto3 retries
# 5 times with exponential backoff, blocking the request for 3+ minutes before
# Railway's proxy kills it with a 502.
_BOTO_CONFIG = BotocoreConfig(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=30,
    read_timeout=60,
)


class StorageBackend(ABC):
    """Abstract storage backend.  All concrete backends must implement these methods."""

    @abstractmethod
    async def upload_file(
        self, file_bytes: bytes, storage_key: str, content_type: str = "application/pdf"
    ) -> str: ...

    @abstractmethod
    async def download_bytes(self, storage_key: str) -> bytes: ...

    @abstractmethod
    async def delete_file(self, storage_key: str) -> None: ...

    @abstractmethod
    async def list_keys_with_prefix(self, prefix: str) -> list[str]: ...

    @abstractmethod
    async def file_exists(self, storage_key: str) -> bool: ...

    # generate_presigned_url is optional (not all backends support it)
    async def generate_presigned_url(
        self, storage_key: str, expires_in_seconds: int = 60
    ) -> str:
        raise NotImplementedError("This storage backend does not support presigned URLs")


class StorageService(StorageBackend):
    def __init__(self):
        kwargs: dict = {
            "aws_access_key_id": settings.storage_access_key_id,
            "aws_secret_access_key": settings.storage_secret_access_key,
            "config": _BOTO_CONFIG,
        }
        if settings.storage_endpoint_url:
            kwargs["endpoint_url"] = settings.storage_endpoint_url
            kwargs["region_name"] = settings.storage_region
            # Phase 8: path-style addressing required for MinIO and some R2 setups.
            # Virtual-hosted style (default) requires the bucket name in the hostname;
            # path-style puts it in the URL path instead.
            cfg_overrides: dict = {"signature_version": "s3v4"}
            if settings.storage_path_style:
                cfg_overrides["s3"] = {"addressing_style": "path"}
            kwargs["config"] = _BOTO_CONFIG.merge(BotocoreConfig(**cfg_overrides))
        elif settings.storage_region:
            kwargs["region_name"] = settings.storage_region

        self._client = boto3.client("s3", **kwargs)
        self._bucket = settings.storage_bucket_name

    def _get_client(self):
        return self._client

    async def upload_file(
        self,
        file_bytes: bytes,
        storage_key: str,
        content_type: str = "application/pdf",
    ) -> str:
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _upload():
            try:
                client.upload_fileobj(
                    io.BytesIO(file_bytes),
                    self._bucket,
                    storage_key,
                    ExtraArgs={"ContentType": content_type},
                )
            except ClientError:
                raise
            except boto3.exceptions.S3UploadFailedError as e:
                # upload_fileobj wraps underlying errors in S3UploadFailedError;
                # unwrap and re-raise so callers get a consistent ClientError.
                raise e.__cause__ or e

        await loop.run_in_executor(_STORAGE_EXECUTOR, _upload)
        return storage_key

    async def generate_presigned_url(
        self,
        storage_key: str,
        expires_in_seconds: int = 60,
    ) -> str:
        loop = asyncio.get_running_loop()
        client = self._get_client()
        url = await loop.run_in_executor(
            _STORAGE_EXECUTOR,
            partial(
                client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self._bucket, "Key": storage_key},
                ExpiresIn=expires_in_seconds,
            ),
        )
        return url

    async def download_bytes(self, storage_key: str) -> bytes:
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _get():
            response = client.get_object(Bucket=self._bucket, Key=storage_key)
            return response["Body"].read()

        return await loop.run_in_executor(_STORAGE_EXECUTOR, _get)

    async def delete_file(self, storage_key: str) -> None:
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _delete():
            try:
                client.delete_object(Bucket=self._bucket, Key=storage_key)
            except ClientError as e:
                if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                    return  # already gone — that's fine
                raise

        await loop.run_in_executor(_STORAGE_EXECUTOR, _delete)

    async def list_keys_with_prefix(self, prefix: str) -> list[str]:
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _list():
            keys = []
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])
            return keys

        return await loop.run_in_executor(_STORAGE_EXECUTOR, _list)

    async def file_exists(self, storage_key: str) -> bool:
        """Return True if the object exists in the bucket (head_object check)."""
        loop = asyncio.get_running_loop()
        client = self._get_client()

        def _head():
            try:
                client.head_object(Bucket=self._bucket, Key=storage_key)
                return True
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code in ("404", "NoSuchKey"):
                    return False
                raise

        return await loop.run_in_executor(_STORAGE_EXECUTOR, _head)


_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
