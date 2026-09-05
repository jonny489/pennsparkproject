-- Shelf schema for Supabase Postgres.
-- Apply in the Supabase SQL editor, or via `psql "$DATABASE_URL" -f schema.sql`.
-- Written to be re-runnable so it can be applied repeatedly during development.

-- All three media types share the same fields, so a single table keeps the
-- schema simple. Per-type fields (page count, runtime, platform) were
-- deliberately left out to hold scope.

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

create table if not exists items (
  id uuid primary key default gen_random_uuid(),

  -- Cascade so deleting an account removes its collection rather than
  -- orphaning rows that no one can reach.
  user_id uuid not null references auth.users (id) on delete cascade,

  -- Reject whitespace-only input at the database level, not just in the API,
  -- so a stray client cannot create unreadable rows.
  title text not null check (length(trim(title)) > 0),
  creator text not null check (length(trim(creator)) > 0),

  media_type media_type not null,
  status item_status not null default 'planned',

  rating smallint check (rating between 1 and 5),

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  -- A rating only means something once the item is finished. Enforced here as
  -- well as in the API so the invariant survives any future writer.
  constraint rating_requires_completed
    check (rating is null or status = 'completed')
);

-- The collection list is always "this user's items, newest first", so index
-- exactly that access pattern.
create index if not exists items_user_id_created_at_idx
  on items (user_id, created_at desc);

-- Keep updated_at honest without trusting callers to send it.
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

-- Row-level security.
--
-- NOTE: the FastAPI service connects with a privileged role, which BYPASSES
-- these policies. Ownership is enforced in the backend by scoping every query
-- to user_id. These policies are defence-in-depth: they protect the table if it
-- is ever reached through Supabase's Data API or an anon/authenticated client.
alter table items enable row level security;

drop policy if exists items_select_own on items;
create policy items_select_own on items
  for select using (auth.uid() = user_id);

drop policy if exists items_insert_own on items;
create policy items_insert_own on items
  for insert with check (auth.uid() = user_id);

drop policy if exists items_update_own on items;
create policy items_update_own on items
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists items_delete_own on items;
create policy items_delete_own on items
  for delete using (auth.uid() = user_id);
