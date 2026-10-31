"""Vercel entry point for POST /api/signup.

Runs the Flask app from checkip.py as a Vercel Python function, so the sign-up
form works on the deployed site without a separate server.
"""

import os
import sys
from pathlib import Path

# Leads go to Supabase (SUPABASE_URL + SUPABASE_SECRET_KEY, set in the Vercel project).
# Without those they fall back to /tmp, the only writable path on Vercel, which is not kept.
os.environ.setdefault("LEADS_LOG", "/tmp/leads.jsonl")
os.environ.setdefault("VISITOR_LOG", "/tmp/visitors.csv")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from checkip import create_app  # noqa: E402

app = create_app()
