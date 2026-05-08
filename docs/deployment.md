# YuKit Deployment Notes

This is the runnable YuKit V1 platform slice. PostgreSQL stores users, sessions, favorites, preferences, and execution history. Redis backs rate limiting and the ARQ worker queue. The first concrete tools are JSON Format, Timestamp, and Base64.

## Local App

```powershell
cd frontend
pnpm install
pnpm build
cd ..
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8080`.

For GitHub OAuth, set `YUKIT_GITHUB_CLIENT_ID`, `YUKIT_GITHUB_CLIENT_SECRET`, `YUKIT_PUBLIC_BASE_URL`, and `YUKIT_API_BASE_URL` in `.env`. Local development can use `YUKIT_DEV_AUTH_ENABLED=true` for the built-in dev login route.

## Development Servers

Run the API:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Run the frontend:

```powershell
cd frontend
pnpm dev
```

Open `http://localhost:5173`.
