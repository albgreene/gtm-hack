"""Who is the company, and does a profile belong to it? Used to never attach someone else's profile."""

from __future__ import annotations

import re

from .config import FREE_MAIL

LEGAL_SUFFIX_RE = re.compile(
    r"\((?:yc|y combinator)[^)]*\)|\b(?:gmbh|ag|se|kg|ug|inc|llc|ltd|limited|corp|corporation|co|sa|sas|sarl|bv|nv|"
    r"plc|oy|ab|as|spa|pty|holding|group|technologies|technology|labs)\b\.?",
    re.IGNORECASE,
)


def email_domain(email: str | None) -> str | None:
    email = (email or "").strip().lower()
    return email.rsplit("@", 1)[1] if "@" in email and email.rsplit("@", 1)[1] else None


def is_free_mail(domain: str | None) -> bool:
    return bool(domain) and domain.strip().lower() in FREE_MAIL


def normalise_name(name: str) -> str:
    return re.sub(r"\s+", " ", LEGAL_SUFFIX_RE.sub(" ", name.lower())).strip(" .,-·")


def company_tokens(domain: str | None, names: list[str]) -> list[str]:
    """The strings that identify the company: the domain's first label and the names without legal suffixes."""
    tokens = []
    if domain:
        label = domain.lower().removeprefix("www.").split(".")[0]
        tokens.append(label)
    tokens += [normalise_name(n) for n in names if n]
    # Very short tokens ("ai", "io") match inside too many words to identify anyone.
    return [t for t in dict.fromkeys(tokens) if len(t) >= 3]


def company_matches(text: str, domain: str | None, names: list[str]) -> bool:
    """True if the profile text (headline, current company) names this company."""
    text = (text or "").lower()
    for token in company_tokens(domain, names):
        # Letters may be split by a space, dot or hyphen ("Kugel Audio" for kugelaudio), but the match must
        # start and end on a word boundary, so "telli" doesn't match inside "intelligence".
        letters = [re.escape(c) for c in token.replace(" ", "")]
        pattern = r"[\s.\-]?".join(letters)
        if re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text):
            return True
    return False
