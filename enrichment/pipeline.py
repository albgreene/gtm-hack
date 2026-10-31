"""Enrich one sign-up end to end: gather sources, find the voice stack, extract facts, check quotes, send."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from . import handoff, source_result, store, techstack, verify
from .config import SOURCE_TIMEOUT_S
from .extract import extract
from .matching import company_matches, email_domain, is_free_mail
from .sources import aiark, hubspot, needle, vendor_search, website
from .sources.hubspot import HubSpotError

EMPTY_CRM = {"hubspot_company_id": None, "is_customer": False, "is_investor": False, "open_deal_owner": None}


def build_lead_block(row: dict, person: dict) -> dict:
    consent = bool((row.get("call_consent") or {}).get("given"))
    return {"lead_id": row["id"], "signed_up_at": row.get("submitted_at"), "first_name": row.get("first_name"),
            "last_name": row.get("last_name"), "role": (person or {}).get("title"), "email": row.get("email"),
            # Without call consent Hermes gets no phone number, so its code can never decide "call".
            "phone": row.get("phone") if consent else None, "country": row.get("country"),
            "timezone": row.get("timezone"), "call_consent": consent}


def _run_parallel(jobs: dict) -> dict:
    """Run {name: (fn, args)} at once; a source that errors or takes too long becomes an error result.
    A HubSpotError is re-raised: without HubSpot we can't rule out a customer or investor."""
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        futures = {name: pool.submit(fn, *args) for name, (fn, args) in jobs.items()}
        deadline = time.monotonic() + SOURCE_TIMEOUT_S
        for name, future in futures.items():
            try:
                results[name] = future.result(timeout=max(1, deadline - time.monotonic()))
            except HubSpotError:
                raise
            except FutureTimeout:
                if name == "hubspot":
                    raise HubSpotError("timed out")
                results[name] = source_result(name, "error", f"timed out after {SOURCE_TIMEOUT_S}s")
            except Exception as exc:  # one broken source never stops the others
                results[name] = source_result(name, "error", f"{type(exc).__name__}: {str(exc)[:200]}")
    return results


def _site_name(title: str | None) -> str | None:
    name = (title or "").split("|")[0].split(" - ")[0].split(" – ")[0].strip()
    return name or None


def gather(row: dict) -> dict:
    email, first, last, phone = row.get("email"), row.get("first_name"), row.get("last_name"), row.get("phone")
    domain = email_domain(email)
    free = is_free_mail(domain)
    company_domain = None if free else domain

    if free:  # the person might still be known at a company: AI Ark's reverse lookup of this exact email
        first_round = _run_parallel({"aiark_person": (aiark.person, (email, phone, first, last, None))})
        found = first_round["aiark_person"]["data"].get("person") or {}
        if found.get("company_domain") and not is_free_mail(found["company_domain"]):
            company_domain = found["company_domain"]
            first_round["aiark_person"]["note"] += f"; company domain {company_domain} from AI Ark"
    else:
        first_round = {}

    jobs = {"hubspot": (hubspot.lookup, (company_domain, email))}
    if not free:
        jobs["aiark_person"] = (aiark.person, (email, phone, first, last, company_domain))
    if company_domain:
        jobs["website"] = (website.scrape, (company_domain,))
        jobs["aiark_company"] = (aiark.company, (company_domain,))
    results = {**first_round, **_run_parallel(jobs)}

    names = [n for n in [(results.get("aiark_company") or {}).get("data", {}).get("company", {}).get("name"),
                         results["hubspot"]["data"].get("company_name"),
                         _site_name((results.get("website") or {}).get("data", {}).get("site_name"))] if n]
    ai_person = results["aiark_person"]["data"].get("person") or {}
    person_company = " ".join(filter(None, [ai_person.get("company_name"), ai_person.get("company_domain")]))
    person_ok = bool(ai_person) and company_domain and company_matches(person_company, company_domain, names)
    if ai_person and not person_ok:
        results["aiark_person"]["note"] += f"; profile found, different company ({person_company or 'none'})"
        results["aiark_person"]["docs"] = []

    if company_domain:
        company_linkedin = ((results.get("aiark_company") or {}).get("data", {}).get("company", {}).get("linkedin")
                            or (ai_person.get("company_linkedin") if person_ok else None))
        results.update(_run_parallel({
            "needle_person": (needle.person, (first, last, company_domain, names,
                                              ai_person.get("linkedin_url") if person_ok else None)),
            "needle_company": (needle.company, (company_domain, company_linkedin)),
            "vendor_search": (vendor_search.search, (names[0] if names else None, company_domain)),
        }))
    return {"domain": company_domain, "names": names, "results": results,
            "person": ai_person if person_ok else {}, "free_mail": free}


def _person_block(gathered: dict) -> dict:
    linked = (gathered["results"].get("needle_person") or {}).get("data", {}).get("person") or {}
    if linked:
        return {"title": linked.get("title") or linked.get("headline"), "linkedin_url": linked.get("linkedin_url"),
                "source": linked.get("linkedin_url")}
    ai = gathered["person"]
    if ai:
        return {"title": ai.get("title"), "linkedin_url": ai.get("linkedin_url"), "source": f"aiark:person {ai['id']}"}
    return {"title": None, "linkedin_url": None, "source": None}


def _sources_tried(gathered: dict) -> list[dict]:
    order = ["hubspot", "website", "vendor_search", "aiark_person", "aiark_company", "needle_person", "needle_company"]
    tried = []
    for key in order:
        result = gathered["results"].get(key)
        if result:
            tried.append({"source": result["source"], "result": result["result"], "note": result["note"][:300]})
        elif key in ("website", "vendor_search", "aiark_company", "needle_person", "needle_company"):
            tried.append({"source": key.replace("_", ":") if key.startswith(("aiark", "needle")) else key,
                          "result": "skipped", "note": "no company domain (free-mail address, employer unknown)"})
    return tried


def _raw_summary(gathered: dict) -> dict:
    return {key: {"result": r["result"], "note": r["note"], "data": r["data"],
                  "docs": [{"url": d["url"], "kind": d["kind"], "title": d.get("title", ""), "chars": len(d["text"]),
                            "start": d["text"][:300]} for d in r["docs"]]}
            for key, r in gathered["results"].items()}


def build_payload(row: dict, gathered: dict) -> tuple[dict, dict]:
    sources = list(gathered["results"].values())
    docs = [d for s in sources for d in s["docs"]]
    candidates = techstack.find_vendors(docs)
    person = _person_block(gathered)
    lead = build_lead_block(row, person)
    company, model = {}, None
    if gathered["domain"]:
        signup = {"first_name": row.get("first_name"), "last_name": row.get("last_name"),
                  "company_domain": gathered["domain"], "country": row.get("country"), "role": person.get("title")}
        locales = (gathered["results"].get("website") or {}).get("data", {}).get("site_locales") or []
        company, model = extract(signup, sources, candidates, locales)

    payload = {
        "lead": lead,
        "domain": gathered["domain"],
        "name": company.get("name") or (gathered["names"][0] if gathered["names"] else None),
        "crm": {**EMPTY_CRM, **gathered["results"]["hubspot"]["data"].get("crm", {})},
        "firmographics": company.get("firmographics") or {},
        "voice": company.get("voice") or {},
        "custom_signals": company.get("custom_signals") or {},
        "person": person,
    }
    payload, dropped = verify.check_quotes(payload, docs)
    payload["sources_tried"] = _sources_tried(gathered)
    if gathered["domain"]:
        payload["sources_tried"].append({"source": "quote check", "result": "ok",
                                         "note": f"{dropped} fact(s) removed: quote not found in the cited source"})
    return verify.fit_size(payload), {"model": model, "candidates": len(candidates), "dropped": dropped}


def enrich_lead(lead_id: str, send: bool = True) -> dict:
    started = time.monotonic()
    if not store.claim(lead_id):
        return {"lead_id": lead_id, "status": "skipped", "reason": "already running or sent"}
    row = store.get_lead(lead_id)
    if not row:
        store.finish(lead_id, status="failed", error="lead not found in Supabase")
        return {"lead_id": lead_id, "status": "failed", "error": "lead not found"}

    try:
        gathered = gather(row)
        payload, info = build_payload(row, gathered)
    except HubSpotError as exc:
        error = f"HubSpot couldn't be read, so the lead was not sent (can't rule out a customer or investor): {exc}"
        store.finish(lead_id, status="failed", error=error[:1000])
        return {"lead_id": lead_id, "status": "failed", "error": error}
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        store.finish(lead_id, status="failed", error=error[:1000])
        return {"lead_id": lead_id, "status": "failed", "error": error}

    fields = {"raw": _raw_summary(gathered), "payload": payload}
    hermes_status, answer = (None, None)
    if send:
        hermes_status, answer = handoff.send(payload)
        delivered = hermes_status == 200 and answer.get("status") == "delivered"
        fields.update(status="sent" if delivered else "failed", hermes_status=hermes_status, hermes_response=answer,
                      error=None if delivered else f"Hermes answered {hermes_status}: {answer}"[:1000])
    else:
        fields.update(status="skipped", error="dry run: not sent to Hermes")
    store.finish(lead_id, **fields)
    stack = [f"{e.get('vendor')} ({e.get('layer')}, {e.get('confidence')})"
             for e in (payload.get("voice") or {}).get("voice_stack") or []]
    return {"lead_id": lead_id, "status": fields["status"], "domain": payload["domain"], "name": payload["name"],
            "crm": payload["crm"], "stack": stack, "quotes_removed": info["dropped"], "hermes_status": hermes_status,
            "hermes": answer, "seconds": round(time.monotonic() - started, 1)}
