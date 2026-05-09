# Login Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the current YuKit login experience with explicit auth options, a frontend login dialog, local dev login, GitHub OAuth navigation, and clear auth feedback.

**Architecture:** Backend adds a small `GET /api/auth/options` endpoint derived from existing settings. Frontend keeps `App.vue` as the current workspace owner, adds a focused auth dialog, and moves auth option decision logic into a small tested helper module. Existing session cookie, `/auth/me`, dev login, GitHub OAuth, and logout contracts remain unchanged.

**Tech Stack:** FastAPI, SQLAlchemy test fixtures, Vue 3, TypeScript, Vitest, Playwright.

---

## File Structure

- Modify `backend/app/api/auth.py`: add `AuthOptionsResponse`, `auth_options()`, and route `GET /auth/options`.
- Modify `backend/tests/api/test_auth_and_me.py`: add auth options tests.
- Create `frontend/src/authFlow.ts`: pure helpers for auth option normalization and preferred login method.
- Create `frontend/src/authFlow.test.ts`: Vitest tests for auth helpers.
- Modify `frontend/src/api/platform.ts`: add `AuthOptions` type and `fetchAuthOptions()`.
- Modify `frontend/src/App.vue`: add auth dialog, auth error state, explicit local/GitHub login handlers, and resource refresh.
- Modify `frontend/src/i18n.ts`: auth dialog labels and error text.
- Modify `frontend/src/styles.css`: auth dialog layout.
- Modify `frontend/e2e/smoke.e2e.ts`: sign-in dialog smoke coverage.

## Task 1: Backend Auth Options

**Files:**
- Modify: `backend/tests/api/test_auth_and_me.py`
- Modify: `backend/app/api/auth.py`

- [ ] **Step 1: Write failing tests**

Add tests that call `GET /api/auth/options`.

Expected in the existing test fixture:

```python
assert response.json() == {"dev_login": True, "github": False, "email": False}
```

Add a second test using `monkeypatch` and `get_settings.cache_clear()` to set:

```text
YUKIT_ENVIRONMENT=production
YUKIT_DEV_AUTH_ENABLED=true
YUKIT_GITHUB_CLIENT_ID=client-id
```

Expected:

```python
assert response.json() == {"dev_login": False, "github": True, "email": False}
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
cd backend
python -m pytest tests/api/test_auth_and_me.py -q
```

Expected: auth options tests fail with 404.

- [ ] **Step 3: Implement endpoint**

In `backend/app/api/auth.py`, add:

```python
class AuthOptionsResponse(BaseModel):
    dev_login: bool
    github: bool
    email: bool


@router.get("/options")
async def auth_options() -> AuthOptionsResponse:
    settings = get_settings()
    return AuthOptionsResponse(
        dev_login=settings.environment != "production" and settings.dev_auth_enabled,
        github=bool(settings.github_client_id),
        email=False,
    )
```

- [ ] **Step 4: Run backend auth tests and verify GREEN**

Run:

```powershell
cd backend
python -m pytest tests/api/test_auth_and_me.py -q
```

Expected: PASS.

## Task 2: Frontend Auth Helpers And API Client

**Files:**
- Create: `frontend/src/authFlow.test.ts`
- Create: `frontend/src/authFlow.ts`
- Modify: `frontend/src/api/platform.ts`

- [ ] **Step 1: Write failing helper tests**

Test:

- `normalizeAuthOptions({ dev_login: true })` returns `{ dev_login: true, github: false, email: false }`.
- `preferredLoginMethod({ dev_login: true, github: true, email: false })` returns `"dev"`.
- `preferredLoginMethod({ dev_login: false, github: true, email: false })` returns `"github"`.
- `preferredLoginMethod({ dev_login: false, github: false, email: false })` returns `"none"`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
cd frontend
pnpm test src/authFlow.test.ts
```

Expected: FAIL because `authFlow.ts` does not exist.

- [ ] **Step 3: Implement helper and API function**

Create `authFlow.ts` with `AuthOptions`, `LoginMethod`, `normalizeAuthOptions`, and `preferredLoginMethod`.

In `platform.ts`, export `AuthOptions` and:

```ts
export async function fetchAuthOptions(): Promise<AuthOptions> {
  const body = await request<AuthOptions>('/auth/options')
  return normalizeAuthOptions(body)
}
```

- [ ] **Step 4: Run frontend helper tests and verify GREEN**

Run:

```powershell
cd frontend
pnpm test src/authFlow.test.ts
```

Expected: PASS.

## Task 3: Frontend Login Dialog

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/i18n.ts`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/e2e/smoke.e2e.ts`

- [ ] **Step 1: Add auth dialog state and handlers**

Add `authDialogOpen`, `authOptions`, `authError`, `authLoaded`, and handlers:

- `openAuthDialog()`
- `loadAuthOptions()`
- `signInWithDev()`
- `signInWithGitHub()`

`signInWithDev` calls `devLogin`, then `loadUserResources`.

`signInWithGitHub` sets `window.location.href = apiBaseUrl() + '/auth/github/start'`.

- [ ] **Step 2: Replace hidden fallback sign-in behavior**

Top bar `Sign in` opens the dialog. Favorite and Text Hash auth-required paths open the dialog when anonymous instead of silently attempting login.

- [ ] **Step 3: Render auth dialog**

Dialog shows local dev login if available, GitHub login if available, disabled GitHub unconfigured state otherwise, reserved email text, auth errors, and close button.

- [ ] **Step 4: Add E2E smoke expectation**

Extend Playwright smoke to click `Sign in` and expect the auth dialog plus local login button.

## Task 4: Verification

**Files:** none

- [ ] **Step 1: Run backend auth tests**

```powershell
cd backend
python -m pytest tests/api/test_auth_and_me.py -q
```

- [ ] **Step 2: Run frontend tests and build**

```powershell
cd frontend
pnpm test
pnpm build
```

- [ ] **Step 3: Run E2E smoke**

```powershell
cd frontend
pnpm test:e2e
```

## Self-Review

- Spec coverage: backend auth options, frontend login dialog, dev login, GitHub navigation, auth errors, and smoke coverage are mapped to Tasks 1-4.
- Placeholder scan: no red-flag placeholder implementation gaps remain.
- Type consistency: `AuthOptions`, `LoginMethod`, and route names are consistent across backend and frontend tasks.
