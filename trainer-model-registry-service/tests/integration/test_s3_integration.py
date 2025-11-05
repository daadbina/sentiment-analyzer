"""
Integration tests for S3 integration.

Tests S3 client and artifact management.
"""

import pytest
from unittest.mock import patch, MagicMock
import hashlib

from src.clients.s3_client import S3Client
from src.registry.artifact_manager import ArtifactManager


class TestS3Integration:
    """Test S3 integration."""

    @pytest.fixture
    def mock_boto3(self):
        """Create mock boto3."""
        with patch('src.clients.s3_client.boto3.client') as mock:
            yield mock

    def test_s3_client_initialization(self, mock_boto3):
        """Test S3 client initialization."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        assert client is not None

    def test_s3_client_upload(self, mock_boto3):
        """Test S3 upload."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        result = client.upload(b'data', 'bucket', 'key')
        
        assert result is not None

    def test_s3_client_download(self, mock_boto3):
        """Test S3 download."""
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {'Body': MagicMock(read=lambda: b'data')}
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        result = client.download('bucket', 'key')
        
        assert result is not None
        assert result == b'data'

    def test_s3_client_list_objects(self, mock_boto3):
        """Test listing S3 objects."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'model_v1.pkl'},
                {'Key': 'model_v2.pkl'},
            ]
        }
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        objects = client.list_objects('bucket', 'prefix')
        
        assert objects is not None

    def test_s3_client_delete_object(self, mock_boto3):
        """Test deleting S3 object."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        client.delete_object('bucket', 'key')
        
        mock_s3.delete_object.assert_called_once()

    def test_s3_client_checksum_validation(self, mock_boto3):
        """Test checksum validation."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        data = b'test_data'
        checksum = client.compute_checksum(data)
        
        assert checksum is not None
        assert isinstance(checksum, str)
        
        is_valid = client.validate_checksum(data, checksum)
        assert is_valid is True

    def test_s3_client_checksum_mismatch(self, mock_boto3):
        """Test checksum mismatch detection."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        data = b'test_data'
        wrong_checksum = 'wrong_checksum'
        
        is_valid = client.validate_checksum(data, wrong_checksum)
        assert is_valid is False

    def test_artifact_manager_upload(self, mock_boto3):
        """Test artifact upload."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        manager = ArtifactManager()
        
        artifact_data = b'model_data'
        result = manager.upload_artifact(artifact_data, 's3://bucket/model.pkl')
        
        assert result is not None

    def test_artifact_manager_download(self, mock_boto3):
        """Test artifact download."""
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {'Body': MagicMock(read=lambda: b'model_data')}
        mock_boto3.return_value = mock_s3
        
        manager = ArtifactManager()
        
        result = manager.download_artifact('s3://bucket/model.pkl')
        
        assert result is not None

    def test_artifact_manager_versioning(self, mock_boto3):
        """Test artifact versioning."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        manager = ArtifactManager()
        
        artifact_data = b'model_data'
        
        # Upload v1
        path_v1 = manager.upload_artifact(artifact_data, 's3://bucket/model_v1.pkl')
        
        # Upload v2
        path_v2 = manager.upload_artifact(artifact_data, 's3://bucket/model_v2.pkl')
        
        assert path_v1 is not None
        assert path_v2 is not None

    def test_artifact_manager_metadata(self, mock_boto3):
        """Test artifact metadata."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        manager = ArtifactManager()
        
        artifact_data = b'model_data'
        metadata = {
            'model_name': 'xgboost',
            'version': 'v1',
            'auc': 0.85
        }
        
        result = manager.upload_artifact_with_metadata(
            artifact_data,
            's3://bucket/model.pkl',
            metadata
        )
        
        assert result is not None

    def test_artifact_manager_retry_logic(self, mock_boto3):
        """Test retry logic."""
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = [
            Exception("Connection error"),
            Exception("Connection error"),
            None
        ]
        mock_boto3.return_value = mock_s3
        
        manager = ArtifactManager()
        
        artifact_data = b'model_data'
        
        # Should retry and eventually succeed
        result = manager.upload_artifact_with_retry(
            artifact_data,
            's3://bucket/model.pkl',
            max_retries=3
        )
        
        assert result is not None

    def test_s3_client_multipart_upload(self, mock_boto3):
        """Test multipart upload for large files."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        # Large data
        large_data = b'x' * (10 * 1024 * 1024)  # 10MB
        
        result = client.upload_multipart(large_data, 'bucket', 'key')
        
        assert result is not None

    def test_s3_client_object_exists(self, mock_boto3):
        """Test checking if object exists."""
        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {'ContentLength': 1024}
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        exists = client.object_exists('bucket', 'key')
        
        assert exists is True

    def test_s3_client_get_object_metadata(self, mock_boto3):
        """Test getting object metadata."""
        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': '2024-01-01',
            'ETag': 'abc123'
        }
        mock_boto3.return_value = mock_s3
        
        client = S3Client()
        
        metadata = client.get_object_metadata('bucket', 'key')
        
        assert metadata is not None
        assert 'ContentLength' in metadata

