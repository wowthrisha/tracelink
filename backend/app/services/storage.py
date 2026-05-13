import asyncio
import io
from functools import partial
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from app.config import settings


class StorageService:
    def __init__(self):
        kwargs = {
            "aws_access_key_id": settings.storage_access_key_id,
            "aws_secret_access_key": settings.storage_secret_access_key,
        }
        if settings.storage_endpoint_url:
            kwargs["endpoint_url"] = settings.storage_endpoint_url
            kwargs["region_name"] = settings.storage_region
            kwargs["config"] = boto3.session.Config(signature_version="s3v4")

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
                    raise e

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

        return await loop.run_in_executor(None, _get)

    async def delete_file(self, storage_key: str) -> None:
        loop = asyncio.get_running_loop()
        client = self._get_client()
        await loop.run_in_executor(
            None,
            partial(client.delete_object, Bucket=self._bucket, Key=storage_key),
        )

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
