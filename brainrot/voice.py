"""Turns each line of the script into speech, with the time each word is said
(needed for word-by-word captions)."""

import asyncio
import re
import subprocess
from dataclasses import dataclass, field

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


def speak_edge(text, character, delivery, stem):
    rate, pitch, volume = prosody(character, delivery)
    mp3, wav = f"{stem}.mp3", f"{stem}.wav"
    last = None
    for attempt in range(3):
        try:
            words = asyncio.run(_edge(text, character.voice, rate, pitch, volume, mp3))
            to_wav(mp3, wav)
            duration = duration_of(wav)
            return Clip(wav, duration, words or spread_words(text, duration))
        except Exception as e:   # network hiccups: try again
            last = e
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


def speak(text, character, delivery, stem):
    if config.VOICE_ENGINE == "espeak":
        return speak_espeak(text, character, delivery, stem)
    return speak_edge(text, character, delivery, stem)
