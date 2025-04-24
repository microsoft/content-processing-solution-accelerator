import pytest
from libs.azure_helper.comsos_mongo import CosmosMongDBHelper
import mongomock


@pytest.fixture
def mock_mongo_client(monkeypatch):
    def mock_mongo_client_init(*args, **kwargs):
        return mongomock.MongoClient()

    monkeypatch.setattr(
        "libs.azure_helper.comsos_mongo.MongoClient", mock_mongo_client_init
    )
    return mongomock.MongoClient()


def test_prepare(mock_mongo_client, monkeypatch):
    indexes = ["field1", "field2"]
    helper = CosmosMongDBHelper(
        "connection_string", "db_name", "container_name", indexes=indexes
    )

    assert helper.client is not None
    assert helper.db is not None
    assert helper.container is not None
    monkeypatch.setattr(helper.container, "index_information", lambda: indexes)
    helper._create_indexes(helper.container, indexes)
    index_info = helper.container.index_information()
    for index in indexes:
        assert f"{index}" in index_info


def test_insert_document(mock_mongo_client):
    helper = CosmosMongDBHelper("connection_string", "db_name", "container_name")

    document = {"key": "value"}
    helper.insert_document(document)

    assert helper.container.find_one(document) is not None


def test_find_document(mock_mongo_client):
    helper = CosmosMongDBHelper("connection_string", "db_name", "container_name")

    query = {"key": "value"}
    helper.insert_document(query)
    result = helper.find_document(query)

    assert len(result) == 1
    assert result[0] == query


def test_find_document_with_sort(mock_mongo_client):
    helper = CosmosMongDBHelper("connection_string", "db_name", "container_name")

    documents = [{"key": "value1", "sort_field": 2}, {"key": "value2", "sort_field": 1}]
    for doc in documents:
        helper.insert_document(doc)

    query = {}
    sort_fields = [("sort_field", 1)]
    result = helper.find_document(query, sort_fields)

    assert len(result) == 2
    assert result[0]["key"] == "value2"
    assert result[1]["key"] == "value1"


def test_update_document(mock_mongo_client):
    helper = CosmosMongDBHelper("connection_string", "db_name", "container_name")

    filter = {"key": "value"}
    update = {"key": "new_value"}
    helper.insert_document(filter)
    helper.update_document(filter, update)

    result = helper.find_document(update)
    assert len(result) == 1
    assert result[0]["key"] == "new_value"


def test_delete_document(mock_mongo_client):
    helper = CosmosMongDBHelper("connection_string", "db_name", "container_name")

    helper.insert_document({"Id": "123"})
    helper.delete_document("123")

    result = helper.find_document({"Id": "123"})
    assert len(result) == 0
