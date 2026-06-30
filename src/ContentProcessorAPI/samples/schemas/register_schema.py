# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Register schemas, create a schema set, and add schemas to the set.

v2 workflow:
  1. Register individual schema files via /schemavault/
  2. Create a schema set via /schemasetvault/
  3. Add each registered schema into the schema set

Usage:
    python register_schema.py <API_BASE_URL> <SCHEMA_INFO_JSON>

Arguments:
    API_BASE_URL       Base URL of the API (e.g. https://host)
    SCHEMA_INFO_JSON   Path to a JSON manifest describing schemas and schema set

Manifest format (see schema_info.json):
    {
        "schemas": [
            { "File": "autoclaim.json", "ClassName": "...", "Description": "..." },
            ...
        ],
        "schemaset": {
            "Name": "Auto Claim",
            "Description": "Claim schema set for auto claims processing"
        }
    }

Only ``.json`` schema files are accepted; the legacy ``.py`` format was
removed as part of the schemavault RCE remediation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests


def _fetch_existing_schemas(schemavault_url: str) -> list[dict]:
    """GET /schemavault/ – return all currently registered schemas."""
    print(f"Fetching existing schemas from: {schemavault_url}")
    try:
        resp = requests.get(schemavault_url, timeout=30)
        resp.raise_for_status()
        schemas = resp.json()
        print(f"Successfully fetched {len(schemas)} existing schema(s).")
        return schemas
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: Could not fetch existing schemas ({exc}). Proceeding...")
        return []


def _register_schema(
    schemavault_url: str,
    schema_path: Path,
    class_name: str,
    description: str,
    existing_schemas: list[dict],
) -> str | None:
    """Register a single schema file. Returns the schema Id or None on failure."""
    print(f"\nProcessing schema: {class_name}")

    if not schema_path.is_file():
        print(f"Error: Schema file '{schema_path}' does not exist. Skipping...")
        return None

    # Check whether this schema is already registered
    existing = next(
        (s for s in existing_schemas if s.get("ClassName") == class_name),
        None,
    )
    if existing:
        schema_id = existing.get("Id")
        print(f"✓ Schema '{class_name}' already exists with ID: {schema_id}")
        print(f"  Description: {existing.get('Description')}")
        return schema_id

    # Only JSON Schema descriptors (.json) are accepted. The legacy
    # ``.py`` (executable Pydantic class) format was removed because
    # the worker would ``exec`` uploaded code, exposing an RCE primitive.
    extension = schema_path.suffix.lower()
    if extension != ".json":
        print(
            f"Error: Unsupported schema extension '{extension}' for "
            f"'{schema_path.name}'. Only .json schemas are accepted. Skipping..."
        )
        return None
    content_type = "application/json"

    print(f"Registering new schema '{class_name}' ({extension})...")
    data_payload = json.dumps({"ClassName": class_name, "Description": description})

    with open(schema_path, "rb") as f:
        files = {"file": (schema_path.name, f, content_type)}
        data = {"data": data_payload}
        resp = requests.post(schemavault_url, files=files, data=data, timeout=60)

    if resp.status_code == 200:
        body = resp.json()
        schema_id = body.get("Id")
        print(
            f"✓ Successfully registered: {body.get('Description')}'s Schema Id - {schema_id}"
        )
        return schema_id

    print(f"✗ Failed to upload '{schema_path.name}'. HTTP Status: {resp.status_code}")
    print(f"Error Response: {resp.text}")
    return None


def _fetch_existing_schemasets(schemasetvault_url: str) -> list[dict]:
    """GET /schemasetvault/ – return all current schema sets."""
    print(f"\nFetching existing schema sets from: {schemasetvault_url}")
    try:
        resp = requests.get(schemasetvault_url, timeout=30)
        resp.raise_for_status()
        sets = resp.json()
        print(f"Successfully fetched {len(sets)} existing schema set(s).")
        return sets
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: Could not fetch existing schema sets ({exc}). Proceeding...")
        return []


def _create_schemaset(
    schemasetvault_url: str,
    name: str,
    description: str,
    existing_sets: list[dict],
) -> str | None:
    """Create a schema set (or return existing Id if name matches). Returns Id or None."""
    # Check whether a set with the same name already exists
    existing = next(
        (s for s in existing_sets if s.get("Name") == name),
        None,
    )
    if existing:
        set_id = existing.get("Id")
        print(f"✓ Schema set '{name}' already exists with ID: {set_id}")
        return set_id

    print(f"Creating schema set '{name}'...")
    resp = requests.post(
        schemasetvault_url,
        json={"Name": name, "Description": description},
        timeout=30,
    )

    if resp.status_code == 200:
        body = resp.json()
        set_id = body.get("Id")
        print(f"✓ Created schema set '{name}' with ID: {set_id}")
        return set_id

    print(f"✗ Failed to create schema set. HTTP Status: {resp.status_code}")
    print(f"Error Response: {resp.text}")
    return None


def _get_schemas_in_set(schemasetvault_url: str, schemaset_id: str) -> set[str]:
    """Return the set of schema Ids already in the given schema set."""
    url = f"{schemasetvault_url}{schemaset_id}/schemas"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return {s.get("Id") for s in resp.json()}
    except Exception:  # noqa: BLE001
        return set()


def _add_schema_to_set(
    schemasetvault_url: str,
    schemaset_id: str,
    schema_id: str,
    class_name: str,
    already_in_set: set[str],
) -> None:
    """POST /schemasetvault/{schemaset_id}/schemas to add a schema."""
    if schema_id in already_in_set:
        print(
            f"  ✓ Schema '{class_name}' ({schema_id}) already in schema set – skipped"
        )
        return

    url = f"{schemasetvault_url}{schemaset_id}/schemas"
    resp = requests.post(url, json={"SchemaId": schema_id}, timeout=30)

    if resp.status_code == 200:
        print(f"  ✓ Added '{class_name}' ({schema_id}) to schema set")
    else:
        print(
            f"  ✗ Failed to add '{class_name}' to schema set. HTTP {resp.status_code}"
        )
        print(f"    Error Response: {resp.text}")


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <API_BASE_URL> <SCHEMA_INFO_JSON>")
        sys.exit(1)

    api_base_url = sys.argv[1].rstrip("/")
    schema_info_json = sys.argv[2]

    schema_info_path = Path(schema_info_json)
    if not schema_info_path.is_file():
        print(f"Error: JSON file '{schema_info_json}' does not exist.")
        sys.exit(1)

    with open(schema_info_path) as f:
        manifest = json.load(f)

    schema_entries = manifest["schemas"]
    schemaset_config = manifest["schemaset"]
    schema_info_dir = schema_info_path.resolve().parent

    schemavault_url = f"{api_base_url}/schemavault/"
    schemasetvault_url = f"{api_base_url}/schemasetvault/"

    # --- Step 1: Register schemas ----------------------------------------
    print("=" * 60)
    print("Step 1: Register schemas")
    print("=" * 60)

    existing_schemas = _fetch_existing_schemas(schemavault_url)

    registered: dict[str, str] = {}  # ClassName -> schema Id
    for entry in schema_entries:
        schema_file = Path(entry["File"])
        if not schema_file.is_absolute():
            schema_file = schema_info_dir / schema_file

        schema_id = _register_schema(
            schemavault_url=schemavault_url,
            schema_path=schema_file,
            class_name=entry["ClassName"],
            description=entry["Description"],
            existing_schemas=existing_schemas,
        )
        if schema_id:
            registered[entry["ClassName"]] = schema_id

    # --- Step 2: Create schema set ----------------------------------------
    print()
    print("=" * 60)
    print("Step 2: Create schema set")
    print("=" * 60)

    existing_sets = _fetch_existing_schemasets(schemasetvault_url)
    schemaset_id = _create_schemaset(
        schemasetvault_url=schemasetvault_url,
        name=schemaset_config["Name"],
        description=schemaset_config["Description"],
        existing_sets=existing_sets,
    )

    if not schemaset_id:
        print("Error: Could not create or find schema set. Aborting step 3.")
        sys.exit(1)

    # --- Step 3: Add schemas into the schema set --------------------------
    print()
    print("=" * 60)
    print("Step 3: Add schemas to schema set")
    print("=" * 60)

    already_in_set = _get_schemas_in_set(schemasetvault_url, schemaset_id)

    for class_name, schema_id in registered.items():
        _add_schema_to_set(
            schemasetvault_url=schemasetvault_url,
            schemaset_id=schemaset_id,
            schema_id=schema_id,
            class_name=class_name,
            already_in_set=already_in_set,
        )

    print()
    print("=" * 60)
    print("Schema registration process completed.")
    print(f"  Schema set ID: {schemaset_id}")
    print(f"  Schemas added: {len(registered)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
