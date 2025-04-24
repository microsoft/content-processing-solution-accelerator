import pytest
from unittest.mock import Mock
from libs.utils.utils import CustomEncoder, flatten_dict, value_match, value_contains


def test_custom_encoder_to_dict(mocker):
    obj = Mock()
    obj.to_dict.return_value = {"key": "value"}
    encoder = CustomEncoder()
    result = encoder.default(obj)
    assert result == {"key": "value"}


def test_custom_encoder_default(mocker):
    class UnserializableObject:
        pass

    obj = UnserializableObject()
    encoder = CustomEncoder()
    with pytest.raises(TypeError):
        encoder.default(obj)


def test_flatten_dict():
    data = {"a": 1, "b": {"c": 2, "d": {"e": 3}}, "f": [4, 5, {"g": 6}]}
    result = flatten_dict(data)
    expected = {"a": 1, "b_c": 2, "b_d_e": 3, "f_0": 4, "f_1": 5, "f_2_g": 6}
    assert result == expected


def test_value_match_strings():
    assert value_match("Hello", "hello") is True
    assert value_match("Hello", "world") is False


def test_value_match_lists():
    assert value_match([1, 2, 3], [1, 2, 3]) is True
    assert value_match([1, 2, 3], [1, 2, 4]) is False


def test_value_match_dicts():
    assert value_match({"a": 1, "b": 2}, {"a": 1, "b": 2}) is True
    assert value_match({"a": 1, "b": 2}, {"a": 1, "b": 3}) is False


def test_value_contains_strings():
    assert value_contains("hello", "Hello world") is True
    assert value_contains("world", "Hello world") is True
    assert value_contains("test", "Hello world") is False


def test_value_contains_lists():
    assert value_contains([4], [1, 2, 3]) is False


def test_value_contains_dicts():
    assert value_contains({"c": 3}, {"a": 1, "b": 2}) is False
