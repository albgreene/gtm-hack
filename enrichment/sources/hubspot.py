"""HubSpot (read-only): is this company already a customer, an investor or an open deal, and what do our notes say?

KugelAudio's portal marks things like this (checked 2026-10-31):
- lifecycle stage `customer`, `6144324828` = Investor, `6157284596` = "Kein Vertriebskontakt" (no sales contact)
- won deals: stages closedwon / 5818079442 (Production) in "Enterprise Fokus",
  6157013239 / 6163434745 in "Kleinkunden & Self-Service"
- the "Fundraising" pipeline (4055645375) holds investors; 5898277081 there means Declined.
"""

from __future__ import annotations

import html
import re
import time

from .. import doc, net, source_result
from ..config import HUBSPOT_URL, env

LIFECYCLE_LABELS = {"lead": "Lead", "marketingqualifiedlead": "Marketing Qualified Lead",
                    "salesqualifiedlead": "Sales Qualified Lead", "opportunity": "Opportunity",
                    "customer": "Customer", "5948859631": "Partner", "5824440515": "Subscriber",
                    "6144324828": "Investor", "6157284596": "Kein Vertriebskontakt"}
WON_STAGES = {"closedwon", "5818079442", "6157013239", "6163434745"}
CLOSED_STAGES = WON_STAGES | {"closedlost", "6157013240", "5898277080", "5898277081", "6301154553", "6301155514"}
FUNDRAISING_PIPELINE, FUNDRAISING_DECLINED = "4055645375", "5898277081"
INVESTOR_LIFECYCLE, NO_SALES_CONTACT = "6144324828", "6157284596"

ENGAGEMENTS = {  # object type -> (body property, title property, source label)
    "notes": ("hs_note_body", None, "NOTE"),
    "calls": ("hs_call_body", "hs_call_title", "CALL"),
    "meetings": ("hs_meeting_body", "hs_meeting_title", "MEETING_EVENT"),
}
MAX_ENGAGEMENTS, MAX_BODY = 8, 1500


class HubSpotError(RuntimeError):
    """HubSpot couldn't be read. The lead must not be sent: we can't rule out a customer or investor."""


def crm_flags(lifecycle: str | None, deals: list[dict], owners: dict[str, str]) -> dict:
    is_customer = lifecycle == "customer" or any(d.get("dealstage") in WON_STAGES for d in deals)
    is_investor = lifecycle == INVESTOR_LIFECYCLE or any(
        d.get("pipeline") == FUNDRAISING_PIPELINE and d.get("dealstage") != FUNDRAISING_DECLINED for d in deals)
    open_owner = None
    for deal in deals:
        if deal.get("dealstage") not in CLOSED_STAGES:
            open_owner = owners.get(str(deal.get("hubspot_owner_id") or ""), "an owner in HubSpot")
            break
    return {"is_customer": bool(is_customer), "is_investor": bool(is_investor), "open_deal_owner": open_owner,
            "lifecycle_stage": LIFECYCLE_LABELS.get(lifecycle or "", lifecycle),
            "do_not_contact": lifecycle == NO_SALES_CONTACT}


def _call(path: str, body: dict | None = None):
    token = env("HUBSPOT_PRIVATE_APP_TOKEN")
    if not token:
        raise HubSpotError("HUBSPOT_PRIVATE_APP_TOKEN is not set")
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(3):
        try:
            if body is None:
                return net.get_json(HUBSPOT_URL + path, headers)
            return net.post_json(HUBSPOT_URL + path, body, headers)
        except net.HTTPError as exc:
            if exc.status not in (429, 500, 502, 503, 504) or attempt == 2:
                raise HubSpotError(f"{path}: {exc}") from exc
        except OSError as exc:  # timeouts, DNS, connection resets
            if attempt == 2:
                raise HubSpotError(f"{path}: {exc}") from exc
        time.sleep(1.5 * (attempt + 1))


def _search(object_type: str, prop: str, value: str, properties: list[str]) -> list[dict]:
    body = {"filterGroups": [{"filters": [{"propertyName": prop, "operator": "EQ", "value": value}]}],
            "properties": properties, "limit": 5}
    return (_call(f"/crm/v3/objects/{object_type}/search", body) or {}).get("results") or []


def _associated(from_type: str, from_id: str, to_type: str) -> list[str]:
    reply = _call(f"/crm/v4/objects/{from_type}/{from_id}/associations/{to_type}?limit=100") or {}
    return [str(r["toObjectId"]) for r in reply.get("results") or []]


def _batch_read(object_type: str, ids: list[str], properties: list[str]) -> list[dict]:
    if not ids:
        return []
    body = {"inputs": [{"id": i} for i in ids[:100]], "properties": properties}
    return (_call(f"/crm/v3/objects/{object_type}/batch/read", body) or {}).get("results") or []


def _owner_names(owner_ids: set[str]) -> dict[str, str]:
    names = {}
    for owner_id in owner_ids:
        try:
            owner = _call(f"/crm/v3/owners/{owner_id}") or {}
            names[owner_id] = " ".join(filter(None, [owner.get("firstName"), owner.get("lastName")])) or owner_id
        except HubSpotError:
            names[owner_id] = "an owner in HubSpot"
    return names


def _plain(text: str) -> str:
    text = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", text or "", flags=re.I)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()


def _engagement_docs(object_type: str, object_id: str) -> list[dict]:
    found = []
    for kind, (body_prop, title_prop, label) in ENGAGEMENTS.items():
        ids = _associated(object_type, object_id, kind)
        props = [body_prop, "hs_timestamp"] + ([title_prop] if title_prop else [])
        for record in _batch_read(kind, ids[-30:], props):
            p = record.get("properties") or {}
            body = _plain(p.get(body_prop) or "")
            if not body:
                continue
            title = _plain(p.get(title_prop) or "") if title_prop else ""
            found.append((p.get("hs_timestamp") or "", doc(f"hubspot:{label} {record['id']}", "hubspot",
                                                          body[:MAX_BODY], title=title)))
    found.sort(key=lambda pair: pair[0], reverse=True)
    return [d for _, d in found[:MAX_ENGAGEMENTS]]


def lookup(domain: str | None, email: str | None) -> dict:
    """Raises HubSpotError when HubSpot can't be read; 'empty' only means HubSpot answered and knows nothing."""
    company = None
    if domain:
        hits = _search("companies", "domain", domain, ["name", "domain", "lifecyclestage", "hubspot_owner_id"])
        company = hits[0] if hits else None
    contact = None
    if email:
        hits = _search("contacts", "email", email, ["email", "lifecyclestage", "firstname", "lastname", "jobtitle"])
        contact = hits[0] if hits else None
        if contact and not company:
            company_ids = _associated("contacts", contact["id"], "companies")
            if company_ids:
                company = (_batch_read("companies", company_ids[:1],
                                       ["name", "domain", "lifecyclestage", "hubspot_owner_id"]) or [None])[0]

    if not company and not contact:
        return source_result("hubspot", "empty", f"no company for {domain or '-'} and no contact for {email or '-'}",
                             data={"crm": {"hubspot_company_id": None, **crm_flags(None, [], {})}})

    record_type, record = ("companies", company) if company else ("contacts", contact)
    props = record.get("properties") or {}
    deal_ids = _associated(record_type, record["id"], "deals")
    deals = [d.get("properties") or {} for d in
             _batch_read("deals", deal_ids, ["dealname", "pipeline", "dealstage", "hubspot_owner_id"])]
    owners = _owner_names({str(d["hubspot_owner_id"]) for d in deals if d.get("hubspot_owner_id")})
    crm = {"hubspot_company_id": company["id"] if company else None,
           **crm_flags(props.get("lifecyclestage"), deals, owners)}
    docs = _engagement_docs(record_type, record["id"])
    name = props.get("name") or " ".join(filter(None, [props.get("firstname"), props.get("lastname")]))
    label = "company" if company else "contact"
    note = f"{label} {record['id']} ({name}), {len(deals)} deal(s), {len(docs)} note(s)/call(s)/meeting(s)"
    return source_result("hubspot", "ok", note, docs=docs,
                         data={"crm": crm, "company_name": props.get("name") if company else None})
