# Shelf

A personal media library for tracking books, movies, and games — what you plan to
start, what you're partway through, and what you've finished and rated.

**Live demo:** https://pennsparkproject.vercel.app
**API docs:** https://pennsparkproject-production.up.railway.app/docs

## Features

- Add, edit, and delete entries across three media types in one collection
- Track each entry as planned, in progress, or completed
- Rate completed entries 1–5 stars — the rating is rejected anywhere else, in the
  API and in the database, not just hidden in the UI
- Search by title and filter by media type and status
- Email and password accounts plus Google sign-in; each account sees only its own collection
- Responsive grid layout with loading, empty, and error states

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript strict, Tailwind, shadcn/ui |
| Backend | FastAPI, Pydantic v2, asyncpg |
| Database | Supabase Postgres |
| Auth | Email + password (bcrypt) and Google OAuth, with API-issued JWTs |

## How it fits together

```
Browser ──► Next.js ──► FastAPI ──► Supabase Postgres
   └── FastAPI hashes passwords, runs the Google OAuth exchange, and signs the JWT
```

The API owns authentication end to end: bcrypt password hashes stored in its own
`users` table, the Google authorization-code exchange, and HS256 tokens it signs
with `JWT_SECRET`. The browser holds a bearer token in `localStorage`, which is
readable by any XSS on the page — an accepted tradeoff here, since the frontend
and API sit on different origins and a cookie would need `SameSite=None; Secure`.

The API connects to Postgres with a privileged role, which **bypasses row level
security**. Ownership is therefore enforced in the backend: every query is scoped
by `user_id`, and each repository method takes it as the first argument so a call
site cannot omit it. The RLS policies in `api/schema.sql` are defence-in-depth for
any future access through Supabase's own Data API.

## Layout

```
api/     FastAPI service — models, repository, auth, routes, schema.sql, tests
shelf/   Next.js frontend
```

## Running locally

### 1. Database

Create a Supabase project, then run `api/schema.sql` in the SQL editor.

### 2. API

```bash
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in DATABASE_URL, JWT_SECRET and the Google client
uvicorn app.main:app --reload
```

Interactive docs at http://127.0.0.1:8000/docs.

### 3. Frontend

```bash
cd shelf
npm install
cp .env.example .env.local    # set NEXT_PUBLIC_API_URL
npm run dev
```

## Tests

```bash
cd api && .venv/bin/python -m pytest
```

The suite runs against an in-memory repository, so it needs no database. It covers
the CRUD round trip, the rating rule (including the patch case where the request
body is valid but the resulting row would not be), search and filtering, and the
ownership isolation that keeps one account out of another's collection.

## API

All `/items` routes require `Authorization: Bearer <token>` from a sign-in call.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Unauthenticated health check |
| `POST` | `/auth/register` | Create an account |
| `POST` | `/auth/login` | Exchange email and password for a token |
| `GET` | `/auth/me` | The signed-in user |
| `GET` | `/auth/google` | Start Google sign-in |
| `GET` | `/auth/google/callback` | Finish Google sign-in |
| `GET` | `/items` | List, with `search`, `media_type`, `status` filters |
| `POST` | `/items` | Create |
| `GET` | `/items/{id}` | Fetch one |
| `PATCH` | `/items/{id}` | Partial update |
| `DELETE` | `/items/{id}` | Delete |

A missing item and another user's item both return `404` — a `403` would confirm
that the id exists.

## Notes

Secrets live in `.env` / `.env.local`, both gitignored. Nothing secret reaches the
browser: the frontend only needs the API's base URL.

Use the Supabase **connection pooler** host in `DATABASE_URL`. The direct
`db.<ref>.supabase.co` host resolves only to IPv6, which fails from any network
without IPv6 connectivity.
