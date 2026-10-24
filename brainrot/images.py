"""Makes the pictures for each scene.

First one reference picture per character, then each scene is drawn with
those references attached, so a character looks the same in every scene.
Needs the OPENAI_API_KEY secret; without it, plain stand-in cards are drawn
so the rest of the system can still be tested.
"""

import base64
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

from . import config
from .story import IMAGE_STYLE

MODEL = os.environ.get("IMAGE_MODEL") or "gpt-image-1-mini"
QUALITY = os.environ.get("IMAGE_QUALITY") or "medium"   # low | medium | high
SIZE = "1024x1536"


def has_key():
    return bool(os.environ.get("OPENAI_API_KEY"))


def _save(result, path):
    path.write_bytes(base64.b64decode(result.data[0].b64_json))
    return path


def character_prompt(c):
    return (f"{IMAGE_STYLE} Character reference: full body, standing, facing the camera, "
            f"plain soft grey studio background. {c['name']}: {c['look']}.")


def scene_prompt(scene, characters):
    cast = " ".join(f"{c['id']} is {c['name']}: {c['look']}." for c in characters
                    if c["id"] in scene["image"])
    return f"{IMAGE_STYLE} Scene: {scene['image']}. {cast} Keep each character exactly as in the reference pictures."


def make_images(story, workdir):
    """Returns one picture path per scene."""
    workdir.mkdir(parents=True, exist_ok=True)
    if not has_key():
        return [placeholder(scene, i, workdir) for i, scene in enumerate(story["scenes"])]

    from openai import OpenAI

    client = OpenAI()
    refs = {}
    for c in story["characters"]:
        path = workdir / f"ref_{c['id']}.png"
        refs[c["id"]] = _save(client.images.generate(
            model=MODEL, prompt=character_prompt(c), size=SIZE, quality=QUALITY), path)

    paths = []
    for i, scene in enumerate(story["scenes"]):
        path = workdir / f"scene{i:02d}.png"
        in_scene = [refs[cid] for cid in refs if cid in scene["image"]]
        prompt = scene_prompt(scene, story["characters"])
        try:
            if in_scene:
                files = [open(p, "rb") for p in in_scene]
                try:
                    result = client.images.edit(model=MODEL, image=files, prompt=prompt, size=SIZE, quality=QUALITY)
                finally:
                    for f in files:
                        f.close()
            else:
                result = client.images.generate(model=MODEL, prompt=prompt, size=SIZE, quality=QUALITY)
            paths.append(_save(result, path))
        except Exception as e:
            # A refused or failed picture shouldn't sink the whole video: reuse the last one.
            print(f"Scene {i + 1} picture failed ({e}); reusing the previous picture.")
            if not paths:
                raise
            paths.append(paths[-1])
    return paths


def placeholder(scene, i, workdir):
    """A plain card with the scene description, for testing."""
    w, h = 1024, 1536
    img = Image.new("RGB", (w, h), (40 + i * 25 % 120, 30, 70 + i * 40 % 150))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(config.FONT_FILE), 56)
    text = textwrap.fill(f"SCENE {i + 1}: {scene['image']}", 28)
    d.multiline_text((60, 300), text, font=font, fill="white", spacing=14)
    path = workdir / f"scene{i:02d}.png"
    img.save(path)
    return path
