# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""FastAPI application bootstrap and dependency wiring.

Configures the ASGI application exposed to uvicorn: registers middleware,
mounts API routers, and binds scoped service dependencies into the
application context used by request handlers.
"""

import os
import warnings
from datetime import datetime

from fastapi.middleware.cors import CORSMiddleware

from app.libs.base.application_base import Application_Base
from app.libs.base.typed_fastapi import TypedFastAPI
from app.routers import claimprocessor, contentprocessor, schemasetvault, schemavault
from app.routers.http_probes import router as http_probes
from app.routers.logics.claimbatchpocessor import (
    ClaimBatchProcessor,
    ClaimBatchProcessRepository,
)
from app.routers.logics.contentprocessor import ContentProcessor
from app.routers.logics.schemasetvault import SchemaSets
from app.routers.logics.schemavault import Schemas

# PyMongo emits a compatibility warning when it detects Azure Cosmos DB (Mongo API).
# This is informational and is commonly suppressed to keep logs clean.
warnings.filterwarnings(
    "ignore",
    message=r"You appear to be connected to a CosmosDB cluster\..*supportability/cosmosdb.*",
    category=UserWarning,
)


class Application(Application_Base):
    """Top-level ASGI application that wires together all API components.

    Responsibilities:
        1. Create and configure the TypedFastAPI instance with CORS middleware.
        2. Register scoped service dependencies (processors, repositories, vaults).
        3. Mount all API routers (content, claims, schemas, health probes).

    Attributes:
        app: The configured TypedFastAPI instance served by uvicorn.
        start_time: Timestamp captured at class-load time for uptime reporting.
    """

    app: TypedFastAPI
    start_time = datetime.now()

    def __init__(self):
        super().__init__(env_file_path=os.path.join(os.path.dirname(__file__), ".env"))

    def initialize(self):
        """Build the FastAPI app, attach middleware, routers, and dependencies.

        Steps:
            1. Create a TypedFastAPI instance and bind the application context.
            2. Add CORS middleware with permissive defaults.
            3. Mount the health-probe router and all feature routers.
            4. Register scoped service factories for dependency injection.
        """
        self.app = TypedFastAPI(
            redirect_slashes=False, title="FastAPI Application", version="1.0.0"
        )
        self.app.set_app_context(self.application_context)

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.app.include_router(http_probes)
        self._register_dependencies()
        self._config_routers()

    def _config_routers(self):
        """Mount feature routers onto the FastAPI application."""
        routers = [
            contentprocessor.router,
            schemasetvault.router,
            schemavault.router,
            claimprocessor.router,
        ]

        for router in routers:
            self.app.include_router(router)

    def _register_dependencies(self):
        """Register scoped service factories into the application context."""
        self.application_context.add_singleton(
            ContentProcessor,
            lambda: ContentProcessor(app_context=self.application_context),
        )
        self.application_context.add_singleton(
            Schemas, lambda: Schemas(app_context=self.application_context)
        )
        self.application_context.add_singleton(
            SchemaSets, lambda: SchemaSets(app_context=self.application_context)
        )
        self.application_context.add_singleton(
            ClaimBatchProcessor,
            lambda: ClaimBatchProcessor(app_context=self.application_context),
        )
        self.application_context.add_singleton(
            ClaimBatchProcessRepository,
            lambda: ClaimBatchProcessRepository(
                connection_string=self.application_context.configuration.app_cosmos_connstr,
                database_name=self.application_context.configuration.app_cosmos_database,
                collection_name="claimprocesses",
            ),
        )

    def run(self, host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
        """No-op; the ASGI server (uvicorn) is launched externally."""
