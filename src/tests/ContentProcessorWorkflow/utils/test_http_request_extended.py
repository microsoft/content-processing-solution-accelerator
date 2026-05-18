"""Extended tests for http_request.py to improve coverage"""
from unittest.mock import Mock
from datetime import datetime, timedelta
from utils.http_request import (
    _join_url,
    _parse_retry_after_seconds,
    _WaitRetryAfterOrExponential,
    HttpResponse,
    HttpRequestError
)


class TestHttpRequestHelpers:
    """Test suite for HTTP request helper functions"""

    def test_join_url_with_base_and_relative(self):
        """Test joining base URL with relative path"""
        result = _join_url("https://api.example.com", "endpoint")
        assert result == "https://api.example.com/endpoint"

    def test_join_url_with_trailing_slash(self):
        """Test joining URL with trailing slash on base"""
        result = _join_url("https://api.example.com/", "endpoint")
        assert result == "https://api.example.com/endpoint"

    def test_join_url_with_leading_slash(self):
        """Test joining URL with leading slash on path"""
        result = _join_url("https://api.example.com", "/endpoint")
        assert result == "https://api.example.com/endpoint"

    def test_join_url_with_absolute_url(self):
        """Test joining with absolute URL should return the absolute URL"""
        result = _join_url("https://api.example.com", "https://other.com/path")
        assert result == "https://other.com/path"

    def test_join_url_with_http_absolute(self):
        """Test joining with http absolute URL"""
        result = _join_url("https://api.example.com", "http://other.com/path")
        assert result == "http://other.com/path"

    def test_join_url_with_none_base(self):
        """Test joining URL with None base"""
        result = _join_url(None, "endpoint")
        assert result == "endpoint"

    def test_join_url_with_empty_base(self):
        """Test joining URL with empty base"""
        result = _join_url("", "endpoint")
        assert result == "endpoint"

    def test_parse_retry_after_seconds_integer(self):
        """Test parsing retry-after header as integer seconds"""
        headers = {"Retry-After": "60"}
        result = _parse_retry_after_seconds(headers)
        assert result == 60.0

    def test_parse_retry_after_seconds_float(self):
        """Test parsing retry-after header as float seconds"""
        headers = {"retry-after": "30.5"}
        result = _parse_retry_after_seconds(headers)
        assert result == 30.5

    def test_parse_retry_after_seconds_case_insensitive(self):
        """Test parsing retry-after header case insensitively"""
        headers = {"RETRY-AFTER": "45"}
        result = _parse_retry_after_seconds(headers)
        assert result == 45.0

    def test_parse_retry_after_seconds_http_date(self):
        """Test parsing retry-after header as HTTP date"""
        future_time = datetime.utcnow() + timedelta(seconds=120)
        date_string = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers = {"Retry-After": date_string}
        result = _parse_retry_after_seconds(headers)
        assert result is not None
        assert 100 < result < 140  # Allow some variance

    def test_parse_retry_after_seconds_missing_header(self):
        """Test parsing retry-after when header is missing"""
        headers = {"Content-Type": "application/json"}
        result = _parse_retry_after_seconds(headers)
        assert result is None

    def test_parse_retry_after_seconds_invalid_format(self):
        """Test parsing retry-after with invalid format"""
        headers = {"Retry-After": "invalid"}
        result = _parse_retry_after_seconds(headers)
        assert result is None

    def test_parse_retry_after_seconds_empty_headers(self):
        """Test parsing retry-after with empty headers"""
        result = _parse_retry_after_seconds({})
        assert result is None


class TestWaitRetryAfterOrExponential:
    """Test suite for retry wait strategy"""

    def test_wait_strategy_initialization(self):
        """Test wait strategy initialization with custom parameters"""
        strategy = _WaitRetryAfterOrExponential(
            min_seconds=1.0,
            max_seconds=30.0,
            multiplier=2.0,
            jitter_seconds=0.5
        )
        assert strategy._min == 1.0
        assert strategy._max == 30.0
        assert strategy._mult == 2.0
        assert strategy._jitter == 0.5

    def test_wait_strategy_default_initialization(self):
        """Test wait strategy with default parameters"""
        strategy = _WaitRetryAfterOrExponential()
        assert strategy._min == 0.5
        assert strategy._max == 20.0
        assert strategy._mult == 1.5
        assert strategy._jitter == 0.2

    def test_wait_strategy_exponential_backoff(self):
        """Test exponential backoff calculation"""
        strategy = _WaitRetryAfterOrExponential(min_seconds=1.0, max_seconds=10.0, multiplier=2.0)

        # Create mock retry state
        retry_state = Mock()
        retry_state.attempt_number = 1
        retry_state.outcome = None

        wait_time = strategy(retry_state)
        assert 0.5 <= wait_time <= 10.0

    def test_wait_strategy_with_retry_after_header(self):
        """Test wait strategy using Retry-After header"""
        strategy = _WaitRetryAfterOrExponential(min_seconds=1.0, max_seconds=30.0)

        # Create mock response with Retry-After header
        response = HttpResponse(
            status=429,
            url="https://api.example.com",
            headers={"Retry-After": "15"},
            body=b""
        )

        # Create mock retry state
        retry_state = Mock()
        retry_state.attempt_number = 2
        retry_state.outcome = Mock()
        retry_state.outcome.failed = False
        retry_state.outcome.result.return_value = response

        wait_time = strategy(retry_state)
        assert wait_time == 15.0

    def test_wait_strategy_retry_after_below_min(self):
        """Test wait strategy when Retry-After is below minimum"""
        strategy = _WaitRetryAfterOrExponential(min_seconds=5.0, max_seconds=30.0)

        response = HttpResponse(
            status=429,
            url="https://api.example.com",
            headers={"Retry-After": "2"},
            body=b""
        )

        retry_state = Mock()
        retry_state.attempt_number = 1
        retry_state.outcome = Mock()
        retry_state.outcome.failed = False
        retry_state.outcome.result.return_value = response

        wait_time = strategy(retry_state)
        assert wait_time == 5.0  # Should be clamped to min

    def test_wait_strategy_retry_after_above_max(self):
        """Test wait strategy when Retry-After is above maximum"""
        strategy = _WaitRetryAfterOrExponential(min_seconds=1.0, max_seconds=10.0)

        response = HttpResponse(
            status=429,
            url="https://api.example.com",
            headers={"Retry-After": "60"},
            body=b""
        )

        retry_state = Mock()
        retry_state.attempt_number = 1
        retry_state.outcome = Mock()
        retry_state.outcome.failed = False
        retry_state.outcome.result.return_value = response

        wait_time = strategy(retry_state)
        assert wait_time == 10.0  # Should be clamped to max

    def test_wait_strategy_failed_outcome(self):
        """Test wait strategy with failed outcome"""
        strategy = _WaitRetryAfterOrExponential(min_seconds=1.0, max_seconds=10.0)

        retry_state = Mock()
        retry_state.attempt_number = 2
        retry_state.outcome = Mock()
        retry_state.outcome.failed = True

        wait_time = strategy(retry_state)
        assert 1.0 <= wait_time <= 10.0

    def test_wait_strategy_exception_handling(self):
        """Test wait strategy when exception occurs getting result"""
        strategy = _WaitRetryAfterOrExponential(min_seconds=1.0, max_seconds=10.0)

        retry_state = Mock()
        retry_state.attempt_number = 1
        retry_state.outcome = Mock()
        retry_state.outcome.failed = False
        retry_state.outcome.result.side_effect = Exception("Test error")

        wait_time = strategy(retry_state)
        assert 0.5 <= wait_time <= 10.0  # Should fall back to exponential


class TestHttpResponse:
    """Test suite for HttpResponse value object"""

    def test_http_response_creation(self):
        """Test creating HttpResponse"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com/endpoint",
            headers={"Content-Type": "application/json"},
            body=b'{"result": "success"}'
        )
        assert response.status == 200
        assert response.url == "https://api.example.com/endpoint"
        assert response.headers["Content-Type"] == "application/json"
        assert response.body == b'{"result": "success"}'

    def test_http_response_text_decoding(self):
        """Test decoding response body as text"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={},
            body=b"Hello World"
        )
        assert response.text() == "Hello World"

    def test_http_response_text_with_encoding(self):
        """Test decoding response body with specific encoding"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={},
            body="Héllo Wörld".encode("utf-8")
        )
        assert response.text("utf-8") == "Héllo Wörld"

    def test_http_response_json_parsing(self):
        """Test parsing response body as JSON"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={},
            body=b'{"status": "ok", "count": 42}'
        )
        data = response.json()
        assert data["status"] == "ok"
        assert data["count"] == 42

    def test_http_response_header_lookup(self):
        """Test case-insensitive header lookup"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={"Content-Type": "application/json", "X-Request-ID": "12345"},
            body=b""
        )
        assert response.header("content-type") == "application/json"
        assert response.header("Content-Type") == "application/json"
        assert response.header("x-request-id") == "12345"

    def test_http_response_header_not_found(self):
        """Test header lookup when header doesn't exist"""
        response = HttpResponse(
            status=200,
            url="https://api.example.com",
            headers={"Content-Type": "application/json"},
            body=b""
        )
        assert response.header("Missing-Header") is None


class TestHttpRequestError:
    """Test suite for HttpRequestError exception"""

    def test_http_request_error_creation(self):
        """Test creating HttpRequestError"""
        error = HttpRequestError(
            "Request failed",
            method="GET",
            url="https://api.example.com/endpoint",
            status=404
        )
        assert str(error) == "Request failed"
        assert error.method == "GET"
        assert error.url == "https://api.example.com/endpoint"
        assert error.status == 404

    def test_http_request_error_with_response_text(self):
        """Test HttpRequestError with response text"""
        error = HttpRequestError(
            "Server error",
            method="POST",
            url="https://api.example.com",
            status=500,
            response_text='{"error": "Internal server error"}'
        )
        assert error.response_text == '{"error": "Internal server error"}'

    def test_http_request_error_with_headers(self):
        """Test HttpRequestError with response headers"""
        headers = {"Content-Type": "application/json", "X-Error-Code": "ERR_500"}
        error = HttpRequestError(
            "Error occurred",
            method="PUT",
            url="https://api.example.com",
            status=500,
            response_headers=headers
        )
        assert error.response_headers == headers

    def test_http_request_error_minimal(self):
        """Test HttpRequestError with minimal information"""
        error = HttpRequestError("Simple error")
        assert str(error) == "Simple error"
        assert error.method is None
        assert error.url is None
        assert error.status is None
