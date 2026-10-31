"""LinkedIn through Needle, read-only: the person's profile, the company page, its posts and job ads.

Needle acts as a real LinkedIn account with a daily limit (about 70-300 calls per kind), so each lead
makes at most: 1 people search, 1-2 profile views, 1 company page, 1 post list, 1 job list, 3 job ads.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .. import doc, net, source_result
from ..config import NEEDLE_ACCOUNT, NEEDLE_MCP_URL, NEEDLE_READ_TOOLS, env
from ..matching import company_matches

# Job ads name the stack ("Voice and backend: Python, FastAPI, LiveKit"): voice and engineering roles first.
JOB_TITLE_WEIGHTS = [(re.compile(r"voice|speech|audio|telephon", re.I), 4),
                     (re.compile(r"engineer|engineering|developer|\bai\b|\bml\b|machine learning|cto|backend|"
                                 r"infrastructure|platform|devops|research", re.I), 2),
                     (re.compile(r"product|solutions? architect|tech", re.I), 1)]
MAX_POSTS, MAX_JOBS = 20, 3


def job_score(title: str) -> int:
    return sum(weight for pattern, weight in JOB_TITLE_WEIGHTS if pattern.search(title or ""))


def _call(tool: str, arguments: dict):
    if tool not in NEEDLE_READ_TOOLS:  # never message, invite, react or comment with this account
        raise PermissionError(f"{tool} is not a read-only Needle tool")
    key = env("NEEDLE_API_KEY")
    if not key:
        raise RuntimeError("NEEDLE_API_KEY is not set")
    auth = key if key.lower().startswith("bearer ") else f"Bearer {key}"
    return net.mcp_call(NEEDLE_MCP_URL, {"Authorization": auth}, tool,
                        {"connectedAccountId": NEEDLE_ACCOUNT, **arguments}, timeout=60)


def _slug(url: str | None, kind: str) -> str | None:
    if not url:
        return None
    match = re.search(rf"linkedin\.com/{kind}/([^/?#]+)", url)
    return match.group(1) if match else None


def _profile_text(profile: dict) -> tuple[str, str]:
    """(text that names the person's current company, the full profile text for the LLM)."""
    current = [w for w in profile.get("workExperience") or [] if not w.get("endedOn")]
    company_text = " | ".join(filter(None, [profile.get("companyName"), profile.get("headline")] +
                                     [w.get("company") for w in current]))
    lines = [f"{profile.get('fullName')}: {profile.get('headline') or ''}",
             f"Current: {profile.get('jobTitle') or ''} at {profile.get('companyName') or ''}",
             f"Location: {profile.get('location') or ''}", f"About: {profile.get('summary') or ''}"]
    lines += [f"Experience: {w.get('position')} at {w.get('company')} since {w.get('startedOn')}: "
              f"{(w.get('description') or '')[:300]}" for w in current]
    return company_text, "\n".join(lines)


def person(first: str, last: str, domain: str | None, company_names: list[str], linkedin_url: str | None) -> dict:
    tried, candidates = [], []
    if _slug(linkedin_url, "in"):
        candidates.append(_slug(linkedin_url, "in"))
        tried.append("profile from AI Ark")
    elif first and last:
        keywords = {"firstName": first, "lastName": last}
        company_word = next((n for n in company_names if n), None) or (domain or "").split(".")[0]
        try:
            hits = (_call("needleSearchLinkedinPeopleClassic", {"advancedKeywords": keywords, "limit": 5})
                    or {}).get("hits") or []
        except (net.ToolError, net.HTTPError) as exc:
            return source_result("needle:person", "error", f"search: {str(exc)[:120]}", data={"person": {}})
        tried.append(f"search '{first} {last}': {len(hits)} hit(s)")
        by_headline = [h for h in hits if company_matches(h.get("headline") or "", domain, company_names)]
        # The headline names the company: fetch that profile. Otherwise check the top hit's current job.
        candidates = [h["publicIdentifier"] for h in (by_headline or hits)[:1] if h.get("publicIdentifier")]
        if not candidates and company_word:
            tried.append(f"no hit at {company_word}")
    if not candidates:
        return source_result("needle:person", "empty", "; ".join(tried) or "no name to search", data={"person": {}})

    identity = candidates[0]
    try:
        profile = (_call("needleGetLinkedinProfile", {"identity": identity}) or {}).get("profile") or {}
    except (net.ToolError, net.HTTPError) as exc:
        return source_result("needle:person", "error", f"profile {identity}: {str(exc)[:120]}", data={"person": {}})
    company_text, text = _profile_text(profile)
    url = f"https://www.linkedin.com/in/{profile.get('publicIdentifier') or identity}"
    if not company_matches(company_text, domain, company_names):
        note = f"profile found, different company ({company_text[:80] or 'no current company'})"
        return source_result("needle:person", "empty", "; ".join(tried + [note]), data={"person": {}})
    found = {"full_name": profile.get("fullName"), "title": profile.get("jobTitle"), "headline": profile.get("headline"),
             "linkedin_url": url, "company": profile.get("companyName")}
    return source_result("needle:person", "ok", "; ".join(tried + ["current company matches"]),
                         docs=[doc(url, "linkedin_profile", text, title=profile.get("fullName") or "")],
                         data={"person": found})


def _website_domain(website: str | None) -> str:
    host = urlparse(website or "").netloc.lower().removeprefix("www.")
    return ".".join(host.split(".")[-2:]) if host else ""


def company(domain: str | None, linkedin_url: str | None) -> dict:
    """Company page, recent posts and job ads. Without a LinkedIn URL, guess the slug and check the website."""
    identifier = _slug(linkedin_url, "company") or (domain or "").split(".")[0]
    if not identifier:
        return source_result("needle:company", "skipped", "no LinkedIn company to look up")
    try:
        page = (_call("needleGetLinkedinCompany", {"identifier": identifier}) or {}).get("company") or {}
    except (net.ToolError, net.HTTPError) as exc:
        return source_result("needle:company", "empty", f"{identifier}: {str(exc)[:120]}")
    if not _slug(linkedin_url, "company") and domain and _website_domain(page.get("website")) != domain:
        return source_result("needle:company", "empty",
                             f"guessed page '{identifier}' belongs to {page.get('website') or 'another site'}")

    slug = page.get("publicIdentifier") or identifier
    url = page.get("profileUrl") or f"https://www.linkedin.com/company/{slug}/"
    lines = [f"{page.get('name')}: {page.get('tagline') or ''}", page.get("description") or "",
             f"Industry: {', '.join(page.get('industry') or [])}", f"Employees: {page.get('employeeCount') or ''}",
             f"Headquarters: {page.get('headquarters') or ''}", f"Website: {page.get('website') or ''}"]
    docs, notes = [doc(url, "linkedin_company", "\n".join(lines), title=page.get("name") or "")], []

    try:
        posts = (_call("needleListLinkedinCompanyPosts", {"identifier": slug, "limit": MAX_POSTS}) or {}).get("posts") or []
        for post in posts:
            if post.get("text") and post.get("url"):
                author = (post.get("author") or {}).get("name") or ""
                docs.append(doc(post["url"].split("?")[0], "linkedin_post", post["text"],
                                title=f"{author}, {(post.get('postedAt') or '')[:10]}"))
        notes.append(f"{len(posts)} post(s)")
    except (net.ToolError, net.HTTPError) as exc:
        notes.append(f"posts: {str(exc)[:80]}")

    try:
        jobs = (_call("needleListLinkedinCompanyJobs", {"identifier": slug, "limit": 25}) or {}).get("jobs") or []
        if jobs:
            docs.append(doc(f"{url.rstrip('/')}/jobs/", "linkedin_jobs",
                            "\n".join(f"{j.get('title')} ({j.get('location')})" for j in jobs), title="Open jobs"))
        picked = [j for j in sorted(jobs, key=lambda j: -job_score(j.get("title"))) if job_score(j.get("title"))]
        picked = picked[:MAX_JOBS]
        for job in picked:
            try:
                full = (_call("needleGetLinkedinJob", {"jobId": str(job["id"])}) or {}).get("job") or {}
            except (net.ToolError, net.HTTPError):
                continue
            if full.get("description"):
                docs.append(doc(full.get("url") or job.get("url"), "job",
                                f"{full.get('title')}\n{full['description']}"[:12000], title=full.get("title") or ""))
        notes.append(f"{len(jobs)} job(s), {len(picked)} read in full")
    except (net.ToolError, net.HTTPError) as exc:
        notes.append(f"jobs: {str(exc)[:80]}")

    return source_result("needle:company", "ok", f"{slug}: " + ", ".join(notes), docs=docs,
                         data={"company": {"name": page.get("name"), "linkedin": url,
                                           "employees": page.get("employeeCount"),
                                           "headquarters": page.get("headquarters")}})
