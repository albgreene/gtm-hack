"""Vercel entry point for POST /api/enrich: enrich one sign-up and hand it to the Hermes qualifier.

Called by the Supabase trigger on leads (supabase/migrations/20261031160000_create_enrichments.sql) with
{"lead_id": ...} and "Authorization: Bearer $ENRICH_WEBHOOK_SECRET". Also accepts a Supabase database
webhook body ({"record": {"id": ...}}) and can be called by hand to re-run a lead.
"""

import hmac
import os
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from enrichment.pipeline import enrich_lead  # noqa: E402

app = Flask(__name__)
# At most two leads at once: each one uses the shared LinkedIn account and several paid APIs.
SLOTS = threading.BoundedSemaphore(2)


@app.route("/api/enrich", methods=["POST"])
def enrich():
    secret = os.environ.get("ENRICH_WEBHOOK_SECRET", "")
    given = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not secret or not hmac.compare_digest(given, secret):
        return jsonify(error="unauthorized"), 401
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id") or (body.get("record") or {}).get("id")
    if not isinstance(lead_id, str) or not lead_id:
        return jsonify(error="expected {\"lead_id\": \"...\"}"), 400
    if not SLOTS.acquire(timeout=120):
        return jsonify(error="busy, try again", lead_id=lead_id), 503
    try:
        result = enrich_lead(lead_id, send=body.get("send", True) is not False)
    finally:
        SLOTS.release()
    print(f"enrich\t{lead_id}\t{result.get('status')}\t{result.get('seconds')}s", flush=True)
    return jsonify(result), 200 if result.get("status") in ("sent", "skipped") else 500
