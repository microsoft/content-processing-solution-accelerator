# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Uvicorn entry point for the ContentProcessorAPI service.

Exposes the module-level ``app`` object that uvicorn imports
(e.g. ``uvicorn app.main:app``).  A singleton Application instance
is lazily created on first access to ensure reload-safe bootstrapping.
"""

import warnings

from application import Application

# PyMongo emits a noisy compatibility warning when it detects Azure Cosmos DB
# (Mongo API). This warning is informational and can be safely suppressed in
# production logs.
warnings.filterwarnings(
    "ignore",
    message=r"You appear to be connected to a CosmosDB cluster\..*supportability/cosmosdb.*",
    category=UserWarning,
)

_app_instance = None


def get_app():
    """Return the singleton Application, creating it on first call."""
    global _app_instance
    if _app_instance is None:
        _app_instance = Application()
    return _app_instance.app


# Module-level reference used by uvicorn's import-string (app.main:app).
app = get_app()


if __name__ == "__main__":
    app = Application().app
