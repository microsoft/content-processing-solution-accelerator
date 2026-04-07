"""Simple HTTP request tests to push coverage over 80%"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from utils.http_request import HttpResponse, HttpRequestError, _join_url, _parse_retry_after_seconds


class TestHttpRequestSimple:
    """Simple tests for easy http_request coverage wins"""
    
    def test_http_response_properties(self):
        """Test HttpResponse basic properties"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com/data",
            headers={"Content-Type": "application/json", "X-Request-ID": "123"},
            body=b'{"result": "success"}'
        )
        
        # Test all properties
        assert response.status == 200
        assert response.url == "https://api.example.com/data"
        assert response.headers["Content-Type"] == "application/json"
        assert response.body == b'{"result": "success"}'
        
        # Test header() method
        assert response.header("content-type") == "application/json"
        assert response.header("x-request-id") == "123"
        assert response.header("missing-header") is None
        
        # Test text() method
        text = response.text()
        assert "success" in text
        
        # Test json() method
        json_data = response.json()
        assert json_data["result"] == "success"
    
    def test_http_request_error_creation(self):
        """Test HttpRequestError with all fields"""
        error = HttpRequestError(
            "Request failed",
            method="POST",
            url="https://api.example.com/endpoint",
            status=500,
            response_text='{"error": "Internal Server Error"}',
            response_headers={"Content-Type": "application/json"}
        )
        
        assert str(error) == "Request failed"
        assert error.method == "POST"
        assert error.url == "https://api.example.com/endpoint"
        assert error.status == 500
        assert "Internal Server Error" in error.response_text
    
    def test_join_url_variations(self):
        """Test _join_url with various inputs"""
        # Basic join
        result = _join_url("https://api.example.com", "users")
        assert result == "https://api.example.com/users"
        
        # Base withtrailing slash
        result = _join_url("https://api.example.com/", "users")
        assert result == "https://api.example.com/users"
        
        # Path with leading slash
        result = _join_url("https://api.example.com", "/users")
        assert result == "https://api.example.com/users"
        
        # Both with slashes
        result = _join_url("https://api.example.com/", "/users")
        assert result == "https://api.example.com/users"
        
        # Multiple segments
        result = _join_url("https://api.example.com", "v1", "users", "123")
        assert result == "https://api.example.com/v1/users/123"
        
        # Empty segments
        result = _join_url("https://api.example.com", "")
        assert result == "https://api.example.com/"
    
    def test_parse_retry_after_numeric(self):
        """Test parsing Retry-After with numeric seconds"""
        # Integer string
        result = _parse_retry_after_seconds("120")
        assert result == 120
        
        # Different value
        result = _parse_retry_after_seconds("60")
        assert result == 60
        
        # Zero
        result = _parse_retry_after_seconds("0")
        assert result == 0
    
    def test_parse_retry_after_invalid(self):
        """Test parsing invalid Retry-After values"""
        # Invalid format
        result = _parse_retry_after_seconds("invalid")
        assert result is None
        
        # Empty string
        result = _parse_retry_after_seconds("")
        assert result is None
        
        # None
        result = _parse_retry_after_seconds(None)
        assert result is None
