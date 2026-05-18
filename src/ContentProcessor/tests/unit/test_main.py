# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for main (Application bootstrap and process orchestration)."""

from __future__ import annotations

import asyncio

from main import Application

# ── Helpers ─────────────────────────────────────────────────────────────


class _DummyHandler:
    def __init__(self, appContext, step_name):
        self.handler_name = step_name
        self.appContext = appContext
        self.step_name = step_name
        self.exitcode = None

    def connect_queue(self, *args):
        pass


class _ConfigItem:
    def __init__(self, key, value):
        self.key = key
        self.value = value


# ── TestApplication ─────────────────────────────────────────────────────


class TestApplication:
    """Smoke-level test for the Application entry point."""

    def test_application_run(self, mocker):
        mock_app_context = mocker.MagicMock()
        mock_app_context.configuration.app_process_steps = ["extract", "transform"]

        mocker.patch(
            "libs.process_host.handler_type_loader.load",
            side_effect=lambda name: _DummyHandler,
        )
        mocker.patch(
            "libs.process_host.handler_process_host.HandlerHostManager"
        ).return_value
        mocker.patch(
            "libs.azure_helper.app_configuration.AppConfigurationHelper.read_configuration",
            return_value=[
                _ConfigItem("app_storage_queue_url", "https://example.com/queue"),
                _ConfigItem("app_storage_blob_url", "https://example.com/blob"),
                _ConfigItem("app_process_steps", "extract,map"),
                _ConfigItem("app_message_queue_interval", "2"),
                _ConfigItem("app_message_queue_visibility_timeout", "1"),
                _ConfigItem("app_message_queue_process_timeout", "2"),
                _ConfigItem("app_logging_level", "DEBUG"),
                _ConfigItem("azure_package_logging_level", "DEBUG"),
                _ConfigItem("azure_logging_packages", "test_package"),
                _ConfigItem("app_cps_processes", "4"),
                _ConfigItem("app_cps_configuration", "value"),
                _ConfigItem(
                    "app_content_understanding_endpoint",
                    "https://example.com/content",
                ),
                _ConfigItem("app_azure_openai_endpoint", "https://example.com/openai"),
                _ConfigItem("app_azure_openai_model", "model-name"),
                _ConfigItem(
                    "app_ai_project_endpoint", "https://example.com/ai-project"
                ),
                _ConfigItem(
                    "app_cosmos_connstr",
                    "AccountEndpoint=https://example.com;AccountKey=key;",
                ),
                _ConfigItem("app_cosmos_database", "database-name"),
                _ConfigItem("app_cosmos_container_process", "container-process"),
                _ConfigItem("app_cosmos_container_schema", "container-schema"),
            ],
        )

        mocker.patch.object(
            Application, "_initialize_application", return_value=mock_app_context
        )
        app = Application()

        async def _run():
            await app.run(test_mode=True)

        asyncio.run(_run())
