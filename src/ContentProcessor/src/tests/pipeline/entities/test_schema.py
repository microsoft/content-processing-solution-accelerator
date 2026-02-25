"""Tests for schema module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from libs.pipeline.entities.schema import Schema


class TestSchema:
    """Tests for Schema class."""

    def test_schema_creation(self):
        """Test creating a Schema object."""
        schema = Schema(
            Id="test-schema-123",
            ClassName="TestClass",
            Description="Test description",
            FileName="test.json",
            ContentType="application/json",
        )
        assert schema.Id == "test-schema-123"
        assert schema.ClassName == "TestClass"
        assert schema.Description == "Test description"
        assert schema.FileName == "test.json"
        assert schema.ContentType == "application/json"

    def test_schema_with_timestamps(self):
        """Test creating a Schema object with timestamps."""
        now = datetime.now()
        schema = Schema(
            Id="test-schema-123",
            ClassName="TestClass",
            Description="Test description",
            FileName="test.json",
            ContentType="application/json",
            Created_On=now,
            Updated_On=now,
        )
        assert schema.Created_On == now
        assert schema.Updated_On == now

    def test_get_schema_empty_id_raises(self):
        """Test that get_schema raises when schema_id is empty."""
        with pytest.raises(Exception, match="Schema Id is not provided"):
            Schema.get_schema(
                connection_string="conn_str",
                database_name="db",
                collection_name="collection",
                schema_id="",
            )

    def test_get_schema_none_id_raises(self):
        """Test that get_schema raises when schema_id is None."""
        with pytest.raises(Exception, match="Schema Id is not provided"):
            Schema.get_schema(
                connection_string="conn_str",
                database_name="db",
                collection_name="collection",
                schema_id=None,
            )

    @patch("libs.pipeline.entities.schema.CosmosMongDBHelper")
    def test_get_schema_not_found_raises(self, mock_cosmos):
        """Test that get_schema raises when schema is not found."""
        mock_instance = MagicMock()
        mock_instance.find_document.return_value = []
        mock_cosmos.return_value = mock_instance

        with pytest.raises(Exception, match="not found in"):
            Schema.get_schema(
                connection_string="conn_str",
                database_name="db",
                collection_name="collection",
                schema_id="nonexistent-id",
            )

    @patch("libs.pipeline.entities.schema.CosmosMongDBHelper")
    def test_get_schema_success(self, mock_cosmos):
        """Test successful schema retrieval."""
        mock_instance = MagicMock()
        mock_instance.find_document.return_value = [
            {
                "Id": "test-123",
                "ClassName": "TestClass",
                "Description": "Test",
                "FileName": "test.json",
                "ContentType": "application/json",
            }
        ]
        mock_cosmos.return_value = mock_instance

        result = Schema.get_schema(
            connection_string="conn_str",
            database_name="db",
            collection_name="collection",
            schema_id="test-123",
        )

        assert result.Id == "test-123"
        assert result.ClassName == "TestClass"
        mock_instance.find_document.assert_called_once_with({"Id": "test-123"})
