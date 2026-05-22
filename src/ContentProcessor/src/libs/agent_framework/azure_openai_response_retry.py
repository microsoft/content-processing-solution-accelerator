# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Retry-aware wrappers for Agent Framework Azure OpenAI clients.

Provides ``AzureOpenAIChatClientWithRetry`` and
``AzureOpenAIResponseClientWithRetry`` that add automatic 429
rate-limit back-off with jitter to the standard Agent Framework
client classes.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import random
from dataclasses import dataclass
from typing import Any, AsyncIterable, MutableSequence

from agent_framework.azure import AzureOpenAIChatClient, AzureOpenAIResponsesClient
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
)
from tenacity.wait import wait_base

logger = logging.getLogger(__name__)


def _format_exc_brief(exc: BaseException) -> str:
    name = type(exc).__name__
    msg = str(exc)
    return f"{name}: {msg}" if msg else name


@dataclass(frozen=True)
class RateLimitRetryConfig:
    max_retries: int = 5
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 30.0

    @staticmethod
    def from_env(
        max_retries_env: str = "AOAI_429_MAX_RETRIES",
        base_delay_env: str = "AOAI_429_BASE_DELAY_SECONDS",
        max_delay_env: str = "AOAI_429_MAX_DELAY_SECONDS",
    ) -> "RateLimitRetryConfig":
        def _int(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, str(default)))
            except Exception:
                return default

        def _float(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, str(default)))
            except Exception:
                return default

        return RateLimitRetryConfig(
            max_retries=max(0, _int(max_retries_env, 5)),
            base_delay_seconds=max(0.0, _float(base_delay_env, 2.0)),
            max_delay_seconds=max(0.0, _float(max_delay_env, 30.0)),
        )


def _looks_like_rate_limit(error: BaseException) -> bool:
    msg = str(error).lower()
    if any(s in msg for s in ["too many requests", "rate limit", "429", "throttle"]):
        return True

    status = getattr(error, "status_code", None) or getattr(error, "status", None)
    if status == 429:
        return True

    cause = getattr(error, "__cause__", None)
    if cause and cause is not error:
        return _looks_like_rate_limit(cause)

    return False


def _looks_like_access_check_challenge(error: BaseException) -> bool:
    """Detect Azure AI Services gateway transient first-request errors.

    The AI Services gateway may reject the very first request with:
      - 400 requiring a ``check-access-response-enc`` challenge header, or
      - 404 "Could not obtain the account information."

    Both are transient — the gateway caches the result and subsequent calls
    succeed.  Retrying once is sufficient.
    """
    msg = str(error).lower()
    if "check-access-response-enc" in msg:
        return True
    if "could not obtain the account information" in msg:
        return True

    cause = getattr(error, "__cause__", None)
    if cause and cause is not error:
        return _looks_like_access_check_challenge(cause)

    return False


def _is_transient_error(error: BaseException) -> bool:
    """Return True for errors that should be retried (rate-limit or access-check challenge)."""
    return _looks_like_rate_limit(error) or _looks_like_access_check_challenge(error)


def _looks_like_context_length(error: BaseException) -> bool:
    msg = str(error).lower()
    if any(
        s in msg
        for s in [
            "exceeds the context window",
            "maximum context length",
            "context length",
            "too many tokens",
            "prompt is too long",
            "input is too long",
            "please reduce the length",
        ]
    ):
        return True

    status = getattr(error, "status_code", None) or getattr(error, "status", None)
    if status in (400, 413):
        # Many SDKs surface context-length failures as 400/413 with a descriptive message.
        return True

    cause = getattr(error, "__cause__", None)
    if cause and cause is not error:
        return _looks_like_context_length(cause)

    return False


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return str(val)


def _truncate_text(
    text: str, *, max_chars: int, keep_head_chars: int, keep_tail_chars: int
) -> str:
    if max_chars <= 0:
        return ""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text

    head = text[: max(0, min(keep_head_chars, max_chars))]
    remaining = max_chars - len(head)
    if remaining <= 0:
        return head

    tail_len = max(0, min(keep_tail_chars, remaining))
    if tail_len <= 0:
        return head

    tail = text[-tail_len:]
    omitted = len(text) - (len(head) + len(tail))
    marker = f"\n... [TRUNCATED {omitted} CHARS] ...\n"

    budget = max_chars - (len(head) + len(tail))
    if budget <= 0:
        return head + tail
    if len(marker) > budget:
        marker = marker[:budget]

    return head + marker + tail


def _estimate_message_text(message: Any) -> str:
    if message is None:
        return ""

    if isinstance(message, dict):
        # Common shapes: {role, content}, {role, text}, {role, contents}
        for key in ("content", "text", "contents"):
            if key in message:
                return _safe_str(message.get(key))
        return _safe_str(message)

    # Attribute-based objects.
    for attr in ("content", "text", "contents"):
        if hasattr(message, attr):
            return _safe_str(getattr(message, attr))
    return _safe_str(message)


def _get_message_role(message: Any) -> str | None:
    if message is None:
        return None
    if isinstance(message, dict):
        role = message.get("role")
        return role if isinstance(role, str) else None
    role = getattr(message, "role", None)
    return role if isinstance(role, str) else None


def _set_message_text(message: Any, new_text: str) -> Any:
    """Best-effort setter for message text.

    - For dict messages: returns a shallow-copied dict with content/text updated.
    - For objects: tries to set .content or .text; if that fails, returns original.
    """
    if isinstance(message, dict):
        out = dict(message)
        if "content" in out:
            out["content"] = new_text
        elif "text" in out:
            out["text"] = new_text
        elif "contents" in out:
            out["contents"] = new_text
        else:
            out["content"] = new_text
        return out

    for attr in ("content", "text"):
        if hasattr(message, attr):
            try:
                setattr(message, attr, new_text)
                return message
            except Exception:
                pass
    return message


@dataclass(frozen=True)
class ContextTrimConfig:
    """Character-budget based context trimming.

    This is a defensive control to prevent hard failures like
    "input exceeds the context window" when upstream accidentally injects
    huge blobs (telemetry JSON, repeated instructions, etc.).
    """

    enabled: bool = True
    # GPT-5.x class models typically support larger context windows. These defaults
    # intentionally allow more history before trimming, while still guarding
    # against accidental multi-hundred-KB blobs being injected into a single call.
    max_total_chars: int = 240_000
    max_message_chars: int = 20_000
    keep_last_messages: int = 40
    keep_head_chars: int = 10_000
    keep_tail_chars: int = 3_000
    keep_system_messages: bool = True
    retry_on_context_error: bool = True

    @staticmethod
    def from_env(
        enabled_env: str = "AOAI_CTX_TRIM_ENABLED",
        max_total_chars_env: str = "AOAI_CTX_MAX_TOTAL_CHARS",
        max_message_chars_env: str = "AOAI_CTX_MAX_MESSAGE_CHARS",
        keep_last_messages_env: str = "AOAI_CTX_KEEP_LAST_MESSAGES",
        keep_head_chars_env: str = "AOAI_CTX_KEEP_HEAD_CHARS",
        keep_tail_chars_env: str = "AOAI_CTX_KEEP_TAIL_CHARS",
        keep_system_messages_env: str = "AOAI_CTX_KEEP_SYSTEM_MESSAGES",
        retry_on_context_error_env: str = "AOAI_CTX_RETRY_ON_CONTEXT_ERROR",
    ) -> "ContextTrimConfig":
        def _int(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, str(default)))
            except Exception:
                return default

        def _bool(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")

        return ContextTrimConfig(
            enabled=_bool(enabled_env, True),
            max_total_chars=max(0, _int(max_total_chars_env, 240_000)),
            max_message_chars=max(0, _int(max_message_chars_env, 20_000)),
            keep_last_messages=max(1, _int(keep_last_messages_env, 40)),
            keep_head_chars=max(0, _int(keep_head_chars_env, 10_000)),
            keep_tail_chars=max(0, _int(keep_tail_chars_env, 3_000)),
            keep_system_messages=_bool(keep_system_messages_env, True),
            retry_on_context_error=_bool(retry_on_context_error_env, True),
        )


def _trim_messages(
    messages: MutableSequence[Any], *, cfg: ContextTrimConfig
) -> list[Any]:
    if not cfg.enabled:
        return list(messages)

    # Keep last N messages; optionally keep system messages from the head.
    system_messages: list[Any] = []
    tail: list[Any] = list(messages)

    if cfg.keep_system_messages:
        for m in messages:
            if _get_message_role(m) == "system":
                system_messages.append(m)
            else:
                break

    if cfg.keep_last_messages > 0:
        tail = tail[-cfg.keep_last_messages :]

    # De-dupe large repeated blobs using author-less fingerprint on head/tail text.
    seen_fingerprints: set[tuple[str, str]] = set()
    cleaned: list[Any] = []

    for m in tail:
        text = _estimate_message_text(m)
        fp = (text[:200], text[-200:])
        if fp in seen_fingerprints:
            continue
        seen_fingerprints.add(fp)

        if cfg.max_message_chars > 0 and len(text) > cfg.max_message_chars:
            text = _truncate_text(
                text,
                max_chars=cfg.max_message_chars,
                keep_head_chars=cfg.keep_head_chars,
                keep_tail_chars=cfg.keep_tail_chars,
            )
            m = _set_message_text(m, text)
        cleaned.append(m)

    # Enforce overall budget by trimming oldest messages from the non-system tail.
    combined: list[Any] = system_messages + cleaned
    if cfg.max_total_chars <= 0:
        return combined

    def _total_chars(msgs: list[Any]) -> int:
        return sum(len(_estimate_message_text(x)) for x in msgs)

    while combined and _total_chars(combined) > cfg.max_total_chars:
        # Prefer dropping earliest non-system message.
        drop_index = 0
        if cfg.keep_system_messages and system_messages:
            drop_index = len(system_messages)
        if drop_index >= len(combined):
            # If only system messages remain, truncate the last one.
            last = combined[-1]
            text = _estimate_message_text(last)
            text = _truncate_text(
                text,
                max_chars=cfg.max_total_chars,
                keep_head_chars=min(cfg.keep_head_chars, cfg.max_total_chars),
                keep_tail_chars=min(cfg.keep_tail_chars, cfg.max_total_chars),
            )
            combined[-1] = _set_message_text(last, text)
            break
        combined.pop(drop_index)

    return combined


def _try_get_retry_after_seconds(error: BaseException) -> float | None:
    inner = getattr(error, "inner_exception", None)
    if isinstance(inner, BaseException) and inner is not error:
        inner_retry = _try_get_retry_after_seconds(inner)
        if inner_retry is not None:
            return inner_retry

    candidates: list[Any] = []
    candidates.append(getattr(error, "retry_after", None))

    response = getattr(error, "response", None)
    if response is not None:
        candidates.append(getattr(response, "headers", None))

    headers = getattr(error, "headers", None)
    if headers is not None:
        candidates.append(headers)

    for item in candidates:
        if item is None:
            continue
        if isinstance(item, (int, float)):
            return float(item)
        if isinstance(item, str):
            try:
                return float(item)
            except Exception:
                continue
        if isinstance(item, dict):
            for key in ("retry-after", "Retry-After"):
                if key in item:
                    try:
                        return float(item[key])
                    except Exception:
                        pass
    return None


async def _retry_call(coro_factory, *, config: RateLimitRetryConfig):
    def _log_before_sleep(retry_state) -> None:
        exc = None
        if retry_state.outcome is not None and retry_state.outcome.failed:
            exc = retry_state.outcome.exception()

        # Tenacity sets next_action when it's about to sleep.
        sleep_s = None
        next_action = getattr(retry_state, "next_action", None)
        if next_action is not None:
            sleep_s = getattr(next_action, "sleep", None)

        retry_after = _try_get_retry_after_seconds(exc) if exc is not None else None
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        attempt = getattr(retry_state, "attempt_number", None)
        max_attempts = config.max_retries + 1

        logger.warning(
            "[AOAI_RETRY] attempt %s/%s; sleeping=%ss; retry_after=%s; status=%s; error=%s",
            attempt,
            max_attempts,
            None if sleep_s is None else round(float(sleep_s), 3),
            None if retry_after is None else round(float(retry_after), 3),
            status,
            None if exc is None else _format_exc_brief(exc),
        )

    class _WaitRetryAfterOrExpJitter(wait_base):
        def __init__(self, retry_config: RateLimitRetryConfig):
            self._cfg = retry_config

        def __call__(self, retry_state) -> float:
            exc = None
            if retry_state.outcome is not None and retry_state.outcome.failed:
                exc = retry_state.outcome.exception()

            if exc is not None:
                retry_after = _try_get_retry_after_seconds(exc)
                if retry_after is not None and retry_after >= 0:
                    return float(retry_after)

            attempt_index = max(0, retry_state.attempt_number - 1)
            delay = self._cfg.base_delay_seconds * (2**attempt_index)
            delay = min(delay, self._cfg.max_delay_seconds)
            delay = delay + random.uniform(0.0, 0.25 * max(delay, 0.1))
            return float(delay)

    retrying = AsyncRetrying(
        retry=retry_if_exception(_is_transient_error),
        stop=stop_after_attempt(config.max_retries + 1),
        wait=_WaitRetryAfterOrExpJitter(config),
        before_sleep=_log_before_sleep,
        reraise=True,
    )

    async for attempt in retrying:
        with attempt:
            return await coro_factory()

    raise RuntimeError("Retry loop exhausted unexpectedly")


class AzureOpenAIResponseClientWithRetry(AzureOpenAIResponsesClient):
    """Azure OpenAI Responses client with 429 retry at the request boundary.

    Retry is centralized in the client layer (not in orchestrators) by retrying the
    underlying Responses calls made by `OpenAIBaseResponsesClient`.
    """

    def __init__(
        self,
        *args: Any,
        retry_config: RateLimitRetryConfig | None = None,
        context_trim_config: ContextTrimConfig | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._retry_config = retry_config or RateLimitRetryConfig.from_env()
        self._context_trim_config = context_trim_config or ContextTrimConfig.from_env()

    async def _inner_get_response(
        self,
        *,
        messages: MutableSequence[Any],
        chat_options: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        parent_inner_get_response = super(
            AzureOpenAIResponseClientWithRetry, self
        )._inner_get_response

        parent_supports_chat_options = (
            "chat_options" in inspect.signature(parent_inner_get_response).parameters
        )

        effective_messages: MutableSequence[Any] | list[Any] = messages
        if self._context_trim_config.enabled:
            approx_chars = sum(len(_estimate_message_text(m)) for m in messages)
            if (
                self._context_trim_config.max_total_chars > 0
                and approx_chars > self._context_trim_config.max_total_chars
            ):
                effective_messages = _trim_messages(
                    messages, cfg=self._context_trim_config
                )
                logger.warning(
                    "[AOAI_CTX_TRIM] pre-trimmed request messages: approx_chars=%s -> %s; count=%s -> %s",
                    approx_chars,
                    sum(len(_estimate_message_text(m)) for m in effective_messages),
                    len(messages),
                    len(effective_messages),
                )

        try:
            if parent_supports_chat_options:
                return await _retry_call(
                    lambda: parent_inner_get_response(
                        messages=effective_messages, chat_options=chat_options, **kwargs
                    ),
                    config=self._retry_config,
                )
            return await _retry_call(
                lambda: parent_inner_get_response(
                    messages=effective_messages, **kwargs
                ),
                config=self._retry_config,
            )
        except Exception as e:
            if not (
                self._context_trim_config.enabled
                and self._context_trim_config.retry_on_context_error
                and _looks_like_context_length(e)
            ):
                raise

            trimmed = _trim_messages(messages, cfg=self._context_trim_config)
            logger.warning(
                "[AOAI_CTX_TRIM] retrying after context-length error; count=%s -> %s",
                len(messages),
                len(trimmed),
            )
            return await _retry_call(
                (
                    (
                        lambda: parent_inner_get_response(
                            messages=trimmed, chat_options=chat_options, **kwargs
                        )
                    )
                    if parent_supports_chat_options
                    else (lambda: parent_inner_get_response(messages=trimmed, **kwargs))
                ),
                config=self._retry_config,
            )

    async def _inner_get_streaming_response(
        self,
        *,
        messages: MutableSequence[Any],
        chat_options: Any | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[Any]:
        # Conservative retry: only retries failures before the first yielded update.
        attempts = self._retry_config.max_retries + 1

        parent_inner_stream = super(
            AzureOpenAIResponseClientWithRetry, self
        )._inner_get_streaming_response
        parent_supports_chat_options = (
            "chat_options" in inspect.signature(parent_inner_stream).parameters
        )

        effective_messages: MutableSequence[Any] | list[Any] = messages
        if self._context_trim_config.enabled:
            approx_chars = sum(len(_estimate_message_text(m)) for m in messages)
            if (
                self._context_trim_config.max_total_chars > 0
                and approx_chars > self._context_trim_config.max_total_chars
            ):
                effective_messages = _trim_messages(
                    messages, cfg=self._context_trim_config
                )
                logger.warning(
                    "[AOAI_CTX_TRIM] pre-trimmed streaming request messages: approx_chars=%s -> %s; count=%s -> %s",
                    approx_chars,
                    sum(len(_estimate_message_text(m)) for m in effective_messages),
                    len(messages),
                    len(effective_messages),
                )

        for attempt_index in range(attempts):
            if parent_supports_chat_options:
                stream = parent_inner_stream(
                    messages=effective_messages, chat_options=chat_options, **kwargs
                )
            else:
                stream = parent_inner_stream(messages=effective_messages, **kwargs)

            iterator = stream.__aiter__()
            try:
                first = await iterator.__anext__()

                async def _tail():
                    yield first
                    async for item in iterator:
                        yield item

                async for item in _tail():
                    yield item
                return
            except StopAsyncIteration:
                return
            except Exception as e:
                close = getattr(stream, "aclose", None)
                if callable(close):
                    try:
                        await close()
                    except Exception as close_exc:
                        # Best-effort stream cleanup: ignore close failures so we preserve
                        # the original exception/retry path.
                        logger.debug(
                            "[AOAI_RETRY_STREAM] ignoring stream close failure during retry handling: %s",
                            _format_exc_brief(close_exc)
                            if isinstance(close_exc, BaseException)
                            else str(close_exc),
                        )

                # One-shot retry for context-length failures.
                if (
                    self._context_trim_config.enabled
                    and self._context_trim_config.retry_on_context_error
                    and _looks_like_context_length(e)
                ):
                    trimmed = _trim_messages(messages, cfg=self._context_trim_config)
                    logger.warning(
                        "[AOAI_CTX_TRIM_STREAM] retrying after context-length error; count=%s -> %s",
                        len(messages),
                        len(trimmed),
                    )
                    effective_messages = trimmed
                    if attempt_index >= attempts - 1:
                        # No more retries available.
                        raise
                    continue

                if not _is_transient_error(e) or attempt_index >= attempts - 1:
                    if _is_transient_error(e):
                        logger.warning(
                            "[AOAI_RETRY_STREAM] giving up after %s/%s attempts; error=%s",
                            attempt_index + 1,
                            attempts,
                            _format_exc_brief(e)
                            if isinstance(e, BaseException)
                            else str(e),
                        )
                    raise

                retry_after = _try_get_retry_after_seconds(e)
                if retry_after is not None and retry_after >= 0:
                    delay = retry_after
                else:
                    delay = self._retry_config.base_delay_seconds * (2**attempt_index)
                    delay = min(delay, self._retry_config.max_delay_seconds)
                    delay = delay + random.uniform(0.0, 0.25 * max(delay, 0.1))

                status = getattr(e, "status_code", None) or getattr(e, "status", None)
                logger.warning(
                    "[AOAI_RETRY_STREAM] attempt %s/%s; sleeping=%ss; retry_after=%s; status=%s; error=%s",
                    attempt_index + 1,
                    attempts,
                    round(float(delay), 3),
                    None if retry_after is None else round(float(retry_after), 3),
                    status,
                    _format_exc_brief(e) if isinstance(e, BaseException) else str(e),
                )

                await asyncio.sleep(delay)


class AzureOpenAIChatClientWithRetry(AzureOpenAIChatClient):
    """Azure OpenAI Chat client with 429 retry at the request boundary.

    This wraps the underlying chat-completions call used by Agent Framework by overriding
    the internal `_inner_get_response` / `_inner_get_streaming_response` methods.
    """

    def __init__(
        self,
        *args: Any,
        retry_config: RateLimitRetryConfig | None = None,
        context_trim_config: ContextTrimConfig | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._retry_config = retry_config or RateLimitRetryConfig.from_env()
        self._context_trim_config = context_trim_config or ContextTrimConfig.from_env()

    async def _inner_get_response(
        self,
        *,
        messages: MutableSequence[Any],
        options: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        parent_inner_get_response = super(
            AzureOpenAIChatClientWithRetry, self
        )._inner_get_response

        effective_messages: MutableSequence[Any] | list[Any] = messages
        if self._context_trim_config.enabled:
            approx_chars = sum(len(_estimate_message_text(m)) for m in messages)
            if (
                self._context_trim_config.max_total_chars > 0
                and approx_chars > self._context_trim_config.max_total_chars
            ):
                effective_messages = _trim_messages(
                    messages, cfg=self._context_trim_config
                )
                logger.warning(
                    "[AOAI_CTX_TRIM] pre-trimmed chat request messages: approx_chars=%s -> %s; count=%s -> %s",
                    approx_chars,
                    sum(len(_estimate_message_text(m)) for m in effective_messages),
                    len(messages),
                    len(effective_messages),
                )

        try:
            return await _retry_call(
                lambda: parent_inner_get_response(
                    messages=effective_messages, options=options, **kwargs
                ),
                config=self._retry_config,
            )
        except Exception as e:
            if not (
                self._context_trim_config.enabled
                and self._context_trim_config.retry_on_context_error
                and _looks_like_context_length(e)
            ):
                raise

            trimmed = _trim_messages(messages, cfg=self._context_trim_config)
            logger.warning(
                "[AOAI_CTX_TRIM] retrying chat after context-length error; count=%s -> %s",
                len(messages),
                len(trimmed),
            )
            return await _retry_call(
                lambda: parent_inner_get_response(
                    messages=trimmed, options=options, **kwargs
                ),
                config=self._retry_config,
            )

    async def _inner_get_streaming_response(
        self,
        *,
        messages: MutableSequence[Any],
        options: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterable[Any]:
        # Conservative retry: only retries failures before the first yielded update.
        attempts = self._retry_config.max_retries + 1

        parent_inner_stream = super(
            AzureOpenAIChatClientWithRetry, self
        )._inner_get_streaming_response

        effective_messages: MutableSequence[Any] | list[Any] = messages
        if self._context_trim_config.enabled:
            approx_chars = sum(len(_estimate_message_text(m)) for m in messages)
            if (
                self._context_trim_config.max_total_chars > 0
                and approx_chars > self._context_trim_config.max_total_chars
            ):
                effective_messages = _trim_messages(
                    messages, cfg=self._context_trim_config
                )
                logger.warning(
                    "[AOAI_CTX_TRIM] pre-trimmed streaming chat request messages: approx_chars=%s -> %s; count=%s -> %s",
                    approx_chars,
                    sum(len(_estimate_message_text(m)) for m in effective_messages),
                    len(messages),
                    len(effective_messages),
                )

        for attempt_index in range(attempts):
            stream = parent_inner_stream(
                messages=effective_messages, options=options, **kwargs
            )

            iterator = stream.__aiter__()
            try:
                first = await iterator.__anext__()

                async def _tail():
                    yield first
                    async for item in iterator:
                        yield item

                async for item in _tail():
                    yield item
                return
            except StopAsyncIteration:
                return
            except Exception as e:
                close = getattr(stream, "aclose", None)
                if callable(close):
                    try:
                        await close()
                    except Exception as close_error:
                        # Intentionally suppress close-time failures so we do not
                        # mask the original streaming exception that triggered retry handling.
                        logger.debug(
                            "[AOAI_RETRY_STREAM] ignoring stream close failure during error handling",
                            exc_info=close_error,
                        )

                # One-shot retry for context-length failures.
                if (
                    self._context_trim_config.enabled
                    and self._context_trim_config.retry_on_context_error
                    and _looks_like_context_length(e)
                ):
                    trimmed = _trim_messages(messages, cfg=self._context_trim_config)
                    logger.warning(
                        "[AOAI_CTX_TRIM_STREAM] retrying chat stream after context-length error; count=%s -> %s",
                        len(messages),
                        len(trimmed),
                    )
                    effective_messages = trimmed
                    if attempt_index >= attempts - 1:
                        raise
                    continue

                if not _is_transient_error(e) or attempt_index >= attempts - 1:
                    if _is_transient_error(e):
                        logger.warning(
                            "[AOAI_RETRY_STREAM] giving up after %s/%s attempts; error=%s",
                            attempt_index + 1,
                            attempts,
                            _format_exc_brief(e)
                            if isinstance(e, BaseException)
                            else str(e),
                        )
                    raise

                retry_after = _try_get_retry_after_seconds(e)
                if retry_after is not None and retry_after >= 0:
                    delay = retry_after
                else:
                    delay = self._retry_config.base_delay_seconds * (2**attempt_index)
                    delay = min(delay, self._retry_config.max_delay_seconds)
                    delay = delay + random.uniform(0.0, 0.25 * max(delay, 0.1))

                status = getattr(e, "status_code", None) or getattr(e, "status", None)
                logger.warning(
                    "[AOAI_RETRY_STREAM] chat attempt %s/%s; sleeping=%ss; retry_after=%s; status=%s; error=%s",
                    attempt_index + 1,
                    attempts,
                    round(float(delay), 3),
                    None if retry_after is None else round(float(retry_after), 3),
                    status,
                    _format_exc_brief(e) if isinstance(e, BaseException) else str(e),
                )

                await asyncio.sleep(delay)
