# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers import contentprocessor, schemavault

start_time = datetime.datetime.now()
# app = FastAPI(dependencies=[Depends(get_token_header), Depends(get_query_token)])
app = FastAPI(redirect_slashes=False)

# Add the routers to the app
app.include_router(contentprocessor.router)
app.include_router(schemavault.router)

# Enable CORS for browser calls from the Web app
# Allows all origins by default; set APP_ALLOWED_ORIGIN env var to restrict
allowed_origin_env = os.getenv("APP_ALLOWED_ORIGIN", "*")
allowed_origins = ["*"] if allowed_origin_env == "*" else [o.strip() for o in allowed_origin_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# class Hello(BaseModel):
#     message: str


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
