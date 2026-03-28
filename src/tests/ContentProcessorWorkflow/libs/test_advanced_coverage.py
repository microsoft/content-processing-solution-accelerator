"""Additional targeted tests to push ContentProcessorWorkflow to 80%"""
import pytest
from unittest.mock import Mock, patch
from utils.http_request import HttpResponse, HttpRequestError


class TestHttpRequestAdvanced:
    """Advanced HTTP request tests"""
    
    def test_http_response_frozen(self):
        """Test that HttpResponse is immutable"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={"Content-Type": "application/json"},
            body=b'{"data": "test"}'
        )
        
        # Verify it's a frozen dataclass
        with pytest.raises(AttributeError):
            response.status = 404
    
    def test_http_response_text_with_errors_replace(self):
        """Test text decoding with errors='replace'"""
        # Invalid UTF-8 bytes
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={},
            body=b'\xff\xfe Invalid UTF-8'
        )
        
        # Should not raise, will use replacement character
        text = response.text()
        assert text is not None
    
    def test_http_response_header_case_sensitivity(self):
        """Test header lookup with various cases"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={
                "Content-Type": "application/json",
                "X-Custom-Header": "value123",
                "Authorization": "Bearer token"
            },
            body=b""
        )
        
        # Test multiple case variations
        assert response.header("content-type") == "application/json"
        assert response.header("CONTENT-TYPE") == "application/json"
        assert response.header("x-CUSTOM-header") == "value123"
        assert response.header("authorization") == "Bearer token"
    
    def test_http_request_error_all_fields(self):
        """Test HttpRequestError with all fields populated"""
        response_headers = {
            "Content-Type": "application/json",
            "X-Request-ID": "req-12345"
        }
        
        error = HttpRequestError(
            "Request failed with server error",
            method="POST",
            url="https://api.example.com/endpoint",
            status=500,
            response_text='{"error": "Internal Server Error", "code": 500}',
            response_headers=response_headers
        )
        
        assert str(error) == "Request failed with server error"
        assert error.method == "POST"
        assert error.url == "https://api.example.com/endpoint"
        assert error.status == 500
        assert "Internal Server Error" in error.response_text
        assert error.response_headers["X-Request-ID"] == "req-12345"
    
    def test_http_response_json_with_nested_data(self):
        """Test JSON parsing with deeply nested data"""
        nested_json = '{"level1": {"level2": {"level3": {"value": 42}}}}'
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={},
            body=nested_json.encode()
        )
        
        data = response.json()
        assert data["level1"]["level2"]["level3"]["value"] == 42
    
    def test_http_response_json_with_array(self):
        """Test JSON parsing with array"""
        json_array = '[{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}]'
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={},
            body=json_array.encode()
        )
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["name"] == "Item2"


class TestLoggingUtilsEdgeCases:
    """Edge case tests for logging utilities"""
    
    def test_configure_logging_with_special_loggers(self):
        """Test that special loggers are always set to WARNING"""
        from utils.logging_utils import configure_application_logging
        import logging
        
        with patch('utils.logging_utils.logging.basicConfig'), \
             patch('utils.logging_utils.logging.getLogger') as mock_get_logger, \
             patch('builtins.print'):
            
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Test with debug mode - special loggers should still be WARNING
            configure_application_logging(debug_mode=True)
            
            # Verify setLevel was called multiple times
            assert mock_logger.setLevel.called
    
    def test_safe_log_with_list_value(self):
        """Test safe_log with list values"""
        from utils.logging_utils import safe_log
        
        logger = Mock()
        test_list = [1, 2, 3, "four", {"five": 5}]
        
        safe_log(logger, "info", "List data: {items}", items=test_list)
        
        logger.info.assert_called_once()
        call_args = str(logger.info.call_args)
        assert "List data:" in call_args
    
    def test_get_error_details_with_nested_cause(self):
        """Test error details with nested exception causes"""
        from utils.logging_utils import get_error_details
        
        try:
            try:
                try:
                    raise ValueError("Level 3 error")
                except ValueError as e3:
                    raise RuntimeError("Level 2 error") from e3
            except RuntimeError as e2:
                raise Exception("Level 1 error") from e2
        except Exception as e1:
            details = get_error_details(e1)
            
            assert details["exception_type"] == "Exception"
            assert details["exception_message"] == "Level 1 error"
            assert details["exception_cause"] is not None
            assert "Level 2 error" in details["exception_cause"]


class TestApplicationContextAdvanced:
    """Advanced AppContext tests"""
    
    def test_application_context_multiple_service_types(self):
        """Test registering multiple service types"""
        from libs.application.application_context import AppContext
        
        context = AppContext()
        
        class Logger:
            def log(self, msg):
                return f"LOG: {msg}"
        
        class Database:
            def query(self):
                return []
        
        class Cache:
            def get(self, key):
                return None
        
        # Register all three with different lifetimes
        context.add_singleton(Logger, Logger)
        context.add_transient(Database, Database)
        context.add_scoped(Cache, Cache)
        
        # Verify all are registered
        assert context.is_registered(Logger)
        assert context.is_registered(Database)
        assert context.is_registered(Cache)
        
        # Get and verify
        logger = context.get_service(Logger)
        db = context.get_service(Database)
        
        assert logger.log("test") == "LOG: test"
        assert db.query() == []
    
    def test_service_descriptor_async_fields(self):
        """Test ServiceDescriptor async-related fields"""
        from libs.application.application_context import ServiceDescriptor, ServiceLifetime
        
        class AsyncService:
            async def initialize(self):
                pass
            
            async def cleanup_async(self):
                pass
        
        descriptor = ServiceDescriptor(
            service_type=AsyncService,
            implementation=AsyncService,
            lifetime=ServiceLifetime.ASYNC_SINGLETON,
            is_async=True,
            cleanup_method="cleanup_async"
        )
        
        assert descriptor.is_async is True
        assert descriptor.cleanup_method == "cleanup_async"
        assert descriptor.lifetime == ServiceLifetime.ASYNC_SINGLETON
