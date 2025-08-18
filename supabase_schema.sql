-- Supabase schema for consulting AI app

create table if not exists public.profiles (
  id uuid primary key,
  email text unique,
  created_at timestamptz default now(),
  stripe_customer_id text,
  pro boolean default false,
  pro_until timestamptz
);

create table if not exists public.plans (
  id bigserial primary key,
  user_id uuid references public.profiles(id) on delete cascade,
  created_at timestamptz default now(),
  form jsonb,
  plan_md text
);

-- RLS
alter table public.profiles enable row level security;
alter table public.plans enable row level security;

do $$ begin
  create policy if not exists "profiles self access"
  on public.profiles
  for select using (auth.uid() = id)
  with check (auth.uid() = id);
exception when others then null; end $$;

do $$ begin
  create policy if not exists "plans self access"
  on public.plans
  for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
exception when others then null; end $$;
