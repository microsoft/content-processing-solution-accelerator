# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Health / liveness / startup probe endpoints."""

import datetime

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

start_time = datetime.datetime.now()

router = APIRouter(
    tags=["http_probes"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/",
    summary="Get API root info",
    description="""
    Returns basic API information and uptime.

    ## Parameters
    None.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /`
    """,
)
async def root():
    """Return basic API information and uptime."""
    return JSONResponse(
        content={
            "message": "Content Processing v2 API",
            "version": "2.0.0",
            "status": "running",
            "timestamp": datetime.datetime.now().isoformat(),
            "uptime_seconds": (datetime.datetime.now() - start_time).total_seconds(),
        }
    )


@router.get(
    "/health",
    summary="Check liveness",
    description="""
    Liveness probe endpoint used by health checks.

    ## Parameters
    None.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /health`
    """,
)
async def ImAlive(response: Response):
    """Liveness probe — always returns 200."""
    return JSONResponse(
        headers={"Custom-Header": "liveness probe"},
        content={"message": "I'm alive!"},
    )


@router.get(
    "/startup",
    summary="Check startup",
    description="""
    Startup probe endpoint showing time since app start.

    ## Parameters
    None.

    ## Example Request Body
    Not applicable. This is a GET endpoint and does not accept a request body.

    Example request:
    `GET /startup`
    """,
)
async def Startup(response: Response):
    """Startup probe returning elapsed uptime since process start."""
    uptime = datetime.datetime.now() - start_time
    hours, remainder = divmod(uptime.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return JSONResponse(
        headers={"Custom-Header": "Startup probe"},
        content={"message": f"Running for {int(hours)}:{int(minutes)}:{int(seconds)}"},
    )
