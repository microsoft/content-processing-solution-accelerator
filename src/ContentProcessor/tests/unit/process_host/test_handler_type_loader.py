# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.process_host.handler_type_loader (dynamic handler import)."""

from __future__ import annotations

import pytest

from libs.pipeline.queue_handler_base import HandlerBase
from libs.process_host.handler_type_loader import load

# ── TestLoad ────────────────────────────────────────────────────────────


class TestLoad:
    """Dynamic handler class resolution by step name."""

    def test_load_success(self, mocker):
        mock_module = mocker.Mock()
        mock_import = mocker.patch("importlib.import_module", return_value=mock_module)
        mock_class = mocker.Mock(spec=HandlerBase)
        setattr(mock_module, "TestHandler", mock_class)

        result = load("test")

        mock_import.assert_called_once_with("libs.pipeline.handlers.test_handler")
        assert result == mock_class

    def test_load_module_not_found(self, mocker):
        mocker.patch("importlib.import_module", side_effect=ModuleNotFoundError)
        with pytest.raises(
            Exception, match="Error loading processor NonexistentHandler"
        ):
            load("nonexistent")
