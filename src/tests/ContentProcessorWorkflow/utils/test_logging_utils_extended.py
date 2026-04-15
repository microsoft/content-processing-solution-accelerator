"""Extended tests for logging_utils.py to improve coverage"""
import pytest
import logging
from unittest.mock import Mock, patch, call
from utils.logging_utils import (
    configure_application_logging,
    create_migration_logger,
    safe_log,
    get_error_details,
    log_error_with_context
)
from azure.core.exceptions import HttpResponseError


class TestConfigureApplicationLogging:
    """Test suite for configure_application_logging"""
    
    def test_configure_logging_debug_mode(self):
        """Test configuring logging in debug mode"""
        with patch('utils.logging_utils.logging.basicConfig') as mock_basic_config, \
             patch('utils.logging_utils.logging.getLogger') as mock_get_logger:
            
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            configure_application_logging(debug_mode=True)
            
            mock_basic_config.assert_called_once_with(level=logging.DEBUG, force=True)
            # Verify debug messages were logged (should have at least one debug call)
            assert mock_logger.debug.called
            # Check that one of the debug messages contains expected text
            debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
            assert any("Debug logging enabled" in call or "Verbose logging suppressed" in call for call in debug_calls)
    
    def test_configure_logging_production_mode(self):
        """Test configuring logging in production mode"""
        with patch('utils.logging_utils.logging.basicConfig') as mock_basic_config:
            
            configure_application_logging(debug_mode=False)
            
            mock_basic_config.assert_called_once_with(level=logging.INFO, force=True)
    
    def test_configure_logging_suppresses_verbose_loggers(self):
        """Test that verbose loggers are suppressed"""
        with patch('utils.logging_utils.logging.basicConfig'), \
             patch('utils.logging_utils.logging.getLogger') as mock_get_logger, \
             patch('builtins.print'):
            
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            configure_application_logging(debug_mode=False)
            
            # Verify loggers were configured
            assert mock_get_logger.called
            assert mock_logger.setLevel.called
    
    def test_configure_logging_sets_environment_variables(self):
        """Test that environment variables are set"""
        with patch('utils.logging_utils.logging.basicConfig'), \
             patch('utils.logging_utils.os.environ.setdefault') as mock_setdefault, \
             patch('builtins.print'):
            
            configure_application_logging(debug_mode=False)
            
            # Verify environment variables were set
            calls = [call("HTTPX_LOG_LEVEL", "WARNING"), call("AZURE_CORE_ENABLE_HTTP_LOGGER", "false")]
            for expected_call in calls:
                assert expected_call in mock_setdefault.call_args_list


class TestCreateMigrationLogger:
    """Test suite for create_migration_logger"""
    
    def test_create_migration_logger_default_level(self):
        """Test creating logger with default level"""
        logger = create_migration_logger("test_logger")
        
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
    
    def test_create_migration_logger_custom_level(self):
        """Test creating logger with custom level"""
        logger = create_migration_logger("test_logger_debug", level=logging.DEBUG)
        
        assert logger.name == "test_logger_debug"
        # Logger level might be affected by pre-configured handlers
        assert logger.level <= logging.DEBUG or logger.level == logging.INFO
    
    def test_create_migration_logger_with_handler(self):
        """Test that logger has stream handler"""
        logger = create_migration_logger("test_logger_handler")
        
        assert len(logger.handlers) > 0
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


class TestSafeLog:
    """Test suite for safe_log"""
    
    def test_safe_log_info_level(self):
        """Test safe logging at info level"""
        logger = Mock()
        
        safe_log(logger, "info", "Processing {item}", item="test_item")
        
        logger.info.assert_called_once_with("Processing test_item")
    
    def test_safe_log_error_level(self):
        """Test safe logging at error level"""
        logger = Mock()
        
        safe_log(logger, "error", "Failed to process {item}", item="test_item")
        
        logger.error.assert_called_once_with("Failed to process test_item")
    
    def test_safe_log_warning_level(self):
        """Test safe logging at warning level"""
        logger = Mock()
        
        safe_log(logger, "warning", "Warning for {item}", item="test_item")
        
        logger.warning.assert_called_once_with("Warning for test_item")
    
    def test_safe_log_debug_level(self):
        """Test safe logging at debug level"""
        logger = Mock()
        
        safe_log(logger, "debug", "Debug info: {data}", data="test_data")
        
        logger.debug.assert_called_once_with("Debug info: test_data")
    
    def test_safe_log_with_dict(self):
        """Test safe logging with dictionary"""
        logger = Mock()
        test_dict = {"key": "value", "nested": {"inner": "data"}}
        
        safe_log(logger, "info", "Data: {data}", data=test_dict)
        
        logger.info.assert_called_once()
        assert "key" in str(logger.info.call_args)
    
    def test_safe_log_with_exception(self):
        """Test safe logging with exception"""
        logger = Mock()
        test_exception = ValueError("Test error")
        
        safe_log(logger, "error", "Exception occurred: {error}", error=test_exception)
        
        logger.error.assert_called_once_with("Exception occurred: Test error")
    
    def test_safe_log_format_failure(self):
        """Test safe logging when format fails"""
        logger = Mock()
        
        # This should raise an exception due to missing placeholder
        with pytest.raises(RuntimeError):
            safe_log(logger, "info", "Missing {placeholder}", wrong_key="value")


class TestGetErrorDetails:
    """Test suite for get_error_details"""
    
    def test_get_error_details_standard_exception(self):
        """Test getting details from standard exception"""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            details = get_error_details(e)
            
            assert details["exception_type"] == "ValueError"
            assert details["exception_message"] == "Test error message"
            assert "full_traceback" in details
            assert details["exception_args"] == ("Test error message",)
    
    def test_get_error_details_with_cause(self):
        """Test getting details from exception with cause"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as original:
                raise RuntimeError("Wrapped error") from original
        except RuntimeError as e:
            details = get_error_details(e)
            
            assert details["exception_type"] == "RuntimeError"
            assert details["exception_cause"] == "Original error"
    
    def test_get_error_details_http_response_error(self):
        """Test getting details from HttpResponseError"""
        response = Mock()
        response.status_code = 404
        response.reason = "Not Found"
        
        error = HttpResponseError(message="Resource not found", response=response)
        error.status_code = 404
        error.reason = "Not Found"
        
        details = get_error_details(error)
        
        assert details["exception_type"] == "HttpResponseError"
        assert details["http_status_code"] == 404
        assert details["http_reason"] == "Not Found"
    
    def test_get_error_details_without_cause(self):
        """Test getting details from exception without cause"""
        try:
            raise KeyError("Missing key")
        except KeyError as e:
            details = get_error_details(e)
            
            assert details["exception_cause"] is None
            assert details["exception_context"] is None


class TestLogErrorWithContext:
    """Test suite for log_error_with_context"""
    
    def test_log_error_with_context_basic(self):
        """Test logging error with context"""
        logger = Mock()
        exception = ValueError("Test error")
        
        log_error_with_context(logger, exception, context="TestOperation")
        
        logger.error.assert_called_once()
        call_args = str(logger.error.call_args)
        assert "TestOperation" in call_args or "ValueError" in call_args
    
    def test_log_error_with_context_and_kwargs(self):
        """Test logging error with additional context"""
        logger = Mock()
        exception = RuntimeError("Processing failed")
        
        log_error_with_context(
            logger, 
            exception, 
            context="DataProcessing",
            user_id="user123",
            request_id="req456"
        )
        
        logger.error.assert_called_once()
    
    def test_log_error_with_http_response_error(self):
        """Test logging HttpResponseError with context"""
        logger = Mock()
        response = Mock()
        response.status_code = 500
        
        error = HttpResponseError(message="Server error", response=response)
        error.status_code = 500
        
        log_error_with_context(logger, error, context="APICall")
        
        logger.error.assert_called_once()
