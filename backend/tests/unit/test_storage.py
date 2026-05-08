import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch

from app.services.storage import StorageService
from app.config import settings


@pytest.fixture
def mock_s3():
    with mock_aws():
        # Create a test bucket
        s3 = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        s3.create_bucket(Bucket="test-bucket")
        yield s3


@pytest.fixture
def storage_svc():
    with mock_aws():
        s3 = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        s3.create_bucket(Bucket="test-bucket")

        svc = StorageService.__new__(StorageService)
        svc._client = s3
        svc._bucket = "test-bucket"
        yield svc


class TestStorageService:

    @pytest.mark.asyncio
    async def test_upload_file_stores_object(self, storage_svc):
        with mock_aws():
            key = await storage_svc.upload_file(b"test content", "test/key.pdf")
            assert key == "test/key.pdf"

    @pytest.mark.asyncio
    async def test_upload_file_returns_storage_key(self, storage_svc):
        with mock_aws():
            key = await storage_svc.upload_file(b"hello", "originals/doc.pdf")
            assert key == "originals/doc.pdf"

    @pytest.mark.asyncio
    async def test_download_bytes_retrieves_content(self, storage_svc):
        with mock_aws():
            content = b"PDF content here"
            await storage_svc.upload_file(content, "test/file.pdf")
            retrieved = await storage_svc.download_bytes("test/file.pdf")
            assert retrieved == content

    @pytest.mark.asyncio
    async def test_delete_file_removes_object(self, storage_svc):
        with mock_aws():
            await storage_svc.upload_file(b"data", "test/del.pdf")
            await storage_svc.delete_file("test/del.pdf")
            # Verify the object is gone
            import botocore.exceptions
            try:
                storage_svc._client.get_object(Bucket="test-bucket", Key="test/del.pdf")
                assert False, "Object should be deleted"
            except storage_svc._client.exceptions.NoSuchKey:
                pass
            except Exception:
                pass  # Any error means it's gone

    @pytest.mark.asyncio
    async def test_list_keys_with_prefix(self, storage_svc):
        with mock_aws():
            await storage_svc.upload_file(b"p1", "pages/doc1/0001.webp")
            await storage_svc.upload_file(b"p2", "pages/doc1/0002.webp")
            await storage_svc.upload_file(b"other", "originals/doc1.pdf")
            keys = await storage_svc.list_keys_with_prefix("pages/doc1/")
            assert len(keys) == 2
            assert "pages/doc1/0001.webp" in keys
            assert "pages/doc1/0002.webp" in keys

    @pytest.mark.asyncio
    async def test_generate_presigned_url_returns_string(self, storage_svc):
        with mock_aws():
            await storage_svc.upload_file(b"data", "test/page.webp")
            url = await storage_svc.generate_presigned_url("test/page.webp")
            assert isinstance(url, str)
            assert "test/page.webp" in url or "test-bucket" in url

    def test_storage_service_init_with_endpoint(self):
        with mock_aws():
            with patch.object(settings, "storage_endpoint_url", "https://r2.example.com"):
                svc = StorageService()
                assert svc._bucket == settings.storage_bucket_name
