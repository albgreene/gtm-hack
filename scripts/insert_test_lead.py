#!/usr/bin/env python3
"""Insert a fake sign-up into Supabase leads, as the sign-up form would. Prints the new lead id.

    .venv/bin/python scripts/insert_test_lead.py --email test.lead@telli.com
    .venv/bin/python scripts/insert_test_lead.py --email someone@gmail.com --no-call-consent

The person is fake (Test Lead, +491500000000). If the Supabase trigger is configured, the insert starts the
enrichment on Vercel by itself.
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.envfile import load_env  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--first", default="Test")
    parser.add_argument("--last", default="Lead")
    parser.add_argument("--phone", default="+491500000000")
    parser.add_argument("--country", default="DE")
    parser.add_argument("--no-call-consent", action="store_true")
    args = parser.parse_args()
    load_env(ROOT / ".env.local")

    from enrichment import net
    from enrichment.config import env

    lead_id = "test_" + os.urandom(6).hex()
    row = {"id": lead_id, "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "first_name": args.first, "last_name": args.last, "email": args.email.lower(), "phone": args.phone,
           "country": args.country, "locale": "de-DE", "timezone": "Europe/Berlin",
           "tos": {"accepted": True, "version": "test", "text": "test lead"},
           "call_consent": {"given": not args.no_call_consent, "version": "test", "text": "test lead"},
           "data_notice": "test lead", "user_agent": "scripts/insert_test_lead.py", "ip": None}
    net.post_json(f"{env('SUPABASE_URL').rstrip('/')}/rest/v1/leads", row,
                  {"apikey": env("SUPABASE_SECRET_KEY"), "Prefer": "return=minimal"})
    print(lead_id)


if __name__ == "__main__":
    main()
