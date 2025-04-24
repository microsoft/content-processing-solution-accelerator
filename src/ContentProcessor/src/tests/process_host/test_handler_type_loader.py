import pytest
from libs.pipeline.queue_handler_base import HandlerBase
from libs.process_host.handler_type_loader import load


def test_load_success(mocker):
    process_step = "test"
    module_name = f"libs.pipeline.handlers.{process_step}_handler"
    class_name = f"{process_step.capitalize()}Handler"

    # Mock import_module to return a mock module
    mock_module = mocker.Mock()
    mock_import_module = mocker.patch(
        "importlib.import_module", return_value=mock_module
    )

    # Mock the dynamic class within the mock module
    mock_class = mocker.Mock(spec=HandlerBase)
    setattr(mock_module, class_name, mock_class)

    result = load(process_step)

    mock_import_module.assert_called_once_with(module_name)
    assert result == mock_class


def test_load_module_not_found(mocker):
    process_step = "nonexistent"
    class_name = f"{process_step.capitalize()}Handler"

    mocker.patch("importlib.import_module", side_effect=ModuleNotFoundError)

    with pytest.raises(Exception) as excinfo:
        load(process_step)

    assert str(excinfo.value) == f"Error loading processor {class_name}: "
