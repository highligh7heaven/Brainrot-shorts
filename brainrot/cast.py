"""Voices for the narrator and the characters.

Characters are invented fresh for each story (fruit and food people), so the
story only says what kind of voice each one has; this file turns that into a
real Microsoft Edge voice.
"""

from dataclasses import dataclass

NARRATOR = ("en-US-AndrewMultilingualNeural", "+8%", "-2Hz")

# kind of voice -> (Edge voice, speed, pitch)
VOICES = {
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
VOICE_KINDS = list(VOICES)


@dataclass(frozen=True)
class Speaker:
    id: str
    name: str
    voice: str
    rate: str
    pitch: str


def narrator():
    voice, rate, pitch = NARRATOR
    return Speaker("narrator", "Narrator", voice, rate, pitch)


def speaker_for(character):
    voice, rate, pitch = VOICES.get(character.get("voice"), VOICES["man"])
    return Speaker(character["id"], character["name"], voice, rate, pitch)
