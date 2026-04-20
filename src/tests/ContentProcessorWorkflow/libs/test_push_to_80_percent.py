"""Targeted tests to push ContentProcessorWorkflow from 78% to 80%"""
from unittest.mock import Mock, patch
import logging


class TestApplicationBaseComplete:
    """Complete coverage for application_base.py (95% → 100%)"""

    def test_application_base_with_explicit_env_path(self):
        """Test ApplicationBase with explicit env file path"""
        from libs.base.application_base import ApplicationBase

        class TestApp(ApplicationBase):
            def initialize(self):
                pass

            def run(self):
                pass

        with patch('libs.base.application_base.load_dotenv') as mock_load_dotenv, \
             patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.Configuration'), \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('libs.base.application_base._envConfiguration') as mock_env_config:

            mock_env_config.return_value.app_config_endpoint = ""

            # Test with explicit path
            _app = TestApp(env_file_path="/custom/path/.env")

            # Should have loaded from explicit path
            mock_load_dotenv.assert_called_with(dotenv_path="/custom/path/.env")

    def test_application_base_with_app_config(self):
        """Test ApplicationBase with Azure App Configuration"""
        from libs.base.application_base import ApplicationBase

        class TestApp(ApplicationBase):
            def initialize(self):
                pass

            def run(self):
                pass

        with patch('libs.base.application_base.load_dotenv'), \
             patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.Configuration') as mock_config, \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('libs.base.application_base._envConfiguration') as mock_env_config, \
             patch('libs.base.application_base.AppConfigurationHelper') as mock_app_config:

            # Set app_config_endpoint to non-empty value
            mock_env_config.return_value.app_config_endpoint = "https://myconfig.azconfig.io"
            mock_config.return_value.app_logging_enable = False

            _app = TestApp()

            # Should have created AppConfigurationHelper
            assert mock_app_config.called
            assert mock_app_config.return_value.read_and_set_environmental_variables.called

    def test_application_base_with_logging_enabled(self):
        """Test ApplicationBase with logging enabled"""
        from libs.base.application_base import ApplicationBase

        class TestApp(ApplicationBase):
            def initialize(self):
                pass

            def run(self):
                pass

        with patch('libs.base.application_base.load_dotenv'), \
             patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.Configuration') as mock_config, \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('libs.base.application_base._envConfiguration') as mock_env_config, \
             patch('libs.base.application_base.logging.basicConfig') as mock_logging:

            mock_env_config.return_value.app_config_endpoint = ""

            # Enable logging
            config_instance = Mock()
            config_instance.app_logging_enable = True
            config_instance.app_logging_level = "DEBUG"
            mock_config.return_value = config_instance

            _app = TestApp()

            # Should have configured logging
            mock_logging.assert_called_once()
            call_level = mock_logging.call_args[1]['level']
            assert call_level == logging.DEBUG


class TestCredentialUtilComplete:
    """Complete coverage for credential_util.py (98% → 100%)"""

    def test_validate_azure_authentication_local_dev(self):
        """Test validate_azure_authentication for local development"""
        from utils.credential_util import validate_azure_authentication

        with patch.dict('os.environ', {}, clear=True), \
             patch('utils.credential_util.get_azure_credential') as mock_get_cred:

            mock_get_cred.return_value = Mock()

            result = validate_azure_authentication()

            assert result["environment"] == "local_development"
            assert result["credential_type"] == "cli_credentials"
            assert result["status"] == "configured"
            assert len(result["recommendations"]) > 0

    def test_validate_azure_authentication_azure_hosted(self):
        """Test validate_azure_authentication for Azure-hosted environment"""
        from utils.credential_util import validate_azure_authentication

        with patch.dict('os.environ', {
            'WEBSITE_SITE_NAME': 'my-webapp',
            'MSI_ENDPOINT': 'http://localhost:8081/msi/token'
        }), \
             patch('utils.credential_util.get_azure_credential') as mock_get_cred:

            mock_get_cred.return_value = Mock()

            result = validate_azure_authentication()

            assert result["environment"] == "azure_hosted"
            assert result["credential_type"] == "managed_identity"
            assert "WEBSITE_SITE_NAME" in result["azure_env_indicators"]
            assert result["status"] == "configured"

    def test_validate_azure_authentication_with_client_id(self):
        """Test validate_azure_authentication with user-assigned managed identity"""
        from utils.credential_util import validate_azure_authentication

        with patch.dict('os.environ', {
            'AZURE_CLIENT_ID': 'client-id-123',
            'IDENTITY_ENDPOINT': 'http://localhost:8081/token'
        }), \
             patch('utils.credential_util.get_azure_credential') as mock_get_cred:

            mock_get_cred.return_value = Mock()

            result = validate_azure_authentication()

            assert result["environment"] == "azure_hosted"
            assert "user-assigned" in str(result["recommendations"])

    def test_validate_azure_authentication_error(self):
        """Test validate_azure_authentication with error"""
        from utils.credential_util import validate_azure_authentication

        with patch.dict('os.environ', {}, clear=True), \
             patch('utils.credential_util.get_azure_credential') as mock_get_cred:

            mock_get_cred.side_effect = Exception("Authentication failed")

            result = validate_azure_authentication()

            assert result["status"] == "error"
            assert "error" in result
            assert "Authentication failed" in result["error"]


class TestApplicationContextAdvanced:
    """Advanced tests for application_context.py to fill remaining gaps"""

    def test_app_context_async_scope_lifecycle(self):
        """Test async scope creation and cleanup"""
        from libs.application.application_context import AppContext
        import asyncio

        async def test_async():
            context = AppContext()

            class AsyncService:
                async def initialize(self):
                    return "initialized"

            # Register async scoped service
            context.add_async_scoped(AsyncService, AsyncService)

            # Create scope
            async with await context.create_scope() as scope:
                # Get service from scope
                service = await scope.get_service_async(AsyncService)
                assert service is not None

        asyncio.run(test_async())

    def test_app_context_get_registered_services(self):
        """Test getting all registered services"""
        from libs.application.application_context import AppContext

        context = AppContext()

        class ServiceA:
            pass

        class ServiceB:
            pass

        context.add_singleton(ServiceA, ServiceA)
        context.add_transient(ServiceB, ServiceB)

        # Get all registered services
        registered = context.get_registered_services()

        assert ServiceA in registered
        assert ServiceB in registered
        assert isinstance(registered, dict)

    def test_app_context_is_registered(self):
        """Test checking if service is registered"""
        from libs.application.application_context import AppContext

        context = AppContext()

        class RegisteredService:
            pass

        class UnregisteredService:
            pass

        context.add_singleton(RegisteredService, RegisteredService)

        assert context.is_registered(RegisteredService) is True
        assert context.is_registered(UnregisteredService) is False

    def test_app_context_async_singleton_lifecycle(self):
        """Test async singleton lifecycle with cleanup"""
        from libs.application.application_context import AppContext
        import asyncio

        async def test_async():
            context = AppContext()

            class AsyncSingletonService:
                def __init__(self):
                    self.initialized = False
                    self.cleaned_up = False

                async def initialize(self):
                    self.initialized = True
                    return self

                async def cleanup(self):
                    self.cleaned_up = True

            # Register with cleanup method
            context.add_async_singleton(
                AsyncSingletonService,
                AsyncSingletonService,
                cleanup_method="cleanup"
            )

            # Get service - should initialize
            service = await context.get_service_async(AsyncSingletonService)
            assert service.initialized is True

            # Cleanup
            await context.shutdown_async()

        asyncio.run(test_async())


class TestLoggingUtilsEdgeCases:
    """Edge cases for logging_utils.py to close remaining gaps"""

    def test_configure_logging_with_file_handler(self):
        """Test logging configuration with file output"""
        from utils.logging_utils import configure_application_logging

        with patch('utils.logging_utils.logging.basicConfig') as mock_basic, \
             patch('utils.logging_utils.logging.getLogger') as mock_get_logger, \
             patch('builtins.print'):

            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Configure with file output
            configure_application_logging(
                debug_mode=False,
                log_file="app.log",
                log_level="INFO"
            )

            # Should have configured logging
            assert mock_basic.called

    def test_safe_log_with_exception_object(self):
        """Test safe_log with exception object as parameter"""
        from utils.logging_utils import safe_log

        logger = Mock()

        try:
            raise ValueError("Test exception with context")
        except ValueError as e:
            safe_log(logger, "error", "Error occurred: {exc}", exc=e)

            assert logger.error.called

    def test_log_error_with_context_and_extra_data(self):
        """Test error logging with extra context data"""
        from utils.logging_utils import log_error_with_context

        logger = Mock()

        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError as e:
            log_error_with_context(
                logger,
                "Operation failed",
                e,
                extra_context={"operation": "data_processing", "record_id": 123}
            )

            assert logger.error.called or logger.exception.called

    def test_get_error_details_with_traceback(self):
        """Test error details extraction with full traceback"""
        from utils.logging_utils import get_error_details

        try:
            # Create nested exception chain
            try:
                raise ValueError("Inner error")
            except ValueError as inner:
                raise RuntimeError("Outer error") from inner
        except RuntimeError as outer:
            details = get_error_details(outer)

            assert "exception_type" in details
            assert "exception_message" in details
            assert "full_traceback" in details  # The actual key name
            assert details["exception_type"] == "RuntimeError"
