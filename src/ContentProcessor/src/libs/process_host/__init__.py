# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Process-host layer for running pipeline handlers as OS processes.

Sub-modules:
    handler_process_host: Manager that spawns, monitors, and restarts
        handler processes.
    handler_type_loader: Dynamic loader that resolves step names to
        handler classes at runtime.
"""
