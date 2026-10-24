"""Draws channel profile picture options and sends them to Telegram.

    python -m brainrot.logo "what the picture should show"
"""

import base64
import os
import sys
from pathlib import Path

from . import config, telegram
from .images import MODEL

DEFAULT = ("a dramatic strawberry-headed queen with a tiny golden crown and one single tear, "
           "looking shocked, with a cheeky smirk")

STYLE = ("YouTube channel profile picture, 3D animated movie style like a glossy Pixar character, "
         "anthropomorphic fruit character, head and shoulders centred, big expressive face, "
         "bold simple background in one strong colour, high contrast so it reads at tiny sizes, "
         "everything important inside the centre circle, no text, no letters, no logos.")


def main():
    idea = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or DEFAULT
    from openai import OpenAI

    client = OpenAI()
    out = Path(os.environ.get("BRAINROT_OUT", config.ROOT / "output")) / "logos"
    out.mkdir(parents=True, exist_ok=True)
    result = client.images.generate(model=MODEL, prompt=f"{STYLE} The character: {idea}.",
                                    size="1024x1024", quality="high", n=3)
    paths = []
    for i, item in enumerate(result.data):
        path = out / f"profile_option_{i + 1}.png"
        path.write_bytes(base64.b64decode(item.b64_json))
        paths.append(path)
        print(f"Saved {path}")
    if telegram.ready():
        telegram.send_files(paths, "Profile picture options. Tap one, then Save Image, then set it in YouTube.")
        print("Sent to Telegram.")


if __name__ == "__main__":
    main()
