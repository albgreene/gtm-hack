"""
B2B visitor qualifier.

Captures a website visitor's IP address, looks up who owns that IP, and
classifies the visitor as:

    business   -> IP belongs to a company network (potential B2B lead)
    consumer   -> residential / mobile ISP (private person, or someone working from home)
    datacenter -> cloud / hosting IP (bots, scrapers, crawlers)
    vpn_proxy  -> anonymising VPN / proxy / Tor
    unknown    -> private IP, lookup failed, etc.

Usage
-----
  CLI (test single IPs):
      python visitor_check.py 8.8.8.8 17.253.144.10

  Web server (receive visits from your website):
      pip install flask
      python visitor_check.py --serve --port 5000

  Then add this to your website (or call /track from your backend):
      <script>fetch("https://your-server.example.com/track?page=" + encodeURIComponent(location.pathname));</script>

Optional: set IPINFO_TOKEN (https://ipinfo.io) for better company detection.
Without it, the free ip-api.com endpoint is used (45 requests/min, no key).
"""

from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

IPINFO_TOKEN = os.environ.get("IPINFO_TOKEN", "")
LOG_FILE = Path(os.environ.get("VISITOR_LOG", "visitors.csv"))
CACHE_TTL = 24 * 3600  # seconds

# Names of ISPs that mostly serve households / mobile users.
# Extend this for the markets you sell in.
CONSUMER_ISP_KEYWORDS = [
    # DACH
    "deutsche telekom", "telekom", "vodafone", "1&1", "1und1", "o2", "telefonica",
    "unitymedia", "kabel deutschland", "netcologne", "m-net", "ewe tel", "pyur",
    "tele columbus", "congstar", "a1 telekom", "magenta", "swisscom", "sunrise",
    "salt mobile", "upc", "drei", "hutchison",
    # Rest of Europe
    "orange", "free sas", "sfr", "bouygues", "proximus", "kpn", "ziggo", "telia",
    "telenor", "elisa", "british telecom", "bt public internet", "sky broadband",
    "virgin media", "talktalk", "ee limited", "movistar", "tim ", "telecom italia",
    "fastweb", "wind tre", "iliad", "digi ", "play ", "netia", "orange polska",
    # North America
    "comcast", "xfinity", "charter", "spectrum", "verizon", "at&t", "cox comm",
    "centurylink", "lumen", "frontier", "t-mobile", "sprint", "optimum", "altice",
    "rogers", "bell canada", "shaw comm", "videotron", "telus", "mediacom",
    "windstream", "suddenlink", "starlink", "spacex",
    # APAC / other
    "telstra", "optus", "tpg", "ntt", "kddi", "softbank", "chinanet", "china unicom",
    "china mobile", "reliance jio", "bharti airtel", "singtel", "starhub",
]

DATACENTER_KEYWORDS = [
    "amazon", "aws", "google cloud", "google llc", "microsoft", "azure",
    "digitalocean", "linode", "akamai", "ovh", "hetzner", "contabo", "vultr",
    "oracle cloud", "alibaba", "tencent", "cloudflare", "fastly", "leaseweb",
    "scaleway", "ionos", "strato", "choopa", "m247", "hosting", "datacenter",
    "data center", "server", "colo",
]

COMPANY_SUFFIX_RE = re.compile(
    r"\b(gmbh|ag|se|kg|ug|inc|llc|ltd|limited|corp|corporation|co\.|s\.a\.|"
    r"sa|sas|sarl|bv|b\.v\.|nv|plc|oy|ab|as|spa|s\.p\.a\.|pty|holding|group)\b",
    re.IGNORECASE,
)
EDU_GOV_RE = re.compile(r"\b(universit|college|school|hochschule|institut|government|ministry|bundes|city of)\w*", re.I)


@dataclass
class VisitorResult:
    ip: str
    category: str = "unknown"
    is_potential_customer: bool = False
    confidence: str = "low"
    company: str | None = None
    isp: str | None = None
    asn: str | None = None
    country: str | None = None
    city: str | None = None
    signal: str = "nosignal"  # signal / nosignal / invalidip
    reasons: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# IP lookup
# --------------------------------------------------------------------------- #

_cache: dict[str, tuple[float, dict]] = {}


def _get_json(url: str, timeout: float = 4.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "b2b-visitor-check/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def lookup_ip(ip: str) -> dict:
    """Return normalised owner info for an IP (cached)."""
    now = time.time()
    if ip in _cache and now - _cache[ip][0] < CACHE_TTL:
        return _cache[ip][1]

    data: dict = {}
    if IPINFO_TOKEN:
        raw = _get_json(f"https://ipinfo.io/{ip}/json?token={IPINFO_TOKEN}")
        company = raw.get("company") or {}
        privacy = raw.get("privacy") or {}
        asn = raw.get("asn") or {}
        org = raw.get("org", "")  # e.g. "AS3320 Deutsche Telekom AG"
        data = {
            "org": company.get("name") or re.sub(r"^AS\d+\s+", "", org),
            "isp": asn.get("name") or re.sub(r"^AS\d+\s+", "", org),
            "asn": asn.get("asn") or (org.split()[0] if org.startswith("AS") else None),
            "company_type": company.get("type"),  # business / isp / hosting / education
            "asn_type": asn.get("type"),
            "hosting": privacy.get("hosting", False),
            "proxy": any(privacy.get(k) for k in ("vpn", "proxy", "tor", "relay")),
            "mobile": bool(raw.get("carrier")),
            "country": raw.get("country"),
            "city": raw.get("city"),
        }
    else:
        fields = "status,message,country,city,isp,org,as,asname,mobile,proxy,hosting,query"
        raw = _get_json(f"http://ip-api.com/json/{ip}?fields={fields}")
        if raw.get("status") != "success":
            raise RuntimeError(raw.get("message", "lookup failed"))
        data = {
            "org": raw.get("org") or "",
            "isp": raw.get("isp") or "",
            "asn": (raw.get("as") or "").split(" ")[0] or None,
            "company_type": None,
            "asn_type": None,
            "hosting": raw.get("hosting", False),
            "proxy": raw.get("proxy", False),
            "mobile": raw.get("mobile", False),
            "country": raw.get("country"),
            "city": raw.get("city"),
        }

    _cache[ip] = (now, data)
    return data


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #

def _matches(text: str, keywords: list[str]) -> bool:
    t = f" {text.lower()} "
    return any(k in t for k in keywords)


def _normalise(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", COMPANY_SUFFIX_RE.sub("", name.lower()))


def classify(ip: str) -> VisitorResult:
    res = VisitorResult(ip=ip)

    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        res.signal = "invalidip"
        res.reasons.append("invalid IP address")
        return res
    if not addr.is_global:
        res.signal = "invalidip"
        res.reasons.append("private/local IP (are you behind a proxy? see TRUSTED_PROXY)")
        return res

    try:
        info = lookup_ip(ip)
    except Exception as exc:  # network error, rate limit, ...
        res.reasons.append(f"lookup failed: {exc}")
        return res

    org, isp = info["org"] or "", info["isp"] or ""
    res.isp, res.asn = isp, info["asn"]
    res.country, res.city = info["country"], info["city"]

    # 1) Strong signal from ipinfo's company classification (paid tiers)
    ctype = info.get("company_type")
    if ctype == "business":
        res.category, res.confidence = "business", "high"
        res.reasons.append("ipinfo marks IP range as owned by a business")
    elif ctype == "education":
        res.category, res.confidence = "business", "medium"
        res.reasons.append("education / research institution")
    elif ctype == "hosting" or info["hosting"]:
        res.category, res.confidence = "datacenter", "high"
        res.reasons.append("IP belongs to a hosting / cloud provider (likely bot)")

    if res.category != "unknown":
        pass  # already decided above
    elif info["proxy"]:
        res.category, res.confidence = "vpn_proxy", "medium"
        res.reasons.append("VPN / proxy / Tor detected – real origin hidden")
    elif info["mobile"]:
        res.category, res.confidence = "consumer", "medium"
        res.reasons.append("mobile carrier network")
    elif _matches(org, DATACENTER_KEYWORDS):
        res.category, res.confidence = "datacenter", "medium"
        res.reasons.append(f"org '{org}' looks like a hosting provider")
    else:
        # 2) Heuristics on org vs. ISP names
        org_is_consumer_isp = _matches(org, CONSUMER_ISP_KEYWORDS)
        org_differs_from_isp = org and _normalise(org) != _normalise(isp)

        if org and not org_is_consumer_isp and org_differs_from_isp:
            # The ISP has delegated this block to a named customer -> a company
            res.category = "business"
            res.confidence = "high" if COMPANY_SUFFIX_RE.search(org) else "medium"
            res.reasons.append(f"IP block registered to '{org}' (not the ISP '{isp}')")
        elif org and not org_is_consumer_isp and not _matches(isp, CONSUMER_ISP_KEYWORDS):
            # Company runs its own network/ASN (e.g. large enterprises)
            res.category, res.confidence = "business", "medium"
            res.reasons.append(f"'{org}' operates its own network")
        elif org_is_consumer_isp or _matches(isp, CONSUMER_ISP_KEYWORDS):
            res.category, res.confidence = "consumer", "medium"
            res.reasons.append(f"residential/consumer ISP '{isp or org}'")
        else:
            res.reasons.append("no clear signal")

    if res.category == "business":
        res.company = org or None
        if EDU_GOV_RE.search(org):
            res.reasons.append("public / education sector")

    res.signal = "nosignal" if res.category == "unknown" else "signal"
    res.is_potential_customer = res.category == "business"
    return res


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

def log_visit(result: VisitorResult, page: str = "", user_agent: str = "") -> None:
    new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "ip", "category", "potential_customer", "confidence",
                        "company", "isp", "asn", "country", "city", "page", "user_agent", "reasons"])
        w.writerow([
            datetime.now(timezone.utc).isoformat(timespec="seconds"), result.ip, result.category,
            result.is_potential_customer, result.confidence, result.company or "", result.isp or "",
            result.asn or "", result.country or "", result.city or "", page, user_agent,
            "; ".join(result.reasons),
        ])


def format_result(result: VisitorResult) -> str:
    status = "lead" if result.is_potential_customer else "nolead"
    return f"{status}\t{result.signal}\t{result.ip}\t{result.company or '-'}"


# --------------------------------------------------------------------------- #
# Web server
# --------------------------------------------------------------------------- #

def create_app():
    from flask import Flask, jsonify, request

    app = Flask(__name__)
    trust_proxy = os.environ.get("TRUSTED_PROXY", "1") == "1"

    def client_ip() -> str:
        # Behind nginx / Cloudflare / a load balancer the real IP is in a header.
        # Only trust these headers if your server really sits behind such a proxy.
        if trust_proxy:
            for header in ("CF-Connecting-IP", "X-Real-IP"):
                if request.headers.get(header):
                    return request.headers[header].strip()
            xff = request.headers.get("X-Forwarded-For")
            if xff:
                return xff.split(",")[0].strip()
        return request.remote_addr or ""

    @app.after_request
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = os.environ.get("ALLOWED_ORIGIN", "*")
        return resp

    @app.route("/track")
    def track():
        result = classify(client_ip())
        log_visit(result, page=request.args.get("page", ""),
                  user_agent=request.headers.get("User-Agent", ""))
        print(format_result(result), flush=True)
        return jsonify(asdict(result))

    @app.route("/check/<ip>")
    def check(ip):
        return jsonify(asdict(classify(ip)))

    return app


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main() -> None:
    p = argparse.ArgumentParser(description="Classify website visitors as business or consumer by IP.")
    p.add_argument("ips", nargs="*", help="IP addresses to check")
    p.add_argument("--serve", action="store_true", help="run the tracking web server")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=5000)
    args = p.parse_args()

    if args.serve:
        create_app().run(host=args.host, port=args.port)
        return
    if not args.ips:
        p.print_help()
        sys.exit(1)

    for ip in args.ips:
        print(format_result(classify(ip)))


if __name__ == "__main__":
    main()
