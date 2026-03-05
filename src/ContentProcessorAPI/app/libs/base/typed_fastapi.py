# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""FastAPI subclass that carries a strongly-typed AppContext attribute.

Used as the application's ASGI instance so that routers can access the
DI container directly via ``request.app.app_context``.
"""

from fastapi import FastAPI

from app.libs.application.application_context import AppContext


class TypedFastAPI(FastAPI):
    """FastAPI subclass exposing a typed ``app_context`` for IDE support.

    Attributes:
        app_context: The shared DI container (set during bootstrap).
    """

    app_context: AppContext | None = None

    def __init__(self, *args, **kwargs):
        """Initialise FastAPI and set app_context to None until wired."""
        super().__init__(*args, **kwargs)
        self.app_context: AppContext | None = None

    def set_app_context(self, app_context: AppContext) -> None:
        """Bind the application-wide DI container.

        Args:
            app_context: Populated AppContext instance.
        """
        self.app_context = app_context
