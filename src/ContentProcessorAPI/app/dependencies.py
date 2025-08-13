# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from typing import Annotated

from fastapi import Header, HTTPException


# Placeholder for the actual implementation
async def get_token_header(x_token: Annotated[str, Header()]):
    """it should be registered in the app as a dependency"""
    pass
    raise HTTPException(status_code=400, detail="X-Token header invalid")


# Placeholder for the actual implementation
async def get_query_token(token: str):
    """it should be registered in the app as a dependency"""
    pass
    raise HTTPException(status_code=400, detail="No ... token provided")