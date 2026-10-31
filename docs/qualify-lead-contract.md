# Enriched lead: what the qualifying agent needs

The enrichment layer sends one JSON per sign-up to Hermes. The agent scores it against the ICP
(`skills/icp-fit.md`, `skills/disqualifiers.md`) and only leads at **7/10 or more** get a call from Kai.

## How to send it

- `POST https://hermes-agent-h0rd.srv2036292.hstgr.cloud/webhooks/qualify-lead`
- Body: the lead as JSON, `Content-Type: application/json`, **max 64 KB** (a Phase 1 company file is about 15 KB).
- Sign it: `X-Hub-Signature-256: sha256=<hex HMAC-SHA256 of the raw body, keyed with the shared secret>`.
  The secret is shared privately; never put it in a browser or a repo.
- Set `X-Request-ID: <lead.lead_id>`. Hermes drops a repeat of the same id, so retries are safe.
- Hermes answers within a second: `200 {"status": "delivered"}` means the lead is queued (Slack gets a
  "New lead in" note) and is scored in the background, usually in 30–60 seconds.
  `200 {"status": "ignored"}` means the body had no `lead` block or no `domain`/email, so nothing happens.
  `401` means a bad signature, `413` a body over 64 KB, `429` more than 30 requests a minute.
- `hermes/send-lead.py` does all of this for a JSON file.

## Rules for every fact

1. **Every fact needs a source:** a URL or `hubspot:<type> <id>`, plus a short quote. A fact without a source scores 0.
2. **Unknown is `null`.** Never guess. If you must include a guess, label it `"confidence": "guess"`; it earns nothing.
3. **Missing data never disqualifies a lead; it just can't earn points.**
4. **Collect facts, don't judge fit.** The agent does the judging.

## What the score looks for, and where to put it

| What the agent scores (points) | Field | Where to look |
|---|---|---|
| What kind of company: telco / phone system / CPaaS, AI phone-agent builder for one industry, sovereign GPU hoster … (25) | `firmographics.what_they_sell`, `who_they_sell_to`, `business_model` | Home and product pages, LinkedIn "About" |
| Live phone traffic: customers live, call volume, case studies (20) | `voice.call_volume_signal`, `voice.voice_ai_mentions[]` | Customer logos, case studies, press, LinkedIn posts |
| A separate TTS step they could swap out (15), and which TTS vendor they use today (5) | `voice.voice_stack[]`, `layer`: tts / stt / s2s / llm / agent_platform / telephony | **Subprocessor list or DPA page first** (it often names the voice vendors), then docs and integrations pages |
| Language (15) | `firmographics.languages_served[]`, `hq_country` | Website languages, markets served |
| Sovereignty: self-hosting, on-prem, Germany/EU-only hosting (10) | `voice.eu_or_on_prem_requirement` | Privacy and security pages, DPA |
| Regulated customers: healthcare, legal, debt collection, insurance, public sector (5) | `custom_signals.regulated_vertical` | Use-case pages, customer logos |
| Runs its own phone infrastructure: SIP lines, numbers, phone system (5) | `voice.telephony_owned` | Product pages, carrier licence |
| **Skip or park signals:** speech-to-speech only (e.g. OpenAI Realtime), 10+ languages, a consultancy that's only testing, video or audiobook only, building its own TTS | same fields; write down what you find | |
| **Never call:** existing customer, investor, open deal | `crm.*` | HubSpot |

**Not needed:** headcount, founding year, total funding, GTM stack. Only `funding_stage` is read, as a warning flag.

## Two must-haves

- **The sign-up form has to collect a work email.** Without it nobody can tell which company signed up, and the lead comes out `unknown`.
- **Fill in `sources_tried`**, so the agent can tell "we looked and found nothing" from "we didn't look".

## Shape

The Phase 1 company format (`.context/icp/companies/*.json`) plus a `lead` and a `crm` block:

```json
{
  "lead": {
    "lead_id": "su_123", "signed_up_at": "2026-10-31T14:02:00Z",
    "first_name": "", "last_name": "", "role": "",
    "email": "", "phone": "+49…", "country": "DE"
  },
  "domain": "smao.ai",
  "name": "smao GmbH",
  "crm": { "hubspot_company_id": null, "is_customer": false, "is_investor": false, "open_deal_owner": null },
  "firmographics": {
    "what_they_sell": "", "who_they_sell_to": "", "business_model": "",
    "hq_country": "", "languages_served": [], "funding_stage": ""
  },
  "voice": {
    "voice_ai_mentions": [{ "where": "website", "url": "", "quote": "" }],
    "voice_stack": [{ "vendor": "", "layer": "tts", "evidence_url": "", "confidence": "confirmed" }],
    "call_volume_signal": "", "telephony_owned": null, "eu_or_on_prem_requirement": ""
  },
  "custom_signals": { "regulated_vertical": null },
  "sources_tried": [{ "source": "", "result": "ok", "note": "" }]
}
```

## What comes out

The score lands in Slack (for now Alberto's DM with Hermes): a headline (`company · X/10 · decision`),
up to three reasons, the open questions, and the full result as JSON. The same JSON is saved on the server
in `/opt/data/workspace/qualify-lead/results/<lead_id>.json`.

`decision` is one of `call`, `self_serve`, `park` (with `reopen_trigger`), `handoff` (customer, investor or
open deal in HubSpot) or `unknown` (no company domain). Code, not the model, decides it: `call` needs a
score of 70 or more, no disqualifier, no failed gate, no existing relationship and a phone number.
For a `call`, the JSON carries `call_brief` with the keys Kai reads as call context
(`leadId`, `firstName`, `lastName`, `email`, `phone`, `company`, `role`, `timezone`, `brief`, `angle`, `opener`).

## What the enrichment layer adds (gtm-hack `enrichment/`)

Copied from `hermes/input-contract.md` on branch `albkugel/qualifying` (2026-10-31). The enrichment layer
sends exactly this shape, plus a few fields Hermes may ignore safely:

- `lead.call_consent` (bool) and `lead.timezone` (the browser's). Without call consent `lead.phone` is `null`,
  so Hermes can never decide `call` for that person.
- `crm.lifecycle_stage` (HubSpot label) and `crm.do_not_contact` (true for "Kein Vertriebskontakt").
  Since 2026-10-31 Hermes's code turns `do_not_contact` into `handoff`, so such a company is never called.
- A `call` decision makes Hermes ask KugelAudio to have Kai (agent gtm-hack) dial `lead.phone`, with the
  call brief as client context; the call id lands in the result's `call` field and in Slack.
- `person`: the signer's title and LinkedIn URL when AI Ark or LinkedIn found them at this company.
- Evidence objects next to optional facts: `firmographics.evidence[]` (`field`, `url`, `quote`),
  `voice.call_volume_evidence`, `voice.telephony_evidence`, `voice.eu_evidence`,
  `custom_signals.regulated_evidence` (each `{url, quote}`), and a `quote` on every `voice_stack` entry.
  Every quote has been checked by code against the cited source's text; facts that failed were removed.
- Sources that aren't web pages are named `hubspot:<TYPE> <id>`, `aiark:person <id>` or `aiark:company <id>`.
