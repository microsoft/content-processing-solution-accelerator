---
agent: 'agent'
tools: ['search/codebase', 'search', 'edit/editFiles', 'problems', 'runTests', 'runCommands', 'testFailure', 'terminalLastCommand']
description: 'Audit and sanitize existing test files — find orphaned tests, stale assertions, missing headers, and compile errors'
---

# Sanitize Test Suite

You are a senior Python test engineer performing a sanitization pass on the
test suite. Follow the project conventions in [test-quality.instructions.md](../instructions/test-quality.instructions.md).

## Steps

1. **List all test files** under `tests/` (exclude `__pycache__`, `__init__.py`).

2. **Find orphaned tests** — for every `import` in each test file, verify the
   imported module exists under `src/`. If it references a deleted or renamed
   module, mark the test file for deletion.

3. **Find stale assertions** — check that field names, method signatures, and
   keyword arguments used in assertions match the current source code. Fix any
   mismatches.

4. **Check file conventions** — every test file must have:
   - Copyright header (2 lines)
   - `from __future__ import annotations`
   - Module-level docstring
   Report and fix any that are missing.

5. **Compile-check** every remaining test file:
   ```
   python -m py_compile <file>
   ```
   Fix any errors.

6. **Run the full suite**:
   ```
   pytest tests/ -v --tb=short
   ```
   Report the final pass/fail count.

## Output

Produce a summary table:

| Action       | File                  | Detail                          |
|--------------|-----------------------|---------------------------------|
| DELETED      | test_old_module.py    | imports deleted module X        |
| FIXED        | test_foo.py           | renamed field bar → baz         |
| HEADER ADDED | test_bar.py           | missing copyright               |
| COMPILE OK   | (all)                 | 0 errors                        |
| TEST RUN     | (all)                 | N passed, 0 failed              |
