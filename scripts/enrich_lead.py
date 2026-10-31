#!/usr/bin/env python3
"""Run the enrichment for one lead from your machine, with the keys in .env.local.

    .venv/bin/python scripts/enrich_lead.py <lead_id>            # enrich and send to Hermes
    .venv/bin/python scripts/enrich_lead.py <lead_id> --no-send  # enrich only; payload saved in Supabase
    .venv/bin/python scripts/enrich_lead.py <lead_id> --rerun    # allow a lead that was already sent

The payload is printed and also stored in the Supabase table enrichments.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.envfile import load_env  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lead_id")
    parser.add_argument("--no-send", action="store_true", help="don't send to Hermes")
    parser.add_argument("--rerun", action="store_true", help="reset the lead's enrichment row first")
    args = parser.parse_args()
    load_env(ROOT / ".env.local")

    from enrichment import store
    from enrichment.pipeline import enrich_lead

    if args.rerun and store.get_enrichment(args.lead_id):
        store.finish(args.lead_id, status="failed", error="reset for a re-run")
    result = enrich_lead(args.lead_id, send=not args.no_send)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    row = store.get_enrichment(args.lead_id) or {}
    out = ROOT / ".context" / f"enrichment-{args.lead_id}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(row.get("payload"), ensure_ascii=False, indent=2))
    print(f"payload written to {out}")


if __name__ == "__main__":
    main()
