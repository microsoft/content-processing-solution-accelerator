# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the contentprocessor router (read endpoints)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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
def client():
    app = FastAPI()
    app.include_router(router)
    configuration = SimpleNamespace(
        app_cosmos_connstr="test_connection_string",
        app_cosmos_database="test_database",
        app_cosmos_container_process="test_container",
        app_cosmos_container_batches="test_batches",
        app_cps_max_filesize_mb=20,
        app_storage_blob_url="test_blob_url",
        app_cps_processes="mock_cps_processes",
    )
    app.app_context = _FakeAppContext(configuration, MagicMock(spec=ContentProcessor))  # type: ignore[attr-defined]
    return TestClient(app)


@patch(
    "app.routers.contentprocessor.CosmosContentProcess.get_all_processes_from_cosmos"
)
def test_get_all_processed_results(mock_get_all_processes, client):
    mock_get_all_processes.return_value = {
        "items": [],
        "total_count": 0,
        "total_pages": 0,
        "current_page": 1,
        "page_size": 10,
    }

    response = client.post(
        "/contentprocessor/processed", json={"page_number": 1, "page_size": 10}
    )
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "current_page": 1,
        "page_size": 10,
        "total_count": 0,
        "total_pages": 0,
    }


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_status_processing(mock_get_status, client):
    mock_get_status.return_value = MagicMock(status="processing")

    response = client.get("/contentprocessor/status/test_process_id")
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    assert "still in progress" in response.json()["message"]


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_status_completed(mock_get_status, client):
    mock_get_status.return_value = MagicMock(status="Completed")

    response = client.get("/contentprocessor/status/test_process_id")
    assert response.status_code == 302
    assert response.json()["status"] == "completed"
    assert "is completed" in response.json()["message"]


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_status_failed(mock_get_status, client):
    mock_get_status.return_value = None

    response = client.get("/contentprocessor/status/test_process_id")
    assert response.status_code == 404
    assert response.json()["status"] == "failed"
    assert "not found" in response.json()["message"]


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_process(mock_get_status, client):
    mock_get_status.return_value = MagicMock(
        process_id="test_process_id",
        processed_file_name="test.pdf",
        processed_file_mime_type="application/pdf",
        processed_time="2025-03-13T12:00:00Z",
        last_modified_by="user",
        status="Completed",
        result={},
        confidence={},
        target_schema={
            "Id": "schema_id",
            "ClassName": "class_name",
            "Description": "description",
            "FileName": "file_name",
            "ContentType": "content_type",
        },
        comment="test comment",
    )

    response = client.get("/contentprocessor/processed/test_process_id")
    assert response.status_code == 200


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_process_not_found(mock_get_status, client):
    mock_get_status.return_value = None

    response = client.get("/contentprocessor/processed/test_process_id")
    assert response.status_code == 404
    assert response.json()["status"] == "failed"


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_blob")
def test_get_process_steps(mock_get_steps, client):
    mock_get_steps.return_value = {"steps": []}

    response = client.get("/contentprocessor/processed/test_process_id/steps")
    assert response.status_code == 200
    assert response.json() == {"steps": []}


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_blob")
def test_get_process_steps_not_found(mock_get_steps, client):
    mock_get_steps.return_value = None

    response = client.get("/contentprocessor/processed/test_process_id/steps")
    assert response.status_code == 404
    assert response.json()["status"] == "failed"


@patch("app.routers.contentprocessor.CosmosContentProcess.update_process_result")
def test_update_process_result(mock_update_result, client):
    mock_update_result.return_value = MagicMock()

    data = {"process_id": "test_process_id", "modified_result": {"key": "value"}}
    response = client.put("/contentprocessor/processed/test_process_id", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@patch("app.routers.contentprocessor.CosmosContentProcess.update_process_comment")
def test_update_process_comment(mock_update_comment, client):
    mock_update_comment.return_value = MagicMock()

    data = {"process_id": "test_process_id", "comment": "new comment"}
    response = client.put("/contentprocessor/processed/test_process_id", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_get_original_file_success(client):
    with (
        patch(
            "app.routers.contentprocessor.CosmosContentProcess",
            autospec=True,
        ) as mock_cosmos_content_process,
        patch(
            "app.routers.contentprocessor.MimeTypesDetection",
            autospec=True,
        ) as mock_mime_types_detection,
    ):
        # Mocking the process status
        mock_process_status = MagicMock()
        mock_process_status.processed_file_name = "testfile.txt"
        mock_process_status.process_id = "123"
        mock_process_status.get_file_bytes_from_blob.return_value = b"file content"
        mock_cosmos_content_process.return_value.get_status_from_cosmos.return_value = (
            mock_process_status
        )

        # Mocking the MIME type detection
        mock_mime_types_detection.get_file_type.return_value = "text/plain"

        response = client.get("/contentprocessor/processed/files/123")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/plain"
        assert (
            response.headers["Content-Disposition"]
            == "inline; filename*=UTF-8''testfile.txt"
        )


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_original_file_not_found(mock_get_status, client):
    mock_get_status.return_value = None

    response = client.get("/contentprocessor/processed/files/test_process_id")
    assert response.status_code == 404
    assert response.json()["status"] == "failed"


@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_status_error(mock_get_status, client):
    mock_get_status.return_value = MagicMock(status="Error")

    response = client.get("/contentprocessor/status/test_process_id")
    assert response.status_code == 500
    assert response.json()["status"] == "failed"
    assert "has failed" in response.json()["message"]


@patch("app.routers.contentprocessor.CosmosContentProcess.delete_processed_file")
def test_delete_processed_file_success(mock_delete, client):
    mock_deleted = MagicMock()
    mock_deleted.process_id = "test_process_id"
    mock_delete.return_value = mock_deleted

    mock_repo = MagicMock()
    mock_repo.delete_async = AsyncMock(return_value=None)

    from app.routers.logics.claimbatchpocessor import ClaimBatchProcessRepository

    orig_create = client.app.app_context.create_scope

    class _WrappedScope:
        def __init__(self, inner):
            self._inner = inner

        def get_service(self, svc):
            if svc is ClaimBatchProcessRepository:
                return mock_repo
            return self._inner.get_service(svc)

    class _WrappedCtx:
        def __init__(self):
            self._real = orig_create()

        async def __aenter__(self):
            self._scope = await self._real.__aenter__()
            return _WrappedScope(self._scope)

        async def __aexit__(self, *a):
            return await self._real.__aexit__(*a)

    client.app.app_context.create_scope = lambda: _WrappedCtx()

    response = client.delete("/contentprocessor/processed/test_process_id")
    assert response.status_code == 200
    assert response.json()["status"] == "Success"


@patch("app.routers.contentprocessor.CosmosContentProcess.update_process_result")
def test_update_process_result_not_found(mock_update_result, client):
    mock_update_result.return_value = None

    data = {"process_id": "missing", "modified_result": {"key": "value"}}
    response = client.put("/contentprocessor/processed/missing", json=data)
    assert response.status_code == 404
    assert response.json()["status"] == "failed"
