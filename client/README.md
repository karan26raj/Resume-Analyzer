# ResumeIQ — Frontend

React (JavaScript) + Vite client for the AI Resume Analyzer FastAPI backend in `../server`.

## Run it

1. Start the backend (from `server/`): `uvicorn app.main:app --reload` — it must be on port 8000, with PostgreSQL and Qdrant running.
2. Start the frontend (from `client/`):

```powershell
npm install
npm run dev
```

3. Open http://localhost:5173 and create an account.

In development, every request to `/api/*` is proxied by Vite to `http://127.0.0.1:8000`, so the backend needs no CORS configuration.

## Configuration (optional)

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Where the dev proxy forwards `/api` requests |
| `VITE_API_BASE_URL` | `/api` | API base URL baked into a production build. If it points to another origin, add that origin to the backend's `CORS_ORIGINS`. |

Put overrides in `client/.env.local` (git-ignored).

## Production build

```powershell
npm run build   # outputs dist/
npm run preview
```

## Pages

| Page | API endpoints used |
|---|---|
| Sign in / Register | `POST /auth/login`, `POST /auth/register`, `GET /auth/me` |
| Dashboard | `GET /resumes/`, `GET /jobs`, `GET /analysis`, `GET /recommendations` |
| Resumes | `POST /resumes/upload`, `GET /resumes/`, `GET /resumes/{id}/text`, `DELETE /resumes/{id}`, `POST /embeddings/index` |
| Jobs | `POST /jobs`, `GET /jobs`, `DELETE /jobs/{id}`, `POST /embeddings/index` |
| Analysis | `POST /analysis/match`, `GET /analysis` |
| Semantic Search | `POST /embeddings/search` |
| AI Assistant | `POST /assistant/ask` |
| Settings | `GET /auth/me`, `GET /health` |

## Data honesty

Everything shown comes from API responses — there is no mock data. Two dashboard figures have no API behind them yet:

- **Indexed documents** — shown as "Not reported by the API yet".
- **AI assistant usage** — counts answers received in this browser. The API does not store chat history, so the conversation is kept in `localStorage` per user.

## Structure

```
src/
  api/          fetch wrapper (auth header, errors, upload progress) + one function per endpoint
  auth/         AuthContext (JWT session, auto sign-out on expiry/401) + ProtectedRoute
  components/
    layout/     sidebar, top bar, app shell
    ui/         fields, modal, toasts, score ring, states (loading/empty/error), markdown
    charts/     score-by-analysis column chart, skill-gap bar list
  hooks/        useApi (loading/error/data), useElementWidth
  pages/        one file per route
  styles/       tokens, base, layout, components, pages
  utils/        date/number formatting, JWT expiry, local chat history
```
