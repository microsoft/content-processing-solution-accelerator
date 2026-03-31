# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the Schemas (schema-vault) logic class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.routers.models.schmavault.model import Schema


@pytest.fixture
def mock_app_context():
    ctx = MagicMock()
    ctx.configuration.app_storage_blob_url = "https://blob.example.com"
    ctx.configuration.app_cps_configuration = "config"
    ctx.configuration.app_cosmos_container_schema = "schemas"
    ctx.configuration.app_cosmos_connstr = "mongodb://localhost"
    ctx.configuration.app_cosmos_database = "db"
    return ctx


@patch("app.routers.logics.schemavault.CosmosMongDBHelper")
@patch("app.routers.logics.schemavault.StorageBlobHelper")
def test_get_all(MockBlob, MockMongo, mock_app_context):
    mock_mongo = MockMongo.return_value
    mock_mongo.find_document.return_value = [
        {
            "Id": "s1",
            "ClassName": "Invoice",
            "Description": "desc",
            "FileName": "invoice.py",
            "ContentType": "text/x-python",
        }
    ]

    from app.routers.logics.schemavault import Schemas

    schemas = Schemas(app_context=mock_app_context)
    result = schemas.GetAll()
    assert len(result) == 1
    assert isinstance(result[0], Schema)
    assert result[0].Id == "s1"


@patch("app.routers.logics.schemavault.CosmosMongDBHelper")
@patch("app.routers.logics.schemavault.StorageBlobHelper")
def test_get_file(MockBlob, MockMongo, mock_app_context):
    mock_mongo = MockMongo.return_value
    mock_mongo.find_document.return_value = [
        {
            "Id": "s1",
            "ClassName": "Invoice",
            "Description": "desc",
            "FileName": "invoice.py",
            "ContentType": "text/x-python",
        }
    ]
    mock_blob = MockBlob.return_value
    mock_blob.download_blob.return_value = b"class Invoice: pass"

    from app.routers.logics.schemavault import Schemas

    schemas = Schemas(app_context=mock_app_context)
    result = schemas.GetFile("s1")
    assert result["File"] == b"class Invoice: pass"
    assert result["FileName"] == "invoice.py"
    assert result["ContentType"] == "text/x-python"


@patch("app.routers.logics.schemavault.CosmosMongDBHelper")
@patch("app.routers.logics.schemavault.StorageBlobHelper")
def test_get_file_not_found(MockBlob, MockMongo, mock_app_context):
    mock_mongo = MockMongo.return_value
    mock_mongo.find_document.return_value = []

    from app.routers.logics.schemavault import Schemas

    schemas = Schemas(app_context=mock_app_context)
    with pytest.raises(Exception, match="Schema not found"):
        schemas.GetFile("missing")


@patch("app.routers.logics.schemavault.CosmosMongDBHelper")
@patch("app.routers.logics.schemavault.StorageBlobHelper")
def test_add(MockBlob, MockMongo, mock_app_context):
    mock_mongo = MockMongo.return_value
    mock_blob = MockBlob.return_value
    mock_blob.upload_blob.return_value = {"date": "2025-01-01T00:00:00Z"}

    from app.routers.logics.schemavault import Schemas

    schemas = Schemas(app_context=mock_app_context)
    file = MagicMock()
    schema = Schema(
        Id="s1",
        ClassName="Invoice",
        Description="desc",
        FileName="invoice.py",
        ContentType="text/x-python",
    )
    result = schemas.Add(file, schema)
    assert result.Created_On == "2025-01-01T00:00:00Z"
    mock_mongo.insert_document.assert_called_once()


@patch("app.routers.logics.schemavault.CosmosMongDBHelper")
@patch("app.routers.logics.schemavault.StorageBlobHelper")
def test_update(MockBlob, MockMongo, mock_app_context):
    mock_mongo = MockMongo.return_value
    mock_mongo.find_document.return_value = [
        {
            "Id": "s1",
            "ClassName": "Old",
            "Description": "desc",
            "FileName": "old.py",
            "ContentType": "text/x-python",
        }
    ]
    mock_blob = MockBlob.return_value
    mock_blob.replace_blob.return_value = {"date": "2025-06-01T00:00:00Z"}

    from app.routers.logics.schemavault import Schemas

    schemas = Schemas(app_context=mock_app_context)
    file = MagicMock()
    file.content_type = "text/x-python"
    result = schemas.Update(file, "s1", "NewClass")
    assert result.ClassName == "NewClass"
    mock_mongo.update_document.assert_called_once()


@patch("app.routers.logics.schemavault.CosmosMongDBHelper")
@patch("app.routers.logics.schemavault.StorageBlobHelper")
def test_update_not_found(MockBlob, MockMongo, mock_app_context):
    mock_mongo = MockMongo.return_value
    mock_mongo.find_document.return_value = []

    from app.routers.logics.schemavault import Schemas

    schemas = Schemas(app_context=mock_app_context)
    with pytest.raises(Exception, match="Schema not found"):
        schemas.Update(MagicMock(), "missing", "X")


@patch("app.routers.logics.schemavault.CosmosMongDBHelper")
@patch("app.routers.logics.schemavault.StorageBlobHelper")
def test_delete(MockBlob, MockMongo, mock_app_context):
    mock_mongo = MockMongo.return_value
    mock_mongo.find_document.return_value = [
        {
            "Id": "s1",
            "ClassName": "Invoice",
            "Description": "desc",
            "FileName": "invoice.py",
            "ContentType": "text/x-python",
        }
    ]

    from app.routers.logics.schemavault import Schemas

    schemas = Schemas(app_context=mock_app_context)
    result = schemas.Delete("s1")
    assert result.Id == "s1"
    mock_mongo.delete_document.assert_called_once_with("s1")


@patch("app.routers.logics.schemavault.CosmosMongDBHelper")
@patch("app.routers.logics.schemavault.StorageBlobHelper")
def test_delete_not_found(MockBlob, MockMongo, mock_app_context):
    mock_mongo = MockMongo.return_value
    mock_mongo.find_document.return_value = []

    from app.routers.logics.schemavault import Schemas

    schemas = Schemas(app_context=mock_app_context)
    with pytest.raises(Exception, match="Schema not found"):
        schemas.Delete("missing")
