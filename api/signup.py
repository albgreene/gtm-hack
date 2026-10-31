"""Vercel entry point for POST /api/signup.

Runs the Flask app from checkip.py as a Vercel Python function, so the sign-up
form works on the deployed site without a separate server.
"""

import os
import sys
from pathlib import Path

# Vercel's filesystem is read-only except /tmp, and /tmp does not survive between
# invocations: leads written here are not kept. Point LEADS_LOG at real storage to keep them.
os.environ.setdefault("LEADS_LOG", "/tmp/leads.jsonl")
os.environ.setdefault("VISITOR_LOG", "/tmp/visitors.csv")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from checkip import create_app  # noqa: E402

app = create_app()
