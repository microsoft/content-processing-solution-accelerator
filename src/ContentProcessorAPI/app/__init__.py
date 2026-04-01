# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Root package for the ContentProcessorAPI application.

Ensures the application source root is on sys.path so that sub-packages
(libs, routers, utils) can be imported by the FastAPI entry point.
"""

import os

source_root = os.path.dirname(os.path.abspath(__file__))
if source_root not in os.sys.path:
    os.sys.path.insert(0, source_root)
