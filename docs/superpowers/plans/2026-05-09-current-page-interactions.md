# Current Page Interactions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete every currently visible YuKit workspace control with useful click, keyboard, and feedback behavior.

**Architecture:** Keep the current single-page Vue workspace and add small pure interaction helpers for behavior that benefits from unit tests. `App.vue` owns UI state and event wiring; `interactions.ts` owns filter/theme/result serialization helpers. Existing API clients and backend routes remain unchanged.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Vitest, Playwright, Vite.

---

## File Structure

- Create `frontend/src/interactions.ts`: pure helpers for tool filtering, theme cycling, and history result serialization.
- Create `frontend/src/interactions.test.ts`: Vitest coverage for the helper behavior.
- Modify `frontend/src/App.vue`: command menu, help dialog, theme toggle, tag filtering, favorites display, system refresh, copy feedback, history restore, and keyboard shortcuts.
- Modify `frontend/src/i18n.ts`: English and Chinese labels for new visible states.
- Modify `frontend/src/styles.css`: command/help overlays, dark theme variables, filtered sidebar states, feedback text, and responsive polish.
- Modify `frontend/e2e/smoke.e2e.ts`: Playwright coverage for command menu, theme button, and tag filtering.

## Task 1: Interaction Helper Module

**Files:**
- Create: `frontend/src/interactions.test.ts`
- Create: `frontend/src/interactions.ts`

- [ ] **Step 1: Write failing helper tests**

Create tests for:

```ts
filterTools(
  [
    { name: 'json-format', title: 'JSON Format', meta: 'Developer · Format', tags: ['format'] },
    { name: 'base64', title: 'Base64', meta: 'Developer · Codec', tags: ['codec'] }
  ],
  'json',
  'all'
)
```

Expected result: only `json-format`.

Also test:

- `filterTools(..., '', 'codec')` returns only `base64`.
- `nextTheme('light') === 'dark'`, `nextTheme('dark') === 'system'`, `nextTheme('system') === 'light'`.
- `serializeExecutionResult({ digest: 'abc' })` returns pretty JSON.
- `serializeExecutionResult('plain')` returns `plain`.

- [ ] **Step 2: Run helper tests and verify RED**

Run:

```powershell
cd frontend
pnpm test src/interactions.test.ts
```

Expected: FAIL because `frontend/src/interactions.ts` does not exist.

- [ ] **Step 3: Implement minimal helpers**

Create `interactions.ts` with exported `ThemePreference`, `ToolTag`, `filterTools`, `nextTheme`, and `serializeExecutionResult`.

- [ ] **Step 4: Run helper tests and verify GREEN**

Run:

```powershell
cd frontend
pnpm test src/interactions.test.ts
```

Expected: PASS.

## Task 2: Wire Visible Controls In `App.vue`

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/i18n.ts`

- [ ] **Step 1: Add command/search state and keyboard handlers**

Add state for `commandOpen`, `commandQuery`, `commandInput`, `activeTag`, `helpOpen`, `themePreference`, `copyStatus`, and `systemStatus`.

Add handlers:

- `openCommandMenu()`
- `closeOverlays()`
- `executeCommand(id)`
- `cycleTheme()`
- `refreshSystemStatus()`
- `restoreExecution(item)`

- [ ] **Step 2: Render command menu**

The visible search button opens a dialog. The dialog includes a focused input, filtered tool results, and commands for run, copy, theme, help, and system refresh.

- [ ] **Step 3: Render help dialog**

The help icon opens a compact dialog showing current tool description, access badge, execution mode, and input storage policy.

- [ ] **Step 4: Wire tag chips and favorites**

Tag chips update `activeTag`. Tool list uses `filterTools`. Favorites section shows clickable signed-in favorites, empty state, or anonymous sign-in hint.

- [ ] **Step 5: Wire feedback actions**

Copy uses Clipboard API with textarea fallback and visible feedback. System badge refreshes `/api/health`. Recent history buttons restore previous results.

## Task 3: Styling And Theme

**Files:**
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add dark theme variables**

Add `:root[data-theme='dark']` variables for background, surfaces, borders, text, and semantic states.

- [ ] **Step 2: Add overlay styling**

Add styles for command menu, help dialog, backdrop, favorite section, empty hints, feedback text, and active tag state.

- [ ] **Step 3: Check responsive layout**

Ensure overlays fit below 560px width and visible text wraps rather than overlapping.

## Task 4: E2E Smoke Coverage And Verification

**Files:**
- Modify: `frontend/e2e/smoke.e2e.ts`

- [ ] **Step 1: Write failing E2E expectations**

Extend smoke test to verify:

- Search button opens the command menu.
- Theme button changes `document.documentElement.dataset.theme`.
- Codec tag filters the visible list to Base64.

- [ ] **Step 2: Run E2E and verify behavior**

Run:

```powershell
cd frontend
pnpm test:e2e
```

Expected after implementation: PASS.

- [ ] **Step 3: Run final frontend verification**

Run:

```powershell
cd frontend
pnpm test
pnpm build
```

Expected: PASS.

## Self-Review

- Spec coverage: command search, theme, help, tags, favorites, copy feedback, history restore, system refresh, and keyboard close/open are covered by Tasks 1-4.
- Placeholder scan: no red-flag placeholder implementation gaps are left for the executor.
- Type consistency: helper names and state names used in the plan match the intended implementation.
