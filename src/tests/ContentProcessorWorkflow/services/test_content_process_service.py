# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for content_process_service.py"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

from services.content_process_service import ContentProcessService, _ProcessRepository
from services.content_process_models import ContentProcessRecord, ArtifactType


@pytest.fixture
def mock_config():
    """Create a mock Configuration object"""
    config = Mock()
    config.app_cosmos_connstr = "mongodb://test"
    config.app_cosmos_database = "test_db"
    config.app_cosmos_container_process = "processes"
    config.app_storage_account_name = "teststorage"
    config.app_cps_processes = "processes"
    config.app_storage_queue_url = "https://test.queue.core.windows.net"
    config.app_message_queue_extract = "extract-queue"
    return config


@pytest.fixture
def mock_credential():
    """Create a mock DefaultAzureCredential"""
    return Mock()


@pytest.fixture
def content_process_service(mock_config, mock_credential):
    """Create a ContentProcessService instance with mocks"""
    with patch('services.content_process_service._ProcessRepository'):
        service = ContentProcessService(mock_config, mock_credential)
        return service


class TestProcessRepository:
    """Test _ProcessRepository"""
    
    def test_process_repository_initialization(self):
        """Test _ProcessRepository initialization"""
        with patch('services.content_process_service.RepositoryBase.__init__', return_value=None):
            repo = _ProcessRepository(
                connection_string="mongodb://test",
                database_name="test_db",
                container_name="processes"
            )
            assert repo is not None


class TestContentProcessService:
    """Test ContentProcessService"""
    
    def test_service_initialization(self, mock_config, mock_credential):
        """Test ContentProcessService initialization"""
        with patch('services.content_process_service._ProcessRepository'):
            service = ContentProcessService(mock_config, mock_credential)
            
            assert service._config == mock_config
            assert service._credential == mock_credential
            assert service._blob_helper is None
            assert service._queue_client is None
    
    def test_get_blob_helper_lazy_initialization(self, content_process_service, mock_config):
        """Test _get_blob_helper lazy initialization"""
        mock_blob_helper = Mock()
        
        with patch('services.content_process_service.StorageBlobHelper', return_value=mock_blob_helper):
            helper = content_process_service._get_blob_helper()
            
            assert helper == mock_blob_helper
            assert content_process_service._blob_helper == mock_blob_helper
            # Verify create_container was called
            mock_blob_helper.create_container.assert_called_once_with(mock_config.app_cps_processes)
    
    def test_get_blob_helper_returns_cached_instance(self, content_process_service):
        """Test _get_blob_helper returns cached instance on subsequent calls"""
        mock_blob_helper = Mock()
        content_process_service._blob_helper = mock_blob_helper
        
        helper = content_process_service._get_blob_helper()
        
        assert helper == mock_blob_helper
    
    def test_get_queue_client_lazy_initialization(self, content_process_service, mock_config, mock_credential):
        """Test _get_queue_client lazy initialization"""
        mock_queue_client = Mock()
        
        with patch('services.content_process_service.QueueClient', return_value=mock_queue_client) as mock_queue_class:
            client = content_process_service._get_queue_client()
            
            assert client == mock_queue_client
            assert content_process_service._queue_client == mock_queue_client
            mock_queue_class.assert_called_once_with(
                account_url=mock_config.app_storage_queue_url,
                queue_name=mock_config.app_message_queue_extract,
                credential=mock_credential
            )
    
    def test_get_queue_client_returns_cached_instance(self, content_process_service):
        """Test _get_queue_client returns cached instance on subsequent calls"""
        mock_queue_client = Mock()
        content_process_service._queue_client = mock_queue_client
        
        client = content_process_service._get_queue_client()
        
        assert client == mock_queue_client
    
    @pytest.mark.asyncio
    async def test_submit_success(self, content_process_service, mock_config):
        """Test successful submit operation"""
        file_bytes = b"test content"
        filename = "test.pdf"
        mime_type = "application/pdf"
        schema_id = "schema-1"
        metadata_id = "meta-1"
        
        mock_blob_helper = Mock()
        mock_queue_client = Mock()
        mock_repo = Mock()
        mock_repo.add_async = AsyncMock()
        
        content_process_service._blob_helper = mock_blob_helper
        content_process_service._queue_client = mock_queue_client
        content_process_service._process_repo = mock_repo
        
        with patch('services.content_process_service.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread, \
             patch('services.content_process_service.uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value = Mock(hex="123456")
            mock_uuid.return_value.__str__ = Mock(return_value="proc-123")
            
            process_id = await content_process_service.submit(
                file_bytes, filename, mime_type, schema_id, metadata_id
            )
            
            # Verify blob upload was called
            assert mock_to_thread.call_count >= 1
            # Verify Cosmos record was created
            assert mock_repo.add_async.called
            # Verify queue message was sent
            assert mock_to_thread.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_get_status_record_exists(self, content_process_service):
        """Test get_status when record exists"""
        process_id = "proc-123"
        mock_record = Mock()
        mock_record.status = "completed"
        mock_record.processed_file_name = "test.pdf"
        
        mock_repo = Mock()
        mock_repo.get_async = AsyncMock(return_value=mock_record)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.get_status(process_id)
        
        assert result is not None
        assert result["status"] == "completed"
        assert result["process_id"] == process_id
        assert result["file_name"] == "test.pdf"
    
    @pytest.mark.asyncio
    async def test_get_status_record_not_found(self, content_process_service):
        """Test get_status when record does not exist"""
        process_id = "proc-123"
        
        mock_repo = Mock()
        mock_repo.get_async = AsyncMock(return_value=None)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.get_status(process_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_status_defaults_to_processing(self, content_process_service):
        """Test get_status defaults status to 'processing' if None"""
        process_id = "proc-123"
        mock_record = Mock()
        mock_record.status = None
        mock_record.processed_file_name = "test.pdf"
        
        mock_repo = Mock()
        mock_repo.get_async = AsyncMock(return_value=mock_record)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.get_status(process_id)
        
        assert result["status"] == "processing"
    
    @pytest.mark.asyncio
    async def test_get_processed_record_exists(self, content_process_service):
        """Test get_processed when record exists"""
        process_id = "proc-123"
        mock_record = ContentProcessRecord(
            id=process_id,
            process_id=process_id,
            status="completed"
        )
        
        mock_repo = Mock()
        mock_repo.get_async = AsyncMock(return_value=mock_record)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.get_processed(process_id)
        
        assert result is not None
        assert result["id"] == process_id
        assert result["process_id"] == process_id
    
    @pytest.mark.asyncio
    async def test_get_processed_record_not_found(self, content_process_service):
        """Test get_processed when record does not exist"""
        process_id = "proc-123"
        
        mock_repo = Mock()
        mock_repo.get_async = AsyncMock(return_value=None)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.get_processed(process_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_steps_success(self, content_process_service, mock_config):
        """Test get_steps when blob exists"""
        process_id = "proc-123"
        step_data = [{"step": "extract", "status": "completed"}]
        
        mock_blob_helper = Mock()
        content_process_service._blob_helper = mock_blob_helper
        
        with patch('services.content_process_service.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = json.dumps(step_data).encode('utf-8')
            
            result = await content_process_service.get_steps(process_id)
            
            assert result == step_data
    
    @pytest.mark.asyncio
    async def test_get_steps_not_found(self, content_process_service, mock_config):
        """Test get_steps when blob does not exist"""
        process_id = "proc-123"
        
        mock_blob_helper = Mock()
        content_process_service._blob_helper = mock_blob_helper
        
        with patch('services.content_process_service.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = Exception("Blob not found")
            
            result = await content_process_service.get_steps(process_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_poll_status_terminal_state(self, content_process_service):
        """Test poll_status returns immediately on terminal state"""
        process_id = "proc-123"
        
        mock_repo = Mock()
        mock_record = Mock()
        mock_record.status = "Completed"
        mock_record.processed_file_name = "test.pdf"
        mock_repo.get_async = AsyncMock(return_value=mock_record)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.poll_status(
            process_id, 
            poll_interval_seconds=0.1, 
            timeout_seconds=1.0
        )
        
        assert result["status"] == "Completed"
        assert result["terminal"] is True
        assert result["process_id"] == process_id
    
    @pytest.mark.asyncio
    async def test_poll_status_timeout(self, content_process_service):
        """Test poll_status timeout"""
        process_id = "proc-123"
        
        mock_repo = Mock()
        mock_record = Mock()
        mock_record.status = "processing"
        mock_record.processed_file_name = "test.pdf"
        mock_repo.get_async = AsyncMock(return_value=mock_record)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.poll_status(
            process_id, 
            poll_interval_seconds=0.1, 
            timeout_seconds=0.2
        )
        
        assert result["terminal"] is True
        assert result["status"] in ("processing", "Timeout")
    
    @pytest.mark.asyncio
    async def test_poll_status_with_callback(self, content_process_service):
        """Test poll_status with on_poll callback"""
        process_id = "proc-123"
        callback_calls = []
        
        def on_poll_callback(status_dict):
            callback_calls.append(status_dict)
        
        mock_repo = Mock()
        mock_record = Mock()
        mock_record.status = "Completed"
        mock_record.processed_file_name = "test.pdf"
        mock_repo.get_async = AsyncMock(return_value=mock_record)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.poll_status(
            process_id, 
            poll_interval_seconds=0.1,
            on_poll=on_poll_callback
        )
        
        assert len(callback_calls) > 0
        assert result["status"] == "Completed"
    
    @pytest.mark.asyncio
    async def test_poll_status_record_not_found(self, content_process_service):
        """Test poll_status when record does not exist"""
        process_id = "proc-123"
        
        mock_repo = Mock()
        mock_repo.get_async = AsyncMock(return_value=None)
        content_process_service._process_repo = mock_repo
        
        result = await content_process_service.poll_status(process_id)
        
        assert result["status"] == "Failed"
        assert result["terminal"] is True
    
    def test_close(self, content_process_service):
        """Test close method"""
        content_process_service._blob_helper = Mock()
        
        content_process_service.close()
        
        assert content_process_service._blob_helper is None
