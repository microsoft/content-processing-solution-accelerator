"""Tests for handler_process_host module."""

from unittest.mock import Mock, patch

from libs.process_host.handler_process_host import HandlerInfo, HandlerHostManager


class TestHandlerInfo:
    """Tests for HandlerInfo class."""

    def test_handler_info_creation(self):
        """Test creating HandlerInfo."""
        handler_info = HandlerInfo()
        assert handler_info.handler is None
        assert handler_info.target_function is None
        assert handler_info.args is None


class TestHandlerHostManager:
    """Tests for HandlerHostManager class."""

    def test_init(self):
        """Test HandlerHostManager initialization."""
        manager = HandlerHostManager()
        assert manager.handlers == []

    @patch("libs.process_host.handler_process_host.Process")
    def test_restart_handler(self, mock_process_class):
        """Test restarting a handler."""
        mock_process = Mock()
        mock_process.start = Mock()
        mock_process.name = "test_handler"
        mock_process_class.return_value = mock_process

        manager = HandlerHostManager()
        mock_func = Mock()
        args = ("queue", Mock(), "handler")

        result = manager._restart_handler("test_handler", mock_func, args)

        mock_process_class.assert_called_once()
        mock_process.start.assert_called_once()
        assert result == mock_process
