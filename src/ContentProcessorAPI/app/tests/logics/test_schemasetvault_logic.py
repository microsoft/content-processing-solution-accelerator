# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the SchemaSets (schema-set vault) logic class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.routers.models.schmavault.model import SchemaSet


@pytest.fixture
def mock_app_context():
    ctx = MagicMock()
    ctx.configuration.app_storage_blob_url = "https://blob.example.com"
    ctx.configuration.app_cps_configuration = "config"
    ctx.configuration.app_cosmos_container_schemaset = "schemasets"
    ctx.configuration.app_cosmos_container_schema = "schemas"
    ctx.configuration.app_cosmos_connstr = "mongodb://localhost"
    ctx.configuration.app_cosmos_database = "db"
    return ctx


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_get_all(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.find_document.return_value = [
        {"Id": "ss1", "Name": "Claims", "Description": "d", "Schemas": []}
    ]

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    result = ss.GetAll()
    assert len(result) == 1
    assert isinstance(result[0], SchemaSet)


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_add_new(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    result = ss.AddNew("TestSet", "A test set")
    assert result.Name == "TestSet"
    assert result.Description == "A test set"
    instance.insert_document.assert_called_once()


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_get_by_id_found(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.find_document.return_value = [
        {"Id": "ss1", "Name": "Claims", "Description": "d", "Schemas": []}
    ]

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    result = ss.GetById("ss1")
    assert result is not None
    assert result.Id == "ss1"


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_get_by_id_not_found(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.find_document.return_value = []

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    assert ss.GetById("missing") is None


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_delete_by_id(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.delete_document.return_value = MagicMock(deleted_count=1)

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    assert ss.DeleteById("ss1") is True


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_delete_by_id_not_found(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.delete_document.return_value = MagicMock(deleted_count=0)

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    assert ss.DeleteById("missing") is False


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_add_schema_to_set(MockBlob, MockMongo, mock_app_context):
    schemaset_instance = MagicMock()
    schema_instance = MagicMock()

    schemaset_instance.find_document.return_value = [
        {"Id": "ss1", "Name": "Claims", "Description": "d", "Schemas": []}
    ]
    schema_instance.find_document.return_value = [
        {
            "Id": "s1",
            "ClassName": "Invoice",
            "Description": "desc",
            "FileName": "invoice.py",
            "ContentType": "text/x-python",
        }
    ]

    MockMongo.side_effect = [schemaset_instance, schema_instance]

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    # Replace helpers injected during __init__
    ss.mongoHelper_schemasets = schemaset_instance
    ss.mongoHelper_schemas = schema_instance

    result = ss.AddSchemaToSet("ss1", "s1")
    assert len(result.Schemas) == 1
    schemaset_instance.update_document_by_query.assert_called_once()


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_add_schema_to_set_not_found(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.find_document.return_value = []

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    with pytest.raises(Exception, match="Schema Set not found"):
        ss.AddSchemaToSet("missing", "s1")


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_add_schema_to_set_schema_not_found(MockBlob, MockMongo, mock_app_context):
    schemaset_instance = MagicMock()
    schema_instance = MagicMock()

    schemaset_instance.find_document.return_value = [
        {"Id": "ss1", "Name": "Claims", "Description": "d", "Schemas": []}
    ]
    schema_instance.find_document.return_value = []

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    ss.mongoHelper_schemasets = schemaset_instance
    ss.mongoHelper_schemas = schema_instance

    with pytest.raises(Exception, match="Schema not found"):
        ss.AddSchemaToSet("ss1", "missing")


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_remove_schema_from_set(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.find_document.return_value = [
        {
            "Id": "ss1",
            "Name": "Claims",
            "Description": "d",
            "Schemas": [
                {"Id": "sm1", "SchemaId": "s1", "Description": "d1"},
                {"Id": "sm2", "SchemaId": "s2", "Description": "d2"},
            ],
        }
    ]

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    result = ss.RemoveSchemaFromSet("ss1", "s1")
    assert len(result.Schemas) == 1
    assert result.Schemas[0].SchemaId == "s2"


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_remove_schema_from_set_not_found(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.find_document.return_value = []

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    with pytest.raises(Exception, match="Schema Set not found"):
        ss.RemoveSchemaFromSet("missing", "s1")


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_get_all_schemas_in_set(MockBlob, MockMongo, mock_app_context):
    schemaset_instance = MagicMock()
    schema_instance = MagicMock()

    schemaset_instance.find_document.return_value = [
        {
            "Id": "ss1",
            "Name": "Claims",
            "Description": "d",
            "Schemas": [{"Id": "sm1", "SchemaId": "s1", "Description": "d1"}],
        }
    ]
    schema_instance.find_document.return_value = [
        {
            "Id": "s1",
            "ClassName": "Invoice",
            "Description": "d1",
            "FileName": "invoice.py",
            "ContentType": "text/x-python",
        }
    ]

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    ss.mongoHelper_schemasets = schemaset_instance
    ss.mongoHelper_schemas = schema_instance

    result = ss.GetAllSchemasInSet("ss1")
    assert len(result) == 1
    assert result[0].ClassName == "Invoice"


@patch("app.routers.logics.schemasetvault.CosmosMongDBHelper")
@patch("app.routers.logics.schemasetvault.StorageBlobHelper")
def test_get_all_schemas_in_set_not_found(MockBlob, MockMongo, mock_app_context):
    instance = MockMongo.return_value
    instance.find_document.return_value = []

    from app.routers.logics.schemasetvault import SchemaSets

    ss = SchemaSets(app_context=mock_app_context)
    with pytest.raises(Exception, match="Schema Set not found"):
        ss.GetAllSchemasInSet("missing")
