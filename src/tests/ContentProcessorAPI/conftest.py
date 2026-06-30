"""
Test configuration for ContentProcessorAPI tests.
"""
import sys
import os

# Add ContentProcessorAPI to path
contentprocessorapi_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'ContentProcessorAPI')
)
sys.path.insert(0, contentprocessorapi_path)

# Mock environment variables before any imports
os.environ.setdefault("APP_CONFIG_ENDPOINT", "https://test-endpoint.azconfig.io")
os.environ.setdefault("APP_STORAGE_BLOB_URL", "https://test.blob.core.windows.net")
os.environ.setdefault("APP_STORAGE_QUEUE_URL", "https://test.queue.core.windows.net")
os.environ.setdefault("APP_COSMOS_CONNSTR", "mongodb://test")
os.environ.setdefault("APP_COSMOS_DATABASE", "test_db")
os.environ.setdefault("APP_COSMOS_CONTAINER_SCHEMA", "schemas")
os.environ.setdefault("APP_COSMOS_CONTAINER_PROCESS", "processes")
os.environ.setdefault("APP_CPS_CONFIGURATION", "configuration")
os.environ.setdefault("APP_CPS_PROCESSES", "processes")
os.environ.setdefault("APP_MESSAGE_QUEUE_EXTRACT", "extract")
os.environ.setdefault("APP_CPS_MAX_FILESIZE_MB", "50")
os.environ.setdefault("APP_LOGGING_LEVEL", "INFO")
os.environ.setdefault("AZURE_PACKAGE_LOGGING_LEVEL", "WARNING")
os.environ.setdefault("AZURE_LOGGING_PACKAGES", "azure.core")

pytest_plugins = ["pytest_mock"]
