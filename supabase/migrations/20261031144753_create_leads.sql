-- Sign-ups from /signup. Only the sign-up API (api/signup.py) writes here, with the secret key.
create table public.leads (
  id            text primary key,           -- leadId the API returns
  submitted_at  timestamptz not null default now(),
  first_name    text not null,
  last_name     text not null,
  email         text not null,
  phone         text not null,              -- E.164, e.g. +4915123456789
  country       text,                       -- ISO code picked in the form
  locale        text,
  timezone      text,
  tos           jsonb not null,             -- {accepted, version, text}: the exact wording agreed to
  call_consent  jsonb not null,             -- {given, version, text}: may Kai call them?
  data_notice   text,
  user_agent    text,
  ip            jsonb                       -- IP check: category, company, isp, country, reasons
);

-- Leads hold names, emails and phone numbers. With RLS on and no policies, the public
-- (anon / publishable) key can neither read nor write them; only the secret key can.
alter table public.leads enable row level security;
