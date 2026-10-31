"""One LLM call: raw documents and vendor candidates in, the company part of the qualifier contract out."""

from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic

from .config import LLM_BASE_URL, LLM_MODEL, env

PROMPT = (Path(__file__).with_name("prompt.md")).read_text()
MAX_DOC_CHARS = 12000


def _nullable(kind: str) -> dict:
    return {"type": [kind, "null"]}


EVIDENCE = {"type": ["object", "null"], "additionalProperties": False, "required": ["url", "quote"],
            "properties": {"url": {"type": "string"}, "quote": {"type": "string"}}}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["name", "firmographics", "voice", "custom_signals"],
    "properties": {
        "name": _nullable("string"),
        "firmographics": {
            "type": "object", "additionalProperties": False,
            "required": ["what_they_sell", "who_they_sell_to", "segment", "sub_industry", "business_model",
                         "hq_country", "hq_city", "languages_served", "funding_stage", "evidence"],
            "properties": {
                "what_they_sell": _nullable("string"), "who_they_sell_to": _nullable("string"),
                "segment": _nullable("string"), "sub_industry": _nullable("string"),
                "business_model": {"type": ["string", "null"],
                                   "enum": ["voice-agent builder", "telco/CPaaS", "platform reseller/hoster",
                                            "end-user enterprise", "non-voice SaaS", "consultancy", "other", None]},
                "hq_country": _nullable("string"), "hq_city": _nullable("string"),
                "languages_served": {"type": "array", "items": {"type": "string"}},
                "funding_stage": _nullable("string"),
                "evidence": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["field", "url", "quote"],
                    "properties": {"field": {"type": "string"}, "url": {"type": "string"},
                                   "quote": {"type": "string"}}}},
            },
        },
        "voice": {
            "type": "object", "additionalProperties": False,
            "required": ["voice_is_core_product", "voice_ai_mentions", "voice_stack", "call_volume_signal",
                         "call_volume_evidence", "telephony_owned", "telephony_evidence",
                         "eu_or_on_prem_requirement", "eu_evidence"],
            "properties": {
                "voice_is_core_product": _nullable("boolean"),
                "voice_ai_mentions": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["where", "url", "quote"],
                    "properties": {"where": {"type": "string", "enum": ["website", "docs", "job", "linkedin_post",
                                                                        "press", "hubspot"]},
                                   "url": {"type": "string"}, "quote": {"type": "string"}}}},
                "voice_stack": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["vendor", "layer", "evidence_url", "quote", "confidence"],
                    "properties": {"vendor": {"type": "string"},
                                   "layer": {"type": "string", "enum": ["tts", "stt", "s2s", "llm", "agent_platform",
                                                                        "telephony", "contact_center"]},
                                   "evidence_url": {"type": "string"}, "quote": {"type": "string"},
                                   "confidence": {"type": "string", "enum": ["confirmed", "likely"]}}}},
                "call_volume_signal": _nullable("string"), "call_volume_evidence": EVIDENCE,
                "telephony_owned": _nullable("boolean"), "telephony_evidence": EVIDENCE,
                "eu_or_on_prem_requirement": _nullable("string"), "eu_evidence": EVIDENCE,
            },
        },
        "custom_signals": {
            "type": "object", "additionalProperties": False,
            "required": ["regulated_vertical", "regulated_evidence", "decision_makers", "critical_event_signals"],
            "properties": {
                "regulated_vertical": _nullable("string"), "regulated_evidence": EVIDENCE,
                "decision_makers": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["name", "title", "url"],
                    "properties": {"name": {"type": "string"}, "title": _nullable("string"),
                                   "url": {"type": "string"}}}},
                "critical_event_signals": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["what", "date", "url"],
                    "properties": {"what": {"type": "string"}, "date": _nullable("string"),
                                   "url": {"type": "string"}}}},
            },
        },
    },
}


def _escape(text: str) -> str:
    return (text or "").replace("</doc>", "</ doc>")


def build_user_content(signup: dict, sources: list[dict], candidates: list[dict], site_locales: list[str]) -> str:
    parts = ["Sign-up (the person who registered):",
             json.dumps(signup, ensure_ascii=False, indent=1),
             f"\nLanguage versions of the company website: {', '.join(site_locales) or 'none found'}",
             "\nCandidate voice vendors found by code (vendor, layer hint, url, exact text around the hit):"]
    parts += [f"- {c['vendor']} ({c['layer']}) at {c['url']}: \"{c['snippet']}\"" for c in candidates] or ["- none"]
    parts.append("\nDocuments:")
    for source in sources:
        for d in source["docs"]:
            parts.append(f'<doc url="{d["url"]}" kind="{d["kind"]}" title="{_escape(d.get("title", ""))[:120]}">\n'
                         f'{_escape(d["text"])[:MAX_DOC_CHARS]}\n</doc>')
    return "\n".join(parts)


def _client() -> anthropic.Anthropic:
    key = env("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return anthropic.Anthropic(base_url=LLM_BASE_URL, auth_token=key, api_key=None, timeout=170.0, max_retries=1)


def extract(signup: dict, sources: list[dict], candidates: list[dict], site_locales: list[str]) -> tuple[dict, str]:
    """Returns (company facts matching SCHEMA, model that answered). Raises on refusal, truncation or no JSON."""
    request = {
        "model": LLM_MODEL,
        "max_tokens": 16000,
        "system": [{"type": "text", "text": PROMPT, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": build_user_content(signup, sources, candidates, site_locales)}],
    }
    effort = env("ENRICH_EFFORT", "medium")
    client = _client()
    try:
        response = client.messages.create(**request, extra_body={
            "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}, "effort": effort}})
    except anthropic.BadRequestError:
        # The proxy may not pass structured outputs through; the prompt asks for the same JSON.
        request["messages"][0]["content"] += ("\n\nAnswer with one JSON object matching this schema:\n"
                                              + json.dumps(SCHEMA))
        response = client.messages.create(**request, extra_body={"output_config": {"effort": effort}})
    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined to extract facts (refusal)")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("the model's answer was cut off (max_tokens)")
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise RuntimeError("the model returned no JSON")
    return json.loads(match.group(0)), response.model
