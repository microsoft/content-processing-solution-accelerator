import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

from app.appsettings import AppConfiguration

client = TestClient(app)


@pytest.fixture
def app_config():
    config = AppConfiguration()
    config.app_cosmos_connstr = "test_connection_string"
    config.app_cosmos_database = "test_database"
    config.app_cosmos_container_process = "test_container"
    config.app_cps_max_filesize_mb = 20
    config.app_storage_blob_url = "test_blob_url"
    return config


@pytest.fixture
def mock_app_config():
    with patch("app.routers.contentprocessor.get_app_config") as mock:
        yield mock


@pytest.fixture
def mock_cosmos_content_process():
    with patch("app.routers.contentprocessor.CosmosContentProcess") as mock:
        yield mock


@pytest.fixture
def mock_mime_types_detection():
    with patch("app.routers.contentprocessor.MimeTypesDetection") as mock:
        yield mock


@patch("app.routers.contentprocessor.get_app_config")
@patch(
    "app.routers.contentprocessor.CosmosContentProcess.get_all_processes_from_cosmos"
)
def test_get_all_processed_results(
    mock_get_all_processes, mock_get_app_config, app_config
):
    mock_get_app_config.return_value = app_config
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


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_status_processing(mock_get_status, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_get_status.return_value = MagicMock(status="processing")

    response = client.get("/contentprocessor/status/test_process_id")
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    assert "still in progress" in response.json()["message"]


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_status_completed(mock_get_status, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_get_status.return_value = MagicMock(status="Completed")

    response = client.get("/contentprocessor/status/test_process_id")
    assert response.status_code == 302
    assert response.json()["status"] == "completed"
    assert "is completed" in response.json()["message"]


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_status_failed(mock_get_status, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_get_status.return_value = None

    response = client.get("/contentprocessor/status/test_process_id")
    assert response.status_code == 404
    assert response.json()["status"] == "failed"
    assert "not found" in response.json()["message"]


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_process(mock_get_status, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
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


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_process_not_found(mock_get_status, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_get_status.return_value = None

    response = client.get("/contentprocessor/processed/test_process_id")
    assert response.status_code == 404
    assert response.json()["status"] == "failed"


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_blob")
def test_get_process_steps(mock_get_steps, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_get_steps.return_value = {"steps": []}

    response = client.get("/contentprocessor/processed/test_process_id/steps")
    assert response.status_code == 200
    assert response.json() == {"steps": []}


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_blob")
def test_get_process_steps_not_found(mock_get_steps, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_get_steps.return_value = None

    response = client.get("/contentprocessor/processed/test_process_id/steps")
    assert response.status_code == 404
    assert response.json()["status"] == "failed"


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.update_process_result")
def test_update_process_result(mock_update_result, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_update_result.return_value = MagicMock()

    data = {"process_id": "test_process_id", "modified_result": {"key": "value"}}
    response = client.put("/contentprocessor/processed/test_process_id", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.update_process_comment")
def test_update_process_comment(mock_update_comment, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_update_comment.return_value = MagicMock()

    data = {"process_id": "test_process_id", "comment": "new comment"}
    response = client.put("/contentprocessor/processed/test_process_id", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_get_original_file_success(
    mock_app_config, mock_cosmos_content_process, mock_mime_types_detection
):
    # Mocking the app config
    mock_app_config.return_value.app_cosmos_connstr = "mock_connstr"
    mock_app_config.return_value.app_cosmos_database = "mock_database"
    mock_app_config.return_value.app_cosmos_container_process = "mock_container_process"
    mock_app_config.return_value.app_storage_blob_url = "mock_blob_url"
    mock_app_config.return_value.app_cps_processes = "mock_cps_processes"

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


@patch("app.routers.contentprocessor.get_app_config")
@patch("app.routers.contentprocessor.CosmosContentProcess.get_status_from_cosmos")
def test_get_original_file_not_found(mock_get_status, mock_get_app_config, app_config):
    mock_get_app_config.return_value = app_config
    mock_get_status.return_value = None

    response = client.get("/contentprocessor/processed/files/test_process_id")
    assert response.status_code == 404
    assert response.json()["status"] == "failed"
