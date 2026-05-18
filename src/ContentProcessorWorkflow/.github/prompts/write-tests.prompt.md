---
agent: 'agent'
tools: ['search/codebase', 'search', 'edit/editFiles', 'problems', 'runTests', 'runCommands', 'testFailure', 'terminalLastCommand']
description: 'Generate a comprehensive pytest test file for a given source module'
---

# Write Tests for a Module

You are a senior Python test engineer. Given a source module path, create a
comprehensive unit test file following the conventions in
[test-quality.instructions.md](../instructions/test-quality.instructions.md).

## Input

The user will provide a source module path, e.g. `src/utils/credential_util.py`.

## Steps

1. **Read the source module** to understand its public API — classes, functions,
   methods, constants.

2. **Determine the test file path** by mirroring the structure:
   `src/utils/credential_util.py` → `tests/unit/utils/test_credential_util.py`
   For deep sub-packages, flatten into the parent test folder.

3. **Create the test file** with this exact header:
   ```python
   # Copyright (c) Microsoft Corporation.
   # Licensed under the MIT License.
   from __future__ import annotations
   """Unit tests for <module description>."""
   ```

4. **Write test classes** grouped by the public class or function being tested.
   Use `TestPascalCase` class names and `test_snake_case` method names.

5. **Prioritize by testability**:
   - Models/dataclasses → construction, defaults, validation, serialization
   - Pure functions → inputs/outputs, edge cases, error paths
   - Repository methods → mock the database layer with AsyncMock
   - Config/settings → use monkeypatch for environment variables

6. **Apply mocking patterns** (in order of preference):
   - `monkeypatch.setenv` / `monkeypatch.delenv` for env vars
   - `patch.object(Class, "__init__", ...)` to bypass constructors
   - `AsyncMock` for async database/HTTP methods
   - Hand-rolled `_Fake*` classes for complex service stubs
   - `asyncio.run()` wrapper for async tests (no pytest-asyncio)

7. **Use plain `assert`** statements (not unittest-style). Use `pytest.raises`
   for expected exceptions.

8. **Compile-check** the new file:
   ```
   python -m py_compile <test_file>
   ```

9. **Run only the new test file**:
   ```
   pytest <test_file> -v --tb=short
   ```
   Fix any failures before finishing.
