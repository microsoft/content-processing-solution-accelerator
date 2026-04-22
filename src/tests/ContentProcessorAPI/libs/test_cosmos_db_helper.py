# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for CosmosMongDBHelper."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ContentProcessorAPI")))

from app.libs.azure.cosmos_db.helper import CosmosMongDBHelper  # noqa: E402


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_cosmos_mongodb_helper_init(mock_certifi, mock_mongo_client):
    """Test CosmosMongDBHelper initialization."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = []
    mock_container = MagicMock()
    mock_db.create_collection.return_value = mock_container
    mock_db.__getitem__.return_value = mock_container

    helper = CosmosMongDBHelper(
        connection_string="mongodb://test",
        db_name="test_db",
        container_name="test_container"
    )

    assert helper.client == mock_client
    assert helper.db == mock_db
    assert helper.container == mock_container


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_insert_document(mock_certifi, mock_mongo_client):
    """Test insert_document method."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = ["test_container"]
    mock_container = MagicMock()
    mock_db.__getitem__.return_value = mock_container

    helper = CosmosMongDBHelper("mongodb://test", "test_db", "test_container")

    document = {"key": "value"}
    mock_result = MagicMock()
    mock_container.insert_one.return_value = mock_result

    result = helper.insert_document(document)

    assert result == mock_result
    mock_container.insert_one.assert_called_once_with(document)


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_find_document(mock_certifi, mock_mongo_client):
    """Test find_document method."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = ["test_container"]
    mock_container = MagicMock()
    mock_db.__getitem__.return_value = mock_container

    helper = CosmosMongDBHelper("mongodb://test", "test_db", "test_container")

    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_container.find.return_value = mock_cursor
    mock_items = [{"id": 1}, {"id": 2}]
    mock_cursor.__iter__.return_value = iter(mock_items)

    query = {"key": "value"}
    helper.find_document(
        query=query,
        sort_fields=[("field", 1)],
        skip=10,
        limit=5,
        projection=["field1"]
    )

    mock_container.find.assert_called_once_with(query, ["field1"])
    mock_cursor.sort.assert_called_once_with([("field", 1)])
    mock_cursor.skip.assert_called_once_with(10)
    mock_cursor.limit.assert_called_once_with(5)


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_count_documents(mock_certifi, mock_mongo_client):
    """Test count_documents method."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = ["test_container"]
    mock_container = MagicMock()
    mock_db.__getitem__.return_value = mock_container

    helper = CosmosMongDBHelper("mongodb://test", "test_db", "test_container")

    mock_container.count_documents.return_value = 42

    result = helper.count_documents({"key": "value"})
    assert result == 42

    result = helper.count_documents()
    mock_container.count_documents.assert_called_with({})


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_update_document(mock_certifi, mock_mongo_client):
    """Test update_document method."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = ["test_container"]
    mock_container = MagicMock()
    mock_db.__getitem__.return_value = mock_container

    helper = CosmosMongDBHelper("mongodb://test", "test_db", "test_container")

    mock_result = MagicMock()
    mock_container.update_one.return_value = mock_result

    update = {"field": "new_value"}
    result = helper.update_document("test_id", update)

    assert result == mock_result
    mock_container.update_one.assert_called_once_with({"Id": "test_id"}, {"$set": update})


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_delete_document(mock_certifi, mock_mongo_client):
    """Test delete_document method."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = ["test_container"]
    mock_container = MagicMock()
    mock_db.__getitem__.return_value = mock_container

    helper = CosmosMongDBHelper("mongodb://test", "test_db", "test_container")

    mock_result = MagicMock()
    mock_container.delete_one.return_value = mock_result

    helper.delete_document("test_id")
    mock_container.delete_one.assert_called_once_with({"Id": "test_id"})


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_update_document_by_query(mock_certifi, mock_mongo_client):
    """Test update_document_by_query method."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = ["test_container"]
    mock_container = MagicMock()
    mock_db.__getitem__.return_value = mock_container

    helper = CosmosMongDBHelper("mongodb://test", "test_db", "test_container")

    mock_result = MagicMock()
    mock_container.update_one.return_value = mock_result

    query = {"key": "value"}
    update = {"field": "new_value"}
    result = helper.update_document_by_query(query, update)

    assert result == mock_result
    mock_container.update_one.assert_called_once_with(query, {"$set": update})


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_init_with_indexes(mock_certifi, mock_mongo_client):
    """Test CosmosMongDBHelper initialization with indexes creates missing indexes."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = ["test_container"]
    mock_container = MagicMock()
    mock_db.__getitem__.return_value = mock_container
    mock_container.index_information.return_value = {}

    CosmosMongDBHelper(
        connection_string="mongodb://test",
        db_name="test_db",
        container_name="test_container",
        indexes=[("field1", 1), ("field2", -1)],
    )

    assert mock_container.create_index.call_count == 2


@patch("app.libs.azure.cosmos_db.helper.MongoClient")
@patch("app.libs.azure.cosmos_db.helper.certifi.where")
def test_create_container_when_missing(mock_certifi, mock_mongo_client):
    """Test _create_container creates collection when it does not exist."""
    mock_certifi.return_value = "/path/to/cert"
    mock_client = MagicMock()
    mock_mongo_client.return_value = mock_client
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.list_collection_names.return_value = []
    mock_container = MagicMock()
    mock_db.__getitem__.return_value = mock_container

    CosmosMongDBHelper("mongodb://test", "test_db", "new_container")

    mock_db.create_collection.assert_called_once_with("new_container")
