import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.routers.schemavault import router, get_schemas


app = FastAPI()
app.include_router(router)

client = TestClient(app)

mock_schemas = MagicMock()


@pytest.fixture
def override_get_schemas():
    def _override_get_schemas():
        return mock_schemas

    app.dependency_overrides[get_schemas] = _override_get_schemas
    yield
    app.dependency_overrides.clear()


def test_get_all_registered_schema(override_get_schemas):
    mock_schemas.GetAll.return_value = []
    response = client.get("/schemavault/")
    assert response.status_code == 200
    assert response.json() == []


# def test_register_schema(override_get_schemas):
#     mock_schemas.Add.return_value = {
#         "Id": "test-id",
#         "ClassName": "TestClass",
#         "Description": "Test description",
#         "FileName": "test.txt",
#         "ContentType": "text/plain",
#     }
#     data = {
#         "ClassName": "TestClass",
#         "Description": "Test description",
#     }
#     files = {"file": ("test.txt", b"test content", "text/plain")}
#     response = client.post(
#         "/schemavault/",
#         data=data,
#         files=files,
#         headers={"Content-Type": "multipart/form-data"},
#     )
#     assert response.status_code == 200


# def test_update_schema(override_get_schemas):
#     mock_schemas.Update.return_value = {
#         "Id": "test-id",
#         "ClassName": "UpdatedClass",
#         "Description": "Updated description",
#         "FileName": "updated.txt",
#         "ContentType": "text/plain",
#     }
#     data = {
#         "SchemaId": "test-id",
#         "ClassName": "UpdatedClass",
#     }
#     files = {"file": ("updated.txt", b"updated content", "text/plain")}
#     response = client.put(
#         "/schemavault/",
#         data=data,
#         files=files,
#         headers={"Content-Type": "multipart/form-data"},
#     )
#     assert response.status_code == 200


# def test_unregister_schema(override_get_schemas):
#     mock_schemas.Delete.return_value = {
#         "Id": "test-id",
#         "ClassName": "TestClass",
#         "FileName": "test.txt",
#     }
#     data = SchemaVaultUnregisterRequest(SchemaId="test-id")
#     response = client.delete(
#         "/schemavault/",
#         data=data.model_dump(),
#     )

#     assert response.status_code == 200
#     assert response.json() == {
#         "Status": "Success",
#         "SchemaId": "test-id",
#         "ClassName": "TestClass",
#         "FileName": "test.txt",
#     }


def test_get_registered_schema_file_by_schema_id(override_get_schemas):
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


def test_get_registered_schema_file_by_schema_id_500_error(override_get_schemas):
    mock_schemas.GetFile.side_effect = Exception("Internal Server Error")

    response = client.get("/schemavault/schemas/test-id")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
