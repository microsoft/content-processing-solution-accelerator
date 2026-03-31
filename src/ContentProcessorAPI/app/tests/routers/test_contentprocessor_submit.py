# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the contentprocessor submit endpoint."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.contentprocessor import router
from app.routers.logics.contentprocessor import ContentProcessor


class _FakeScope:
    def __init__(self, content_processor: ContentProcessor):
        self._content_processor = content_processor

    def get_service(self, service_type):
        if service_type is ContentProcessor:
            return self._content_processor
        raise KeyError(service_type)


class _FakeScopeContextManager:
    def __init__(self, scope: _FakeScope):
        self._scope = scope

    async def __aenter__(self):
        return self._scope

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeAppContext:
    def __init__(self, configuration, content_processor: ContentProcessor):
        self.configuration = configuration
        self._content_processor = content_processor

    def create_scope(self):
        return _FakeScopeContextManager(_FakeScope(self._content_processor))


@pytest.fixture
def client_and_cp():
    app = FastAPI()
    app.include_router(router)

    mock_cp = MagicMock(spec=ContentProcessor)
    mock_cp.save_file_to_blob = MagicMock()
    mock_cp.enqueue_message = MagicMock()
    # Used by batch submission code path.
    mock_cp.config = SimpleNamespace(
        app_cosmos_connstr="test_conn",
        app_cosmos_database="test_db",
        app_cosmos_container_process="test_container",
    )

    configuration = SimpleNamespace(
        app_cps_max_filesize_mb=20,
        app_cosmos_connstr="test_conn",
        app_cosmos_database="test_db",
        app_cosmos_container_process="test_container",
        app_cosmos_container_batches="test_batches",
    )

    app.app_context = _FakeAppContext(configuration, mock_cp)  # type: ignore[attr-defined]
    return TestClient(app), mock_cp


@pytest.fixture
def mock_cosmos_update():
    with patch(
        "app.routers.contentprocessor.CosmosContentProcess.update_process_status_to_cosmos",
        autospec=True,
        return_value=None,
    ) as mock:
        yield mock


def test_submit_pdf_ok_sanitizes_filename(client_and_cp, mock_cosmos_update):
    client, mock_cp = client_and_cp

    pdf_bytes = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
    files = {
        "file": (
            "C:\\fakepath\\test.pdf",
            pdf_bytes,
            "application/pdf",
        ),
        "data": (
            None,
            json.dumps({"Schema_Id": "schema", "Metadata_Id": "meta"}),
            "application/json",
        ),
    }

    response = client.post("/contentprocessor/submit", files=files)
    assert response.status_code == 202

    # Blob name should not include client path components
    assert mock_cp.save_file_to_blob.call_count == 1
    assert mock_cp.save_file_to_blob.call_args.kwargs["file_name"] == "test.pdf"


def test_submit_rejects_mismatched_magic(client_and_cp, mock_cosmos_update):
    client, mock_cp = client_and_cp

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    files = {
        "file": ("test.pdf", png_bytes, "application/pdf"),
        "data": (
            None,
            json.dumps({"Schema_Id": "schema", "Metadata_Id": "meta"}),
            "application/json",
        ),
    }

    response = client.post("/contentprocessor/submit", files=files)
    assert response.status_code == 415
    assert mock_cp.save_file_to_blob.call_count == 0


def test_submit_rejects_too_long_filename(client_and_cp, mock_cosmos_update):
    client, mock_cp = client_and_cp

    pdf_bytes = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    long_name = ("a" * 1100) + ".pdf"

    files = {
        "file": (long_name, pdf_bytes, "application/pdf"),
        "data": (
            None,
            json.dumps({"Schema_Id": "schema", "Metadata_Id": "meta"}),
            "application/json",
        ),
    }

    response = client.post("/contentprocessor/submit", files=files)
    assert response.status_code == 400
    assert mock_cp.save_file_to_blob.call_count == 0
