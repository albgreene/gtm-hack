#!/usr/bin/env python3
"""Insert a fake sign-up into Supabase leads, as the sign-up form would. Prints the new lead id.

    .venv/bin/python scripts/insert_test_lead.py --email test.lead@telli.com
    .venv/bin/python scripts/insert_test_lead.py --email you@company.com --call-me +4917612345678

The person is fake (Test Lead) and gives no call consent, so the fake number +491500000000 is never passed
on and nobody is dialed. --call-me puts your own number in with call consent: if Hermes decides "call",
Kai rings that number. The insert starts the enrichment on Vercel by itself (Supabase trigger).
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
    parser.add_argument("--call-me", metavar="PHONE", help="your own number, E.164; gives call consent")
    parser.add_argument("--country", default="DE")
    args = parser.parse_args()
    load_env(ROOT / ".env.local")

    from enrichment import net
    from enrichment.config import env

    lead_id = "test_" + os.urandom(6).hex()
    row = {"id": lead_id, "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "first_name": args.first, "last_name": args.last, "email": args.email.lower(),
           "phone": args.call_me or "+491500000000",
           "country": args.country, "locale": "de-DE", "timezone": "Europe/Berlin",
           "tos": {"accepted": True, "version": "test", "text": "test lead"},
           "call_consent": {"given": bool(args.call_me), "version": "test", "text": "test lead"},
           "data_notice": "test lead", "user_agent": "scripts/insert_test_lead.py", "ip": None}
    net.post_json(f"{env('SUPABASE_URL').rstrip('/')}/rest/v1/leads", row,
                  {"apikey": env("SUPABASE_SECRET_KEY"), "Prefer": "return=minimal"})
    print(lead_id)


if __name__ == "__main__":
    main()
