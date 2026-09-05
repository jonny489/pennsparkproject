-- Shelf schema for Supabase Postgres.
-- Apply in the Supabase SQL editor, or via `psql "$DATABASE_URL" -f schema.sql`.
-- Re-runnable, so it can be applied repeatedly during development.

-- Case-insensitive email uniqueness. Available on Supabase, not enabled by default.
create extension if not exists citext;

do $$
begin
  if not exists (select 1 from pg_type where typname = 'media_type') then
    create type media_type as enum ('book', 'movie', 'game');
  end if;
  if not exists (select 1 from pg_type where typname = 'item_status') then
    create type item_status as enum ('planned', 'in_progress', 'completed');
  end if;
end
$$;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email citext not null unique,

  -- Null for a Google-only account.
  password_hash text,
  -- Google's stable subject id. Null for a password-only account.
  google_sub text unique,

  created_at timestamptz not null default now(),

  -- An account with neither credential could never be signed into.
  constraint has_a_login_method
    check (password_hash is not null or google_sub is not null)
);

-- All three media types share the same fields, so one table covers them.
create table if not exists items (
  id uuid primary key default gen_random_uuid(),

  -- Cascade so deleting an account removes its collection.
  user_id uuid not null references users (id) on delete cascade,

  -- Reject whitespace-only input in the database, not just the API.
  title text not null check (length(trim(title)) > 0),
  creator text not null check (length(trim(creator)) > 0),

  media_type media_type not null,
  status item_status not null default 'planned',
  rating smallint check (rating between 1 and 5),

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  -- A rating only means something once the item is finished.
  constraint rating_requires_completed
    check (rating is null or status = 'completed')
);

-- The collection list is always "this user's items, newest first".
create index if not exists items_user_id_created_at_idx
  on items (user_id, created_at desc);

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists items_set_updated_at on items;
create trigger items_set_updated_at
  before update on items
  for each row
  execute function set_updated_at();

-- RLS stays ON with NO policies, which denies Supabase's anon and authenticated
-- roles outright while the backend's privileged role is unaffected. Ownership
-- itself is enforced by the API scoping every query to user_id.
alter table users enable row level security;
alter table items enable row level security;
