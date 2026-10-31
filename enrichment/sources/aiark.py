"""AI Ark, called through its MCP endpoint: who is the person behind the email, and what is the company?"""

from __future__ import annotations

import json

from .. import doc, net, source_result
from ..config import AIARK_MCP_URL, env
from ..matching import company_matches


def _call(tool: str, arguments: dict):
    token = env("AIARK_API_TOKEN")
    if not token:
        raise RuntimeError("AIARK_API_TOKEN is not set")
    return net.mcp_call(f"{AIARK_MCP_URL}?token={token}", {}, tool, arguments, timeout=45)


def _first(reply) -> dict | None:
    content = (reply or {}).get("content") if isinstance(reply, dict) else None
    return content[0] if content else None


def _person_summary(record: dict) -> dict:
    profile, company = record.get("profile") or {}, record.get("company") or {}
    summary, link = company.get("summary") or {}, company.get("link") or {}
    return {"id": record.get("id"), "full_name": profile.get("full_name"), "title": profile.get("title"),
            "headline": profile.get("headline"), "linkedin_url": (record.get("link") or {}).get("linkedin"),
            "company_name": summary.get("name"), "company_domain": (link.get("domain") or "").lower() or None,
            "company_linkedin": link.get("linkedin"), "location": (record.get("location") or {}).get("default")}


def _person_doc(person: dict) -> dict:
    lines = [f"{person['full_name']}: {person.get('title') or ''} at {person.get('company_name') or 'unknown company'}",
             f"Headline: {person.get('headline') or ''}", f"LinkedIn: {person.get('linkedin_url') or ''}",
             f"Company domain: {person.get('company_domain') or ''}", f"Location: {person.get('location') or ''}"]
    return doc(f"aiark:person {person['id']}", "aiark", "\n".join(lines), title=person.get("full_name") or "")


def person(email: str, phone: str | None, first: str, last: str, domain: str | None) -> dict:
    """Reverse lookup by email, then phone. Without a hit, a name search inside the company's domain."""
    tried = []
    for kind, value in (("email", email), ("phone", phone)):
        if not value:
            continue
        try:
            record = _first(_call("reverse_people_lookup", {"requestBody": json.dumps(
                {"kind": "CONTACT", "search": value, "page": 0, "size": 3})}))
        except net.ToolError as exc:
            tried.append(f"{kind}: {str(exc)[:60]}")
            continue
        if record:
            found = _person_summary(record)
            return source_result("aiark:person", "ok", f"found by {kind}", docs=[_person_doc(found)],
                                 data={"person": found, "match": kind})
        tried.append(f"{kind}: no match")

    if domain and first and last:
        try:
            reply = _call("people_search", {"fullName": f"{first} {last}", "companyDomain": domain, "size": 3})
        except net.ToolError as exc:
            reply = None
            tried.append(f"name in {domain}: {str(exc)[:60]}")
        for record in (reply or {}).get("content") or []:
            found = _person_summary(record)
            same_name = (found["full_name"] or "").lower() == f"{first} {last}".lower()
            if same_name and company_matches(" ".join(filter(None, [found["company_name"], found["company_domain"]])),
                                             domain, []):
                return source_result("aiark:person", "ok", f"found by name at {domain}", docs=[_person_doc(found)],
                                     data={"person": found, "match": "name"})
        tried.append(f"name in {domain}: no match")
    return source_result("aiark:person", "empty", "; ".join(tried) or "nothing to look up", data={"person": {}})


def company(domain: str) -> dict:
    try:
        record = _first(_call("company_search", {"domain": domain, "size": 1}))
    except net.ToolError as exc:
        return source_result("aiark:company", "empty", str(exc)[:100], data={"company": {}})
    if not record or ((record.get("link") or {}).get("domain") or "").lower() != domain.lower():
        return source_result("aiark:company", "empty", f"no company with domain {domain}", data={"company": {}})

    summary, link = record.get("summary") or {}, record.get("link") or {}
    hq = ((record.get("location") or {}).get("headquarter") or {})
    funding = ((record.get("financial") or {}).get("funding") or {})
    staff = (summary.get("staff") or {}).get("total")
    technologies = [t.get("name") for t in record.get("technologies") or [] if t.get("name")]
    lines = [f"{summary.get('name')} ({summary.get('legal_name') or ''}): {summary.get('description') or ''}",
             f"Industry: {summary.get('industry') or ''}; industries: {', '.join(record.get('industries') or [])}",
             f"Headquarters: {hq.get('raw_address') or ', '.join(filter(None, [hq.get('city'), hq.get('country')]))}",
             f"Employees: {staff or ''}", f"Founded: {summary.get('founded_year') or ''}",
             f"Funding: {funding.get('type') or ''}, total {funding.get('total_amount') or ''}",
             f"Languages: {', '.join(record.get('languages') or [])}",
             f"Website: {link.get('website') or ''}; LinkedIn: {link.get('linkedin') or ''}",
             f"Technologies: {', '.join(technologies)}"]
    data = {"company": {"id": record.get("id"), "name": summary.get("name"), "legal_name": summary.get("legal_name"),
                        "linkedin": link.get("linkedin"), "hq_country": hq.get("country"), "hq_city": hq.get("city"),
                        "funding_type": funding.get("type"), "employees": staff}}
    return source_result("aiark:company", "ok", summary.get("name") or domain,
                         docs=[doc(f"aiark:company {record.get('id')}", "aiark", "\n".join(lines),
                                   title=summary.get("name") or "")], data=data)
