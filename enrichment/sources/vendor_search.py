"""Search voice vendors' own sites for the company: case studies and customer pages.

This is how telli's Cartesia contract was found: it's on cartesia.ai/customers/telli, not on telli.com.
Needs FIRECRAWL_API_KEY (Firecrawl search); without it the source is recorded as skipped.
"""

from __future__ import annotations

from .. import doc, net, source_result
from ..config import FIRECRAWL_URL, env
from ..matching import company_matches

VENDOR_SITES = ["elevenlabs.io", "cartesia.ai", "deepgram.com", "vapi.ai", "retellai.com", "livekit.io",
                "twilio.com", "speechmatics.com", "assemblyai.com", "gladia.io", "synthflow.ai", "play.ht",
                "rime.ai", "telnyx.com", "pipecat.ai"]


def search(company_name: str | None, domain: str | None) -> dict:
    if not env("FIRECRAWL_API_KEY"):
        return source_result("vendor_search", "skipped", "no FIRECRAWL_API_KEY")
    name = (company_name or (domain or "").split(".")[0]).strip()
    if len(name) < 3:
        return source_result("vendor_search", "skipped", "no company name to search for")

    query = f'"{name}" (' + " OR ".join(f"site:{site}" for site in VENDOR_SITES) + ")"
    try:
        reply = net.post_json(f"{FIRECRAWL_URL}/search",
                              {"query": query, "limit": 6,
                               "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True}},
                              {"Authorization": f"Bearer {env('FIRECRAWL_API_KEY')}"}, timeout=60)
    except (net.HTTPError, OSError) as exc:
        return source_result("vendor_search", "error", str(exc)[:200])

    data = (reply or {}).get("data") or {}
    hits = data.get("web") if isinstance(data, dict) else data
    docs = []
    for hit in hits or []:
        text = hit.get("markdown") or hit.get("description") or ""
        if hit.get("url") and company_matches(text, domain, [name]):
            docs.append(doc(hit["url"], "vendor_site", text[:12000], title=hit.get("title") or ""))
    result = "ok" if docs else "empty"
    return source_result("vendor_search", result, f"{len(hits or [])} hit(s), {len(docs)} naming {name}", docs=docs)
