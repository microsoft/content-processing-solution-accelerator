# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Async HTTP client with connection pooling, retries, OAuth, and polling.

Provides:
    HttpRequestClient  -- High-level async client built on ``aiohttp`` with
                          ``tenacity``-based retry policies, OAuth2 token
                          injection, multipart upload, and long-running
                          operation polling.
    HttpRequestError   -- Rich exception carrying method, URL, status, and
                          response body for failed HTTP calls.
    HttpResponse       -- Frozen response value-object (status, body, headers).
    MultipartFile      -- Descriptor for files in multipart form uploads.
    OAuthClientCredentials -- Token provider for OAuth2 client-credentials.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Mapping

import aiohttp
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_any,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
)


class HttpRequestError(RuntimeError):
    """Exception raised for HTTP request failures.

    Attributes:
            method: HTTP method that was used (GET, POST, etc.).
            url: Request URL.
            status: HTTP status code, if available.
            response_text: Decoded response body, if available.
            response_headers: Response headers mapping, if available.
    """

    def __init__(
        self,
        message: str,
        *,
        method: str | None = None,
        url: str | None = None,
        status: int | None = None,
        response_text: str | None = None,
        response_headers: Mapping[str, str] | None = None,
    ):
        super().__init__(message)
        self.method = method
        self.url = url
        self.status = status
        self.response_text = response_text
        self.response_headers = response_headers


@dataclass(frozen=True)
class HttpResponse:
    """Immutable HTTP response value-object.

    Attributes:
            status: HTTP status code.
            url: Final (possibly redirected) URL.
            headers: Response headers as a string mapping.
            body: Raw response body bytes.
    """

    status: int
    url: str
    headers: Mapping[str, str]
    body: bytes

    def text(self, encoding: str | None = None) -> str:
        """Decode the response body as text."""
        return self.body.decode(encoding or "utf-8", errors="replace")

    def json(self) -> Any:
        """Parse the response body as JSON."""
        return json.loads(self.body)

    def header(self, name: str) -> str | None:
        """Return the first header value matching *name* (case-insensitive)."""
        for k, v in self.headers.items():
            if k.lower() == name.lower():
                return v
        return None


TokenProvider = Callable[[], Awaitable[str]]
PollCallback = Callable[[HttpResponse], Awaitable[None] | None]


def _join_url(base_url: str | None, url: str) -> str:
    """Combine a base URL with a relative path, preserving absolute URLs."""
    if not base_url:
        return url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return base_url.rstrip("/") + "/" + url.lstrip("/")


def _parse_retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """Extract a ``Retry-After`` header value as seconds, or ``None``."""
    retry_after = None
    for k, v in headers.items():
        if k.lower() == "retry-after":
            retry_after = v
            break
    if not retry_after:
        return None

    retry_after = retry_after.strip()
    # seconds
    try:
        return float(retry_after)
    except ValueError:
        pass

    # http-date
    try:
        dt = datetime.strptime(retry_after, "%a, %d %b %Y %H:%M:%S GMT")
        delta = dt - datetime.utcnow()
        return max(delta.total_seconds(), 0.0)
    except Exception:
        return None


class _WaitRetryAfterOrExponential:
    """Tenacity wait strategy that honours ``Retry-After`` or falls back to exponential backoff."""

    def __init__(
        self,
        *,
        min_seconds: float = 0.5,
        max_seconds: float = 20.0,
        multiplier: float = 1.5,
        jitter_seconds: float = 0.2,
    ):
        self._min = min_seconds
        self._max = max_seconds
        self._mult = multiplier
        self._jitter = jitter_seconds

    def __call__(self, retry_state: RetryCallState) -> float:
        # Prefer Retry-After (e.g., 429).
        try:
            if retry_state.outcome and retry_state.outcome.failed is False:
                result = retry_state.outcome.result()
                if isinstance(result, HttpResponse):
                    ra = _parse_retry_after_seconds(result.headers)
                    if ra is not None:
                        return min(max(ra, self._min), self._max)
        except Exception:
            # Intentionally ignore non-critical errors while inspecting Retry-After
            # and fall back to exponential backoff below.
            pass

        attempt = max(retry_state.attempt_number, 1)
        base = self._min * (self._mult ** (attempt - 1))
        jitter = min(self._jitter * attempt, self._max)
        # Deterministic-ish jitter without random dependency.
        frac = (time.perf_counter() % 1.0) - 0.5
        return max(self._min, min(self._max, base + (jitter * frac)))


class OAuthClientCredentials:
    """Token provider for OAuth2 client-credentials.

    This is intentionally minimal and compatible with most providers.
    It caches the token until shortly before expiration.
    """

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
        extra_form_fields: Mapping[str, str] | None = None,
    ):
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._extra_form_fields = dict(extra_form_fields or {})
        self._lock = asyncio.Lock()
        self._access_token: str | None = None
        self._expires_at: datetime | None = None

    async def get_token(self, session: aiohttp.ClientSession) -> str:
        async with self._lock:
            if self._access_token and self._expires_at:
                # Refresh a bit early to avoid race/clock skew.
                if datetime.utcnow() < (self._expires_at - timedelta(seconds=30)):
                    return self._access_token

            form = {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            }
            if self._scope:
                form["scope"] = self._scope
            form.update(self._extra_form_fields)

            async with session.post(
                self._token_url,
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                body = await resp.read()
                if resp.status < 200 or resp.status >= 300:
                    raise HttpRequestError(
                        "OAuth token request failed",
                        method="POST",
                        url=str(resp.url),
                        status=resp.status,
                        response_text=body.decode("utf-8", errors="replace"),
                        response_headers=dict(resp.headers),
                    )

            payload = json.loads(body)
            token = payload.get("access_token")
            if not token:
                raise HttpRequestError(
                    "OAuth token response missing access_token",
                    method="POST",
                    url=self._token_url,
                    response_text=str(payload),
                )

            expires_in = payload.get("expires_in")
            try:
                expires_in_s = int(expires_in) if expires_in is not None else 3600
            except Exception:
                expires_in_s = 3600

            self._access_token = str(token)
            self._expires_at = datetime.utcnow() + timedelta(seconds=expires_in_s)
            return self._access_token


@dataclass(frozen=True)
class MultipartFile:
    """Descriptor for a file part in a multipart form upload.

    Attributes:
            field_name: Form field name.
            filename: Filename to include in the Content-Disposition header.
            content: Raw bytes or a ``Path`` to read from disk.
            content_type: MIME type; defaults to ``application/octet-stream``.
    """

    field_name: str
    filename: str
    content: bytes | Path
    content_type: str | None = None


class HttpRequestClient:
    """Async HTTP client with pooling, retries, OAuth, and polling support.

    Uses:
    - `aiohttp.ClientSession` for connection pooling and async I/O
    - `tenacity` for retry policies

    Typical usage:

            async with HttpRequestClient(base_url="https://api.example.com", token_provider=token) as client:
                    resp = await client.get_json("/v1/items")
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        retry_attempts: int = 3,
        retry_statuses: Iterable[int] = (408, 429, 500, 502, 503, 504),
        pool_limit: int = 100,
        pool_limit_per_host: int = 20,
        default_headers: Mapping[str, str] | None = None,
        token_provider: TokenProvider | None = None,
        user_agent: str = "ContentProcessWorkflow/HttpRequestClient",
        session: aiohttp.ClientSession | None = None,
    ):
        """Initialise the HTTP client.

        Args:
                base_url: Optional base URL prepended to relative paths.
                timeout_seconds: Total request timeout.
                retry_attempts: Maximum number of retry attempts.
                retry_statuses: HTTP status codes eligible for automatic retry.
                pool_limit: Global connection pool limit.
                pool_limit_per_host: Per-host connection limit.
                default_headers: Headers merged into every request.
                token_provider: Async callable returning a bearer token.
                user_agent: Default User-Agent header value.
                session: Externally managed ``aiohttp.ClientSession``; when
                        provided the client will not own or close it.
        """
        self._base_url = base_url
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._retry_attempts = max(int(retry_attempts), 1)
        self._retry_statuses = set(retry_statuses)
        self._default_headers = dict(default_headers or {})
        self._default_headers.setdefault("User-Agent", user_agent)
        self._token_provider = token_provider

        self._connector = None
        self._session_owner = False
        self._session = session
        if self._session is None:
            self._connector = aiohttp.TCPConnector(
                limit=pool_limit,
                limit_per_host=pool_limit_per_host,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )
            self._session_owner = True

    async def __aenter__(self) -> "HttpRequestClient":
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=self._connector,
                raise_for_status=False,
            )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying session if this client owns it."""
        if (
            self._session_owner
            and self._session is not None
            and not self._session.closed
        ):
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        """Return the active ``aiohttp.ClientSession``.

        Raises:
                RuntimeError: If the session has not been initialised.
        """
        if self._session is None:
            raise RuntimeError(
                "HttpRequestClient session not initialized. Use 'async with' or call __aenter__()."
            )
        return self._session

    async def _build_headers(self, headers: Mapping[str, str] | None) -> dict[str, str]:
        """Merge default, caller, and token-provider headers."""
        merged = dict(self._default_headers)
        if headers:
            merged.update(headers)

        # Respect explicit Authorization.
        has_auth = any(k.lower() == "authorization" for k in merged)
        if (not has_auth) and self._token_provider is not None:
            token = await self._token_provider()
            merged["Authorization"] = f"Bearer {token}"

        return merged

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        json_body: Any | None = None,
        data: Any | None = None,
        headers: Mapping[str, str] | None = None,
        expected_status: int | Iterable[int] | None = None,
        allow_redirects: bool = True,
    ) -> HttpResponse:
        """Send an HTTP request with retry logic.

        Args:
                method: HTTP method (GET, POST, PUT, DELETE, etc.).
                url: Relative or absolute URL.
                params: Optional query parameters.
                json_body: JSON-serialisable request body.
                data: Raw request body (form data, ``aiohttp.FormData``, etc.).
                headers: Additional request headers.
                expected_status: Acceptable status code(s); others raise
                        ``HttpRequestError``.
                allow_redirects: Whether to follow redirects automatically.

        Returns:
                Frozen ``HttpResponse`` on success.

        Raises:
                HttpRequestError: On unexpected status or exhausted retries.
        """
        full_url = _join_url(self._base_url, url)

        expected: set[int] | None
        if expected_status is None:
            expected = None
        elif isinstance(expected_status, int):
            expected = {expected_status}
        else:
            expected = set(expected_status)

        async def _do() -> HttpResponse:
            req_headers = await self._build_headers(headers)
            async with self.session.request(
                method.upper(),
                full_url,
                params=params,
                json=json_body,
                data=data,
                headers=req_headers,
                allow_redirects=allow_redirects,
            ) as resp:
                body = await resp.read()
                response = HttpResponse(
                    status=resp.status,
                    url=str(resp.url),
                    headers=dict(resp.headers),
                    body=body,
                )

                if resp.status in self._retry_statuses:
                    return response

                if expected is not None and resp.status not in expected:
                    raise HttpRequestError(
                        "Unexpected HTTP status",
                        method=method.upper(),
                        url=str(resp.url),
                        status=resp.status,
                        response_text=response.text(),
                        response_headers=response.headers,
                    )

                if expected is None and (resp.status < 200 or resp.status >= 300):
                    raise HttpRequestError(
                        "HTTP request failed",
                        method=method.upper(),
                        url=str(resp.url),
                        status=resp.status,
                        response_text=response.text(),
                        response_headers=response.headers,
                    )

                return response

        def _is_retriable_response(result: Any) -> bool:
            return (
                isinstance(result, HttpResponse)
                and result.status in self._retry_statuses
            )

        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._retry_attempts),
            retry=retry_any(
                retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
                retry_if_result(_is_retriable_response),
            ),
            wait=_WaitRetryAfterOrExponential(),
            reraise=True,
        )

        result: HttpResponse = await retrying(_do)
        if result.status in self._retry_statuses:
            raise HttpRequestError(
                "HTTP request received retriable status",
                method=method.upper(),
                url=result.url,
                status=result.status,
                response_text=result.text(),
                response_headers=result.headers,
            )

        return result

    async def get(self, url: str, **kwargs) -> HttpResponse:
        """Send a GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> HttpResponse:
        """Send a POST request."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> HttpResponse:
        """Send a PUT request."""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> HttpResponse:
        """Send a DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    async def get_json(self, url: str, **kwargs) -> Any:
        """GET a URL and return the parsed JSON body."""
        resp = await self.get(url, **kwargs)
        return resp.json()

    async def post_json(self, url: str, *, json_body: Any, **kwargs) -> Any:
        """POST a JSON body and return the parsed JSON response."""
        resp = await self.post(url, json_body=json_body, **kwargs)
        return resp.json() if resp.body else None

    async def post_multipart_json(
        self,
        url: str,
        *,
        json_part_name: str = "metadata",
        json_payload: Any | None = None,
        files: Iterable[MultipartFile] | None = None,
        headers: Mapping[str, str] | None = None,
        expected_status: int | Iterable[int] | None = None,
    ) -> HttpResponse:
        """POST a multipart form containing a JSON part and optional file parts.

        Args:
                url: Relative or absolute URL.
                json_part_name: Form field name for the JSON part.
                json_payload: JSON-serialisable metadata.
                files: Optional file descriptors to include.
                headers: Additional request headers.
                expected_status: Acceptable status code(s).

        Returns:
                Frozen ``HttpResponse``.
        """
        form = aiohttp.FormData()

        if json_payload is not None:
            form.add_field(
                name=json_part_name,
                value=json.dumps(json_payload, ensure_ascii=False),
                content_type="application/json",
            )

        opened: list[Any] = []
        try:
            for f in files or []:
                if isinstance(f.content, Path):
                    handle = f.content.open("rb")
                    opened.append(handle)
                    form.add_field(
                        name=f.field_name,
                        value=handle,
                        filename=f.filename,
                        content_type=f.content_type or "application/octet-stream",
                    )
                else:
                    form.add_field(
                        name=f.field_name,
                        value=f.content,
                        filename=f.filename,
                        content_type=f.content_type or "application/octet-stream",
                    )

            return await self.post(
                url,
                data=form,
                headers=headers,
                expected_status=expected_status,
            )
        finally:
            for h in opened:
                try:
                    h.close()
                except Exception:
                    # Best-effort cleanup: do not let close() failures mask the main request result.
                    pass

    async def poll_until_done(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
        data: Any | None = None,
        pending_statuses: Iterable[int] = (202,),
        done_statuses: Iterable[int] = (200,),
        poll_interval_seconds: float = 2.0,
        timeout_seconds: float = 120.0,
        location_header: str = "Location",
        on_poll: PollCallback | None = None,
    ) -> HttpResponse:
        """Poll an async operation endpoint until it completes.

        Common pattern:
        - 202 Accepted: operation still running, optionally returns `Location` for status URL
        - 200 OK: operation complete
        """

        pending = set(pending_statuses)
        done = set(done_statuses)

        start = time.monotonic()
        next_url = url

        while True:
            if time.monotonic() - start > timeout_seconds:
                raise TimeoutError(
                    f"Polling timed out after {timeout_seconds}s (url={_join_url(self._base_url, next_url)})"
                )

            resp = await self.request(
                method,
                next_url,
                params=params,
                headers=headers,
                json_body=json_body,
                data=data,
                allow_redirects=False,
                expected_status=pending | done,
            )

            if on_poll is not None:
                maybe_awaitable = on_poll(resp)
                if inspect.isawaitable(maybe_awaitable):
                    await maybe_awaitable

            if resp.status in done:
                return resp

            # 202/pending
            loc = resp.header(location_header)
            if loc:
                next_url = loc

            # Prefer Retry-After if present, otherwise use poll interval.
            delay = _parse_retry_after_seconds(resp.headers)
            if delay is None:
                delay = poll_interval_seconds
            await asyncio.sleep(max(0.0, float(delay)))
