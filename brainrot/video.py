"""Puts the video together with ffmpeg: background (gameplay clip if there is
one, otherwise a moving colour background), the characters (the speaker
jumps up front and bounces, the others wait small and dimmed at the sides),
the captions and the voices."""

import random
import subprocess

from . import config
from .cast import image_path

BIG, SMALL = 660, 340          # character sizes in pixels (talking / waiting)
BIG_Y = 340                    # top of the talking character
# Where waiting characters peek in from the screen edges: (left x, top y).
SLOTS = [(-70, 760), (config.WIDTH - SMALL + 70, 760), (config.WIDTH - SMALL + 70, 330)]

PALETTES = [
    ("0x7b2ff7", "0xf107a3", "0x00d4ff"),
    ("0xff6a00", "0xee0979", "0xffd200"),
    ("0x11998e", "0x38ef7d", "0x0575e6"),
    ("0xfc466b", "0x3f5efb", "0xf9d423"),
    ("0x8e2de2", "0x4a00e0", "0xff0080"),
    ("0xf12711", "0xf5af19", "0x2af598"),
]


def gameplay_clips():
    if not config.GAMEPLAY_DIR.exists():
        return []
    return sorted(p for p in config.GAMEPLAY_DIR.iterdir() if p.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv"))


def background_input(duration, rng):
    """ffmpeg input arguments and a filter that turns it into a 1080x1920 picture."""
    w, h = config.WIDTH, config.HEIGHT
    clips = gameplay_clips()
    if clips:
        clip = rng.choice(clips)
        length = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(clip)],
            capture_output=True, text=True, check=True).stdout.strip())
        start = rng.uniform(0, max(length - duration - 1, 0))
        args = ["-ss", f"{start:.2f}", "-stream_loop", "-1", "-i", str(clip)]
        filt = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                f"fps={config.FPS},eq=brightness=-0.06:saturation=1.1,setsar=1")
        return args, filt
    c0, c1, c2 = rng.choice(PALETTES)
    args = ["-f", "lavfi", "-i",
            f"gradients=s={w}x{h}:c0={c0}:c1={c1}:c2={c2}:n=3:speed=0.015:r={config.FPS}:d={duration:.2f}"]
    return args, "setsar=1"


def between(spans):
    return "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in spans) or "0"


def render(turns, characters, audio, ass_path, duration, out_path, seed=None):
    """turns: [(character_id, start, end)] when each character speaks."""
    rng = random.Random(seed)
    bg_args, bg_filter = background_input(duration, rng)
    args = ["ffmpeg", "-v", "error", "-y", *bg_args]
    for c in characters:
        args += ["-loop", "1", "-framerate", str(config.FPS), "-t", f"{duration:.2f}", "-i", str(image_path(c))]
    args += ["-i", str(audio)]
    audio_index = len(characters) + 1

    filters = [f"[0:v]{bg_filter},trim=duration={duration:.2f}[bg]"]
    talking = {c.id: between([(s, e) for cid, s, e in turns if cid == c.id]) for c in characters}
    for k, c in enumerate(characters):
        filters.append(f"[{k + 1}:v]format=rgba,split[big{k}][small{k}]")
        # Talking: big, centred, bouncing and wobbling.
        filters.append(
            f"[big{k}]scale={BIG}:{BIG}:force_original_aspect_ratio=decrease,"
            f"rotate='0.05*sin(2*PI*t*1.7)':c=none:ow='rotw(0.08)':oh='roth(0.08)'[b{k}]")
        # Waiting: small, a bit see-through and gently swaying.
        filters.append(
            f"[small{k}]scale={SMALL}:{SMALL}:force_original_aspect_ratio=decrease,"
            f"colorchannelmixer=aa=0.8,rotate='0.05*sin(2*PI*t*0.6+{k})':c=none:ow='rotw(0.07)':oh='roth(0.07)'[s{k}]")
    # Waiting characters first, so whoever is talking is always drawn on top.
    last = "bg"
    for k, c in enumerate(characters):
        x, y = SLOTS[k % len(SLOTS)]
        filters.append(f"[{last}][s{k}]overlay=x={x}:y='{y}+10*sin(t*2+{k})':enable='not({talking[c.id]})'[w{k}]")
        last = f"w{k}"
    for k, c in enumerate(characters):
        filters.append(
            f"[{last}][b{k}]overlay=x='(W-w)/2':y='{BIG_Y}-abs(sin(t*9))*28':enable='{talking[c.id]}'[t{k}]")
        last = f"t{k}"

    font_dir = str(config.FONT_FILE.parent)
    ass = str(ass_path).replace("\\", "/").replace(":", r"\:")
    filters.append(f"[{last}]ass='{ass}':fontsdir='{font_dir}',format=yuv420p[v]")

    args += ["-filter_complex", ";".join(filters), "-map", "[v]", "-map", f"{audio_index}:a",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "6M", "-bufsize", "12M",
             "-profile:v", "high", "-r", str(config.FPS),
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-t", f"{duration:.2f}", "-movflags", "+faststart", str(out_path)]
    subprocess.run(args, check=True)
    return out_path
