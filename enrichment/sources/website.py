"""The company's own website: homepage, subprocessor/DPA and product pages, and a few voice-related posts.

Vendor logos often only show up as image alt text or file names (telli's ElevenLabs logo), so each page's
text ends with one line per image and script. Uses Firecrawl when FIRECRAWL_API_KEY is set (renders
JavaScript), otherwise a plain HTTP fetch.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

from .. import doc, net, source_result
from ..config import FIRECRAWL_URL, env
from ..techstack import VENDOR_WORDS

MAX_PAGE_CHARS = 12000
SKIP_EXT = re.compile(r"\.(png|jpe?g|gif|svg|webp|ico|css|js|mjs|json|xml|zip|mp4|mp3|wav|woff2?|ttf)(\?|$)", re.I)
# (rank, pattern): lower rank first. Subprocessor and DPA pages name voice vendors most reliably; ranks 0-3
# share a cap of MAX_PRIVACY pages, every other rank gets one page, so the picks cover different topics.
PRIORITY = [
    (0, r"sub-?processor|unterauftrag|sub-?contractor"),
    (1, r"\bdpa\b|data-processing|avv|auftragsverarbeitung"),
    (2, r"privacy|datenschutz|gdpr|dsgvo"),
    (3, r"trust|security|sicherheit|compliance"),
    (4, r"customers?|case-stud|kunden|referenz|success-stor"),
    (5, r"integration|partner|technolog|how-it-works"),
    (6, r"product|produkt|platform|plattform|feature|solution|loesung|lösung|use-?case|voice"),
    (7, r"docs|developer|api"),
]
MAX_PRIORITY, MAX_PRIVACY, MAX_DEEP = 6, 3, 4
DEEP_SECTION = re.compile(r"/(blog|articles?|news|posts?|changelog|updates|careers|jobs|press|insights|stories)/[^/]+",
                          re.I)
LOCALE_PREFIX = re.compile(r"^/(de|en|es|fr|it|nl|pt|pl|sv|da|at|ch|en-us|en-gb|de-de|de-at|de-ch)(?=/|$)", re.I)
VOICE_WORDS = r"voice|speech|tts|stt|text-to-speech|speech-to-speech|realtime|real-time|duplex|telephon|phone|" \
              r"calls?|agents?|audio|stimme|sprach"
# Announcements and posts on these topics say what a company runs on; generic SEO articles rarely do.
STRONG_WORDS = r"introduc|launch|announc|release|built|stack|infrastructure|hosting|on-?prem|self-?host|sovereign|" \
               r"gdpr|model|voices|duplex|speech-to-speech|realtime|real-time|latency"


class _PageParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "head"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base, self.depth, self.title_open = base_url, 0, False
        self.title, self.text, self.extras, self.links = "", [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self.title_open = True
        if tag in self.SKIP:
            self.depth += 1
        if tag == "script" and a.get("src"):
            self.extras.append(f"[script] src={a['src']}")
        elif tag == "img":
            alt, src = (a.get("alt") or "").strip(), (a.get("src") or a.get("data-src") or "").strip()
            if alt or src:
                self.extras.append(f"[image] alt={alt} src={src}")
        elif tag == "a" and a.get("href"):
            self.links.append(urldefrag(urljoin(self.base, a["href"].strip()))[0])
        elif tag in ("p", "div", "li", "br", "h1", "h2", "h3", "h4", "section", "tr"):
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self.title_open = False
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.title_open:
            self.title += data
        elif not self.depth and data.strip():
            self.text.append(data.strip() + " ")


def parse_html(url: str, html: str) -> dict:
    parser = _PageParser(url)
    parser.feed(html)
    body = re.sub(r"\n\s*\n+", "\n", "".join(parser.text)).strip()
    text = body[:MAX_PAGE_CHARS] + ("\n" + "\n".join(dict.fromkeys(parser.extras))[:4000] if parser.extras else "")
    return {"url": url, "title": parser.title.strip(), "text": text, "links": list(dict.fromkeys(parser.links))}


def _site_root(host: str) -> str:
    parts = host.lower().removeprefix("www.").split(".")
    return ".".join(parts[-3:]) if len(parts) > 2 and parts[-2] in ("co", "com", "org") else ".".join(parts[-2:])


def choose_pages(home_url: str, links: list[str]) -> list[str]:
    root = _site_root(urlparse(home_url).netloc)
    home = urldefrag(home_url)[0].rstrip("/")
    by_key: dict[str, str] = {}  # one URL per page, preferring the version without a /de/, /es/ … prefix
    for link in links:
        url = urldefrag(urljoin(home_url, link))[0].rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or _site_root(parsed.netloc) != root:
            continue
        if SKIP_EXT.search(parsed.path) or url == home or not parsed.path.strip("/") and parsed.netloc in home:
            continue
        key = parsed.netloc.removeprefix("www.") + LOCALE_PREFIX.sub("", parsed.path).lower()
        current = by_key.get(key)
        if current is None or (LOCALE_PREFIX.match(urlparse(current).path) and not LOCALE_PREFIX.match(parsed.path)):
            by_key[key] = url

    ranked, deep = [], []
    for url in by_key.values():
        parsed = urlparse(url)
        path = (parsed.netloc.split(".")[0] + " " + LOCALE_PREFIX.sub("", parsed.path)).lower()
        if DEEP_SECTION.search(parsed.path):
            # Score the post's own slug, each word once: section names like /ai-voice-agents/ say nothing.
            slug = parsed.path.rstrip("/").rsplit("/", 1)[-1].lower()
            strength = (len(set(re.findall(VENDOR_WORDS, slug))) * 3 + len(set(re.findall(STRONG_WORDS, slug))) * 2
                        + len(set(re.findall(VOICE_WORDS, slug))))
            if strength:
                deep.append((-strength, url))
            continue
        for rank, pattern in PRIORITY:
            if re.search(pattern, path):
                ranked.append((rank, len(url), url))
                break
    ranked.sort()
    picked, privacy, used_ranks = [], 0, set()
    for rank, _, url in ranked:
        if len(picked) >= MAX_PRIORITY:
            break
        if rank <= 3:
            if privacy >= MAX_PRIVACY:
                continue
            privacy += 1
        elif rank in used_ranks:
            continue
        used_ranks.add(rank)
        picked.append(url)
    deep.sort()
    return picked + [url for _, url in deep[:MAX_DEEP]]


def _fetch_firecrawl(url: str) -> dict:
    reply = net.post_json(f"{FIRECRAWL_URL}/scrape", {"url": url, "formats": ["markdown", "rawHtml", "links"],
                                                       "onlyMainContent": False, "timeout": 30000},
                          {"Authorization": f"Bearer {env('FIRECRAWL_API_KEY')}"}, timeout=45)
    data = (reply or {}).get("data") or {}
    final = (data.get("metadata") or {}).get("url") or (data.get("metadata") or {}).get("sourceURL") or url
    page = parse_html(final, data.get("rawHtml") or "")
    if data.get("markdown"):
        extras = page["text"].split("\n[image]", 1)
        tail = "\n[image]" + extras[1] if len(extras) > 1 else ""
        page["text"] = data["markdown"][:MAX_PAGE_CHARS] + tail
    page["links"] = list(dict.fromkeys((data.get("links") or []) + page["links"]))
    page["title"] = page["title"] or (data.get("metadata") or {}).get("title") or ""
    return page


def _fetch_plain(url: str) -> dict:
    final, body = net.get_text(url)
    return parse_html(final, body)


def _sitemap_links(home_url: str) -> list[str]:
    """URLs from /sitemap.xml (one level of sitemap index), so posts the homepage doesn't link are found too."""
    def locs(url):
        try:
            _, body = net.get_text(url, timeout=10)
        except Exception:
            return []
        return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
    found = locs(urljoin(home_url, "/sitemap.xml"))
    nested = [u for u in found if u.endswith(".xml")][:3]
    for url in nested:
        found += locs(url)
    return [u for u in found if not u.endswith(".xml")][:2000]


def scrape(domain: str) -> dict:
    fetch = _fetch_firecrawl if env("FIRECRAWL_API_KEY") else _fetch_plain
    how = "firecrawl" if fetch is _fetch_firecrawl else "plain HTTP (no FIRECRAWL_API_KEY)"
    home, errors = None, []
    for candidate in (f"https://{domain}", f"https://www.{domain}"):
        try:
            home = fetch(candidate)
            break
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
    if not home:
        return source_result(f"website:{domain}", "error", f"{how}; " + "; ".join(errors)[:400])

    links = home["links"] + _sitemap_links(home["url"])
    pages = choose_pages(home["url"], links)
    docs, failed = [doc(home["url"], "website", home["text"], home["title"])], []
    with ThreadPoolExecutor(max_workers=5) as pool:
        for url, result in zip(pages, pool.map(lambda u: _safe(fetch, u), pages)):
            if isinstance(result, dict) and result.get("text"):
                docs.append(doc(result["url"], "website", result["text"], result["title"]))
            else:
                failed.append(url)
    note = f"{how}; {len(docs)} page(s)" + (f"; failed: {', '.join(failed)[:300]}" if failed else "")
    result = "ok" if any(len(d["text"]) > 200 for d in docs) else "empty"
    return source_result(f"website:{domain}", result, note, docs=docs,
                         data={"site_name": home["title"], "home_url": home["url"], "pages": [d["url"] for d in docs]})


def _safe(fetch, url):
    try:
        return fetch(url)
    except Exception as exc:
        return str(exc)
