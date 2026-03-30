---
applyTo: '**/*.test.{ts,tsx}'
---
# Test Quality Instructions for TypeScript & React Codebase

You are a senior TypeScript/React test engineer. Your job is to audit, sanitize, and write comprehensive unit tests for a React 18 + TypeScript codebase that uses Fluent UI v9, Redux Toolkit, MSAL, and SCSS. The test stack is **Jest 27** (bundled via react-scripts / react-app-rewired) with **React Testing Library**.

---

## 1. Project Layout (Co-located Tests)

Tests live **next to the source files** they cover — NOT in a separate `tests/` folder:

```
src/
├── test-utils.tsx                        ← shared render helper
├── setupTests.ts                         ← jest-dom + global mocks
├── App.tsx
├── App.test.tsx                          ← test for App
├── Components/
│   └── Header/
│       ├── Header.tsx
│       └── Header.test.tsx               ← test for Header
├── Hooks/
│   └── useFileType.ts
│       └── useFileType.test.ts           ← test for hook
├── Services/
│   └── httpUtility.ts
│       └── httpUtility.test.ts           ← test for service
├── store/
│   └── slices/
│       ├── leftPanelSlice.ts
│       └── leftPanelSlice.test.ts        ← test for slice
└── Pages/
    └── DefaultPage/
        ├── PanelLeft.tsx
        └── PanelLeft.test.tsx            ← test for page component
```

Key rules:
- **Every test file sits in the same directory as the module it tests.**
- CRA's built-in `testMatch` discovers `src/**/*.test.{ts,tsx}` automatically — no jest.config overrides needed.
- A shared `src/test-utils.tsx` re-exports React Testing Library with app-level providers pre-wrapped (see §6).
- `src/setupTests.ts` imports `@testing-library/jest-dom` so matchers are globally available.

---

## 2. Test Sanitization (run first, before writing new tests)

Before writing any new tests, audit all existing test files:

a) **FIND ORPHANED TESTS** — tests that import modules that no longer exist.
   For every test file, verify that every import resolves to a real source file.
   Delete any test file whose import target has been deleted or renamed.

b) **FIND STALE ASSERTIONS** — tests whose assertions reference renamed props,
   changed function signatures, or removed Redux state fields.
   Fix these to match the current source code.

c) **TYPE-CHECK** every remaining test file:
   ```
   pnpm tsc --noEmit
   ```
   Fix any type errors or import failures.

d) **ADD MISSING COPYRIGHT HEADERS** to any file that lacks one.

---

## 3. File Format Conventions

Every test file must follow this structure:

```tsx
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Tests for <ModuleName> — <brief description>.
 */

import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '../../test-utils';
import { MyComponent } from './MyComponent';

// ── Section Name ────────────────────────────────────────────────────────

describe('MyComponent', () => {
  it('should render the title', () => {
    renderWithProviders(<MyComponent title="Hello" />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

Rules:
- ALWAYS include the 2-line copyright header.
- ALWAYS include a JSDoc `@file` comment describing what is tested.
- Use `describe` / `it` blocks (not `test`). Nest `describe` for sub-scenarios.
- Use ASCII banner comments to separate logical sections in longer files.
- Import `screen`, `waitFor`, `within` from `@testing-library/react`.
- Import `userEvent` from `@testing-library/user-event`.
- Import the custom `renderWithProviders` from `test-utils.tsx` for component tests.

---

## 4. Naming Conventions

| Element           | Convention                          | Example                                  |
|-------------------|-------------------------------------|------------------------------------------|
| Test file         | `<SourceFile>.test.tsx` or `.test.ts` | `Header.test.tsx`                      |
| `describe` block  | PascalCase component/function name  | `describe('Header', …)`                 |
| `it` block        | starts with "should …"             | `it('should show the logo', …)`          |
| Helper function   | `create…` / `render…` / `mock…`    | `createMockStore`, `renderHeader`        |
| Mock file         | `__mocks__/<module>.ts`             | `__mocks__/axios.ts`                     |

File naming must mirror the source module:
```
src/Components/Header/Header.tsx       → src/Components/Header/Header.test.tsx
src/store/slices/leftPanelSlice.ts     → src/store/slices/leftPanelSlice.test.ts
src/Hooks/useFileType.ts               → src/Hooks/useFileType.test.ts
src/Services/httpUtility.ts            → src/Services/httpUtility.test.ts
```

---

## 5. What to Test (prioritize by testability)

Focus on UNIT-TESTABLE code — pure logic and isolated components:

**HIGH PRIORITY** (test these thoroughly):
- **Redux slices**: reducers, action creators, initial state, edge cases for each `case`
- **Utility functions**: `httpUtility.ts`, helpers, formatters, validators
- **Custom hooks**: `useFileType`, `useHeaderHooks`, `usePanelHooks` (via `renderHook`)
- **Type definitions**: if a type file exports runtime validators or factories, test them
- **Pure components**: components with no side effects, only props → rendered output

**MEDIUM PRIORITY** (test with mocks):
- **Components with Redux**: use `renderWithProviders` with a preloaded state
- **Components with API calls**: mock `axios` / `httpUtility` to return controlled data
- **MSAL-protected components**: mock `useAuth` / `useMsal` hooks
- **Components with router dependencies**: wrap in `<MemoryRouter>` with initial entries

**LOW PRIORITY** (skip or test only the interface):
- `index.tsx` (entry point bootstrap)
- MSAL configuration files (`msaConfig.ts`, `msalInstance.tsx`)
- SCSS/CSS files (tested via visual regression, not unit tests)

---

## 6. Test Utilities — `src/test-utils.tsx`

Create a shared render helper that wraps all app-level providers:

```tsx
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Custom render function that wraps components with all app-level providers.
 */

import React, { type PropsWithChildren, type ReactElement } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { configureStore, type EnhancedStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { FluentProvider, webLightTheme } from '@fluentui/react-components';

import { rootReducer, type RootState } from './store/rootReducer';

/** Options for the custom render function. */
interface ExtendedRenderOptions extends Omit<RenderOptions, 'queries'> {
  readonly preloadedState?: Partial<RootState>;
  readonly store?: EnhancedStore;
  readonly route?: string;
}

/**
 * Renders a component wrapped in Redux Provider, FluentProvider, and MemoryRouter.
 * Use this instead of bare `render()` for any component that depends on context.
 */
export function renderWithProviders(
  ui: ReactElement,
  {
    preloadedState = {},
    store = configureStore({ reducer: rootReducer, preloadedState }),
    route = '/',
    ...renderOptions
  }: ExtendedRenderOptions = {},
) {
  function Wrapper({ children }: PropsWithChildren) {
    return (
      <Provider store={store}>
        <FluentProvider theme={webLightTheme}>
          <MemoryRouter initialEntries={[route]}>
            {children}
          </MemoryRouter>
        </FluentProvider>
      </Provider>
    );
  }

  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}

// Re-export everything from RTL so tests only need one import source.
export * from '@testing-library/react';
```

Also ensure `src/setupTests.ts` exists:

```ts
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Jest setup — extends expect with jest-dom matchers.
 */

import '@testing-library/jest-dom';
```

---

## 7. Mocking Patterns

Use these patterns in order of preference:

### a) `jest.mock` — module-level mocks (axios, services, MSAL)

```ts
jest.mock('../../Services/httpUtility', () => ({
  getRequest: jest.fn(),
  postRequest: jest.fn(),
}));
```

### b) `jest.spyOn` — spy on individual methods without replacing the module

```ts
const spy = jest.spyOn(httpUtility, 'getRequest').mockResolvedValue({ data: [] });
// ...
expect(spy).toHaveBeenCalledWith('/api/items');
spy.mockRestore();
```

### c) Preloaded Redux state — for components that read from the store

```ts
renderWithProviders(<PanelLeft />, {
  preloadedState: {
    leftPanel: { selectedItem: mockItem, items: [mockItem] },
  },
});
```

### d) Mock MSAL hooks — for auth-dependent components

```ts
jest.mock('../../msal-auth/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { name: 'Test User' },
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));
```

### e) Mock `window` / browser APIs

```ts
beforeEach(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    })),
  });
});
```

### f) Factory helpers for complex mock data

```ts
function createMockProcessItem(overrides: Partial<ProcessItem> = {}): ProcessItem {
  return {
    id: 'item-1',
    status: 'completed',
    fileName: 'test.pdf',
    ...overrides,
  };
}
```

**DO NOT** use `jest.mock` for modules that can be tested directly.
**DO NOT** mock implementation details — mock at the boundary (API, store, auth).

---

## 8. Assertion Style

Use `expect` with **jest-dom** matchers for DOM assertions and plain Jest matchers for logic:

### DOM assertions (via `@testing-library/jest-dom`)

```ts
expect(screen.getByText('Submit')).toBeInTheDocument();
expect(screen.getByRole('button')).toBeEnabled();
expect(screen.getByTestId('loader')).toHaveClass('spinner--active');
expect(screen.queryByText('Error')).not.toBeInTheDocument();
```

### Logic assertions (plain Jest)

```ts
expect(result).toBe(42);
expect(items).toHaveLength(3);
expect(state.selectedItem).toBeNull();
expect(action.type).toBe('leftPanel/fetchItems/fulfilled');
expect(callback).toHaveBeenCalledTimes(1);
expect(callback).toHaveBeenCalledWith('arg1', expect.any(Number));
```

### Async assertions

```ts
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
});
```

### Error assertions

```ts
expect(() => dangerousFunction()).toThrow('invalid input');
```

---

## 9. Testing Specific Patterns

### Redux Slices

Test reducers as pure functions — no DOM, no providers:

```ts
import reducer, { setSelectedItem, resetState } from './leftPanelSlice';

describe('leftPanelSlice', () => {
  it('should return the initial state', () => {
    expect(reducer(undefined, { type: 'unknown' })).toEqual(initialState);
  });

  it('should handle setSelectedItem', () => {
    const next = reducer(initialState, setSelectedItem(mockItem));
    expect(next.selectedItem).toEqual(mockItem);
  });
});
```

### Custom Hooks

Use `renderHook` from React Testing Library:

```ts
import { renderHook, act } from '@testing-library/react';
import { useFileType } from './useFileType';

describe('useFileType', () => {
  it('should return "pdf" for a .pdf filename', () => {
    const { result } = renderHook(() => useFileType('report.pdf'));
    expect(result.current).toBe('pdf');
  });
});
```

### User Interactions

Use `userEvent` (not `fireEvent`) for realistic interactions:

```ts
import userEvent from '@testing-library/user-event';

it('should call onSubmit when the button is clicked', async () => {
  const user = userEvent.setup();
  const handleSubmit = jest.fn();

  renderWithProviders(<MyForm onSubmit={handleSubmit} />);
  await user.click(screen.getByRole('button', { name: /submit/i }));

  expect(handleSubmit).toHaveBeenCalledTimes(1);
});
```

### Async Components (API calls)

```ts
import { waitFor } from '@testing-library/react';
import * as httpUtility from '../../Services/httpUtility';

jest.mock('../../Services/httpUtility');
const mockGet = httpUtility.getRequest as jest.MockedFunction<typeof httpUtility.getRequest>;

it('should display items after loading', async () => {
  mockGet.mockResolvedValueOnce({ data: [{ id: '1', name: 'Item 1' }] });

  renderWithProviders(<ItemList />);

  await waitFor(() => {
    expect(screen.getByText('Item 1')).toBeInTheDocument();
  });
});
```

---

## 10. Coverage Configuration

CRA handles Jest configuration internally. To customize coverage, add to `package.json`:

```json
{
  "jest": {
    "collectCoverageFrom": [
      "src/**/*.{ts,tsx}",
      "!src/**/*.test.{ts,tsx}",
      "!src/**/index.tsx",
      "!src/declarations.d.ts",
      "!src/test-utils.tsx",
      "!src/setupTests.ts",
      "!src/msal-auth/msaConfig.ts",
      "!src/msal-auth/msalInstance.tsx"
    ],
    "coverageThresholds": {
      "global": {
        "branches": 60,
        "functions": 60,
        "lines": 70,
        "statements": 70
      }
    }
  }
}
```

Run coverage:
```
pnpm test -- --coverage --watchAll=false
```

---

## 11. Required Dependencies

These packages must be installed as dev dependencies:

```
pnpm add -D @testing-library/react @testing-library/jest-dom @testing-library/user-event @types/jest
```

- `@testing-library/react` — render, screen, waitFor, renderHook
- `@testing-library/jest-dom` — `.toBeInTheDocument()`, `.toHaveClass()`, etc.
- `@testing-library/user-event` — realistic click, type, keyboard interactions
- `@types/jest` — TypeScript types for `describe`, `it`, `expect`, `jest.fn()`

**DO NOT** install `jest` directly — it is bundled via `react-scripts`.
**DO NOT** install `ts-jest` — CRA uses Babel for TypeScript transpilation.
**DO NOT** install `@testing-library/react-hooks` — `renderHook` is included in `@testing-library/react` v14+.

---

## 12. Docker / Git Exclusions

`.gitignore` must exclude test artifacts (NOT the test files themselves):
```
coverage/
*.lcov
```

`.dockerignore` must exclude test files AND artifacts from the build context:
```
src/**/*.test.ts
src/**/*.test.tsx
src/test-utils.tsx
src/setupTests.ts
src/**/__mocks__/
coverage/
```

---

## 13. VS Code Integration

Install the **Jest Runner** extension (`firsttris.vscode-jest-runner`) for:
- CodeLens "Run | Debug" links above every `describe` and `it` block
- Test Explorer sidebar with pass/fail tree view
- One-click test execution from the editor gutter

CRA's `testMatch` patterns ensure automatic discovery — no extra configuration needed.

---

## 14. Workflow Checklist

Follow this order:

□ **Phase 1 — Setup**
  1. Install dev dependencies: `pnpm add -D @testing-library/react @testing-library/jest-dom @testing-library/user-event @types/jest`
  2. Create `src/setupTests.ts` with `import '@testing-library/jest-dom'`
  3. Create `src/test-utils.tsx` with `renderWithProviders` (see §6)
  4. Verify: `pnpm test -- --watchAll=false` runs and exits cleanly

□ **Phase 2 — Sanitize** (if tests already exist)
  5. List all `*.test.ts` / `*.test.tsx` files
  6. For each: verify imports resolve to existing source modules
  7. Delete orphaned test files (imports reference deleted modules)
  8. Fix stale tests (wrong prop names, changed signatures, renamed state fields)
  9. Add missing copyright headers
  10. Type-check: `pnpm tsc --noEmit`

□ **Phase 3 — Identify gaps**
  11. List all source modules under `src/` (excluding test files, styles, declarations)
  12. List all existing test files
  13. Produce a gap matrix: source module → has test? → coverage gaps

□ **Phase 4 — Write tests**
  14. For each uncovered module, create a co-located `.test.tsx` / `.test.ts` file
  15. Prioritize: Redux slices → utility functions → custom hooks → simple components → complex components
  16. Type-check each new test file immediately after creation

□ **Phase 5 — Validate**
  17. Run full suite: `pnpm test -- --watchAll=false`
  18. Fix any failures
  19. Run with coverage: `pnpm test -- --coverage --watchAll=false`
  20. Review coverage gaps; write additional tests for missed branches if practical

□ **Phase 6 — Project hygiene**
  21. Ensure `src/setupTests.ts` exists and imports `@testing-library/jest-dom`
  22. Ensure `src/test-utils.tsx` wraps all providers (Redux, Fluent, Router)
  23. Ensure `.gitignore` excludes `coverage/`
  24. Ensure `.dockerignore` excludes test files and coverage artifacts
