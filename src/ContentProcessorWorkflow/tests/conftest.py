# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Shared pytest fixtures and configuration for the test suite."""

import sys
from pathlib import Path

# Ensure the workspace `src/` directory is on sys.path so imports like `libs.*`
# (used throughout the application code) work when running pytest from repo root.
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# `sitecustomize` is auto-imported only at interpreter startup, so pytest won't
# pick up our `src/sitecustomize.py` unless `PYTHONPATH=src` is set. Import it
# explicitly after adding `src/` to `sys.path` so test collection works.
try:
    import sitecustomize  # noqa: F401
except Exception:
    # Tests should still be able to run even if the compatibility hook is absent.
    pass
