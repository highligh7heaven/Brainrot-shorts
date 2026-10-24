"""Turns each line of the script into speech, with the time each word is said
(needed for word-by-word captions)."""

import asyncio
import re
import subprocess
from dataclasses import dataclass, field, replace

from . import config

# How each kind of delivery changes the character's normal voice.
DELIVERY = {
    "normal": (0, 0, 0),     # (rate %, pitch Hz, volume %)
    "shout": (8, 12, 15),
    "whisper": (-8, -4, -25),
    "fast": (18, 4, 0),
    "sad": (-12, -10, -5),
}


@dataclass
class Clip:
    path: str
    duration: float
    words: list = field(default_factory=list)   # [(word, start, end)] in seconds


def _num(value):
    return int(re.sub(r"[^\d-]", "", value) or 0)


def prosody(character, delivery):
    rate, pitch, volume = DELIVERY.get(delivery, DELIVERY["normal"])
    rate += _num(character.rate)
    pitch += _num(character.pitch)
    return f"{rate:+d}%", f"{pitch:+d}Hz", f"{volume:+d}%"


def duration_of(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def to_wav(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "48000", str(dst)], check=True)


def spread_words(text, duration, lead=0.05):
    """Even word timings by length, for voices that don't report them."""
    words = text.split()
    weights = [len(w) + 2 for w in words]
    total = sum(weights) or 1
    t, out = lead, []
    usable = max(duration - lead * 2, 0.1)
    for w, wt in zip(words, weights):
        span = usable * wt / total
        out.append((w, t, t + span))
        t += span
    return out


async def _edge(text, voice, rate, pitch, volume, mp3):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume,
                                       boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append((chunk["text"], start, start + chunk["duration"] / 1e7))
    return words


FALLBACK_VOICE = "en-US-AndrewMultilingualNeural"
_available = None


def available_voices():
    """Names of the voices Microsoft offers right now (empty if the list can't be read)."""
    global _available
    if _available is None:
        import edge_tts

        try:
            _available = {v["ShortName"] for v in asyncio.run(edge_tts.list_voices())}
        except Exception:
            _available = set()
    return _available


def speak_edge(text, character, delivery, stem):
    rate, pitch, volume = prosody(character, delivery)
    voice = character.voice
    known = available_voices()
    if known and voice not in known:
        print(f"Voice {voice} isn't offered by Microsoft any more; using {FALLBACK_VOICE}.")
        voice = FALLBACK_VOICE
    mp3, wav = f"{stem}.mp3", f"{stem}.wav"
    # Try the chosen voice, then the same voice without speed/pitch changes, then a safe voice.
    attempts = [(voice, rate, pitch, volume), (voice, rate, pitch, volume),
                (voice, "+0%", "+0Hz", "+0%"), (FALLBACK_VOICE, "+0%", "+0Hz", "+0%")]
    last = None
    for v, r, p, vol in attempts:
        try:
            words = asyncio.run(_edge(text, v, r, p, vol, mp3))
            to_wav(mp3, wav)
            duration = duration_of(wav)
            return Clip(wav, duration, words or spread_words(text, duration))
        except Exception as e:
            last = e
            print(f"Voice {v} ({r}, {p}) failed on {text!r}: {e}")
    raise RuntimeError(f"The Microsoft voice service didn't answer ({last}).")


def speak_espeak(text, character, delivery, stem):
    rate, pitch, _ = prosody(character, delivery)
    speed = int(175 * (1 + _num(rate) / 100))
    wav_raw, wav = f"{stem}.raw.wav", f"{stem}.wav"
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", str(speed), "-p", str(50 + _num(pitch)),
                    "-w", wav_raw, text], check=True)
    to_wav(wav_raw, wav)
    duration = duration_of(wav)
    return Clip(wav, duration, spread_words(text, duration))


ACTING = {
    "normal": "",
    "shout": " Say this line loudly and angrily, almost shouting.",
    "whisper": " Whisper this line, secretive and tense.",
    "fast": " Say this line quickly and excitedly.",
    "sad": " Say this line sadly, close to tears.",
}


def word_times(client, path):
    """Asks OpenAI's speech-to-text when each word is said (about $0.006 a minute)."""
    with open(path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1", file=f, response_format="verbose_json", timestamp_granularities=["word"])
    return [(w.word, w.start, w.end) for w in (result.words or [])]


def speak_openai(text, character, delivery, stem):
    from openai import OpenAI

    client = OpenAI()
    mp3, wav = f"{stem}.mp3", f"{stem}.wav"
    with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts", voice=character.voice, input=text,
            instructions=character.style + ACTING.get(delivery, ""),
            speed=float(character.rate or 1.0), response_format="mp3") as response:
        response.stream_to_file(mp3)
    to_wav(mp3, wav)
    duration = duration_of(wav)
    try:
        words = word_times(client, wav)
    except Exception as e:
        print(f"Word timing failed ({e}); spreading words evenly instead.")
        words = []
    return Clip(wav, duration, words or spread_words(text, duration))


def speak(text, character, delivery, stem):
    if config.VOICE_ENGINE == "espeak":
        return speak_espeak(text, character, delivery, stem)
    if character.engine == "openai":
        try:
            return speak_openai(text, character, delivery, stem)
        except Exception as e:
            print(f"OpenAI voice {character.voice} failed ({e}); using a Microsoft voice for this line.")
            character = replace(character, voice=FALLBACK_VOICE, rate="+8%", pitch="+0Hz", engine="edge")
    return speak_edge(text, character, delivery, stem)
