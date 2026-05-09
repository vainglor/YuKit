# YuKit Login Experience Design

## Goal

Complete the practical login flow for the current YuKit app without adding email magic-link delivery.

The app already has backend sessions, local dev login, GitHub OAuth start/callback, `GET /api/auth/me`, and logout. This work finishes the product experience around those primitives so users get clear login options, loading states, errors, and post-login user data.

## Scope

In scope:

- Add an auth options endpoint so the frontend can know whether dev login and GitHub login are available.
- Keep dev login available only outside production when `YUKIT_DEV_AUTH_ENABLED=true`.
- Keep GitHub OAuth as the real external login provider.
- Show a login dialog instead of making the sign-in button immediately try hidden fallbacks.
- In local development, show a one-click local login action.
- Show GitHub login when configured or as the production/default path.
- Surface GitHub unconfigured and database/session errors in the UI instead of landing on a raw JSON page when possible.
- Keep `GET /api/auth/me` as the source of truth after page load and after OAuth redirects back to the app.
- Logout clears frontend user resources and the session cookie.
- Add tests for auth options and frontend login decision helpers.

Out of scope:

- Email magic-link implementation.
- Password login.
- Account settings/profile editing.
- CSRF token redesign.
- Session revocation table cleanup beyond the existing cookie-based logout behavior.

## UX

The top bar `Sign in` button opens an auth dialog. The dialog shows:

- Current state: anonymous, signing in, signed in, or failed.
- Local dev login button when enabled.
- GitHub login button when configured, or a disabled/unavailable state when not configured.
- A short explanation that email login is reserved for a later release.

Clicking local dev login calls `POST /api/auth/dev-login`, then refreshes account-dependent data: favorites, preferences, and executions.

Clicking GitHub login navigates to `/api/auth/github/start`. After callback, the backend redirects to `public_base_url`; the frontend loads `/api/auth/me` on mount and displays the signed-in user.

## API

Add:

```text
GET /api/auth/options
```

Response:

```json
{
  "dev_login": true,
  "github": true,
  "email": false
}
```

Rules:

- `dev_login` is true when environment is not production and dev auth is enabled.
- `github` is true when `github_client_id` is configured.
- `email` remains false because email magic links are not implemented.

## Errors

Frontend auth errors should be displayed inline in the auth dialog. User input and current tool state should remain intact.

Backend auth errors continue to use the existing error envelope.

## Testing

Backend:

- `GET /api/auth/options` reports local dev login availability in test/local config.
- Production config disables dev login in options.

Frontend:

- Auth option normalization defaults missing values to false.
- Login decision helper prefers dev login when available and GitHub otherwise.
- E2E smoke verifies the sign-in dialog opens and exposes local dev login in the current test preview.
