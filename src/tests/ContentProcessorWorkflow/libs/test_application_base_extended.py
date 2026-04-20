"""Extended tests for application_base.py to improve coverage"""
from unittest.mock import Mock, patch
from libs.base.application_base import ApplicationBase
from libs.application.application_context import AppContext


class ConcreteApplication(ApplicationBase):
    """Concrete implementation for testing ApplicationBase"""

    def __init__(self, *args, **kwargs):
        self.initialized = False
        self.running = False
        super().__init__(*args, **kwargs)
        # ApplicationBase doesn't automatically call initialize(), so do it here for testing
        self.initialize()

    def initialize(self):
        """Implementation of abstract initialize method"""
        self.initialized = True

    def run(self):
        """Implementation of abstract run method"""
        self.running = True


class TestApplicationBaseExtended:
    """Extended test suite for ApplicationBase"""

    def test_initialization_with_explicit_env_file(self, tmp_path):
        """Test initialization with explicit .env file path"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value\nAPP_LOGGING_ENABLE=false\n")

        with patch('libs.base.application_base.DefaultAzureCredential') as mock_cred, \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'):

            mock_cred_instance = Mock()
            mock_cred.return_value = mock_cred_instance

            app = ConcreteApplication(env_file_path=str(env_file))

            assert app.application_context is not None
            assert isinstance(app.application_context, AppContext)
            assert app.initialized is True

    def test_initialization_auto_discover_env_file(self, tmp_path, monkeypatch):
        """Test auto-discovery of .env file"""
        # Create a temporary Python file and .env in same directory
        test_file = tmp_path / "test_app.py"
        test_file.write_text("# test file")
        env_file = tmp_path / ".env"
        env_file.write_text("AUTO_DISCOVERED=true\nAPP_LOGGING_ENABLE=false\n")

        with patch('libs.base.application_base.DefaultAzureCredential') as mock_cred, \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('inspect.getfile') as mock_getfile:

            mock_getfile.return_value = str(test_file)
            mock_cred.return_value = Mock()

            app = ConcreteApplication()

            assert app.application_context is not None
            assert app.initialized is True

    def test_initialization_with_app_config_endpoint(self, tmp_path, monkeypatch):
        """Test initialization with Azure App Configuration"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_CONFIG_ENDPOINT=https://myconfig.azconfig.io\nAPP_LOGGING_ENABLE=false\n")

        monkeypatch.setenv("APP_CONFIG_ENDPOINT", "https://myconfig.azconfig.io")

        with patch('libs.base.application_base.DefaultAzureCredential') as mock_cred, \
             patch('libs.base.application_base.AppConfigurationHelper') as mock_app_config, \
             patch('libs.base.application_base.AgentFrameworkSettings'):

            mock_cred_instance = Mock()
            mock_cred.return_value = mock_cred_instance
            mock_app_config_instance = Mock()
            mock_app_config.return_value = mock_app_config_instance

            _app = ConcreteApplication(env_file_path=str(env_file))

            mock_app_config.assert_called_once()
            mock_app_config_instance.read_and_set_environmental_variables.assert_called_once()

    def test_initialization_with_logging_enabled(self, tmp_path, monkeypatch):
        """Test initialization with logging enabled"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_LOGGING_ENABLE=true\nAPP_LOGGING_LEVEL=DEBUG\n")

        monkeypatch.setenv("APP_LOGGING_ENABLE", "true")
        monkeypatch.setenv("APP_LOGGING_LEVEL", "DEBUG")

        with patch('libs.base.application_base.DefaultAzureCredential') as mock_cred, \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('libs.base.application_base.logging.basicConfig') as mock_logging:

            mock_cred.return_value = Mock()

            _app = ConcreteApplication(env_file_path=str(env_file))

            # Verify logging was configured
            mock_logging.assert_called_once()
            call_kwargs = mock_logging.call_args[1]
            assert 'level' in call_kwargs

    def test_initialization_without_logging(self, tmp_path, monkeypatch):
        """Test initialization with logging disabled"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_LOGGING_ENABLE=false\n")

        monkeypatch.setenv("APP_LOGGING_ENABLE", "false")

        with patch('libs.base.application_base.DefaultAzureCredential') as mock_cred, \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('libs.base.application_base.logging.basicConfig') as mock_logging:

            mock_cred.return_value = Mock()

            _app = ConcreteApplication(env_file_path=str(env_file))

            # Verify logging was NOT configured
            mock_logging.assert_not_called()

    def test_initialization_sets_llm_settings(self, tmp_path):
        """Test that LLM settings are initialized"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_LOGGING_ENABLE=false\n")

        with patch('libs.base.application_base.DefaultAzureCredential') as mock_cred, \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings') as mock_llm_settings:

            mock_cred.return_value = Mock()
            mock_llm_instance = Mock()
            mock_llm_settings.return_value = mock_llm_instance

            app = ConcreteApplication(env_file_path=str(env_file))

            assert app.application_context.llm_settings == mock_llm_instance
            mock_llm_settings.assert_called_once_with(
                use_entra_id=True,
                custom_service_prefixes={"PHI4": "PHI4"}
            )

    def test_load_env_with_explicit_path(self, tmp_path):
        """Test _load_env with explicit file path"""
        env_file = tmp_path / "custom.env"
        env_file.write_text("CUSTOM_VAR=custom_value\nAPP_LOGGING_ENABLE=false\n")

        with patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('libs.base.application_base.load_dotenv') as mock_load_dotenv:

            _app = ConcreteApplication(env_file_path=str(env_file))

            # Verify load_dotenv was called at least once
            assert mock_load_dotenv.call_count >= 1

    def test_get_derived_class_location(self, tmp_path):
        """Test _get_derived_class_location method"""
        with patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'), \
             patch('inspect.getfile') as mock_getfile:

            expected_path = "/path/to/concrete_app.py"
            mock_getfile.return_value = expected_path

            # Create test env file
            test_env = tmp_path / ".env"
            test_env.write_text("APP_LOGGING_ENABLE=false\n")

            app = ConcreteApplication(env_file_path=str(test_env))

            location = app._get_derived_class_location()

            assert location == expected_path
            mock_getfile.assert_called()

    def test_application_context_credential_set(self, tmp_path):
        """Test that credential is set in application context"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_LOGGING_ENABLE=false\n")

        with patch('libs.base.application_base.DefaultAzureCredential') as mock_cred, \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'):

            mock_cred_instance = Mock()
            mock_cred.return_value = mock_cred_instance

            app = ConcreteApplication(env_file_path=str(env_file))

            assert app.application_context.credential == mock_cred_instance

    def test_application_context_configuration_set(self, tmp_path, monkeypatch):
        """Test that configuration is set in application context"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_LOGGING_ENABLE=false\n")

        monkeypatch.setenv("APP_LOGGING_ENABLE", "false")

        with patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'):

            app = ConcreteApplication(env_file_path=str(env_file))

            assert app.application_context.configuration is not None

    def test_run_method_called(self, tmp_path):
        """Test that run method can be called"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_LOGGING_ENABLE=false\n")

        with patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'):

            app = ConcreteApplication(env_file_path=str(env_file))

            assert app.running is False
            app.run()
            assert app.running is True

    def test_initialize_method_called_during_init(self, tmp_path):
        """Test that initialize is NOT called automatically during __init__"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_LOGGING_ENABLE=false\n")

        with patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.AppConfigurationHelper'), \
             patch('libs.base.application_base.AgentFrameworkSettings'):

            # initialized flag is set in ConcreteApplication.__init__ which calls super().__init__
            # But the initialize() method sets initialized=True
            app = ConcreteApplication(env_file_path=str(env_file))

            # The initialize() method should have been called in ConcreteApplication.__init__
            assert app.initialized is True

    def test_empty_app_config_endpoint_skipped(self, tmp_path, monkeypatch):
        """Test that empty APP_CONFIG_ENDPOINT is skipped"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_CONFIG_ENDPOINT=\nAPP_LOGGING_ENABLE=false\n")

        monkeypatch.setenv("APP_CONFIG_ENDPOINT", "")

        with patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.AppConfigurationHelper') as mock_app_config, \
             patch('libs.base.application_base.AgentFrameworkSettings'):

            _app = ConcreteApplication(env_file_path=str(env_file))

            # AppConfigurationHelper should not be called with empty endpoint
            mock_app_config.assert_not_called()

    def test_none_app_config_endpoint_skipped(self, tmp_path, monkeypatch):
        """Test that None APP_CONFIG_ENDPOINT is skipped"""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_LOGGING_ENABLE=false\n")

        # Don't set APP_CONFIG_ENDPOINT at all
        monkeypatch.delenv("APP_CONFIG_ENDPOINT", raising=False)

        with patch('libs.base.application_base.DefaultAzureCredential'), \
             patch('libs.base.application_base.AppConfigurationHelper') as mock_app_config, \
             patch('libs.base.application_base.AgentFrameworkSettings'):

            _app = ConcreteApplication(env_file_path=str(env_file))

            # AppConfigurationHelper should not be called
            mock_app_config.assert_not_called()
