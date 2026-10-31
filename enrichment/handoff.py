"""Send the enriched lead to the Hermes qualify-lead webhook (contract: docs/qualify-lead-contract.md)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request

from .config import HERMES_URL, env


def encode(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send(payload: dict) -> tuple[int, dict]:
    """POST the signed lead. Returns (HTTP status, Hermes's answer). Retries a 429 twice."""
    secret = env("QUALIFY_LEAD_SECRET")
    if not secret:
        raise RuntimeError("QUALIFY_LEAD_SECRET is not set")
    body = encode(payload)
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sign(body, secret),
               "X-Request-ID": str(payload["lead"]["lead_id"])}
    for attempt in range(3):
        request = urllib.request.Request(HERMES_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, raw = response.status, response.read().decode(errors="replace")
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read().decode(errors="replace")
        if status != 429 or attempt == 2:
            break
        time.sleep(10)
    try:
        answer = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        answer = {"text": raw[:500]}
    return status, answer if isinstance(answer, dict) else {"answer": answer}
