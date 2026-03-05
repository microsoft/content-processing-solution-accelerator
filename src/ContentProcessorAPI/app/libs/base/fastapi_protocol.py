# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Structural-typing protocol for a FastAPI instance with an app_context.

Provides a Protocol class so that code can depend on the shape of the
object rather than a concrete subclass; largely superseded by TypedFastAPI
but kept for backward compatibility in type-check-only paths.
"""

from typing import Protocol

from fastapi import FastAPI
from libs.application.application_context import AppContext


class FastAPIWithContext(Protocol):
    """Protocol describing a FastAPI app that carries an AppContext.

    Attributes:
        app_context: The DI container attached to the application.
    """

    app_context: AppContext

    def include_router(self, *args, **kwargs) -> None: ...


def add_app_context_to_fastapi(
    app: FastAPI, app_context: AppContext
) -> FastAPIWithContext:
    """Attach *app_context* to a plain FastAPI instance and return it typed.

    Args:
        app: Plain FastAPI application.
        app_context: DI container to attach.

    Returns:
        The same *app*, now typed as FastAPIWithContext.
    """
    app.app_context = app_context  # type: ignore
    return app  # type: ignore
