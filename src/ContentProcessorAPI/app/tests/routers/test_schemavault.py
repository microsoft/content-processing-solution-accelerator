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

    def get_service(self, service_type):
        if service_type is Schemas:
            return self._schemas
        raise KeyError(service_type)


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


def test_register_schema_rejects_py(client_and_schemas):
    """Legacy .py uploads must be refused outright (RCE remediation)."""
    client, mock_schemas = client_and_schemas
    mock_schemas.Add.reset_mock()

    files = {
        "file": ("C:/fakepath/invoice.py", b"class Invoice: pass\n", "text/x-python"),
        "data": (
            None,
            json.dumps({"ClassName": "TestClass", "Description": "Test description"}),
            "application/json",
        ),
    }

    response = client.post("/schemavault/", files=files)
    assert response.status_code == 415
    assert mock_schemas.Add.call_count == 0


def test_register_schema_rejects_unsupported_extension(client_and_schemas):
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
        "ClassName": "InvoiceSchema",
        "Description": "desc",
        "FileName": "updated.json",
        "ContentType": "application/json",
        "Format": "json",
    }

    files = {
        "file": ("updated.json", _minimal_json_schema_bytes(), "application/json"),
        "data": (
            None,
            json.dumps({"SchemaId": "test-id", "ClassName": "InvoiceSchema"}),
            "application/json",
        ),
    }

    response = client.put("/schemavault/", files=files)
    assert response.status_code == 200
    mock_schemas.Update.assert_called_once()


def test_update_schema_rejects_py(client_and_schemas):
    client, mock_schemas = client_and_schemas

    files = {
        "file": ("updated.py", b"class Updated: pass\n", "text/x-python"),
        "data": (
            None,
            json.dumps({"SchemaId": "test-id", "ClassName": "X"}),
            "application/json",
        ),
    }

    response = client.put("/schemavault/", files=files)
    assert response.status_code == 415


def test_update_schema_rejects_unsupported_extension(client_and_schemas):
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
        Id="test-id", ClassName="TestClass", FileName="test.json"
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


# ---------------------------------------------------------------------------
# JSON-schema upload path (declarative format, replaces executable .py)
# ---------------------------------------------------------------------------


def _minimal_json_schema_bytes(title: str = "InvoiceSchema") -> bytes:
    return json.dumps({
        "type": "object",
        "title": title,
        "properties": {"invoice_id": {"type": "string"}},
    }).encode("utf-8")


def test_register_schema_accepts_json(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Add.return_value = {
        "Id": "test-id",
        "ClassName": "InvoiceSchema",
        "Description": "desc",
        "FileName": "invoice.json",
        "ContentType": "application/json",
        "Format": "json",
    }

    files = {
        "file": (
            "invoice.json",
            _minimal_json_schema_bytes(),
            "application/json",
        ),
        "data": (
            None,
            json.dumps({"ClassName": "ignored", "Description": "desc"}),
            "application/json",
        ),
    }

    response = client.post("/schemavault/", files=files)
    assert response.status_code == 200, response.text

    add_args, _ = mock_schemas.Add.call_args
    schema_obj = add_args[1]
    # Schema's title wins over the request body's ClassName.
    assert schema_obj.ClassName == "InvoiceSchema"
    assert schema_obj.Format == "json"
    assert schema_obj.FileName == "invoice.json"


def test_register_schema_rejects_invalid_json(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Add.reset_mock()

    files = {
        "file": ("schema.json", b"{not json", "application/json"),
        "data": (
            None,
            json.dumps({"ClassName": "X", "Description": "Y"}),
            "application/json",
        ),
    }

    response = client.post("/schemavault/", files=files)
    assert response.status_code == 400
    assert "errors" in response.json()["detail"]
    assert mock_schemas.Add.call_count == 0


def test_register_schema_rejects_json_without_object_root(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Add.reset_mock()

    files = {
        "file": (
            "schema.json",
            json.dumps({"type": "array"}).encode("utf-8"),
            "application/json",
        ),
        "data": (
            None,
            json.dumps({"ClassName": "X", "Description": "Y"}),
            "application/json",
        ),
    }

    response = client.post("/schemavault/", files=files)
    assert response.status_code == 400
    assert mock_schemas.Add.call_count == 0


def test_register_schema_falls_back_to_filename_for_classname(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Add.return_value = {
        "Id": "test-id",
        "ClassName": "fallback",
        "Description": "desc",
        "FileName": "auto-claim.json",
        "ContentType": "application/json",
        "Format": "json",
    }

    schema_bytes = json.dumps({
        "type": "object",
        "properties": {"x": {"type": "string"}},
    }).encode("utf-8")

    files = {
        "file": ("auto-claim.json", schema_bytes, "application/json"),
        "data": (
            None,
            json.dumps({"ClassName": "fallback", "Description": "desc"}),
            "application/json",
        ),
    }

    response = client.post("/schemavault/", files=files)
    assert response.status_code == 200, response.text
    schema_obj = mock_schemas.Add.call_args[0][1]
    # When the JSON has no title, the request-body ClassName is used as
    # the fallback (after sanitisation to a Python identifier).
    assert schema_obj.ClassName == "fallback"
    assert schema_obj.Format == "json"


def test_update_schema_accepts_json(client_and_schemas):
    client, mock_schemas = client_and_schemas
    mock_schemas.Update.return_value = {
        "Id": "test-id",
        "ClassName": "InvoiceSchema",
        "Description": "",
        "FileName": "invoice.json",
        "ContentType": "application/json",
        "Format": "json",
    }

    files = {
        "file": (
            "invoice.json",
            _minimal_json_schema_bytes(),
            "application/json",
        ),
        "data": (
            None,
            json.dumps({"SchemaId": "test-id", "ClassName": "x"}),
            "application/json",
        ),
    }

    response = client.put("/schemavault/", files=files)
    assert response.status_code == 200, response.text
    args, _ = mock_schemas.Update.call_args
    # Update is called with (file, schema_id, class_name, storage_format).
    assert args[2] == "InvoiceSchema"
    assert args[3] == "json"
