# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the ClaimProcess and ClaimItem domain models."""

from __future__ import annotations

from unittest.mock import patch

from app.routers.models.contentprocessor.claim import ClaimItem, ClaimProcess

CONN = "mongodb://localhost:27017"
DB = "test_db"
COL = "test_col"


class TestClaimItem:
    def test_defaults(self):
        item = ClaimItem(claim_id="c1", schema_id="s1", metadata_id="m1")
        assert item.file_name is None
        assert item.size is None
        assert item.mime_type is None
        assert item.id is None


class TestClaimProcessSave:
    @patch("app.routers.models.contentprocessor.claim.CosmosMongDBHelper")
    def test_inserts_when_new(self, MockHelper):
        mock_helper = MockHelper.return_value
        mock_helper.find_document.return_value = []

        cp = ClaimProcess(claim_id="c1", schema_collection_id="ss1")
        cp.save(connection_string=CONN, database_name=DB, collection_name=COL)

        mock_helper.insert_document.assert_called_once()

    @patch("app.routers.models.contentprocessor.claim.CosmosMongDBHelper")
    def test_updates_when_existing(self, MockHelper):
        mock_helper = MockHelper.return_value
        mock_helper.find_document.return_value = [{"claim_id": "c1"}]

        cp = ClaimProcess(claim_id="c1", schema_collection_id="ss1")
        cp.save(connection_string=CONN, database_name=DB, collection_name=COL)

        mock_helper.update_document_by_query.assert_called_once()


class TestClaimProcessGet:
    @patch("app.routers.models.contentprocessor.claim.CosmosMongDBHelper")
    def test_returns_process_when_found(self, MockHelper):
        mock_helper = MockHelper.return_value
        mock_helper.find_document.return_value = [
            {"claim_id": "c1", "schema_collection_id": "ss1"}
        ]

        result = ClaimProcess.get(
            claim_id="c1",
            connection_string=CONN,
            database_name=DB,
            collection_name=COL,
        )
        assert isinstance(result, ClaimProcess)
        assert result.claim_id == "c1"

    @patch("app.routers.models.contentprocessor.claim.CosmosMongDBHelper")
    def test_returns_none_when_not_found(self, MockHelper):
        mock_helper = MockHelper.return_value
        mock_helper.find_document.return_value = []

        result = ClaimProcess.get(
            claim_id="missing",
            connection_string=CONN,
            database_name=DB,
            collection_name=COL,
        )
        assert result is None
