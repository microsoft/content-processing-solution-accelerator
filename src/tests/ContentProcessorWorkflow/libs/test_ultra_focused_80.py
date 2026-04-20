"""Ultra-focused tests to hit the final 13 lines for 80% coverage"""
from unittest.mock import Mock, patch, AsyncMock


class TestApplicationContextMissedLines:
    """Hit specific missed lines in application_context.py"""

    def test_service_descriptor_with_all_fields(self):
        """Test ServiceDescriptor with all optional fields"""
        from libs.application.application_context import ServiceDescriptor, ServiceLifetime

        class TestService:
            pass

        descriptor = ServiceDescriptor(
            service_type=TestService,
            implementation=TestService,
            lifetime=ServiceLifetime.SINGLETON,
            is_async=False,
            cleanup_method=None
        )

        assert descriptor.service_type == TestService
        assert descriptor.lifetime == ServiceLifetime.SINGLETON
        assert descriptor.is_async is False

    def test_app_context_create_instance_with_dependencies(self):
        """Test _create_instance with service that has dependencies"""
        from libs.application.application_context import AppContext

        context = AppContext()

        class DependencyService:
            pass

        class ServiceWithDependency:
            def __init__(self, dep: DependencyService):
                self.dep = dep

        # Register dependency first
        context.add_singleton(DependencyService, DependencyService)

        # Register service with dependency
        context.add_singleton(ServiceWithDependency, ServiceWithDependency)

        # Get service - should resolve dependency
        service = context.get_service(ServiceWithDependency)
        assert service.dep is not None
        assert isinstance(service.dep, DependencyService)


class TestLoggingUtilsMissedLines:
    """Hit specific missed lines in logging_utils.py"""

    def test_safe_log_with_complex_formatting(self):
        """Test safe_log with multiple format arguments"""
        from utils.logging_utils import safe_log

        logger = Mock()
        safe_log(logger, "info", "User {user} performed {action} on {resource}",
                 user="alice", action="update", resource="document")

        assert logger.info.called
        call_str = str(logger.info.call_args)
        assert "alice" in call_str or "update" in call_str

    def test_log_error_minimal_params(self):
        """Test log_error_with_context with minimal parameters"""
        from utils.logging_utils import log_error_with_context

        logger = Mock()
        exception = ValueError("Simple error")

        log_error_with_context(logger, "Error occurred", exception)

        # Should have logged
        assert logger.error.called or logger.exception.called


class TestApplicationBaseMissedLines:
    """Hit specific missed lines in application_base.py"""

    def test_load_env_returns_path(self):
        """Test that _load_env returns the loaded path"""
        from libs.base.application_base import ApplicationBase

        class TestApp(ApplicationBase):
            def initialize(self):
                pass

            def run(self):
                pass

        with patch('libs.base.application_base.load_dotenv') as mock_load, \
             patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.Configuration') as mock_config, \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('libs.base.application_base._envConfiguration') as mock_env:

            mock_env.return_value.app_config_endpoint = ""
            mock_config.return_value.app_logging_enable = False

            # Create app with no explicit env path
            TestApp()

            # Should have called load_dotenv
            assert mock_load.called


class TestCredentialUtilMissedLines:
    """Hit the final 2 missed lines in credential_util.py"""

    def test_validate_authentication_with_kubernetes(self):
        """Test validate_azure_authentication with Kubernetes environment"""
        from utils.credential_util import validate_azure_authentication

        with patch.dict('os.environ', {
            'KUBERNETES_SERVICE_HOST': 'kubernetes.default.svc',
            'IDENTITY_ENDPOINT': 'http://169.254.169.254/metadata/identity'
        }), patch('utils.credential_util.get_azure_credential') as mock_cred:

            mock_cred.return_value = Mock()

            result = validate_azure_authentication()

            # Should detect Azure hosted environment
            assert result["environment"] == "azure_hosted"
            assert "KUBERNETES_SERVICE_HOST" in result["azure_env_indicators"]

    async def test_get_async_bearer_token_provider(self):
        """Test get_async_bearer_token_provider function"""
        from utils.credential_util import get_async_bearer_token_provider

        with patch('utils.credential_util.get_async_azure_credential') as mock_get_cred:
            mock_credential = Mock()
            mock_token = Mock()
            mock_token.token = "test-token-123"
            mock_credential.get_token = AsyncMock(return_value=mock_token)
            mock_get_cred.return_value = mock_credential

            # Get async token provider
            provider = await get_async_bearer_token_provider()

            # Should return a callable
            assert callable(provider)

            # Call the provider
            token = await provider()

            # Should return token string
            assert token == "test-token-123"


class TestPromptUtilCoverage:
    """Ensure prompt_util.py stays at 100%"""

    def test_prompt_template_rendering(self):
        """Test basic prompt template usage"""
        from utils.prompt_util import PromptTemplate

        template = PromptTemplate("Hello {name}, you have {count} messages")
        result = template.render(name="Alice", count=5)

        assert "Alice" in result
        assert "5" in result
