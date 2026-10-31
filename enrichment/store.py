"""Supabase access (PostgREST with the secret key): read a sign-up, track its enrichment."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

from . import net
from .config import env


def _base() -> tuple[str, dict]:
    url, key = env("SUPABASE_URL").rstrip("/"), env("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
    return f"{url}/rest/v1", {"apikey": key}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_lead(lead_id: str) -> dict | None:
    base, headers = _base()
    rows = net.get_json(f"{base}/leads?id=eq.{urllib.parse.quote(lead_id)}&select=*", headers)
    return rows[0] if rows else None


def get_enrichment(lead_id: str) -> dict | None:
    base, headers = _base()
    rows = net.get_json(f"{base}/enrichments?lead_id=eq.{urllib.parse.quote(lead_id)}&select=*", headers)
    return rows[0] if rows else None


def claim(lead_id: str) -> bool:
    """Mark the lead as running. False if it is already running or sent (a repeat webhook or a double click)."""
    base, headers = _base()
    existing = get_enrichment(lead_id)
    if existing and existing.get("status") in ("running", "sent"):
        return False
    row = {"lead_id": lead_id, "status": "running", "started_at": now(), "finished_at": None, "error": None,
           "attempts": (existing or {}).get("attempts", 0) + 1}
    net.post_json(f"{base}/enrichments?on_conflict=lead_id", row,
                  {**headers, "Prefer": "resolution=merge-duplicates,return=minimal"})
    return True


def finish(lead_id: str, **fields) -> None:
    base, headers = _base()
    fields.setdefault("finished_at", now())
    net.post_json(f"{base}/enrichments?lead_id=eq.{urllib.parse.quote(lead_id)}", fields,
                  {**headers, "Prefer": "return=minimal"}, method="PATCH")
