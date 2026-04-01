# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the schemavault router."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.logics.schemavault import Schemas
from app.routers.schemavault import router


class _FakeScope:
    def __init__(self, schemas: Schemas):
        self._schemas = schemas

    def get_service(self, service_type):
        if service_type is Schemas:
            return self._schemas
        raise KeyError(service_type)


class _FakeScopeContextManager:
    def __init__(self, scope: _FakeScope):
        self._scope = scope

    async def __aenter__(self):
        return self._scope

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeAppContext:
    def __init__(self, schemas: Schemas):
        self._schemas = schemas

    def create_scope(self):
        return _FakeScopeContextManager(_FakeScope(self._schemas))


@pytest.fixture
def client_and_schemas():
    app = FastAPI()
    app.include_router(router)
    mock_schemas = MagicMock(spec=Schemas)
    app.app_context = _FakeAppContext(mock_schemas)  # type: ignore[attr-defined]
    return TestClient(app), mock_schemas


def test_get_all_registered_schema(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.GetAll.return_value = []

    response = client.get("/schemavault/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_registered_schema_file_by_schema_id(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.GetFile.return_value = {
        "FileName": "test.txt",
        "ContentType": "text/plain",
        "File": b"test content",
    }
    response = client.get("/schemavault/schemas/test-id")
    assert response.status_code == 200
    assert (
        response.headers["Content-Disposition"]
        == "attachment; filename*=UTF-8''test.txt"
    )
    assert response.content == b"test content"


def test_get_registered_schema_file_by_schema_id_500_error(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.GetFile.side_effect = Exception("Internal Server Error")

    response = client.get("/schemavault/schemas/test-id")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}


def test_register_schema_accepts_py_and_sanitizes_filename(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Add.return_value = {
        "Id": "test-id",
        "ClassName": "TestClass",
        "Description": "Test description",
        "FileName": "invoice.py",
        "ContentType": "text/x-python",
    }

    files = {
        "file": ("C:/fakepath/invoice.py", b"class Invoice: pass\n", "text/x-python"),
        "data": (
            None,
            json.dumps({"ClassName": "TestClass", "Description": "Test description"}),
            "application/json",
        ),
    }

    response = client.post("/schemavault/", files=files)
    assert response.status_code == 200

    # Ensure Add() is called with Schema.FileName sanitized to just the basename
    add_args, _ = mock_schemas.Add.call_args
    schema_obj = add_args[1]
    assert schema_obj.FileName == "invoice.py"


def test_register_schema_rejects_non_py(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Add.reset_mock()

    files = {
        "file": ("evil.exe", b"MZ" + b"0" * 8, "application/octet-stream"),
        "data": (
            None,
            json.dumps({"ClassName": "TestClass", "Description": "Test description"}),
            "application/json",
        ),
    }

    response = client.post("/schemavault/", files=files)
    assert response.status_code == 415
    assert mock_schemas.Add.call_count == 0


def test_update_schema_success(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Update.return_value = {
        "Id": "test-id",
        "ClassName": "Updated",
        "Description": "desc",
        "FileName": "updated.py",
        "ContentType": "text/x-python",
    }

    files = {
        "file": ("updated.py", b"class Updated: pass\n", "text/x-python"),
        "data": (
            None,
            json.dumps({"SchemaId": "test-id", "ClassName": "Updated"}),
            "application/json",
        ),
    }

    response = client.put("/schemavault/", files=files)
    assert response.status_code == 200
    mock_schemas.Update.assert_called_once()


def test_update_schema_rejects_non_py(client_and_schemas):
    client, mock_schemas = client_and_schemas

    files = {
        "file": ("data.txt", b"plain text", "text/plain"),
        "data": (
            None,
            json.dumps({"SchemaId": "test-id", "ClassName": "X"}),
            "application/json",
        ),
    }

    response = client.put("/schemavault/", files=files)
    assert response.status_code == 415


def test_unregister_schema_success(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Delete.return_value = MagicMock(
        Id="test-id", ClassName="TestClass", FileName="test.py"
    )

    response = client.request(
        "DELETE",
        "/schemavault/",
        json={"SchemaId": "test-id"},
    )
    assert response.status_code == 200
    assert response.json()["Status"] == "Success"


def test_unregister_schema_error(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Delete.side_effect = Exception("Schema not found")

    response = client.request(
        "DELETE",
        "/schemavault/",
        json={"SchemaId": "missing"},
    )
    assert response.status_code == 500
