import base64
from libs.utils.base64_util import is_base64_encoded


def test_is_base64_encoded_valid():
    valid_base64 = base64.b64encode(b"test data").decode("utf-8")
    assert is_base64_encoded(valid_base64) is True


def test_is_base64_encoded_invalid():
    invalid_base64 = "invalid_base64_string"
    assert is_base64_encoded(invalid_base64) is False


def test_is_base64_encoded_empty_string():
    empty_string = " "
    assert is_base64_encoded(empty_string) is False


def test_is_base64_encoded_special_characters():
    special_characters = "!@#$%^&*()"
    assert is_base64_encoded(special_characters) is False


def test_is_base64_encoded_partial_base64():
    partial_base64 = base64.b64encode(b"test").decode("utf-8")[:5]
    assert is_base64_encoded(partial_base64) is False
