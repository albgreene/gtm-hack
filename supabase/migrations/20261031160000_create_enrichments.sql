-- Enrichment of each sign-up (enrichment/ and api/enrich.py). One row per lead.
create table public.enrichments (
  lead_id          text primary key references public.leads (id) on delete cascade,
  status           text not null,               -- running | sent | failed | skipped
  attempts         integer not null default 1,
  started_at       timestamptz not null default now(),
  finished_at      timestamptz,
  raw              jsonb,                       -- every source's trimmed result, for debugging
  payload          jsonb,                       -- exactly what was sent to Hermes
  hermes_status    integer,
  hermes_response  jsonb,
  error            text
);

-- Same as leads: RLS on, no policies, so only the secret key can read or write.
alter table public.enrichments enable row level security;

-- Every new sign-up starts its enrichment: pg_net POSTs {lead_id} to /api/enrich.
-- The URL and the shared secret live in Supabase Vault (enrich_webhook_url, enrich_webhook_secret),
-- never in the repo. pg_net runs the request in the background, so the sign-up insert isn't held up;
-- the long timeout keeps the connection open while enrichment runs (it takes one to three minutes).
create extension if not exists pg_net;

create or replace function public.enqueue_enrichment()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  hook_url    text;
  hook_secret text;
begin
  select decrypted_secret into hook_url from vault.decrypted_secrets where name = 'enrich_webhook_url';
  select decrypted_secret into hook_secret from vault.decrypted_secrets where name = 'enrich_webhook_secret';
  if hook_url is null or hook_secret is null then
    return new;  -- not configured yet: sign-ups still save
  end if;
  perform net.http_post(
    url := hook_url,
    body := jsonb_build_object('lead_id', new.id),
    headers := jsonb_build_object('Content-Type', 'application/json', 'Authorization', 'Bearer ' || hook_secret),
    timeout_milliseconds := 300000
  );
  return new;
end;
$$;

create trigger leads_enqueue_enrichment
  after insert on public.leads
  for each row execute function public.enqueue_enrichment();
