import pytest
from main import Application


class DummyHandler:
    def __init__(self, appContext, step_name):
        self.handler_name = step_name
        self.appContext = appContext
        self.step_name = step_name
        self.exitcode = None

    def connect_queue(self, *args):
        print(f"Connecting queue for handler: {self.handler_name}")


class ConfigItem:
    def __init__(self, key, value):
        self.key = key
        self.value = value


@pytest.mark.asyncio
async def test_application_run(mocker):
    # Mock the application context and configuration
    mock_app_context = mocker.MagicMock()
    mock_app_context.configuration.app_process_steps = ["extract", "transform"]

    # Mock the handler loader to return a DummyHandler
    mocker.patch(
        "libs.process_host.handler_type_loader.load",
        side_effect=lambda name: DummyHandler,
    )

    # Mock the HandlerHostManager instance
    mocker.patch(
        "libs.process_host.handler_process_host.HandlerHostManager"
    ).return_value

    # Note: Azure credentials are mocked globally via conftest.py

    # Mock the read_configuration method to return a complete configuration
    mocker.patch(
        "libs.azure_helper.app_configuration.AppConfigurationHelper.read_configuration",
        return_value=[
            ConfigItem("app_storage_queue_url", "https://example.com/queue"),
            ConfigItem("app_storage_blob_url", "https://example.com/blob"),
            ConfigItem("app_process_steps", "extract,map"),
            ConfigItem("app_message_queue_interval", "2"),
            ConfigItem("app_message_queue_visibility_timeout", "1"),
            ConfigItem("app_message_queue_process_timeout", "2"),
            ConfigItem("app_logging_enable", "True"),
            ConfigItem("app_logging_level", "DEBUG"),
            ConfigItem("app_cps_processes", "4"),
            ConfigItem("app_cps_configuration", "value"),
            ConfigItem(
                "app_content_understanding_endpoint", "https://example.com/content"
            ),
            ConfigItem("app_azure_openai_endpoint", "https://example.com/openai"),
            ConfigItem("app_azure_openai_model", "model-name"),
            ConfigItem(
                "app_cosmos_connstr",
                "AccountEndpoint=https://example.com;AccountKey=key;",
            ),
            ConfigItem("app_cosmos_database", "database-name"),
            ConfigItem("app_cosmos_container_process", "container-process"),
            ConfigItem("app_cosmos_container_schema", "container-schema"),
        ],
    )

    # Initialize the application with the mocked context
    mocker.patch.object(
        Application, "_initialize_application", return_value=mock_app_context
    )
    app = Application()

    # Run the application
    await app.run(test_mode=True)
