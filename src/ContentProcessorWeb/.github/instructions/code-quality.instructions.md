---
applyTo: '**/*.{ts,tsx,scss,css}'
---
# Systematic Code-Quality Pass Instructions for TypeScript & React Codebase

You are performing a systematic code-quality pass on a TypeScript/React codebase (React 18, Fluent UI v9, Redux Toolkit, MSAL, SCSS, pnpm). Work through every folder one at a time. For each `.ts` / `.tsx` / `.scss` / `.css` file, apply ALL of the following rules, then type-check every edited file before moving to the next folder.

---

## 1. Copyright & File Header

- Every `.ts` and `.tsx` file must start with:
  ```ts
  // Copyright (c) Microsoft Corporation.
  // Licensed under the MIT License.
  ```
- Immediately after, add a JSDoc file-level comment that:
  - Describes what the module/component does in 1–2 sentences.
  - Mentions its role in the broader application (e.g., "Renders the left navigation panel for content processing queue").
  - Does NOT contain generic filler like "This file contains a component."

---

## 2. Component Structure & Naming

- **One exported component per `.tsx` file.** Co-located helpers and sub-components are fine if they are small and not reused elsewhere.
- Use `React.FC<Props>` with an explicitly named props interface (e.g., `HeaderPageProps`). Avoid inline anonymous prop types.
- Component file name must match the default/named export (e.g., `Header.tsx` → `export default HeaderPage` or `export const Header`).
- Keep component files focused: if a component exceeds ~250 lines, extract child components or custom hooks.

---

## 3. TypeScript Typing Rules

- **No `any`** — replace with proper types, generics, or `unknown` + type guards.
  - For Redux thunk payloads, define explicit request/response interfaces instead of `createAsyncThunk<any, ...>`.
  - For API responses, create shared response type interfaces in `Services/` or a `types/` folder.
- **Prefer `interface` over `type`** for object shapes; use `type` for unions, intersections, and mapped types.
- **All function parameters and return types must be explicitly typed** for exported functions, hooks, and utility functions. Inferred return types are acceptable only for simple component render functions and inline callbacks.
- **Avoid type assertions (`as`)** unless narrowing from `unknown`; prefer type guards instead.
- **Use `readonly` on props interfaces and state shapes** where the data should not be mutated.
- **Enum alternatives**: prefer `as const` objects or union string literal types over TypeScript `enum`.

---

## 4. Props & Interface Definitions

- Props interfaces live in:
  - The same `.tsx` file if used only by that component, OR
  - A sibling `*Types.ts` file (e.g., `DialogComponentTypes.ts`) if shared across multiple files.
- Every prop must have a JSDoc comment:
  ```ts
  interface HeaderPageProps {
    /** Callback to toggle between light and dark themes. */
    toggleTheme: () => void;
    /** Whether the UI is currently in dark mode. */
    isDarkMode: boolean;
  }
  ```
- Use discriminated unions for variant props rather than optional booleans:
  ```ts
  // Prefer this:
  type PanelMode = { mode: 'view' } | { mode: 'edit'; onSave: () => void };
  // Over this:
  interface PanelProps { isEditing?: boolean; onSave?: () => void; }
  ```

---

## 5. React Hooks & Patterns

- **Custom hooks** must be in the `Hooks/` folder, prefixed with `use`, and have a JSDoc block explaining purpose, parameters, and return value.
- **Dependency arrays** — every `useEffect`, `useMemo`, and `useCallback` must have an exhaustive dependency array. Suppress the ESLint rule only with an adjacent `// eslint-disable-next-line react-hooks/exhaustive-deps` AND a comment explaining why.
- **Avoid `useEffect` for derived state** — use `useMemo` instead.
- **Event handlers** — name them `handle<Event>` (e.g., `handleClick`, `handleFileUpload`). Pass them as `on<Event>` props (e.g., `onClick`, `onFileUpload`).
- **Avoid anonymous functions in JSX** that are recreated on every render for non-trivial logic; wrap with `useCallback`.

---

## 6. Redux Toolkit & State Management

- **Slice files** live in `store/slices/`. Each slice file must:
  - Define and export its state interface (e.g., `CenterPanelState`).
  - Type the `initialState` with that interface.
  - Export typed selectors (e.g., `selectContentData`) rather than relying on inline `useSelector` lambdas everywhere.
- **Async thunks** (`createAsyncThunk`):
  - Must define explicit generic types: `createAsyncThunk<ResponseType, ArgType>()`.
  - Error handling must use `rejectWithValue` with a typed error payload, not bare strings.
- **Use `shallowEqual`** with `useSelector` when selecting object/array slices to avoid unnecessary re-renders (already done in parts of the codebase — enforce everywhere).
- **Selectors** — prefer `createSelector` from `@reduxjs/toolkit` for derived/computed data.

---

## 7. Styling Rules (SCSS / CSS)

- Use SCSS module files (`.styles.scss`) co-located with their component.
- Prefer Fluent UI v9 tokens (`tokens.colorBrandBackground`, `tokens.spacingHorizontalM`, etc.) over hardcoded colors and spacing.
- No inline `style={}` props unless values are truly dynamic and cannot be expressed via class toggling.
- Class names: use camelCase in SCSS modules or BEM (`.block__element--modifier`) in global CSS. Be consistent within each file.

---

## 8. Import Hygiene

- **Group imports** in this order, separated by blank lines:
  1. React / React DOM
  2. Third-party libraries (`@fluentui/*`, `react-redux`, `axios`, `react-router-dom`, etc.)
  3. Internal modules — hooks, services, store, types
  4. Sibling / relative components
  5. Style imports (`.scss`, `.css`)
- **No unused imports** — delete them.
- **No commented-out imports** — delete them.
- **Prefer named imports** over wildcard (`import * as React`) unless required for JSX transform compatibility.
- **Do not include file extensions in imports** (e.g., use `./Header/Header` not `./Header/Header.tsx`) unless the project explicitly requires it in `tsconfig.json`.

---

## 9. JSDoc & Comment Standards

### Component JSDoc
```tsx
/**
 * Displays the application header with navigation tabs, theme toggle, and user menu.
 *
 * Used at the top of every page via the Router layout in App.tsx.
 */
const HeaderPage: React.FC<HeaderPageProps> = ({ toggleTheme, isDarkMode }) => { ... };
```

### Hook JSDoc
```ts
/**
 * Determines the MIME type of a file based on its extension or browser-reported type.
 *
 * @param file - The file object with at least a `name` property.
 * @returns The resolved MIME type string (e.g., `"application/pdf"`).
 */
const useFileType = (file: FileWithExtension | null) => { ... };
```

### Utility / Service Function JSDoc
```ts
/**
 * Wraps an async API call for use inside a Redux `createAsyncThunk`.
 *
 * Returns the response data on 200/202, or calls `rejectWithValue` with
 * a descriptive error message on failure.
 *
 * @param apiCall - The promise returned by `httpUtility.get/post/put/delete`.
 * @param rejectWithValue - The thunk's `rejectWithValue` callback.
 * @param errorMessage - A human-readable fallback error message.
 * @param endpoint - Optional API path for logging.
 * @returns The unwrapped response data of type `T`.
 */
export const handleApiThunk = async <T>( ... ): Promise<T> => { ... };
```

---

## 10. Comment Cleanup — REMOVE These

- **Redundant inline comments** that restate the code:
  `// Import Header` next to `import Header from "./Header/Header"`.
- **Banner / section-divider comments**:
  `// ===================== ACTIONS =====================`
- **Commented-out code** (old imports, dead JSX, unused handlers).
- **Heritage/provenance comments** referencing deleted files:
  `// Replaces the old AuthService.ts`
- **Placeholder comments** with no implementation plan:
  `// Add more` or `// Placeholder for future feature`
- **"For demonstration" / "Here you would typically"** comments.
- **Trailing inline comments that just name the import**:
  `import { Foo } from "./Foo"; // Import Foo`

---

## 11. Comment Cleanup — KEEP These

- **Actionable TODOs** with clear intent: `// TODO: Replace hardcoded routes with a config map`
- **Non-obvious "why" comments** explaining a design decision:
  `// shallowEqual prevents re-render when unrelated store slices change.`
- **Contract/protocol comments** documenting API or external behavior:
  `// The backend returns 202 for async processing jobs.`

---

## 12. Fix Stale References

- Search for outdated terminology (old project names, old component names, old route paths) and correct them to match the current code.
- Ensure all route values in `tabConfigs` / `tabRoutes` match routes defined in `App.tsx`.

---

## 13. Remove Dead Code

- Delete unused imports (React auto-import of `React` is still needed if `import * as React` is used with JSX transform).
- Delete unused local variables, interfaces, and type aliases.
- Delete empty or no-op `useEffect` blocks.
- Delete unreachable code after early returns.
- Delete duplicate type definitions across files — consolidate into a shared types file.

---

## 14. Accessibility (a11y)

- Every interactive element must be keyboard-accessible (Fluent UI handles most of this — ensure custom components follow suit).
- Images and icons must have `aria-label` or `alt` text.
- Use semantic HTML (`<main>`, `<nav>`, `<section>`, `<header>`) rather than generic `<div>` where appropriate.

---

## 15. Error Handling

- All `createAsyncThunk` actions must handle both `fulfilled` and `rejected` cases in `extraReducers`.
- API errors should surface user-friendly messages via `react-toastify`; raw error objects must never reach the UI.
- Use `ErrorBoundary` components to catch and gracefully handle rendering errors.

---

## 16. Type-Check & Lint

- After finishing each folder, run:
  ```bash
  pnpm exec tsc --noEmit
  ```
  on the project to verify zero type errors.
- Run:
  ```bash
  pnpm exec eslint src/<folder>
  ```
  on edited files and fix all warnings/errors before proceeding.

---

## Working Process

1. List the directory tree of the target folder.
2. Read all `.ts`, `.tsx`, `.scss`, and `.css` files in the folder.
3. Create a TODO list for the folder (one item per file + one for type-check/lint).
4. Edit files, marking each TODO as you go.
5. Run `pnpm exec tsc --noEmit` and `pnpm exec eslint` on all edited files.
6. Fix any errors before moving to the next folder.

Start with the folder I specify and work through it completely before asking what to do next.
