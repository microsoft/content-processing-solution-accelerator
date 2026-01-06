# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime

from fastapi import FastAPI, Response

from app.routers import contentprocessor, schemavault

start_time = datetime.datetime.now()
# app = FastAPI(dependencies=[Depends(get_token_header), Depends(get_query_token)])
app = FastAPI(redirect_slashes=False)

# Add the routers to the app
app.include_router(contentprocessor.router)
app.include_router(schemavault.router)


@app.get("/health")
async def ImAlive(response: Response):
    # Add Header Name is Custom-Header
    response.headers["Custom-Header"] = "liveness probe"
    return {"message": "I'm alive!"}


@app.get("/startup")
async def Startup(response: Response):
    # Add Header Name is Custom-Header
    response.headers["Custom-Header"] = "Startup probe"
    uptime = datetime.datetime.now() - start_time
    hours, remainder = divmod(uptime.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return {"message": f"Running for {int(hours)}:{int(minutes)}:{int(seconds)}"}
