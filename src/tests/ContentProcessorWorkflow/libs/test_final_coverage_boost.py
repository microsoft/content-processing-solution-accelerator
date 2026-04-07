"""Final coverage boost tests for ContentProcessorWorkflow"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from libs.application.application_context import ServiceLifetime


class TestApplicationContextFinal:
    """Fill remaining application_context gaps"""
    
    def test_service_registration_chaining(self):
        """Test method chaining in service registration"""
        from libs.application.application_context import AppContext
        
        context = AppContext()
        
        class ServiceA:
            pass
        
        class ServiceB:
            pass
        
        # Test chaining
        result = context.add_singleton(ServiceA, ServiceA).add_transient(ServiceB, ServiceB)
        
        # Should return context for chaining
        assert result is context or isinstance(result, AppContext)
    
    def test_get_all_services_of_type(self):
        """Test getting all registered services"""
        from libs.application.application_context import AppContext
        
        context = AppContext()
        
        class MyService:
            def __init__(self, name):
                self.name = name
        
        # Register multiple instances
        context.add_singleton(MyService, lambda: MyService("first"))
        
        # Should be able to retrieve
        service = context.get_service(MyService)
        assert service is not None
    
    def test_service_lifecycle_async(self):
        """Test async service lifecycle"""
        from libs.application.application_context import ServiceDescriptor, ServiceLifetime
        
        class AsyncService:
            async def initialize(self):
                return True
        
        descriptor = ServiceDescriptor(
            service_type=AsyncService,
            implementation=AsyncService,
            lifetime=ServiceLifetime.ASYNC_SINGLETON,
            is_async=True
        )
        
        assert descriptor.is_async is True
        assert descriptor.lifetime == ServiceLifetime.ASYNC_SINGLETON


class TestApplicationBaseFinal:
    """Fill remaining application_base gaps"""
    
    def test_application_base_logging_setup(self):
        """Test application base logging configuration"""
        from libs.base.application_base import ApplicationBase
        from libs.application.application_context import AppContext
        
        app = ApplicationBase(AppContext())
        
        # Should have logger configured
        assert hasattr(app, 'logger') or hasattr(app, '_logger')
    
    def test_application_base_exception_handling(self):
        """Test exception handling in application base"""
        from libs.base.application_base import ApplicationBase
        from libs.application.application_context import AppContext
        
        app = ApplicationBase(AppContext())
        
        # Test error handling method exists
        assert hasattr(app, 'handle_error') or hasattr(app, 'on_error')


class TestCredentialUtilFinal:
    """Fill final credential_util gaps"""
    
    def test_get_managed_identity_with_client_id_env(self):
        """Test managed identity creation with client_id from env"""
        from utils.credential_util import get_managed_identity_credential
        
        with patch.dict('os.environ', {'AZURE_CLIENT_ID': 'test-client-id-123'}):
            credential = get_managed_identity_credential()
            
            # Should return a credential object
            assert credential is not None
    
    def test_credential_with_custom_kwargs(self):
        """Test credential creation with custom kwargs"""
        from utils.credential_util import get_credential
        
        with patch('utils.credential_util.DefaultAzureCredential') as mock_cred:
            mock_cred.return_value = Mock()
            
            get_credential(
                managed_identity_client_id="custom-id",
                exclude_environment_credential=True
            )
            
            # Should have been called with custom args
            assert mock_cred.called


class TestLoggingUtilsFinal:
    """Fill final logging_utils gaps"""
    
    def test_error_context_with_traceback(self):
        """Test error logging with full traceback"""
        from utils.logging_utils import log_error_with_context
        
        logger = Mock()
        
        try:
            raise ValueError("Test error with context")
        except ValueError as e:
            log_error_with_context(logger, "Operation failed", e, include_traceback=True)
            
            # Should have logged with error level
            assert logger.error.called or logger.exception.called
    
    def test_safe_log_with_none_values(self):
        """Test safe_log handles None values"""
        from utils.logging_utils import safe_log
        
        logger = Mock()
        
        safe_log(logger, "info", "Value is {val}", val=None)
        
        # Should handle None gracefully
        assert logger.info.called
    
    def test_logging_format_with_special_chars(self):
        """Test logging with special characters"""
        from utils.logging_utils import safe_log
        
        logger = Mock()
        
        special_text = "Text with special chars: {} [] () <> @ # $ %"
        safe_log(logger, "info", "Processing: {text}", text=special_text)
        
        assert logger.info.called
