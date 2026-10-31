import pytest

from enrichment import pipeline
from enrichment.sources import hubspot

ROW = {"id": "abc123", "submitted_at": "2026-10-31T15:00:00+00:00", "first_name": "Test", "last_name": "Lead",
       "email": "test.lead@telli.com", "phone": "+491500000000", "country": "DE", "timezone": "Europe/Berlin",
       "call_consent": {"given": True, "version": "v1"}}


def test_consent_keeps_phone():
    lead = pipeline.build_lead_block(ROW, {"title": "CTO"})
    assert lead == {"lead_id": "abc123", "signed_up_at": "2026-10-31T15:00:00+00:00", "first_name": "Test",
                    "last_name": "Lead", "role": "CTO", "email": "test.lead@telli.com", "phone": "+491500000000",
                    "country": "DE", "timezone": "Europe/Berlin", "call_consent": True}


def test_no_consent_hides_phone():
    lead = pipeline.build_lead_block({**ROW, "call_consent": {"given": False}}, {})
    assert lead["phone"] is None
    assert lead["call_consent"] is False
    assert lead["role"] is None


@pytest.fixture
def recorder(monkeypatch):
    calls = {"finish": [], "sent": []}
    monkeypatch.setattr(pipeline.store, "get_lead", lambda lead_id: ROW)
    monkeypatch.setattr(pipeline.store, "finish", lambda lead_id, **f: calls["finish"].append(f))
    monkeypatch.setattr(pipeline.handoff, "send", lambda payload: calls["sent"].append(payload) or (200, {"status": "delivered"}))
    return calls


def test_claim_twice_skips(monkeypatch, recorder):
    monkeypatch.setattr(pipeline.store, "claim", lambda lead_id: False)
    monkeypatch.setattr(pipeline, "gather", lambda *a: pytest.fail("sources must not run"))
    result = pipeline.enrich_lead("abc123")
    assert result["status"] == "skipped"
    assert recorder["sent"] == [] and recorder["finish"] == []


def test_hubspot_error_is_not_sent(monkeypatch, recorder):
    monkeypatch.setattr(pipeline.store, "claim", lambda lead_id: True)

    def broken_gather(*args):
        raise hubspot.HubSpotError("401 token expired")

    monkeypatch.setattr(pipeline, "gather", broken_gather)
    result = pipeline.enrich_lead("abc123")
    assert result["status"] == "failed"
    assert recorder["sent"] == []
    assert recorder["finish"][0]["status"] == "failed"
    assert "HubSpot" in recorder["finish"][0]["error"]


def test_free_mail_without_company_is_sent_with_null_domain(monkeypatch, recorder):
    row = {**ROW, "email": "someone@gmail.com"}
    monkeypatch.setattr(pipeline.store, "get_lead", lambda lead_id: row)
    monkeypatch.setattr(pipeline.store, "claim", lambda lead_id: True)
    monkeypatch.setattr(pipeline.aiark, "person",
                        lambda *a: {"source": "aiark:person", "result": "empty", "note": "", "docs": [], "data": {"person": {}}})
    monkeypatch.setattr(pipeline.hubspot, "lookup",
                        lambda d, e: {"source": "hubspot", "result": "empty", "note": "", "docs": [],
                                      "data": {"crm": {"hubspot_company_id": None, "is_customer": False,
                                                       "is_investor": False, "open_deal_owner": None}}})
    monkeypatch.setattr(pipeline, "extract", lambda *a: pytest.fail("no company: no LLM call"))
    result = pipeline.enrich_lead("abc123")
    assert result["status"] == "sent"
    sent = recorder["sent"][0]
    assert sent["domain"] is None
    assert sent["lead"]["email"] == "someone@gmail.com"
    assert any(s["source"] == "website" and s["result"] == "skipped" for s in sent["sources_tried"])
