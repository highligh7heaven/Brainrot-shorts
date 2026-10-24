"""Voices for the narrator and the characters.

Each video picks one of several narrators at random, so the channel doesn't
sound the same every time. If the narrator is an OpenAI voice, the
characters get OpenAI voices too (they can act: shout, whisper, cry);
otherwise they get Microsoft Edge voices. Characters are invented fresh for
each story, so the story only says what kind of voice each one has.
"""

import random
from dataclasses import dataclass

# (engine, voice, speed, Edge pitch)
NARRATORS = [
    ("edge", "en-US-AndrewMultilingualNeural", "+8%", "-2Hz"),
    ("edge", "en-US-BrianMultilingualNeural", "+8%", "+0Hz"),
    ("edge", "en-US-ChristopherNeural", "+6%", "-2Hz"),
    ("openai", "ash", "1.05", ""),
    ("openai", "onyx", "1.05", ""),
    ("openai", "ballad", "1.05", ""),
    ("openai", "coral", "1.05", ""),
]

NARRATOR_STYLE = ("A dramatic storyteller narrating a viral soap-opera short. Emotional and gripping, "
                  "building suspense, pausing briefly before reveals and hitting the key words hard. "
                  "Fast and punchy, like a movie trailer.")

# kind of voice -> (Edge voice, speed, pitch)
EDGE_VOICES = {
    "man": ("en-US-GuyNeural", "+8%", "+0Hz"),
    "deep_man": ("en-US-ChristopherNeural", "+4%", "-6Hz"),
    "old_man": ("en-US-RogerNeural", "+0%", "-4Hz"),
    "italian_man": ("it-IT-GiuseppeMultilingualNeural", "+8%", "+0Hz"),
    "woman": ("en-US-AvaMultilingualNeural", "+8%", "+0Hz"),
    "posh_woman": ("en-GB-SoniaNeural", "+6%", "+0Hz"),
    "old_woman": ("en-US-EmmaMultilingualNeural", "-4%", "-8Hz"),
    "girl": ("en-US-AnaNeural", "+6%", "+0Hz"),
    "boy": ("en-GB-MaisieNeural", "+6%", "-6Hz"),
}

# kind of voice -> (OpenAI voice, how to play the part)
OPENAI_VOICES = {
    "man": ("echo", "a regular grown man"),
    "deep_man": ("onyx", "a powerful man with a deep, intimidating voice"),
    "old_man": ("fable", "a wise, slightly shaky old man"),
    "italian_man": ("verse", "a passionate man with a light Italian accent"),
    "woman": ("nova", "a confident young woman"),
    "posh_woman": ("shimmer", "a snobby, rich, posh woman"),
    "old_woman": ("sage", "a warm but sharp-tongued grandmother"),
    "girl": ("coral", "a young girl, sweet and emotional"),
    "boy": ("alloy", "a cheeky young boy"),
}
VOICE_KINDS = list(EDGE_VOICES)


@dataclass(frozen=True)
class Speaker:
    id: str
    name: str
    voice: str
    rate: str
    pitch: str
    engine: str = "edge"     # "edge" or "openai"
    style: str = ""          # how an OpenAI voice should play the part


def pick_narrator(rng=random):
    return rng.randrange(len(NARRATORS))


def speakers_for(story):
    """Everyone who talks in this story, with the voice they'll use."""
    engine, voice, rate, pitch = NARRATORS[story.get("narrator", 0) % len(NARRATORS)]
    out = {"narrator": Speaker("narrator", "Narrator", voice, rate, pitch, engine, NARRATOR_STYLE)}
    for c in story["characters"]:
        kind = c.get("voice") if c.get("voice") in EDGE_VOICES else "man"
        if engine == "openai":
            v, part = OPENAI_VOICES[kind]
            out[c["id"]] = Speaker(c["id"], c["name"], v, "1.05", "", "openai",
                                   f"You are {c['name']}, {part}, in a dramatic soap-opera short. "
                                   "Act the line with real emotion, don't just read it.")
        else:
            v, r, p = EDGE_VOICES[kind]
            out[c["id"]] = Speaker(c["id"], c["name"], v, r, p)
    return out
