# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the schemasetvault router."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.logics.schemasetvault import SchemaSets
from app.routers.models.schmavault.model import SchemaMetadata, SchemaSet
from app.routers.schemasetvault import router


class _FakeScope:
    def __init__(self, schemasets: SchemaSets):
        self._schemasets = schemasets

    def get_service(self, service_type):
        if service_type is SchemaSets:
            return self._schemasets
        raise KeyError(service_type)


class _FakeScopeCtx:
    def __init__(self, scope):
        self._scope = scope

    async def __aenter__(self):
        return self._scope

    async def __aexit__(self, *args):
        return False


class _FakeAppContext:
    def __init__(self, schemasets):
        self._schemasets = schemasets

    def create_scope(self):
        return _FakeScopeCtx(_FakeScope(self._schemasets))


@pytest.fixture
def client_and_mock():
    app = FastAPI()
    app.include_router(router)
    mock_ss = MagicMock(spec=SchemaSets)
    app.app_context = _FakeAppContext(mock_ss)  # type: ignore[attr-defined]
    return TestClient(app), mock_ss


def test_get_all_schema_sets(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.GetAll.return_value = []
    response = client.get("/schemasetvault/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_schema_set(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.AddNew.return_value = SchemaSet(
        Id="ss1", Name="Claims", Description="desc", Schemas=[]
    )
    response = client.post(
        "/schemasetvault/",
        json={"Name": "Claims", "Description": "desc"},
    )
    assert response.status_code == 200
    assert response.json()["Name"] == "Claims"


def test_get_schema_set_by_id_found(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.GetById.return_value = SchemaSet(
        Id="ss1", Name="Claims", Description="desc", Schemas=[]
    )
    response = client.get("/schemasetvault/ss1")
    assert response.status_code == 200
    assert response.json()["Id"] == "ss1"


def test_get_schema_set_by_id_not_found(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.GetById.return_value = None
    response = client.get("/schemasetvault/missing")
    assert response.status_code == 404


def test_delete_schema_set_success(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.DeleteById.return_value = True
    response = client.delete("/schemasetvault/ss1")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_delete_schema_set_not_found(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.DeleteById.return_value = False
    response = client.delete("/schemasetvault/missing")
    assert response.status_code == 404


def test_get_all_schemas_in_set(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.GetAllSchemasInSet.return_value = []
    response = client.get("/schemasetvault/ss1/schemas")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_schemas_in_set_not_found(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.GetAllSchemasInSet.side_effect = Exception("Schema Set not found")
    response = client.get("/schemasetvault/missing/schemas")
    assert response.status_code == 404


def test_add_schema_to_set(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.AddSchemaToSet.return_value = SchemaSet(
        Id="ss1",
        Name="Claims",
        Description="desc",
        Schemas=[SchemaMetadata(Id="sm1", SchemaId="s1", Description="d")],
    )
    response = client.post(
        "/schemasetvault/ss1/schemas",
        json={"SchemaId": "s1"},
    )
    assert response.status_code == 200
    assert len(response.json()["Schemas"]) == 1


def test_add_schema_to_set_error(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.AddSchemaToSet.side_effect = Exception("Schema Set not found")
    response = client.post(
        "/schemasetvault/missing/schemas",
        json={"SchemaId": "s1"},
    )
    assert response.status_code == 404


def test_remove_schema_from_set(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.RemoveSchemaFromSet.return_value = SchemaSet(
        Id="ss1", Name="Claims", Description="desc", Schemas=[]
    )
    response = client.delete("/schemasetvault/ss1/schemas/s1")
    assert response.status_code == 200
    assert response.json()["Schemas"] == []


def test_remove_schema_from_set_error(client_and_mock):
    client, mock_ss = client_and_mock
    mock_ss.RemoveSchemaFromSet.side_effect = Exception("Schema Set not found")
    response = client.delete("/schemasetvault/missing/schemas/s1")
    assert response.status_code == 404
