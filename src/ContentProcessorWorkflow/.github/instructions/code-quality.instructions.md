---
applyTo: '**.py'
---
# Systematic Code-Quality Pass Instructions for Python Codebase

You are performing a systematic code-quality pass on a Python codebase. Work through every folder one at a time. For each Python file, apply ALL of the following rules, then compile-check every edited file before moving to the next folder.

## 1. Copyright & Module Docstring
- Every `.py` file (except empty `__init__.py`) must start with:
  ```
  # Copyright (c) Microsoft Corporation.
  # Licensed under the MIT License.
  ```
- Immediately after, add or replace the module-level docstring. It must:
  - Describe what the module does in 1-2 sentences.
  - Mention its role in the broader system (e.g., which pipeline stage, what it depends on).
  - NOT contain generic filler like "This module provides utilities for…"

## 2. Package `__init__.py`
- If empty, add the copyright header and a package docstring listing sub-modules with one-line descriptions.

## 3. Class Docstrings
- Replace generic class docstrings with structured ones:
  ```
  """One-line summary.

  Responsibilities:
      1. First responsibility.
      2. Second responsibility.

  Attributes:
      attr_name: Description.
  """
  ```
- For dataclasses / Pydantic models, list all fields under "Attributes:".

## 4. Method / Function Docstrings
- Every public and non-trivial private method must have a docstring.
- Use this structure:
  ```
  """One-line summary.

  Steps:                    ← only for complex multi-step methods
      1. First step.
      2. Second step.

  Args:
      param: Description.

  Returns:
      Description.

  Raises:
      ExceptionType: When condition.
  """
  ```
- Simple one-line methods (getters, delegates) get a single-line docstring.

## 5. Comment Cleanup — REMOVE These
- **Redundant inline comments** that just restate the code:
  `# Create Claim_Process entry in Cosmos DB` above `new_claim_process = Claim_Process(...)`
- **Banner comments** / section dividers:
  `############################################################`
  `## Initialize AgentFrameworkHelper and add it to the app  ##`
  `############################################################`
- **Commented-out code** (dead imports, print statements, old logic).
- **Heritage/provenance comments** referencing deleted files:
  `Replaces create_quiet_logger() from quiet_logging.py`
- **Placeholder comments** that describe unimplemented intent:
  `# Placeholder for document processing logic`
- **"For demonstration" / "Here you would typically"** comments.

## 6. Comment Cleanup — KEEP These
- **Actionable TODOs** with clear intent: `# TODO: Make configurable if needed`
- **Non-obvious "why" comments** that explain a design decision:
  `# Avoid unbounded growth on very chatty endpoints.`
- **Contract/protocol comments** that document external API behavior:
  `# Image files bypass the 'extract' step.`

## 7. Fix Stale References
- Search for outdated terminology (old project names, old class names, old pipeline descriptions) and correct them to match the current code.

## 8. Remove Dead Code
- Delete unused imports.
- Delete `pass` in `else` blocks that only existed to hold a now-deleted comment.
- Delete redundant assignments like `claim_id = claim_id`.
- Delete duplicate imports (e.g., `import os` at module level AND inside a function).

## 9. Compile-Check
- After finishing each folder, run `python -m py_compile <file>` on every edited file.
- Fix any errors before proceeding to the next folder.

## Working Process
1. List the directory tree of the target folder.
2. Read all Python files in the folder.
3. Create a TODO list for the folder (one item per file + one for compile-check).
4. Edit files, marking each TODO as you go.
5. Compile-check all edited files.
6. Move to the next folder.

Start with the folder I specify and work through it completely before asking what to do next.
