import pytest
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from app.libs.cosmos_db.helper import CosmosMongDBHelper


@pytest.fixture
def mock_mongo_client(mocker):
    client = mocker.MagicMock(spec=MongoClient)
    return client


@pytest.fixture
def mock_database(mocker):
    db = mocker.MagicMock(spec=Database)
    db.list_collection_names.return_value = []
    return db


@pytest.fixture
def mock_collection(mocker):
    collection = mocker.Mock(spec=Collection)
    collection.insert_one.return_value = mocker.Mock(inserted_id="mock_id")
    collection.find.return_value = [{"key": "value"}]
    collection.count_documents.return_value = 1
    collection.update_one.return_value = mocker.Mock(matched_count=1, modified_count=1)
    collection.delete_one.return_value = mocker.Mock(deleted_count=1)
    return collection


@pytest.fixture
def cosmos_mongo_db_helper(mock_mongo_client, mock_database, mock_collection, mocker):
    # Mock the MongoClient to return the mock database
    mocker.patch(
        "app.libs.cosmos_db.helper.MongoClient", return_value=mock_mongo_client
    )
    mock_mongo_client.__getitem__.return_value = mock_database
    mock_database.__getitem__.return_value = mock_collection

    # Initialize the CosmosMongDBHelper with the mocked client
    helper = CosmosMongDBHelper(
        connection_string="mongodb://localhost:27017",
        db_name="test_db",
        container_name="test_collection",
    )
    helper.client = mock_mongo_client
    helper.db = mock_database
    helper.container = mock_collection
    return helper


def test_insert_document(cosmos_mongo_db_helper, mock_collection):
    document = {"key": "value"}
    result = cosmos_mongo_db_helper.insert_document(document)
    mock_collection.insert_one.assert_called_once_with(document)
    assert result.inserted_id == "mock_id"


def test_find_document(cosmos_mongo_db_helper, mock_collection):
    query = {"key": "value"}
    result = cosmos_mongo_db_helper.find_document(query)
    mock_collection.find.assert_called_once_with(query, None)
    assert result == [{"key": "value"}]


def test_count_documents(cosmos_mongo_db_helper, mock_collection):
    query = {"key": "value"}
    result = cosmos_mongo_db_helper.count_documents(query)
    mock_collection.count_documents.assert_called_once_with(query)
    assert result == 1


def test_update_document(cosmos_mongo_db_helper, mock_collection):
    item_id = "123"
    update = {"key": "new_value"}
    result = cosmos_mongo_db_helper.update_document(item_id, update)
    mock_collection.update_one.assert_called_once_with(
        {"Id": item_id}, {"$set": update}
    )
    assert result.matched_count == 1
    assert result.modified_count == 1


def test_delete_document(cosmos_mongo_db_helper, mock_collection):
    item_id = "123"
    result = cosmos_mongo_db_helper.delete_document(item_id)
    mock_collection.delete_one.assert_called_once_with({"Id": item_id})
    assert result.deleted_count == 1
