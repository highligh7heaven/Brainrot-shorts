"""The channel's own cast of brainrot characters.

Each character has one reference picture in assets/characters/<id>.png that
is reused in every video, so they always look the same. Until a picture
exists, a simple placeholder is drawn so the rest of the system still works.
"""

from dataclasses import dataclass

from PIL import Image, ImageDraw

from . import config


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    look: str          # what the picture shows (also used to draw it)
    personality: str   # how they talk and act in stories
    voice: str         # Microsoft Edge voice
    rate: str = "+10%"
    pitch: str = "+0Hz"
    color: str = "#ff3d7f"


CAST = [
    Character(
        "spaghettino", "Spaghettino Turbino",
        "a single wiggly spaghetti noodle with two tiny jet engines and racing goggles",
        "hyperactive, always in a hurry, shouts everything, thinks speed solves every problem",
        "it-IT-GiuseppeMultilingualNeural", "+20%", "+8Hz", "#f7c948"),
    Character(
        "frigorifero", "Frigorifero Leone",
        "a white kitchen fridge with a huge golden lion's mane and a crown magnet",
        "dramatic royal, speaks like a movie trailer narrator, deeply offended by everything",
        "en-US-ChristopherNeural", "+0%", "-6Hz", "#e8e8e8"),
    Character(
        "pinguino", "Pinguino Espresso",
        "a small penguin whose body is a steaming espresso cup",
        "jittery fast-talker, over-caffeinated, has a conspiracy theory for everything",
        "en-AU-WilliamNeural", "+25%", "+4Hz", "#8b5a2b"),
    Character(
        "nonna", "Nonna Tornado",
        "a tiny grandma spinning inside her own small tornado, holding a wooden spoon",
        "sweet but terrifying, gives life advice that makes no sense, threatens with the spoon",
        "it-IT-IsabellaMultilingualNeural", "+5%", "+0Hz", "#9ad1ff"),
    Character(
        "sandalino", "Sandalino Gigantino",
        "a giant blue flip-flop with muscular legs and sunglasses",
        "lovable and not very smart, takes everything literally, very proud of his legs",
        "en-US-GuyNeural", "+5%", "-4Hz", "#3d8bff"),
    Character(
        "gattino", "Gattino Pomodoro",
        "a round red tomato with cat ears, whiskers and a tail",
        "sassy and judgemental, rates everything out of ten, secretly the smartest one",
        "en-GB-MaisieNeural", "+10%", "+0Hz", "#ff4b3e"),
    Character(
        "tostapane", "Tostapane Tenore",
        "a shiny chrome toaster with a curly opera moustache, toast popping out like a hat",
        "sings his feelings like an opera tenor, cries easily, very loud",
        "de-DE-FlorianMultilingualNeural", "+0%", "-2Hz", "#c0c6cc"),
    Character(
        "polpo", "Polpo Pilota",
        "a purple octopus wearing an old pilot helmet and scarf, each tentacle holding a gadget",
        "overconfident inventor, every plan is genius and every plan fails",
        "en-US-AndrewMultilingualNeural", "+10%", "+0Hz", "#a35cff"),
]

BY_ID = {c.id: c for c in CAST}


def image_path(character):
    """The character's picture, drawing a placeholder first if it's missing."""
    path = config.CHARACTER_DIR / f"{character.id}.png"
    if not path.exists():
        path = config.OUTPUT_DIR / "placeholders" / f"{character.id}.png"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            draw_placeholder(character).save(path)
    return path


def draw_placeholder(character, size=720):
    """A friendly blob with eyes: clearly a stand-in until the real picture exists."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = size // 12
    d.rounded_rectangle((pad, pad, size - pad, size - pad * 3), radius=size // 4,
                        fill=character.color, outline="black", width=size // 60)
    for cx in (size * 0.36, size * 0.64):
        r = size * 0.09
        d.ellipse((cx - r, size * 0.32 - r, cx + r, size * 0.32 + r), fill="white", outline="black", width=6)
        d.ellipse((cx - r / 2.4, size * 0.33 - r / 2.4, cx + r / 2.4, size * 0.33 + r / 2.4), fill="black")
    d.arc((size * 0.36, size * 0.38, size * 0.64, size * 0.6), 20, 160, fill="black", width=size // 50)
    return img
