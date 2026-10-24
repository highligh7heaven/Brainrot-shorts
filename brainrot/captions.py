"""Builds the .ass subtitle file burned into the video: big bold word-by-word
captions in the middle (the spoken word lights up and pops), the speaker's
name above them, and the title at the top."""

import re

from . import config

WHITE = "&H00FFFFFF"
YELLOW = "&H0000F0FF"     # ASS colours are written blue-green-red
BLACK = "&H00000000"

MAX_WORDS = 3
MAX_CHUNK = 1.25
CAPTION_Y = 1240
NAME_Y = 1085
TITLE_Y = 150


def ass_time(seconds):
    cs = int(round(max(seconds, 0) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_colour(hex_rgb):
    h = hex_rgb.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def clean(text):
    return re.sub(r"[{}\\]", "", text).strip()


def chunks(words):
    """Groups words into 1-3 word bites, like popular Shorts captions."""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= MAX_WORDS or w[2] - cur[0][1] > MAX_CHUNK):
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?,]$", w[0]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def header():
    font = config.FONT_NAME
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {config.WIDTH}
PlayResY: {config.HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},136,{WHITE},{WHITE},{BLACK},&H80000000,0,0,0,0,100,100,2,0,1,9,4,5,60,60,0,1
Style: Name,{font},66,{WHITE},{WHITE},{BLACK},&H80000000,0,0,0,0,100,100,3,0,1,6,0,5,60,60,0,1
Style: Title,{font},108,{WHITE},{WHITE},{BLACK},&H80000000,0,0,0,0,100,100,2,0,1,8,3,8,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def event(start, end, style, text, layer=0):
    return f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}\n"


def build(segments, title, total):
    """segments: [(character, [(word, start, end), ...]), ...] with times in the
    finished video. Returns the .ass file text."""
    out = [header()]
    out.append(event(0, total, "Title",
                     r"{\pos(540,%d)\fad(150,0)}" % TITLE_Y + clean(title).upper(), layer=2))
    bites = []
    for character, words in segments:
        if not words:
            continue
        out.append(event(words[0][1], words[-1][2] + 0.15, "Name",
                         r"{\pos(540,%d)\c%s}" % (NAME_Y, ass_colour(character.color)) + clean(character.name).upper(),
                         layer=1))
        bites.extend(chunks(words))

    for i, bite in enumerate(bites):
        # Keep a bite on screen until the next one starts, unless there's a long pause.
        nxt = bites[i + 1][0][1] if i + 1 < len(bites) else total
        bite_end = min(nxt, bite[-1][2] + 0.35)
        for j, (_, start, _) in enumerate(bite):
            end = bite[j + 1][1] if j + 1 < len(bite) else bite_end
            if end <= start:
                continue
            parts = []
            for k, (word, _, _) in enumerate(bite):
                colour = YELLOW if k == j else WHITE
                parts.append(r"{\c%s}" % colour + clean(word).upper())
            pop = r"\fscx78\fscy78\t(0,90,\fscx100\fscy100)" if j == 0 else ""
            out.append(event(start, end, "Caption",
                             r"{\pos(540,%d)%s}" % (CAPTION_Y, pop) + " ".join(parts), layer=3))
    return "".join(out)
