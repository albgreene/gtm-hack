from enrichment import doc, techstack


def vendors(text, url="https://www.telli.com/"):
    return {(c["vendor"], c["layer"]) for c in techstack.find_vendors([doc(url, "website", text)])}


def test_finds_logo_vendors():
    text = ("Model Agnostic. Built on the best AI models, never locked to one provider.\n"
            "[image] alt=ElevenLabs src=/logos/elevenlabs.svg\n[image] alt= src=/logos/cartesia-wordmark.svg")
    found = vendors(text)
    assert ("ElevenLabs", "tts") in found
    assert ("Cartesia", "tts") in found


def test_google_needs_speech_word():
    assert not vendors("We use Google Analytics and Google Tag Manager.")
    assert ("Google Cloud Speech", "tts") in vendors("Voices by Google Text-to-Speech in 40 languages.")


def test_livekit_in_job_ad():
    text = "our tech stack\nVoice and backend: Python, uv, FastAPI, LiveKit, TypeScript"
    found = vendors(text, "https://www.linkedin.com/jobs/view/4429615204")
    assert ("LiveKit", "agent_platform") in found


def test_speech_to_speech_models():
    found = vendors("we received early access to OpenAI's new GPT-Live model, a full-duplex speech-to-speech model")
    assert ("OpenAI GPT-Live", "s2s") in found


def test_snippet_is_exact_text_and_deduped():
    text = "Deepgram transcribes every call. " * 5
    candidates = techstack.find_vendors([doc("https://acme.de/", "website", text)])
    assert len([c for c in candidates if c["vendor"] == "Deepgram"]) == 1
    snippet = candidates[0]["snippet"]
    assert " ".join(snippet.split()) in " ".join(text.split())


def test_no_match_inside_words():
    assert not vendors("The vapid copy and the retelling of history.")
