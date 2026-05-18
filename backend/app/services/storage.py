import asyncio
import concurrent.futures
import io
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


class StorageService:
    def __init__(self):
        kwargs: dict = {
            "aws_access_key_id": settings.storage_access_key_id,
            "aws_secret_access_key": settings.storage_secret_access_key,
            "config": _BOTO_CONFIG,
        }
        if settings.storage_endpoint_url:
            kwargs["endpoint_url"] = settings.storage_endpoint_url
            kwargs["region_name"] = settings.storage_region
            # Merge signature version into the existing config object
            kwargs["config"] = _BOTO_CONFIG.merge(
                BotocoreConfig(signature_version="s3v4")
            )

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
            except ClientError as e:
                # If bucket doesn't exist, try creating it (useful for local Moto testing)
                if e.response['Error']['Code'] == 'NoSuchBucket':
                    client.create_bucket(Bucket=self._bucket)
                    client.upload_fileobj(
                        io.BytesIO(file_bytes),
                        self._bucket,
                        storage_key,
                        ExtraArgs={"ContentType": content_type},
                    )
                else:
                    raise
            except boto3.exceptions.S3UploadFailedError as e:
                # upload_fileobj wraps underlying errors in S3UploadFailedError;
                # unwrap and re-raise so callers get a consistent ClientError.
                raise e.__cause__ or e

        await loop.run_in_executor(None, _upload)
        return storage_key

    async def generate_presigned_url(
        self,
        storage_key: str,
        expires_in_seconds: int = 60,
    ) -> str:
        loop = asyncio.get_running_loop()
        client = self._get_client()
        url = await loop.run_in_executor(
            None,
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

        await loop.run_in_executor(None, _delete)

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

        return await loop.run_in_executor(None, _list)


_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
