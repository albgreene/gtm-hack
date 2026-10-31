"""Load KEY=value lines (as written by `vercel env pull`) into os.environ, without overriding what's set."""

import os
import re
from pathlib import Path


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        match = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
        if match:
            os.environ.setdefault(match.group(1), match.group(2).strip().strip('"').strip("'"))
