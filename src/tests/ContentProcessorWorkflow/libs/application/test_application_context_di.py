# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.application.application_context (DI container lifetimes)."""

from __future__ import annotations

import asyncio

import pytest

from libs.application.application_context import AppContext, ServiceLifetime


class _S1:
    pass


class _S2:
    pass


# ── Singleton ───────────────────────────────────────────────────────────


class TestSingleton:
    """Singleton lifetime: one instance for the entire container."""

    def test_caches_instance(self) -> None:
        ctx = AppContext().add_singleton(_S1)
        a = ctx.get_service(_S1)
        b = ctx.get_service(_S1)
        assert a is b

    def test_with_factory(self) -> None:
        ctx = AppContext().add_singleton(_S1, lambda: _S1())
        a = ctx.get_service(_S1)
        b = ctx.get_service(_S1)
        assert a is b

    def test_with_prebuilt_instance(self) -> None:
        instance = _S1()
        ctx = AppContext().add_singleton(_S1, instance)
        assert ctx.get_service(_S1) is instance


# ── Transient ───────────────────────────────────────────────────────────


class TestTransient:
    """Transient lifetime: new instance on every resolution."""

    def test_returns_new_instances(self) -> None:
        ctx = AppContext().add_transient(_S1)
        a = ctx.get_service(_S1)
        b = ctx.get_service(_S1)
        assert a is not b

    def test_with_factory(self) -> None:
        ctx = AppContext().add_transient(_S1, _S1)
        a = ctx.get_service(_S1)
        b = ctx.get_service(_S1)
        assert isinstance(a, _S1)
        assert a is not b


# ── Scoped ──────────────────────────────────────────────────────────────


class TestScoped:
    """Scoped lifetime: one instance per scope, isolated across scopes."""

    def test_requires_scope(self) -> None:
        ctx = AppContext().add_scoped(_S1)
        with pytest.raises(ValueError, match="requires an active scope"):
            ctx.get_service(_S1)

    def test_caches_within_scope(self) -> None:
        async def _run() -> None:
            ctx = AppContext().add_scoped(_S1)
            async with ctx.create_scope() as scope:
                a = scope.get_service(_S1)
                b = scope.get_service(_S1)
                assert a is b

        asyncio.run(_run())

    def test_isolates_across_scopes(self) -> None:
        async def _run() -> None:
            ctx = AppContext().add_scoped(_S1)
            async with ctx.create_scope() as scope1:
                a = scope1.get_service(_S1)

            async with ctx.create_scope() as scope2:
                b = scope2.get_service(_S1)
                assert b is not a

        asyncio.run(_run())


# ── Async Singleton ────────────────────────────────────────────────────


class TestAsyncSingleton:
    """Async singleton lifetime: created once, supports async init/cleanup."""

    def test_caches_instance(self) -> None:
        async def _run() -> None:
            ctx = AppContext().add_async_singleton(_S1)
            a = await ctx.get_service_async(_S1)
            b = await ctx.get_service_async(_S1)
            assert a is b

        asyncio.run(_run())

    def test_shutdown_calls_cleanup(self) -> None:
        class _Closeable:
            def __init__(self) -> None:
                self.closed = False

            async def close(self) -> None:
                self.closed = True

        async def _run() -> None:
            ctx = AppContext().add_async_singleton(_Closeable, cleanup_method="close")
            svc = await ctx.get_service_async(_Closeable)
            assert svc.closed is False
            await ctx.shutdown_async()
            assert svc.closed is True

        asyncio.run(_run())


# ── Async Scoped ────────────────────────────────────────────────────────


class TestAsyncScoped:
    """Async scoped lifetime: per-scope instances with async cleanup."""

    def test_cleanup_on_scope_exit(self) -> None:
        class _AsyncScoped:
            def __init__(self) -> None:
                self.closed = False

            async def close(self) -> None:
                self.closed = True

        async def _run() -> None:
            ctx = AppContext().add_async_scoped(
                _AsyncScoped, _AsyncScoped, cleanup_method="close"
            )

            async with ctx.create_scope() as scope:
                svc = await scope.get_service_async(_AsyncScoped)
                assert svc.closed is False

            # Fresh scope yields a fresh (unclosed) instance.
            async with ctx.create_scope() as scope2:
                svc2 = await scope2.get_service_async(_AsyncScoped)
                assert svc2.closed is False

        asyncio.run(_run())

    def test_caches_within_scope(self) -> None:
        async def _run() -> None:
            ctx = AppContext().add_async_scoped(_S1)
            async with ctx.create_scope() as scope:
                a = await scope.get_service_async(_S1)
                b = await scope.get_service_async(_S1)
                assert a is b

        asyncio.run(_run())


# ── Resolution Errors ───────────────────────────────────────────────────


class TestResolutionErrors:
    """Error paths for service resolution."""

    def test_get_service_raises_for_unregistered(self) -> None:
        ctx = AppContext()
        with pytest.raises(KeyError, match="_S1"):
            ctx.get_service(_S1)

    def test_get_service_async_raises_for_unregistered(self) -> None:
        async def _run() -> None:
            ctx = AppContext()
            with pytest.raises(KeyError, match="_S1"):
                await ctx.get_service_async(_S1)

        asyncio.run(_run())

    def test_get_service_async_raises_for_non_async(self) -> None:
        async def _run() -> None:
            ctx = AppContext().add_singleton(_S1)
            with pytest.raises(ValueError, match="not registered as an async"):
                await ctx.get_service_async(_S1)

        asyncio.run(_run())


# ── Introspection ───────────────────────────────────────────────────────


class TestIntrospection:
    """is_registered / get_registered_services helpers."""

    def test_is_registered_true(self) -> None:
        ctx = AppContext().add_singleton(_S1)
        assert ctx.is_registered(_S1) is True

    def test_is_registered_false(self) -> None:
        ctx = AppContext()
        assert ctx.is_registered(_S1) is False

    def test_get_registered_services(self) -> None:
        ctx = AppContext().add_singleton(_S1).add_transient(_S2)
        services = ctx.get_registered_services()
        assert services[_S1] == ServiceLifetime.SINGLETON
        assert services[_S2] == ServiceLifetime.TRANSIENT

    def test_fluent_chaining(self) -> None:
        ctx = AppContext().add_singleton(_S1).add_transient(_S2)
        assert ctx.is_registered(_S1)
        assert ctx.is_registered(_S2)
