# Shelf

A personal media library for tracking books, movies, and games — what you plan to
start, what you're partway through, and what you've finished and rated.

Built for the Penn Spark Fall 2026 Red Developer technical assessment.

> **Before submitting, fill in the two placeholders below:** the live link and the
> actual time spent. Both are required by the assessment, and neither should be
> guessed.

- **Live demo:** _TODO — not yet deployed_
- **Time spent:** _TODO_

## Features

- Add, edit, and delete entries across three media types in one collection
- Track each entry as planned, in progress, or completed
- Rate completed entries 1–5 stars — the rating is rejected anywhere else, in the
  API and in the database, not just hidden in the UI
- Search by title and filter by media type and status
- Passwordless magic-link sign-in; each account sees only its own collection
- Responsive grid layout with loading, empty, and error states

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript strict, Tailwind, shadcn/ui |
| Backend | FastAPI, Pydantic v2, asyncpg |
| Database | Supabase Postgres |
| Auth | Supabase Auth (magic link), ES256 JWT verified by the API against the project JWKS |

## How it fits together

```
Browser ──► Next.js ──► FastAPI ──► Supabase Postgres
   └── Supabase Auth issues a JWT; FastAPI verifies it and reads the user id
```

Supabase signs access tokens with ES256 asymmetric keys, so the API verifies
signatures against the project's public JWKS endpoint and holds no shared secret
at all. The expected issuer is derived from the configured `SUPABASE_URL` rather
than read from the token, so a token minted by another project is rejected.

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
cp .env.example .env          # fill in DATABASE_URL and SUPABASE_URL
uvicorn app.main:app --reload
```

Interactive docs at http://127.0.0.1:8000/docs.

### 3. Frontend

```bash
cd shelf
npm install
cp .env.example .env.local    # fill in the Supabase URL, anon key, and API URL
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

All routes except `/health` require `Authorization: Bearer <supabase access token>`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Unauthenticated health check |
| `GET` | `/items` | List, with `search`, `media_type`, `status` filters |
| `POST` | `/items` | Create |
| `GET` | `/items/{id}` | Fetch one |
| `PATCH` | `/items/{id}` | Partial update |
| `DELETE` | `/items/{id}` | Delete |

A missing item and another user's item both return `404` — a `403` would confirm
that the id exists.

## Notes

Secrets live in `.env` / `.env.local`, both gitignored. Only the Supabase anon key
reaches the browser; the service-role key is never used by this project.
