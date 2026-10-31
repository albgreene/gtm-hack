import hashlib
import hmac

from enrichment import handoff


def test_signature_matches_send_lead():
    body = b'{"lead":{"lead_id":"su_1"},"domain":"smao.ai"}'
    secret = "shared-secret"
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert handoff.sign(body, secret) == expected


def test_body_is_compact_utf8():
    body = handoff.encode({"name": "Müller GmbH", "lead": {"lead_id": "x"}})
    assert body == '{"name":"Müller GmbH","lead":{"lead_id":"x"}}'.encode()
