---
applyTo: 'tests/**'
---
# Test Quality Instructions

You are a senior Python test engineer. Your job is to audit, sanitize, and write
comprehensive unit tests for a Python project that follows these conventions.

═══════════════════════════════════════════════════════════════════════════════
1. PROJECT LAYOUT
═══════════════════════════════════════════════════════════════════════════════

The project uses a src-layout with tests outside src/:

    ProjectRoot/
    ├── src/                  ← production code only
    │   ├── libs/
    │   ├── services/
    │   ├── steps/
    │   ├── utils/
    │   └── repositories/
    ├── tests/                ← all test code lives here (peer to src/)
    │   ├── conftest.py       ← sys.path setup for imports
    │   └── unit/
    │       ├── libs/
    │       ├── services/
    │       ├── steps/
    │       ├── utils/
    │       └── repositories/
    ├── pyproject.toml        ← pytest + coverage config
    ├── .gitignore            ← excludes htmlcov/, .coverage*, .pytest_cache/
    └── .dockerignore         ← excludes tests/, htmlcov/, .coverage*, etc.

Key rules:
- tests/ should NOT have an __init__.py (tests are not a package).
- Test directory structure mirrors src/ at the top level
  (e.g., src/utils/ → tests/unit/utils/, src/services/ → tests/unit/services/).
  Deep sub-packages may be flattened: e.g., tests for
  src/steps/gap_analysis/executor/gap_executor.py live in
  tests/unit/steps/test_gap_executor.py — no need to replicate every
  nested executor/models/prompt directory.
- tests/conftest.py adds src/ to sys.path.

═══════════════════════════════════════════════════════════════════════════════
2. TEST SANITIZATION (run first, before writing new tests)
═══════════════════════════════════════════════════════════════════════════════

Before writing any new tests, audit all existing test files:

a) FIND ORPHANED TESTS — tests that import modules that no longer exist.
   For every test file, verify that every import resolves to a real source file.
   Delete any test file whose imports reference deleted/renamed modules.

b) FIND STALE ASSERTIONS — tests whose assertions reference renamed fields,
   changed method signatures, or removed keyword arguments.
   Fix these to match the current source code.

c) COMPILE-CHECK every remaining test file:
       python -m py_compile <test_file>
   Fix any syntax errors or import failures.

d) ADD MISSING COPYRIGHT HEADERS to any file that lacks one.

═══════════════════════════════════════════════════════════════════════════════
3. FILE FORMAT CONVENTIONS
═══════════════════════════════════════════════════════════════════════════════

Every test file must follow this exact structure:

    # Copyright (c) Microsoft Corporation.
    # Licensed under the MIT License.

    """Tests for <module_path> (<brief description>)."""

    from __future__ import annotations

    <stdlib imports>
    <third-party imports (pytest, pydantic, etc.)>
    <application imports>


    # ── Section Name ────────────────────────────────────────────────────────


    class TestClassName:
        """Optional class docstring."""

        def test_descriptive_snake_case_name(self):
            ...

Rules:
- ALWAYS include the 2-line copyright header.
- ALWAYS include `from __future__ import annotations`.
- ALWAYS include a module-level docstring: """Tests for <path>."""
- Use ASCII banner comments to separate logical sections.
- Import pytest only when you use its features (raises, parametrize, fixtures).

═══════════════════════════════════════════════════════════════════════════════
4. NAMING CONVENTIONS
═══════════════════════════════════════════════════════════════════════════════

| Element          | Convention                  | Example                              |
|------------------|-----------------------------|--------------------------------------|
| Test file        | test_<module_name>.py       | test_credential_util.py              |
| Test class       | TestPascalCase              | TestGetAzureCredential               |
| Test method      | test_snake_case             | test_returns_cli_in_local_env        |
| Helper method    | _prefixed                   | _make_executor, _reset_class_state   |
| Fixture (rare)   | snake_case function         | monkeypatch, tmp_path                |

File naming must mirror the source module:
  src/utils/credential_util.py  →  tests/unit/utils/test_credential_util.py
  src/steps/claim_processor.py  →  tests/unit/steps/test_claim_processor.py

═══════════════════════════════════════════════════════════════════════════════
5. WHAT TO TEST (prioritize by testability)
═══════════════════════════════════════════════════════════════════════════════

Focus on UNIT-TESTABLE code — pure logic that can run without external services:

HIGH PRIORITY (test these thoroughly):
- Pydantic/dataclass models: construction, defaults, validation, serialization
- Enum classes: values, membership, string inheritance
- Exception classes: message formatting, detail serialization
- Pure utility functions: string manipulation, template rendering, file loading
- Static/class methods with deterministic output
- Builder patterns: fluent API chaining, attribute storage

MEDIUM PRIORITY (test with mocks):
- Repository CRUD methods: mock the database layer with AsyncMock
- Credential factories: mock Azure SDK classes, use monkeypatch for env vars
- Settings/config classes: use monkeypatch to control environment variables
- Prompt/rules loaders: test file-not-found, empty-file, valid-file scenarios

LOW PRIORITY (skip or test only the interface):
- Methods that orchestrate multiple external services (HTTP + DB + agent)
- Main entry points (main.py, main_service.py)
- Deep async orchestration with event streaming

═══════════════════════════════════════════════════════════════════════════════
6. MOCKING PATTERNS
═══════════════════════════════════════════════════════════════════════════════

Use these patterns in order of preference:

a) monkeypatch (for environment variables):
       def test_something(self, monkeypatch):
           monkeypatch.setenv("KEY", "value")
           monkeypatch.delenv("KEY", raising=False)

b) patch.object (for bypassing __init__):
       with patch.object(MyClass, "__init__", lambda self, *a, **kw: None):
           obj = MyClass.__new__(MyClass)

c) AsyncMock (for async database/HTTP methods):
       from unittest.mock import AsyncMock, patch
       mock_repo = AsyncMock()
       mock_repo.find_one.return_value = {"_id": "123"}

d) Hand-rolled fake classes (for complex service stubs):
       class _FakeQueue:
           def __init__(self):
               self.deleted: list[tuple[str, str]] = []
           def delete_message(self, msg_id, receipt):
               self.deleted.append((msg_id, receipt))

e) asyncio.run() wrapper (for async tests WITHOUT pytest-asyncio):
       def test_async_operation(self):
           async def _run():
               result = await some_async_function()
               assert result == expected
           asyncio.run(_run())

DO NOT use pytest-asyncio (it is not installed).
DO NOT use unittest.TestCase (use plain pytest classes).

═══════════════════════════════════════════════════════════════════════════════
7. ASSERTION STYLE
═══════════════════════════════════════════════════════════════════════════════

Use plain `assert` statements (pytest-native). Examples:

    assert result == expected
    assert "keyword" in str(exc)
    assert len(items) == 3
    assert obj.field is None
    assert isinstance(cred, SomeClass)

For expected exceptions:
    with pytest.raises(ValueError, match=r"must include"):
        function_that_raises()

For Pydantic validation errors:
    with pytest.raises(ValidationError):
        MyModel()  # missing required fields

═══════════════════════════════════════════════════════════════════════════════
8. COVERAGE CONFIGURATION
═══════════════════════════════════════════════════════════════════════════════

pyproject.toml must include:

    [tool.pytest.ini_options]
    testpaths = ["tests"]
    pythonpath = ["src"]

    [tool.coverage.run]
    source = ["src"]
    omit = ["src/__init__.py"]

    [tool.coverage.report]
    show_missing = true
    skip_empty = true
    exclude_lines = [
        "pragma: no cover",
        "if __name__ == .__main__.",
        "if TYPE_CHECKING:",
    ]

    [tool.coverage.html]
    directory = "htmlcov"

Run with:  pytest --cov --cov-report=term-missing --cov-report=html

═══════════════════════════════════════════════════════════════════════════════
9. DOCKER / GIT EXCLUSIONS
═══════════════════════════════════════════════════════════════════════════════

.gitignore must exclude test artifacts (NOT the tests/ folder itself):
    .pytest_cache/
    .coverage
    .coverage.*
    coverage.xml
    htmlcov/
    .hypothesis/

.dockerignore must exclude tests AND artifacts from the build context:
    tests/
    htmlcov/
    .coverage
    .coverage.*
    coverage.xml
    .pytest_cache/
    .hypothesis/

═══════════════════════════════════════════════════════════════════════════════
10. WORKFLOW CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

Follow this order:

□ Phase 1 — Sanitize
  1. List all test files
  2. For each: verify imports resolve to existing source modules
  3. Delete orphaned test files (imports reference deleted modules)
  4. Fix stale tests (wrong field names, changed signatures, renamed kwargs)
  5. Add missing copyright headers
  6. Compile-check all remaining tests: python -m py_compile <file>

□ Phase 2 — Identify gaps
  7. List all source modules under src/ (excluding __init__.py, __pycache__)
  8. List all existing test files under tests/
  9. Produce a gap matrix: source module → has test? → coverage gaps

□ Phase 3 — Write tests
  10. For each uncovered module, create a test file following the conventions
  11. Prioritize: models → utils → repositories → framework libs → executors
  12. Compile-check each new test file immediately after creation

□ Phase 4 — Validate
  13. Run full suite: pytest tests/ -v --tb=short
  14. Fix any failures
  15. Run with coverage: pytest --cov --cov-report=term-missing
  16. Review coverage gaps; write additional tests for missed branches if practical

□ Phase 5 — Project hygiene
  17. Ensure tests/ is outside src/ (not src/tests/)
  18. Ensure pyproject.toml has [tool.pytest] and [tool.coverage] sections
  19. Ensure .gitignore excludes test artifacts
  20. Ensure .dockerignore excludes tests/ and all test artifacts
