"""Enrichment: turn a Supabase sign-up into an enriched lead for the Hermes qualifier.

Spec: docs/superpowers/specs/2026-10-31-enrichment-design.md
Output contract: docs/qualify-lead-contract.md

Every source returns a SourceResult:
    {"source": str, "result": "ok" | "empty" | "error" | "skipped", "note": str,
     "docs": [Doc, ...], "data": {...}}
and every piece of raw text is a Doc:
    {"url": str, "kind": str, "title": str, "text": str}
The LLM may only quote text that is in a Doc; verify.check_quotes enforces that.
"""


def source_result(source: str, result: str = "ok", note: str = "", docs: list | None = None,
                  data: dict | None = None) -> dict:
    return {"source": source, "result": result, "note": note, "docs": docs or [], "data": data or {}}


def doc(url: str, kind: str, text: str, title: str = "") -> dict:
    return {"url": url, "kind": kind, "title": title, "text": text}
