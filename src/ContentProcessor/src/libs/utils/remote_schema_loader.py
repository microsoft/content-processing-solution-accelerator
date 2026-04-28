# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Materialise a Pydantic model from a JSON Schema descriptor.

A JSON schema descriptor is treated strictly as data:

1. Bytes are downloaded from blob storage.
2. ``json.loads`` parses them into a ``dict``.
3. A recursive walk converts the schema into Pydantic ``BaseModel``
   subclasses via :func:`pydantic.create_model`.

There is **no** ``exec``, ``compile``, ``importlib`` or any other
mechanism that would execute attacker-supplied code. The worst a
malicious schema can do is fail validation at load time.
"""

from __future__ import annotations

import json
import logging
from typing import Any, ForwardRef, List, Literal, Optional, Tuple, Type, Union

from azure.storage.blob import BlobServiceClient
from pydantic import BaseModel, ConfigDict, Field, create_model

from libs.utils.azure_credential_utils import get_azure_credential

logger = logging.getLogger(__name__)


class JsonSchemaLoadError(ValueError):
    """Raised when a JSON schema descriptor cannot be turned into a model."""


def load_schema_from_blob_json(
    account_url: str,
    container_name: str,
    blob_name: str,
    model_name: str,
) -> Type[BaseModel]:
    """Download a JSON Schema and return a generated Pydantic model class.

    Args:
        account_url: Azure Blob Storage account URL.
        container_name: Container (path) holding the blob.
        blob_name: Blob filename to download (a ``.json`` schema).
        model_name: Name to assign to the root generated model class.

    Returns:
        A dynamically generated subclass of :class:`pydantic.BaseModel`
        whose shape matches the JSON Schema.

    Raises:
        JsonSchemaLoadError: If the blob is not valid JSON or the schema
            cannot be translated into a Pydantic model.
    """
    raw = _download_blob_content(container_name, blob_name, account_url)
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise JsonSchemaLoadError(
            f"Schema blob '{blob_name}' is not valid JSON: {exc.msg}"
        ) from exc

    if not isinstance(document, dict):
        raise JsonSchemaLoadError("Schema root must be a JSON object.")

    return build_model_from_schema(document, model_name)


def build_model_from_schema(
    document: dict[str, Any], model_name: str
) -> Type[BaseModel]:
    """Build a Pydantic model class from an in-memory JSON Schema document.

    This is split out from :func:`load_schema_from_blob_json` so it can
    be unit-tested without touching Azure storage.
    """
    defs = document.get("$defs") or document.get("definitions") or {}
    if not isinstance(defs, dict):
        raise JsonSchemaLoadError("'$defs' must be a JSON object if present.")

    builder = _ModelBuilder(defs)
    model = builder.build_object(document, model_name, is_root=True)
    builder.resolve_forward_refs()
    return model


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _download_blob_content(
    container_name: str, blob_name: str, account_url: str
) -> str:
    """Download the blob and return its UTF-8 contents as a string."""
    credential = get_azure_credential()
    blob_service_client = BlobServiceClient(
        account_url=account_url, credential=credential
    )
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=blob_name
    )
    return blob_client.download_blob().readall().decode("utf-8")


class _ModelBuilder:
    """Recursive JSON-Schema-to-Pydantic translator.

    The builder maintains a memo of already-generated models keyed by
    ``$defs`` name so that repeated ``$ref`` references reuse the same
    class and so that self/mutually-recursive schemas terminate.
    """

    _PRIMITIVE_TYPES: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "null": type(None),
    }

    def __init__(self, defs: dict[str, Any]):
        self._defs = defs
        self._models: dict[str, Type[BaseModel]] = {}
        self._in_progress: set[str] = set()
        self._all_models: list[Type[BaseModel]] = []

    # -- public driver ----------------------------------------------------

    def build_object(
        self,
        node: dict[str, Any],
        model_name: str,
        *,
        is_root: bool = False,
    ) -> Type[BaseModel]:
        """Build a Pydantic model from an object-typed schema node."""
        if not is_root:
            # Avoid colliding with a reserved $defs name when the caller
            # supplies an inline object schema.
            model_name = self._dedupe_name(model_name)

        # Reserve the slot so $ref to the same definition resolves to us
        # even before we finish constructing it.
        self._in_progress.add(model_name)
        try:
            properties = node.get("properties") or {}
            required = set(node.get("required") or [])
            fields: dict[str, tuple[Any, Any]] = {}

            for prop_name, prop_schema in properties.items():
                python_type, default = self._field_for(
                    prop_schema, prop_name, parent_name=model_name
                )
                if prop_name in required and default is None:
                    field_default: Any = ...
                else:
                    field_default = default

                description = (
                    prop_schema.get("description")
                    if isinstance(prop_schema, dict)
                    else None
                )
                fields[prop_name] = (
                    python_type,
                    Field(default=field_default, description=description),
                )

            model = create_model(  # type: ignore[call-overload]
                model_name,
                __config__=ConfigDict(extra="ignore"),
                **fields,
            )
            description = node.get("description") or node.get("title")
            if isinstance(description, str):
                model.__doc__ = description
        finally:
            self._in_progress.discard(model_name)

        self._models[model_name] = model
        self._all_models.append(model)
        return model

    def resolve_forward_refs(self) -> None:
        """Resolve any ``ForwardRef`` placeholders left during construction."""
        ns = dict(self._models)
        for model in self._all_models:
            try:
                model.model_rebuild(_types_namespace=ns)
            except Exception:  # pragma: no cover - defensive
                logger.exception(
                    "Failed to rebuild model %s while resolving forward refs",
                    model.__name__,
                )

    # -- field translation ------------------------------------------------

    def _field_for(
        self,
        schema: Any,
        prop_name: str,
        parent_name: str,
    ) -> Tuple[Any, Any]:
        """Translate a property schema into ``(python_type, default_value)``.

        ``default_value`` is ``None`` when the field is nullable / optional;
        callers replace it with ``...`` when the field is required.
        """
        if schema is True or schema is None or schema == {}:
            return (Any, None)
        if not isinstance(schema, dict):
            raise JsonSchemaLoadError(
                f"Property '{prop_name}' has invalid schema (not an object)."
            )

        # $ref resolution (local refs only).
        ref = schema.get("$ref")
        if isinstance(ref, str):
            return (self._resolve_ref(ref), None)

        # anyOf / oneOf — treat as Union.
        for key in ("anyOf", "oneOf"):
            if key in schema:
                members = schema[key]
                if not isinstance(members, list) or not members:
                    raise JsonSchemaLoadError(
                        f"'{key}' for '{prop_name}' must be a non-empty list."
                    )
                resolved = [
                    self._field_for(m, prop_name, parent_name)[0] for m in members
                ]
                return (Union[tuple(resolved)], None)  # type: ignore[valid-type]

        # enum — Literal[...] of allowed values.
        if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
            literal_args = tuple(schema["enum"])
            return (Literal[literal_args], None)  # type: ignore[valid-type]

        json_type = schema.get("type")

        if isinstance(json_type, list):
            # e.g. ["string", "null"]
            python_types = [self._type_for_simple(t, schema, prop_name, parent_name)
                            for t in json_type]
            if len(python_types) == 1:
                return (python_types[0], None)
            unioned: Any = Union[tuple(python_types)]  # type: ignore[valid-type]
            return (unioned, None)

        if isinstance(json_type, str):
            return (
                self._type_for_simple(json_type, schema, prop_name, parent_name),
                None,
            )

        # No type declared → permissive.
        return (Any, None)

    def _type_for_simple(
        self,
        json_type: str,
        schema: dict[str, Any],
        prop_name: str,
        parent_name: str,
    ) -> Any:
        """Translate a single JSON-Schema primitive ``type`` token."""
        if json_type in self._PRIMITIVE_TYPES:
            return self._PRIMITIVE_TYPES[json_type]
        if json_type == "array":
            items = schema.get("items")
            if items is None:
                return List[Any]
            item_type, _ = self._field_for(items, f"{prop_name}_item", parent_name)
            return List[item_type]  # type: ignore[valid-type]
        if json_type == "object":
            inline_name = self._inline_object_name(parent_name, prop_name)
            return self.build_object(schema, inline_name)
        raise JsonSchemaLoadError(
            f"Unsupported JSON Schema type '{json_type}' for property '{prop_name}'."
        )

    def _resolve_ref(self, ref: str) -> Any:
        """Resolve a local JSON-Pointer reference into a generated model."""
        prefix_defs = "#/$defs/"
        prefix_definitions = "#/definitions/"
        if ref.startswith(prefix_defs):
            name = ref[len(prefix_defs):]
        elif ref.startswith(prefix_definitions):
            name = ref[len(prefix_definitions):]
        else:
            raise JsonSchemaLoadError(
                f"Only local '#/$defs/...' refs are supported (got '{ref}')."
            )

        if name in self._models:
            return self._models[name]

        if name in self._in_progress:
            # Cycle: emit a forward reference; resolved later.
            return ForwardRef(name)

        if name not in self._defs:
            raise JsonSchemaLoadError(
                f"Reference '{ref}' does not resolve to a known $defs entry."
            )

        sub_schema = self._defs[name]
        if not isinstance(sub_schema, dict):
            raise JsonSchemaLoadError(
                f"$defs entry '{name}' must be a JSON object."
            )

        sub_type = sub_schema.get("type")
        if sub_type == "object" or "properties" in sub_schema:
            return self.build_object(sub_schema, name)

        # Non-object $defs entry (rare): translate as a field type.
        translated, _ = self._field_for(sub_schema, name, parent_name=name)
        # Cache simple-type aliases so repeated refs return the same thing.
        # (We don't add to self._models because that map is for BaseModel
        # subclasses only, but ForwardRef handling does not apply to scalar
        # aliases — return the type directly.)
        return translated

    # -- name helpers ----------------------------------------------------

    def _dedupe_name(self, candidate: str) -> str:
        """Ensure a freshly generated model name does not collide."""
        if candidate not in self._models and candidate not in self._in_progress:
            return candidate
        i = 2
        while f"{candidate}_{i}" in self._models or f"{candidate}_{i}" in self._in_progress:
            i += 1
        return f"{candidate}_{i}"

    @staticmethod
    def _inline_object_name(parent_name: str, prop_name: str) -> str:
        """Synthesize a stable name for an inline object schema."""
        camel = "".join(part.capitalize() for part in prop_name.split("_") if part)
        return f"{parent_name}_{camel or 'Inline'}"
