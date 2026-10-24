"""Builds the .ass subtitle file burned into the video: one big bold word at a
time in the middle of the screen, popping in as it's spoken. Money, numbers
and dramatic words turn yellow."""

import re

from . import config

WHITE = "&H00FFFFFF"
YELLOW = "&H0000E1FF"     # ASS colours are written blue-green-red
BLACK = "&H00000000"

CAPTION_Y = 1180
PART_Y = 170
MIN_SHOW = 0.18           # shortest time a word stays up

DRAMATIC = {
    "gold", "golden", "million", "millions", "billion", "billions", "rich", "poor", "money", "never",
    "secret", "truth", "lie", "lied", "liar", "twins", "baby", "wedding", "fired", "karma", "revenge",
    "mother", "father", "daughter", "son", "hospital", "dead", "shocked", "shock", "everyone", "nobody",
    "first", "last", "dollar", "dollars", "prize", "winner", "betrayed", "stole", "stolen", "cheated", "won", "lost", "free", "love", "hate",
}


def ass_time(seconds):
    cs = int(round(max(seconds, 0) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def clean(text):
    return re.sub(r"[{}\\]", "", text).strip()


def is_dramatic(word):
    bare = re.sub(r"[^\w$]", "", word.lower())
    return bool(re.search(r"\d|\$", bare)) or bare in DRAMATIC


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
Style: Word,{font},170,{WHITE},{WHITE},{BLACK},&H96000000,0,0,0,0,100,100,3,0,1,11,6,5,40,40,0,1
Style: Part,{font},72,{WHITE},{WHITE},{BLACK},&H96000000,0,0,0,0,100,100,3,0,1,7,3,8,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def event(start, end, style, text, layer=0):
    return f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}\n"


def build(words, total, part_label=None):
    """words: [(word, start, end), ...] with times in the finished video."""
    out = [header()]
    if part_label:
        out.append(event(0, min(3.0, total), "Part", r"{\pos(540,%d)\fad(0,300)}" % PART_Y + clean(part_label).upper()))
    for i, (word, start, end) in enumerate(words):
        nxt = words[i + 1][1] if i + 1 < len(words) else total
        # Stay up until the next word (bridging short pauses), but not across long silences.
        stop = max(min(nxt, end + 0.4), start + MIN_SHOW)
        if nxt > start:
            stop = min(stop, nxt)
        text = clean(word).upper().strip(",.;:")
        if not text:
            continue
        colour = r"\c%s" % YELLOW if is_dramatic(word) else ""
        out.append(event(start, stop, "Word",
                         r"{\pos(540,%d)%s\fscx70\fscy70\t(0,80,\fscx108\fscy108)\t(80,140,\fscx100\fscy100)}"
                         % (CAPTION_Y, colour) + text, layer=1))
    return "".join(out)
