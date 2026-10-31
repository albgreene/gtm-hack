# Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every new Supabase `leads` row is enriched (HubSpot, website, vendor search, AI Ark, Needle), turned into the Hermes input contract by one LLM call, quote-checked, and POSTed signed to Hermes, with status in a Supabase `enrichments` table.

**Architecture:** A Python package `enrichment/` holds one module per source, a vendor matcher, the LLM extraction, the quote check, the Hermes handoff and the Supabase store. `api/enrich.py` is a Vercel Python function (Flask, like `api/signup.py`) that runs `pipeline.enrich_lead(lead_id)`. A pg_net trigger on `leads` calls it.

**Tech Stack:** Python 3.12, Flask, `anthropic` SDK (OpenRouter base_url), urllib for every other HTTP call, pytest, Supabase (PostgREST + pg_net), Vercel.

**Spec:** `docs/superpowers/specs/2026-10-31-enrichment-design.md`

## Global Constraints

- Every fact in the payload carries a source URL or `hubspot:<TYPE> <id>` and a word-for-word quote; unknown = `null`.
- Payload body ≤ 65536 bytes; header `X-Hub-Signature-256: sha256=<hmac>` and `X-Request-ID: <lead_id>`.
- Needle connected account `01a181fb-417f-7f18-a037-e554eec499fd`; only these Needle tools may be called: `needleGetLinkedinProfile`, `needleSearchLinkedinPeopleClassic`, `needleGetLinkedinCompany`, `needleListLinkedinCompanyPosts`, `needleListLinkedinCompanyJobs`, `needleGetLinkedinJob`.
- HubSpot is read-only: only `GET` and `POST .../search` / `.../batch/read`.
- LLM: model `anthropic/claude-opus-5.5` through `https://openrouter.ai/api` with `OPENROUTER_API_KEY`, effort set explicitly, structured output with the Hermes worker's fallback (plain-prompt JSON if the proxy rejects `output_config`).
- No call consent → `lead.phone = null`, `lead.call_consent = false`.
- HubSpot error (not empty) after 2 retries → lead not sent, status `failed`.
- Hard cap about 3 minutes per lead; at most 2 leads at once.
- Secrets only from env vars; none printed, none in the repo.
- Free-mail list = Hermes `FREE_MAIL`.

## Review Focus

- A free-mail sign-up AI Ark doesn't know → `domain: null`, no website or HubSpot company lookups, still sent (Hermes answers `unknown`).
- A company website that blocks or times out → website `error` in `sources_tried`, the rest still runs.
- A LinkedIn search hit for the same name at another company (Alberto at KugelAudio vs a sign-up from telli.com) → not attached, "profile found, different company" noted. Test in Task 2.
- The LLM quotes text that isn't in the cited source → that entry is dropped. Test in Task 4.
- The same lead triggered twice (webhook retry) → second run sees status `running`/`sent` and stops. Test in Task 5.

---

### Task 1: Shared plumbing and the store

**Files:**
- Create: `enrichment/__init__.py`, `enrichment/config.py`, `enrichment/net.py`, `enrichment/store.py`
- Create: `supabase/migrations/20261031160000_create_enrichments.sql`
- Test: `tests/test_net.py`

**Interfaces:**
- Produces: `config` constants (`FREE_MAIL: set[str]`, `NEEDLE_ACCOUNT`, `NEEDLE_READ_TOOLS: set[str]`, `HERMES_URL`, `env(name) -> str`); `net.get_json(url, headers=None, timeout=20) -> dict|list`, `net.post_json(url, body, headers=None, timeout=30) -> dict|list`, `net.get_text(url, timeout=15) -> tuple[str, str]` (final URL, body), `net.mcp_call(url, headers, tool, arguments, timeout=60) -> dict` (JSON-RPC `tools/call`, accepts JSON or SSE replies, returns the parsed JSON of the first text content block, raises `RuntimeError` on `isError`); `store.get_lead(lead_id) -> dict|None`, `store.claim(lead_id) -> bool` (inserts `enrichments` row with status `running`; returns False if a row is already `running` or `sent`), `store.finish(lead_id, **fields) -> None`.
- `Doc` = `dict(url=str, kind=str, title=str, text=str)` — every source returns documents in this shape. `SourceResult` = `dict(source=str, result="ok"|"empty"|"error"|"skipped", note=str, docs=list[Doc], data=dict)`.

- [ ] Write `tests/test_net.py::test_parse_sse_reply` (an SSE body with two `data:` lines → the last JSON-RPC result) and `test_mcp_error_raises` (result with `isError: true` → `RuntimeError`).
- [ ] Implement `net.py`; parse helpers are pure functions (`parse_rpc_body(content_type, raw) -> dict`) so tests need no network.
- [ ] Migration: `enrichments` table per spec (`lead_id text primary key references leads(id)`, `status`, `attempts int default 1`, `started_at`, `finished_at`, `raw jsonb`, `payload jsonb`, `hermes_status int`, `hermes_response jsonb`, `error text`), RLS on, no policies. Trigger function `enqueue_enrichment()` on `leads` AFTER INSERT calls `net.http_post(url, body jsonb {lead_id}, headers {Authorization: Bearer <vault secret enrich_webhook_secret>}, timeout_milliseconds := 300000)`; URL from vault secret `enrich_webhook_url`. `create extension if not exists pg_net`.
- [ ] Run `pytest tests/test_net.py -v` → PASS. Commit.

### Task 2: Sources

**Files:**
- Create: `enrichment/sources/__init__.py`, `hubspot.py`, `website.py`, `vendor_search.py`, `aiark.py`, `needle.py`, `enrichment/matching.py`
- Test: `tests/test_matching.py`, `tests/test_website.py`, `tests/test_hubspot.py`

**Interfaces:**
- Consumes: Task 1 `net`, `config`, `Doc`, `SourceResult`.
- Produces:
  - `matching.is_free_mail(domain) -> bool`; `matching.company_matches(text: str, domain: str|None, names: list[str]) -> bool` (true if the domain's first label or any normalised name — lowercase, legal suffixes like GmbH/AG/Inc/(YC …) stripped — appears in `text`).
  - `hubspot.lookup(domain, email) -> SourceResult`; `data` = `{"crm": {...contract crm block, plus "lifecycle_stage": label|None, "do_not_contact": bool}}`. Rules: customer = lifecycle `customer` or a deal in stage `closedwon`/`5818079442`/`6157013239`/`6163434745`; investor = lifecycle `6144324828` or any Fundraising-pipeline (`4055645375`) deal not `5898277081`; `open_deal_owner` = owner name of any deal whose stage is open; `do_not_contact` = lifecycle `6157284596` ("Kein Vertriebskontakt"). Notes/calls/meetings on the company (latest 8, ≤1500 chars each) become docs with url `hubspot:NOTE <id>` etc. Raises `HubSpotError` on HTTP errors after 2 retries.
  - `website.scrape(domain) -> SourceResult`: homepage + up to 6 priority pages + up to 3 voice-word deep links (spec order). Each page doc's text includes visible text, then a line per image `[image] alt=… src=…` and per script `[script] src=…`. Firecrawl `/v2/scrape` (formats `markdown`, `links`, `rawHtml`) when `FIRECRAWL_API_KEY` is set; otherwise `net.get_text` + `html.parser`. `data` = `{"links": [...], "site_name": str|None}`.
  - `website.choose_pages(home_url, links) -> list[str]` — pure, tested.
  - `vendor_search.search(company_name, domain) -> SourceResult`: Firecrawl `/v2/search` with vendor `site:` filters; keeps hits whose text names the company; `skipped` without a key.
  - `aiark.person(email, phone) -> SourceResult` (`data.person` = name, title, linkedin, company name/domain, or `{}`); `aiark.company(domain) -> SourceResult` (`data.company` = the `content[0]` record).
  - `needle.person(first, last, company_names, domain, linkedin_url=None) -> SourceResult`; `needle.company(identifier) -> SourceResult` (company page + posts ≤20 + job list + ≤3 full job ads preferring titles with engineer/AI/voice/product/tech).
- [ ] Tests: `test_company_matches_rejects_other_company` (`"Growth @ KugelAudio (YC P26)"`, domain `telli.com`, names `["telli"]` → False; same text with domain `kugelaudio.com` → True); `test_free_mail` (`gmail.com` True, `telli.com` False); `test_choose_pages_priority` (links incl. `/subprocessors`, `/blog`, `/blog/introducing-telli-duo-agents`, `/careers`, `/pricing`, external links → subprocessors first, the duo-agents post included, external dropped, ≤10 total); `test_html_to_doc_keeps_logo_alt` (`<img alt="ElevenLabs logo" src="/l/elevenlabs.svg">` → text contains `ElevenLabs`); `test_crm_rules` (pure `hubspot.crm_flags(lifecycle, deals, owners)` with an open default-pipeline deal → `open_deal_owner` set; lifecycle `6157284596` → `do_not_contact` True).
- [ ] Implement the modules; run `pytest tests -v` → PASS. Commit.

### Task 3: Tech stack matcher

**Files:**
- Create: `enrichment/techstack.py`
- Test: `tests/test_techstack.py`

**Interfaces:**
- Produces: `VENDORS: list[tuple[str, str, list[str]]]` (vendor, layer, regex aliases) seeded from the spec; `find_vendors(docs: list[Doc]) -> list[dict]` → `{vendor, layer, url, snippet}` deduped per (vendor, url), snippet ≤300 chars around the hit.
- [ ] Tests: `test_finds_logo_vendors` (doc text "Model Agnostic ... [image] alt=ElevenLabs src=/elevenlabs.svg ... Cartesia" → ElevenLabs tts and Cartesia tts); `test_google_needs_speech_word` ("Google Analytics" → nothing; "Google Text-to-Speech" → Google TTS); `test_livekit_in_job_ad`.
- [ ] Implement with word-boundary regexes; ambiguous vendors (Google, Azure, Amazon, OpenAI) only match when a speech word is within 40 chars. Run tests → PASS. Commit.

### Task 4: Extraction and quote check

**Files:**
- Create: `enrichment/extract.py`, `enrichment/verify.py`, `enrichment/prompt.md`
- Create: `docs/qualify-lead-contract.md` (copy of `stuttgart/hermes/input-contract.md`)
- Test: `tests/test_verify.py`

**Interfaces:**
- Produces: `extract.extract(lead: dict, sources: list[SourceResult], candidates: list[dict]) -> dict` (company part of the contract: `domain`, `name`, `firmographics`, `voice`, `custom_signals`, `person`; `crm` and `lead` are added by the pipeline); `verify.check_quotes(payload: dict, docs: list[Doc]) -> tuple[dict, int]` (returns the payload with failing entries removed and the count dropped); `verify.fit_size(payload: dict, limit=65536) -> dict`.
- [ ] Tests: `test_drops_invented_quote` (a `voice_ai_mentions` entry whose quote isn't in its URL's doc is removed, a real one stays; count = 1); `test_quote_check_normalises_whitespace_and_case`; `test_stack_entry_needs_quote_in_cited_doc`; `test_fit_size_trims_lists` (a 100 KB payload comes back ≤ 65536 bytes with `lead` intact).
- [ ] Implement `verify.py`. Fields checked: `voice.voice_ai_mentions[].quote` vs `url`, `voice.voice_stack[].quote` vs `evidence_url`, and every `{"value","source","quote"}` evidence object the prompt asks for in firmographics. A doc is found by exact URL, else by URL without query/fragment/trailing slash.
- [ ] Implement `extract.py`: system prompt from `prompt.md` (cached), user content = lead summary + sources as `<doc url=… kind=…>` blocks + candidates; JSON schema for the company part; `output_config={"format": …, "effort": "medium"}`; streaming with `max_tokens=32000`, `.get_final_message()`; check `stop_reason` (`refusal`, `max_tokens` → raise). Fall back to plain prompt JSON on `BadRequestError` like Hermes.
- [ ] Run `pytest tests/test_verify.py -v` → PASS. Commit.

### Task 5: Pipeline, handoff, endpoint

**Files:**
- Create: `enrichment/handoff.py`, `enrichment/pipeline.py`, `api/enrich.py`, `scripts/enrich_lead.py`, `scripts/insert_test_lead.py`
- Modify: `vercel.json` (functions `api/enrich.py` `maxDuration: 300`), `requirements.txt` (`anthropic`), `.gitignore` (`.venv`)
- Test: `tests/test_handoff.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `handoff.sign(body: bytes, secret: str) -> str`; `handoff.send(payload: dict) -> tuple[int, dict]` (retries 429 twice after 10 s); `pipeline.build_lead_block(row: dict, person: dict) -> dict`; `pipeline.enrich_lead(lead_id: str, send: bool = True) -> dict` (claims, gathers in a thread pool, matches, extracts, verifies, sends, stores; returns the stored summary).
- [ ] Tests: `test_signature_matches_send_lead` (same HMAC as `send-lead.py` for a fixed body/secret); `test_no_consent_hides_phone` (`call_consent.given` false → `phone` None, `call_consent` False); `test_consent_keeps_phone`; `test_claim_twice_skips` (with `store.claim` returning False the pipeline returns `{"status": "skipped"}` without calling sources — monkeypatch).
- [ ] Implement. `api/enrich.py`: `POST /api/enrich` with `Authorization: Bearer $ENRICH_WEBHOOK_SECRET`, body `{lead_id}` (or `{record: {id}}` from a Supabase webhook), runs `enrich_lead` and returns its summary; 401 on bad secret; a module-level `threading.BoundedSemaphore(2)`.
- [ ] Run `pytest tests -v` → PASS. Commit.

### Task 6: Live wiring and end-to-end runs

- [ ] Pull keys into `.env.local` (gitignored) and Vercel env without printing: Supabase from Vercel, HubSpot/Needle/OpenRouter from the VPS `.env`, AI Ark token from `~/.claude.json`, `QUALIFY_LEAD_SECRET` from `stuttgart/.context/qualify-lead.secret`, new `ENRICH_WEBHOOK_SECRET`.
- [ ] Apply the migration with the Supabase CLI (project `axvyiuqkuljrcmvrhxlh`), set the two vault secrets.
- [ ] Local run: `scripts/insert_test_lead.py --domain telli.com` then `scripts/enrich_lead.py <id> --no-send` → inspect payload: ≥3 of ElevenLabs/Cartesia/GPT-Live/LiveKit incl. speech-to-speech evidence (Cartesia and the vendor search need Firecrawl; note if skipped), crm shows HubSpot company. Then with send → Hermes `delivered`, result in Slack.
- [ ] Runs for a gmail lead (→ `domain` null) and `alberto@kugelaudio.com`.
- [ ] Push branch, deploy, prove the trigger: insert a test lead, watch `enrichments` go `running` → `sent`.
- [ ] Commit, open PR.
