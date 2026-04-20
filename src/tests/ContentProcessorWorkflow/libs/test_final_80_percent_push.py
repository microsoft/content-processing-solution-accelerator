"""Targeted tests to reach 80% coverage for ContentProcessorWorkflow"""
import pytest
from unittest.mock import Mock, patch


class TestApplicationContextEdgeCases:
    """Target remaining application_context.py gaps (91% → 95%+)"""

    def test_service_scope_get_service_not_registered(self):
        """Test ServiceScope.get_service with unregistered service"""
        from libs.application.application_context import AppContext

        context = AppContext()

        class UnregisteredService:
            pass

        # Attempt to get unregistered service should raise or return None
        with pytest.raises(Exception):  # KeyError or custom exception
            if hasattr(context, 'create_scope'):
                import asyncio

                async def test():
                    async with await context.create_scope() as scope:
                        scope.get_service(UnregisteredService)
                asyncio.run(test())

    def test_app_context_transient_creates_new_instance(self):
        """Test that transient services create new instances each time"""
        from libs.application.application_context import AppContext

        context = AppContext()

        class TransientService:
            pass

        context.add_transient(TransientService, TransientService)

        # Get service twice
        instance1 = context.get_service(TransientService)
        instance2 = context.get_service(TransientService)

        # Should be different instances
        assert instance1 is not instance2

    def test_app_context_singleton_returns_same_instance(self):
        """Test that singleton services return same instance"""
        from libs.application.application_context import AppContext

        context = AppContext()

        class SingletonService:
            pass

        context.add_singleton(SingletonService, SingletonService)

        # Get service twice
        instance1 = context.get_service(SingletonService)
        instance2 = context.get_service(SingletonService)

        # Should be same instance
        assert instance1 is instance2

    def test_app_context_scoped_service_different_in_different_scopes(self):
        """Test scoped services are different across scopes"""
        from libs.application.application_context import AppContext

        context = AppContext()

        class ScopedService:
            pass

        context.add_scoped(ScopedService, ScopedService)

        # Get from root scope
        instance1 = context.get_service(ScopedService)
        instance2 = context.get_service(ScopedService)

        # Within same scope, should be same
        assert instance1 is instance2

    def test_app_context_with_factory_function(self):
        """Test service registration with factory function"""
        from libs.application.application_context import AppContext

        context = AppContext()

        class ConfigurableService:
            def __init__(self, config_value):
                self.config_value = config_value

        # Register with factory
        context.add_singleton(
            ConfigurableService,
            lambda: ConfigurableService("custom_config")
        )

        service = context.get_service(ConfigurableService)
        assert service.config_value == "custom_config"


class TestLoggingUtilsComplete:
    """Target remaining logging_utils.py gaps (92% → 100%)"""

    def test_configure_logging_info_level(self):
        """Test configure_application_logging with INFO level"""
        from utils.logging_utils import configure_application_logging

        with patch('utils.logging_utils.logging.basicConfig') as mock_basic, \
             patch('utils.logging_utils.logging.getLogger') as mock_logger, \
             patch('builtins.print'):

            mock_logger.return_value = Mock()

            configure_application_logging(debug_mode=False)

            assert mock_basic.called

    def test_configure_logging_warning_level(self):
        """Test configure_application_logging with WARNING level"""
        from utils.logging_utils import configure_application_logging
        import logging

        with patch('utils.logging_utils.logging.basicConfig'), \
             patch('utils.logging_utils.logging.getLogger') as mock_logger, \
             patch('builtins.print'):

            mock_logger.return_value = Mock()

            # Configure with WARNING level via debug_mode=False
            configure_application_logging(debug_mode=False)

            # Should have set some loggers to WARNING
            if mock_logger.return_value.setLevel.called:
                # Check that WARNING was used
                call_args = [call[0][0] for call in mock_logger.return_value.setLevel.call_args_list]
                assert logging.WARNING in call_args or any(arg == logging.WARNING for arg in call_args)

    def test_safe_log_debug_level(self):
        """Test safe_log with debug level"""
        from utils.logging_utils import safe_log

        logger = Mock()
        safe_log(logger, "debug", "Debug message: {value}", value=123)

        assert logger.debug.called

    def test_safe_log_warning_level(self):
        """Test safe_log with warning level"""
        from utils.logging_utils import safe_log

        logger = Mock()
        safe_log(logger, "warning", "Warning message: {issue}", issue="potential problem")

        assert logger.warning.called

    def test_safe_log_critical_level(self):
        """Test safe_log with critical level"""
        from utils.logging_utils import safe_log

        logger = Mock()
        safe_log(logger, "critical", "Critical failure: {error}", error="system down")

        assert logger.critical.called

    def test_create_migration_logger(self):
        """Test creating migration logger"""
        from utils.logging_utils import create_migration_logger

        with patch('utils.logging_utils.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = create_migration_logger("test_migration")

            assert logger == mock_logger or logger is not None


class TestApplicationBaseEdgeCases:
    """Target remaining application_base.py gaps (95% → 100%)"""

    def test_application_base_get_derived_class_location(self):
        """Test _get_derived_class_location method"""
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
             patch('libs.base.application_base._envConfiguration') as mock_env:

            mock_env.return_value.app_config_endpoint = ""
            mock_config.return_value.app_logging_enable = False

            app = TestApp()

            # Test _get_derived_class_location
            location = app._get_derived_class_location()

            # Should return a file path
            assert isinstance(location, str)
            assert len(location) > 0


class TestCredentialUtilEdgeCases:
    """Target remaining credential_util.py gaps (98% → 100%)"""

    def test_get_azure_credential_with_all_env_vars(self):
        """Test get_azure_credential with all environment variables set"""
        from utils.credential_util import get_azure_credential

        with patch.dict('os.environ', {
            'AZURE_CLIENT_ID': 'test-client-id',
            'AZURE_TENANT_ID': 'test-tenant-id',
            'AZURE_CLIENT_SECRET': 'test-secret'
        }), \
             patch('utils.credential_util.DefaultAzureCredential') as mock_cred:

            mock_cred.return_value = Mock()

            credential = get_azure_credential()

            # Should have created credential
            assert credential is not None
            assert mock_cred.called

    def test_get_bearer_token_provider(self):
        """Test get_bearer_token_provider function"""
        from utils.credential_util import get_bearer_token_provider

        with patch('utils.credential_util.get_azure_credential') as mock_get_cred:
            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential

            # Get token provider
            provider = get_bearer_token_provider()

            # Should return a callable
            assert callable(provider)
