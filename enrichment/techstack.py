"""Find voice vendors (TTS, STT, speech-to-speech, agent platforms, telephony) named in raw documents.

Pure code, no LLM: it only finds candidates with the exact text around them. The LLM step decides which
candidates are real stack entries and how sure the source is.
"""

from __future__ import annotations

import re

# (vendor, layer, aliases, ambiguous). Ambiguous names only count with a speech word close by.
VENDORS: list[tuple[str, str, list[str], bool]] = [
    # text to speech
    ("ElevenLabs", "tts", [r"eleven\s?labs"], False),
    ("Cartesia", "tts", [r"cartesia"], False),
    ("PlayHT", "tts", [r"play\.?ht"], False),
    ("Rime", "tts", [r"rime\.ai", r"rime labs"], False),
    ("Resemble AI", "tts", [r"resemble\s?ai"], False),
    ("WellSaid Labs", "tts", [r"wellsaid"], False),
    ("LMNT", "tts", [r"lmnt"], False),
    ("Hume AI", "tts", [r"hume\s?ai", r"hume\.ai"], False),
    ("Murf", "tts", [r"murf\.ai", r"murf ai"], False),
    ("Inworld TTS", "tts", [r"inworld"], True),
    ("KugelAudio", "tts", [r"kugel\s?audio"], False),
    ("Amazon Polly", "tts", [r"amazon polly", r"aws polly", r"polly"], True),
    ("Google Cloud Speech", "tts", [r"google(?: cloud)?(?: text-to-speech| tts| speech| wavenet| chirp)"], False),
    ("Google Cloud Speech", "tts", [r"google"], True),
    ("Azure Speech", "tts", [r"azure(?: ai)?(?: speech| tts| neural voices?)", r"microsoft speech"], False),
    ("Azure Speech", "tts", [r"azure", r"microsoft"], True),
    ("OpenAI TTS", "tts", [r"openai tts", r"gpt-4o-mini-tts", r"tts-1(?:-hd)?"], False),
    # speech to text
    ("Deepgram", "stt", [r"deepgram"], False),
    ("Speechmatics", "stt", [r"speechmatics"], False),
    ("AssemblyAI", "stt", [r"assembly\s?ai"], False),
    ("Gladia", "stt", [r"gladia"], False),
    ("Rev AI", "stt", [r"rev\.ai", r"rev ai"], False),
    ("Soniox", "stt", [r"soniox"], False),
    ("OpenAI Whisper", "stt", [r"whisper"], True),
    ("Amazon Transcribe", "stt", [r"amazon transcribe", r"aws transcribe"], False),
    # speech to speech
    ("OpenAI Realtime", "s2s", [r"openai realtime", r"realtime api", r"gpt-4o-realtime", r"gpt-realtime"], False),
    ("OpenAI GPT-Live", "s2s", [r"gpt-?live"], False),
    ("Gemini Live", "s2s", [r"gemini live", r"gemini [0-9.]+ flash live"], False),
    ("Amazon Nova Sonic", "s2s", [r"nova sonic"], False),
    ("Ultravox", "s2s", [r"ultravox"], False),
    # voice agent platforms and frameworks
    ("Vapi", "agent_platform", [r"vapi"], False),
    ("Retell AI", "agent_platform", [r"retell\s?ai", r"retellai"], False),
    ("Synthflow", "agent_platform", [r"synthflow"], False),
    ("PolyAI", "agent_platform", [r"poly\s?ai"], False),
    ("Parloa", "agent_platform", [r"parloa"], False),
    ("Cognigy", "agent_platform", [r"cognigy"], False),
    ("LiveKit", "agent_platform", [r"livekit"], False),
    ("Pipecat", "agent_platform", [r"pipecat"], False),
    ("Bland AI", "agent_platform", [r"bland\s?ai", r"bland\.ai"], False),
    ("Voiceflow", "agent_platform", [r"voiceflow"], False),
    ("ElevenLabs Agents", "agent_platform", [r"elevenlabs (?:conversational ai|agents)"], False),
    # telephony
    ("Twilio", "telephony", [r"twilio"], False),
    ("Vonage", "telephony", [r"vonage"], False),
    ("Telnyx", "telephony", [r"telnyx"], False),
    ("Plivo", "telephony", [r"plivo"], False),
    ("sipgate", "telephony", [r"sipgate"], False),
    ("Placetel", "telephony", [r"placetel"], False),
    ("Asterisk", "telephony", [r"asterisk"], True),
    ("FreeSWITCH", "telephony", [r"freeswitch"], False),
    ("Kamailio", "telephony", [r"kamailio"], False),
    ("Aircall", "telephony", [r"aircall"], False),
    ("Dialpad", "telephony", [r"dialpad"], False),
    ("3CX", "telephony", [r"3cx"], False),
    ("NFON", "telephony", [r"nfon"], False),
    ("Starface", "telephony", [r"starface"], False),
    # contact centre
    ("Genesys", "contact_center", [r"genesys"], False),
    ("Five9", "contact_center", [r"five9"], False),
    ("NICE CXone", "contact_center", [r"cxone", r"nice incontact"], False),
    ("Talkdesk", "contact_center", [r"talkdesk"], False),
    ("Amazon Connect", "contact_center", [r"amazon connect"], False),
    ("Avaya", "contact_center", [r"avaya"], False),
]

SPEECH_NEAR = re.compile(r"tts|text.to.speech|speech|stt|transcri|voice|stimme|sprach|asr|neural voice|audio", re.I)
WINDOW, SNIPPET = 40, 150

# Used to rank which blog posts and pages are worth fetching.
VENDOR_WORDS = r"elevenlabs|cartesia|deepgram|vapi|retell|livekit|twilio|speechmatics|assemblyai|gladia|" \
               r"synthflow|parloa|cognigy|pipecat|polyai|sipgate|telnyx|vonage|playht|realtime|gpt-live"

_COMPILED = [(vendor, layer, re.compile(rf"(?<![a-z0-9])(?:{'|'.join(aliases)})(?![a-z0-9])", re.I), ambiguous)
             for vendor, layer, aliases, ambiguous in VENDORS]


def _snippet(text: str, start: int, end: int) -> str:
    # Start and end on whole words, so the snippet is exact text from the document (whitespace collapsed).
    left = max(0, start - SNIPPET)
    if left > 0 and not text[left - 1].isspace():
        gap = re.search(r"\s", text[left:start])
        left = left + gap.end() if gap else start
    right = min(len(text), end + SNIPPET)
    if right < len(text) and not text[right].isspace():
        gap = max(text.rfind(" ", end, right), text.rfind("\n", end, right))
        right = gap if gap > end else end
    return " ".join(text[left:right].split())


def find_vendors(docs: list[dict]) -> list[dict]:
    found, seen = [], set()
    for d in docs:
        text = d.get("text") or ""
        for vendor, layer, pattern, ambiguous in _COMPILED:
            if (vendor, d["url"]) in seen:
                continue
            for match in pattern.finditer(text):
                if ambiguous and not SPEECH_NEAR.search(text[max(0, match.start() - WINDOW):match.end() + WINDOW]):
                    continue
                seen.add((vendor, d["url"]))
                found.append({"vendor": vendor, "layer": layer, "url": d["url"], "kind": d.get("kind"),
                              "snippet": _snippet(text, match.start(), match.end())})
                break
    return found
