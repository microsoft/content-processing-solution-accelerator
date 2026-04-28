# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Convert a legacy Pydantic ``.py`` schema into a declarative ``.json`` schema.

This helper is part of the migration away from executable Python schemas.
It imports a Pydantic model from a ``.py`` file *in a trusted local
context* (the developer's machine), reads its
:py:meth:`pydantic.BaseModel.model_json_schema` output, and writes the
result to a ``.json`` file alongside.

Usage:

    python scripts/py_schema_to_json.py \
        src/ContentProcessorAPI/samples/schemas/autoclaim.py \
        AutoInsuranceClaimForm

The generated JSON is what should be uploaded to the schema vault going
forward; it is data only and never executed by the worker.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from pydantic import BaseModel


def convert(py_path: Path, class_name: str, out_path: Path | None = None) -> Path:
    """Load *class_name* from *py_path* and write its JSON schema next to it."""
    spec = importlib.util.spec_from_file_location(py_path.stem, py_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import schema module from {py_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # noqa: S102 - trusted local conversion only

    cls = getattr(module, class_name, None)
    if cls is None or not isinstance(cls, type) or not issubclass(cls, BaseModel):
        raise RuntimeError(
            f"'{class_name}' is not a Pydantic BaseModel in {py_path}"
        )

    schema = cls.model_json_schema()
    # Pydantic emits "title" at the root; ensure it matches the requested
    # class name so the worker's ``derive_class_name`` picks it up.
    schema["title"] = class_name

    target = out_path or py_path.with_suffix(".json")
    target.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("py_path", type=Path, help="Path to the .py schema file.")
    parser.add_argument("class_name", help="BaseModel class to export.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output .json path (defaults to alongside the input).",
    )
    args = parser.parse_args()

    target = convert(args.py_path, args.class_name, args.out)
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
