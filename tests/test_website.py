from enrichment.sources import website


def test_choose_pages_priority():
    home = "https://www.telli.com/"
    links = [
        "https://www.telli.com/pricing",
        "https://www.telli.com/blog",
        "https://www.telli.com/articles/introducing-telli-duo-agents",
        "https://www.telli.com/careers",
        "https://www.telli.com/legal/subprocessors",
        "https://www.telli.com/integrations",
        "https://www.telli.com/#features",
        "https://twitter.com/telli",
        "https://www.linkedin.com/company/tellitechnologies",
        "https://www.telli.com/logo.png",
        "mailto:hi@telli.com",
    ]
    pages = website.choose_pages(home, links)
    assert pages[0] == "https://www.telli.com/legal/subprocessors"
    assert "https://www.telli.com/articles/introducing-telli-duo-agents" in pages
    assert "https://www.telli.com/integrations" in pages
    assert not any("twitter.com" in p or "linkedin.com" in p or p.endswith(".png") for p in pages)
    assert len(pages) <= 10
    assert len(pages) == len(set(pages))


def test_choose_pages_skips_translations_and_prefers_announcements():
    home = "https://www.telli.com/"
    links = ["/de/articles/introducing-telli-duo-agents", "/articles/introducing-telli-duo-agents",
             "/es/articles/introducing-eu-hosting", "/articles/introducing-eu-hosting",
             "/ai-voice-agents/article/ai-voice-agent-vs-ivr", "/ai-voice-agents/article/prompt-engineering-for-ai-voice-agents",
             "/articles/telli-opens-an-office-in-france", "/articles/personal-agents-are-here",
             "/articles/introducing-telli-voices", "/de/data-privacy", "/data-privacy", "/customers/sky", "/customers"]
    pages = website.choose_pages(home, links)
    assert "https://www.telli.com/articles/introducing-telli-duo-agents" in pages
    assert "https://www.telli.com/articles/introducing-eu-hosting" in pages
    assert "https://www.telli.com/articles/introducing-telli-voices" in pages
    assert not any("/de/" in p or "/es/" in p for p in pages)
    assert "https://www.telli.com/data-privacy" in pages
    assert "https://www.telli.com/customers" in pages
    assert "https://www.telli.com/articles/telli-opens-an-office-in-france" not in pages


def test_choose_pages_accepts_relative_links_and_subdomains():
    pages = website.choose_pages("https://acme.de", ["/datenschutz", "https://docs.acme.de/voice-api", "/impressum"])
    assert "https://acme.de/datenschutz" in pages
    assert "https://docs.acme.de/voice-api" in pages


def test_html_to_doc_keeps_logo_alt():
    html = """<html><head><title>telli</title><script src="https://cdn.vapi.ai/widget.js"></script>
    <style>.x{}</style></head><body><h1>Model Agnostic</h1><p>Built on the best AI models.</p>
    <img alt="ElevenLabs logo" src="/l/elevenlabs.svg"><img src="/l/cartesia-wordmark.svg">
    <a href="/legal/subprocessors">Subprocessors</a></body></html>"""
    page = website.parse_html("https://www.telli.com/", html)
    assert page["title"] == "telli"
    assert "Model Agnostic" in page["text"]
    assert "ElevenLabs" in page["text"]
    assert "cartesia-wordmark.svg" in page["text"]
    assert "cdn.vapi.ai/widget.js" in page["text"]
    assert ".x{}" not in page["text"]
    assert "https://www.telli.com/legal/subprocessors" in page["links"]
