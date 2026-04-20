"""Targeted tests for small utility gaps to reach 80%"""
from unittest.mock import patch


class TestBase64Util:
    """Tests for base64_util to fill gaps"""

    def test_base64_decode_success(self):
        """Test successful base64 decoding"""
        from libs.utils.base64_util import base64_decode

        # Test basic decode
        encoded = "SGVsbG8gV29ybGQ="  # "Hello World"
        decoded = base64_decode(encoded)
        assert decoded == "Hello World"

    def test_base64_encode_decode_roundtrip(self):
        """Test encode/decode roundtrip"""
        from libs.utils.base64_util import base64_encode, base64_decode

        original = "Test data with special chars: !@#$%"
        encoded = base64_encode(original)
        decoded = base64_decode(encoded)
        assert decoded == original


class TestStopwatch:
    """Tests for stopwatch to fill gaps"""

    def test_stopwatch_reset(self):
        """Test stopwatch reset functionality"""
        from libs.utils.stopwatch import Stopwatch
        import time

        sw = Stopwatch()
        sw.start()
        time.sleep(0.01)
        sw.stop()

        # Reset should clear timing
        sw.reset()
        elapsed = sw.elapsed_time()
        assert elapsed == 0 or elapsed < 0.001

    def test_stopwatch_restart(self):
        """Test stopwatch restart"""
        from libs.utils.stopwatch import Stopwatch
        import time

        sw = Stopwatch()
        sw.start()
        time.sleep(0.01)

        # Restart should reset and start again
        sw.restart()
        new_elapsed = sw.elapsed_time()
        assert new_elapsed < 0.005  # Should be very small since just restarted


class TestUtils:
    """Tests for utils.py to fill gaps"""

    def test_value_in_list(self):
        """Test checking if value is in a list"""
        from libs.utils.utils import value_in_list

        test_list = ["apple", "banana", "cherry"]
        assert value_in_list("banana", test_list) is True
        assert value_in_list("grape", test_list) is False

    def test_get_nested_value(self):
        """Test getting nested dictionary values"""
        from libs.utils.utils import get_nested_value

        data = {
            "level1": {
                "level2": {
                    "level3": "found_value"
                }
            }
        }

        result = get_nested_value(data, "level1.level2.level3")
        assert result == "found_value"

    def test_safe_get_with_default(self):
        """Test safe dictionary get with default"""
        from libs.utils.utils import safe_get

        data = {"key1": "value1"}

        # Existing key
        result1 = safe_get(data, "key1", "default")
        assert result1 == "value1"

        # Missing key - should return default
        result2 = safe_get(data, "missing_key", "default_value")
        assert result2 == "default_value"

    def test_remove_none_values(self):
        """Test removing None values from dict"""
        from libs.utils.utils import remove_none_values

        data = {
            "key1": "value1",
            "key2": None,
            "key3": "value3",
            "key4": None
        }

        cleaned = remove_none_values(data)
        assert "key1" in cleaned
        assert "key3" in cleaned
        assert "key2" not in cleaned
        assert "key4" not in cleaned
