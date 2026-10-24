"""Makes short voice samples of the same dramatic line and sends them to
Telegram, so you can pick the narrator voice by ear.

    python -m brainrot.voice_samples
"""

import asyncio
import os
from pathlib import Path

from . import config, telegram

LINE = ("She poured gold on only one daughter. The other got nothing but mud. "
        "But that night... the forgotten daughter found a secret worth one billion dollars.")

DRAMATIC = ("Voice: a dramatic storyteller narrating a viral soap-opera short. "
            "Tone: emotional and gripping, building suspense. Pause before the big reveal, "
            "then hit the last words hard. Pace: fast and punchy, like a movie trailer.")

EDGE = [
    ("1 Microsoft Andrew (current)", "en-US-AndrewMultilingualNeural"),
    ("2 Microsoft Brian", "en-US-BrianMultilingualNeural"),
    ("3 Microsoft Christopher (deep)", "en-US-ChristopherNeural"),
]
OPENAI = [
    ("4 OpenAI Ash (dramatic)", "ash"),
    ("5 OpenAI Onyx (deep, dramatic)", "onyx"),
    ("6 OpenAI Ballad (emotional)", "ballad"),
    ("7 OpenAI Coral (female, dramatic)", "coral"),
]


async def edge_sample(voice, path):
    import edge_tts

    await edge_tts.Communicate(LINE, voice, rate="+8%").save(str(path))


def main():
    out = Path(os.environ.get("BRAINROT_OUT", config.ROOT / "output")) / "voices"
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for name, voice in EDGE:
        path = out / f"{name}.mp3"
        asyncio.run(edge_sample(voice, path))
        made.append((name, path))
    if os.environ.get("OPENAI_API_KEY"):
        from openai import OpenAI

        client = OpenAI()
        for name, voice in OPENAI:
            path = out / f"{name}.mp3"
            with client.audio.speech.with_streaming_response.create(
                    model="gpt-4o-mini-tts", voice=voice, input=LINE, instructions=DRAMATIC,
                    response_format="mp3") as response:
                response.stream_to_file(path)
            made.append((name, path))
    for name, path in made:
        print(f"Made {path}")
    if telegram.ready():
        telegram.send_audio(made, "Voice samples above. Reply to Claude with the number you like best.")
        print("Sent to Telegram.")


if __name__ == "__main__":
    main()
