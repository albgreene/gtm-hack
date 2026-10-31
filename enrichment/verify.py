"""Checks after the LLM: every quote must really be in the source it cites, and the payload must fit Hermes."""

from __future__ import annotations

import copy
import json
import re
from urllib.parse import urlparse

from .config import MAX_PAYLOAD_BYTES

# Optional facts that carry their own evidence object: (section, value field, evidence field).
EVIDENCED_FACTS = [("voice", "call_volume_signal", "call_volume_evidence"),
                   ("voice", "telephony_owned", "telephony_evidence"),
                   ("voice", "eu_or_on_prem_requirement", "eu_evidence"),
                   ("custom_signals", "regulated_vertical", "regulated_evidence")]
TRANSLATE = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "„": '"', "–": "-", "—": "-", " ": " "})


def normalise_text(text: str) -> str:
    text = (text or "").translate(TRANSLATE).lower()
    text = re.sub(r"[*_`#>|]+", " ", text)
    return " ".join(text.split())


def normalise_url(url: str) -> str:
    url = (url or "").strip()
    if not url.startswith("http"):
        return url.lower()
    parsed = urlparse(url)
    return parsed.netloc.lower().removeprefix("www.") + parsed.path.rstrip("/").lower()


def _quote_in(quote: str, text: str) -> bool:
    parts = [normalise_text(p) for p in re.split(r"\.\.\.|…", quote or "")]
    parts = [p.strip(" .,;:") for p in parts if p.strip(" .,;:")]
    if not parts or sum(len(p) for p in parts) < 8:
        return False
    position = 0
    for part in parts:
        found = text.find(part, position)
        if found < 0:
            return False
        position = found + len(part)
    return True


def check_quotes(payload: dict, docs: list[dict]) -> tuple[dict, int]:
    """Drop every fact whose quote isn't in the document it cites. Returns (checked payload, number dropped)."""
    texts: dict[str, str] = {}
    for d in docs:
        key = normalise_url(d["url"])
        texts[key] = texts.get(key, "") + " " + normalise_text(f"{d.get('title', '')} {d['text']}")
    out, dropped = copy.deepcopy(payload), 0

    def ok(url, quote):
        return _quote_in(quote, texts.get(normalise_url(url), ""))

    voice, firmo, custom = out.get("voice") or {}, out.get("firmographics") or {}, out.get("custom_signals") or {}
    for container, key, url_field in ((voice, "voice_ai_mentions", "url"), (voice, "voice_stack", "evidence_url"),
                                      (firmo, "evidence", "url")):
        kept = [e for e in container.get(key) or [] if ok(e.get(url_field), e.get("quote"))]
        dropped += len(container.get(key) or []) - len(kept)
        if key in container:
            container[key] = kept

    for section, value_field, evidence_field in EVIDENCED_FACTS:
        part = out.get(section) or {}
        evidence = part.get(evidence_field)
        if evidence and not ok(evidence.get("url"), evidence.get("quote")):
            part[evidence_field], dropped = None, dropped + 1
        if not part.get(evidence_field) and part.get(value_field) is not None:
            part[value_field] = None

    all_text = " ".join(texts.values())
    makers = custom.get("decision_makers") or []
    custom["decision_makers"] = [m for m in makers if m.get("name") and normalise_text(m["name"]) in all_text]
    events = custom.get("critical_event_signals") or []
    custom["critical_event_signals"] = [e for e in events if normalise_url(e.get("url")) in texts]
    dropped += len(makers) - len(custom["decision_makers"]) + len(events) - len(custom["critical_event_signals"])
    return out, dropped


def size(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())


def fit_size(payload: dict, limit: int = MAX_PAYLOAD_BYTES) -> dict:
    """Trim the longest lists first, then long strings, until the body fits. The lead block is never touched."""
    out = copy.deepcopy(payload)
    lists = [("voice", "voice_ai_mentions"), ("custom_signals", "critical_event_signals"),
             ("custom_signals", "decision_makers"), ("firmographics", "evidence"), ("voice", "voice_stack"),
             (None, "sources_tried")]
    def holder(section):
        return (out.get(section) or {}) if section else out

    while size(out) > limit:
        count, section, key = max((len(holder(s).get(k) or []), s or "", k) for s, k in lists)
        if count <= 3:
            break
        holder(section or None)[key].pop()
    if size(out) > limit:
        def shorten(value):
            if isinstance(value, str):
                return value[:300]
            if isinstance(value, list):
                return [shorten(v) for v in value]
            if isinstance(value, dict):
                return {k: shorten(v) for k, v in value.items()}
            return value
        out = {k: (v if k == "lead" else shorten(v)) for k, v in out.items()}
    return out
