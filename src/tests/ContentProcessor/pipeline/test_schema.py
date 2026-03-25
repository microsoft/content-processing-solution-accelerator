# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.entities.schema (Schema model and Cosmos lookup)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from libs.pipeline.entities.schema import Schema

# ── TestSchema ──────────────────────────────────────────────────────────


class TestSchema:
    """Schema model construction and get_schema lookups."""

    def test_construction(self):
        schema = Schema(
            Id="s-1",
            ClassName="InvoiceSchema",
            Description="Invoice extraction",
            FileName="invoice_schema.py",
            ContentType="application/pdf",
        )
        assert schema.Id == "s-1"
        assert schema.ClassName == "InvoiceSchema"
        assert schema.Created_On is None

    def test_get_schema_raises_on_empty_id(self):
        with pytest.raises(Exception, match="Schema Id is not provided"):
            Schema.get_schema("connstr", "db", "coll", "")

    def test_get_schema_raises_on_none_id(self):
        with pytest.raises(Exception, match="Schema Id is not provided"):
            Schema.get_schema("connstr", "db", "coll", None)

    @patch("libs.pipeline.entities.schema.CosmosMongDBHelper")
    def test_get_schema_returns_schema(self, mock_helper_cls):
        mock_instance = MagicMock()
        mock_helper_cls.return_value = mock_instance
        mock_instance.find_document.return_value = [
            {
                "Id": "s-1",
                "ClassName": "MySchema",
                "Description": "desc",
                "FileName": "file.py",
                "ContentType": "text/plain",
            }
        ]
        result = Schema.get_schema("connstr", "db", "coll", "s-1")
        assert result.Id == "s-1"
        assert result.ClassName == "MySchema"

    @patch("libs.pipeline.entities.schema.CosmosMongDBHelper")
    def test_get_schema_raises_on_not_found(self, mock_helper_cls):
        mock_instance = MagicMock()
        mock_helper_cls.return_value = mock_instance
        mock_instance.find_document.return_value = []
        with pytest.raises(Exception, match="Schema with Id .* not found"):
            Schema.get_schema("connstr", "db", "coll", "missing-id")
