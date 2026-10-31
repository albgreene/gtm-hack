import json

from enrichment import doc, verify

HOME = doc("https://www.telli.com/", "website",
           "Model Agnostic. Built on the best AI models,\n never locked to one provider.\n"
           "[image] alt=ElevenLabs src=/l/elevenlabs.svg\nRunning **millions** of calls every month.")
JOB = doc("https://www.linkedin.com/jobs/view/4429615204", "job", "Voice and backend: Python, uv, FastAPI, LiveKit")


def payload(**voice):
    return {"lead": {"lead_id": "x", "email": "a@telli.com"}, "domain": "telli.com", "name": "telli",
            "firmographics": {"what_they_sell": "AI voice agents", "evidence": []},
            "voice": {"voice_ai_mentions": [], "voice_stack": [], "call_volume_signal": None,
                      "call_volume_evidence": None, "telephony_owned": None, "telephony_evidence": None,
                      "eu_or_on_prem_requirement": None, "eu_evidence": None, **voice},
            "custom_signals": {"regulated_vertical": None, "regulated_evidence": None, "decision_makers": [],
                               "critical_event_signals": []},
            "sources_tried": []}


def test_drops_invented_quote():
    p = payload(voice_ai_mentions=[
        {"where": "website", "url": "https://www.telli.com/", "quote": "Built on the best AI models"},
        {"where": "website", "url": "https://www.telli.com/", "quote": "We use Deepgram for every call"}])
    checked, dropped = verify.check_quotes(p, [HOME, JOB])
    assert dropped == 1
    assert [m["quote"] for m in checked["voice"]["voice_ai_mentions"]] == ["Built on the best AI models"]


def test_quote_check_normalises_whitespace_case_markdown_and_url():
    p = payload(voice_ai_mentions=[
        {"where": "website", "url": "https://telli.com", "quote": "best ai models, never locked to one provider"},
        {"where": "website", "url": "https://www.telli.com/?utm=x", "quote": "Running millions of calls every month"}])
    checked, dropped = verify.check_quotes(p, [HOME])
    assert dropped == 0
    assert len(checked["voice"]["voice_ai_mentions"]) == 2


def test_quote_with_ellipsis_needs_each_part_in_order():
    ok = payload(voice_ai_mentions=[{"where": "website", "url": "https://www.telli.com/",
                                     "quote": "Model Agnostic ... never locked to one provider"}])
    bad = payload(voice_ai_mentions=[{"where": "website", "url": "https://www.telli.com/",
                                      "quote": "never locked to one provider ... Model Agnostic"}])
    assert verify.check_quotes(ok, [HOME])[1] == 0
    assert verify.check_quotes(bad, [HOME])[1] == 1


def test_stack_entry_needs_quote_in_cited_doc():
    p = payload(voice_stack=[
        {"vendor": "LiveKit", "layer": "agent_platform", "evidence_url": JOB["url"], "quote": "FastAPI, LiveKit",
         "confidence": "confirmed"},
        {"vendor": "LiveKit", "layer": "agent_platform", "evidence_url": HOME["url"], "quote": "FastAPI, LiveKit",
         "confidence": "confirmed"}])
    checked, dropped = verify.check_quotes(p, [HOME, JOB])
    assert dropped == 1
    assert checked["voice"]["voice_stack"][0]["evidence_url"] == JOB["url"]


def test_unverified_evidence_clears_the_fact():
    p = payload(call_volume_signal="millions of calls a month",
                call_volume_evidence={"url": HOME["url"], "quote": "millions of calls every month"},
                telephony_owned=True, telephony_evidence={"url": HOME["url"], "quote": "we run our own SIP trunks"})
    checked, dropped = verify.check_quotes(p, [HOME])
    assert checked["voice"]["call_volume_signal"] == "millions of calls a month"
    assert checked["voice"]["telephony_owned"] is None and checked["voice"]["telephony_evidence"] is None
    assert dropped == 1


def test_hubspot_sources_are_checked_too():
    note = doc("hubspot:NOTE 513085772004", "hubspot", "er ist einer der ersten, der direkt auf Voice-to-Voice ansprechen möchte")
    p = payload(voice_ai_mentions=[{"where": "hubspot", "url": "hubspot:NOTE 513085772004",
                                    "quote": "direkt auf Voice-to-Voice ansprechen"}])
    assert verify.check_quotes(p, [note])[1] == 0


def test_fit_size_trims_lists():
    mentions = [{"where": "linkedin_post", "url": f"https://x/{i}", "quote": "q" * 900} for i in range(120)]
    p = payload(voice_ai_mentions=mentions)
    fitted = verify.fit_size(p, limit=65536)
    assert len(json.dumps(fitted, ensure_ascii=False, separators=(",", ":")).encode()) <= 65536
    assert fitted["lead"] == p["lead"]
    assert 0 < len(fitted["voice"]["voice_ai_mentions"]) < 120
