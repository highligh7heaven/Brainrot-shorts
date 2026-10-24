"""Writes each video's script with Claude, in the "AI fruit drama" style:
3D fruit and food people in emotional, over-the-top soap-opera stories,
told mostly by a narrator and ending on a cliffhanger.

Variety comes from random picks for the drama type, the place and the
twist, plus a list of past stories that Claude is told not to repeat.
"""

import json
import random
import re

from . import config
from .cast import VOICE_KINDS

DRAMAS = [
    "a parent who spoils one child and neglects the other",
    "a poor worker humiliated by a rich boss, then karma",
    "twins swapped or separated at birth",
    "a wedding that goes terribly wrong",
    "a rich family judging a poor partner",
    "a glow-up after years of bullying",
    "a secret inheritance or hidden fortune",
    "a betrayal by a best friend",
    "a lie that gets bigger and bigger",
    "a talent show where the underdog shocks everyone",
    "a greedy landlord or boss getting what they deserve",
    "a kind stranger who turns out to be a billionaire",
    "a school rivalry that escalates",
    "a mysterious new neighbour",
]

PLACES = [
    "a luxury mansion with chandeliers", "a hospital room", "a school classroom",
    "a fancy restaurant", "a small poor apartment", "a wedding hall", "a supermarket",
    "a construction site", "a courtroom", "a beach resort", "a farm", "a car at night",
    "a palace", "a fast food restaurant", "a junkyard", "an airport",
]

TWISTS = [
    "the quiet one was secretly the richest all along",
    "the villain's own plan backfires on them",
    "a hidden recording reveals the truth",
    "the outcast turns out to be the hero",
    "a DNA or paper reveal changes everything",
    "the kind act from the start comes back as a reward",
    "it ends on a shocking cliffhanger for part 2",
]

IMAGE_STYLE = ("3D animated movie still in a glossy Pixar-like style with realistic textures. "
               "Characters are anthropomorphic fruit or food people: human bodies, clothes and hands, "
               "with a big expressive fruit or food head and a detailed face. Cinematic lighting, "
               "rich detailed setting, vertical portrait composition, no text, no captions, no logos.")

SYSTEM = f"""You write scripts for a YouTube Shorts channel of viral "AI fruit drama" stories:
3D fruit and food people (a banana mum, a pomegranate billionaire, a strawberry wife, a broccoli
bulldozer driver...) living over-the-top emotional soap-opera dramas, plus the odd absurd
brainrot-style object character. The videos are a slideshow of movie-like scenes with a narrator.

Rules for every script:
- The FIRST line is the hook, said by the narrator: at most 8 words, dramatic and specific,
  so a scroller stops in the first 2 seconds (e.g. "She poured gold on only one daughter.").
- 110 to 140 words in total (38-50 seconds read aloud), in 5 to 7 scenes. Each scene is one
  picture with 1 to 3 short lines. Mostly the narrator in punchy present-tense sentences, with
  a few short, strong lines spoken by the characters.
- Big emotions, clear villain and underdog, an escalating twist, and a last line that is a
  cliffhanger or a satisfying karma punch.
- 2 to 4 characters, each a fruit or food person with a memorable name (like "Mrs Banana",
  "Pomegranate Pete"). "look" describes their head, face, body and clothes in one sentence so
  they are drawn the same in every scene. "voice" is the kind of voice.
- Each scene's "image" describes one movie still: the place, which characters are in it (by
  id), what they are doing and their facial expressions. Never ask for text or signs.
- Written to be spoken: no stage directions, emojis or brackets inside lines.
- Keep it PG: no blood, gore, weapons, sexual content, real people, politics or brand names.
  If the trending topic is sad, serious or political, ignore it and only borrow a harmless
  word or vibe from it.
- Never mention AI, the script, or the channel.
- title: an emotional curiosity-gap title under 70 characters, no hashtags or emojis.
- description: 1-2 short sentences plus a question that invites comments.
- hashtags: 4-6 tags starting with #, always including #shorts and #brainrot.
- cliffhanger: one sentence saying what part 2 would be about."""


def schema():
    line = {
        "type": "object",
        "properties": {
            "who": {"type": "string"},
            "text": {"type": "string"},
            "delivery": {"type": "string", "enum": ["normal", "shout", "whisper", "fast", "sad"]},
        },
        "required": ["who", "text", "delivery"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "characters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "look": {"type": "string"},
                        "voice": {"type": "string", "enum": VOICE_KINDS},
                    },
                    "required": ["id", "name", "look", "voice"],
                    "additionalProperties": False,
                },
            },
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "image": {"type": "string"},
                        "lines": {"type": "array", "items": line},
                    },
                    "required": ["image", "lines"],
                    "additionalProperties": False,
                },
            },
            "description": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "cliffhanger": {"type": "string"},
        },
        "required": ["title", "characters", "scenes", "description", "hashtags", "cliffhanger"],
        "additionalProperties": False,
    }


def pick_brief(topic=None, rng=random, avoid=()):
    """Random ingredients for one story."""
    return {
        "topic": topic,
        "drama": rng.choice(DRAMAS),
        "place": rng.choice(PLACES),
        "twist": rng.choice(TWISTS),
        "avoid": list(avoid)[-30:],
    }


def brief_prompt(brief):
    topic = brief["topic"] or "no specific topic, invent something fresh"
    avoid = "\n".join(f"- {a}" for a in brief["avoid"]) or "- (nothing yet)"
    return (f"Topic or trend to riff on: {topic}\n"
            f"Kind of drama: {brief['drama']}\n"
            f"Main place: {brief['place']}\n"
            f"Kind of twist: {brief['twist']}\n\n"
            f"Past stories, do NOT repeat their premise:\n{avoid}")


def write_story(brief):
    """Asks Claude for the script. Needs the ANTHROPIC_API_KEY secret."""
    import anthropic

    client = anthropic.Anthropic()
    request = dict(
        model=config.STORY_MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": brief_prompt(brief)}],
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema()}},
    )
    try:
        # If the story model declines a request, Anthropic quietly retries it on a fallback model.
        response = client.beta.messages.create(
            betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request)
    except anthropic.BadRequestError as e:
        if "fallback" not in str(e).lower():
            raise
        response = client.messages.create(**request)
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to write this story; the next run will pick a new idea.")
    text = next(b.text for b in response.content if b.type == "text")
    return check_story(json.loads(text), brief)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "x"


def check_story(story, brief):
    """Tidies the script so the rest of the system can trust it."""
    ids = {}
    for c in story["characters"]:
        c["id"] = slug(c["id"])
        ids[c["id"]] = c
    for scene in story["scenes"]:
        scene["lines"] = [l for l in scene["lines"] if l["text"].strip()]
        for line in scene["lines"]:
            who = slug(line["who"])
            line["who"] = who if who in ids else "narrator"
    story["scenes"] = [s for s in story["scenes"] if s["lines"]]
    if len(story["scenes"]) < 3:
        raise RuntimeError("The story came back too short.")
    tags = [t if t.startswith("#") else f"#{t}" for t in story["hashtags"]]
    for must in ("#shorts", "#brainrot"):
        if must not in [t.lower() for t in tags]:
            tags.append(must)
    story["hashtags"] = [t.replace(" ", "") for t in tags][:8]
    story["brief"] = brief
    return story


def sample_story():
    """A ready-made script for testing without an API key."""
    brief = {"topic": "test", "drama": DRAMAS[0], "place": PLACES[0], "twist": TWISTS[0], "avoid": []}
    story = {
        "title": "She Gave Gold to One Daughter and Mud to the Other",
        "characters": [
            {"id": "mrs_banana", "name": "Mrs Banana", "voice": "posh_woman",
             "look": "tall banana-headed woman with red lipstick, pearl earrings and a green satin gown"},
            {"id": "goldie", "name": "Goldie", "voice": "girl",
             "look": "little girl with a shiny golden lemon head and a cream dress"},
            {"id": "lemmy", "name": "Lemmy", "voice": "girl",
             "look": "little girl with a plain yellow lemon head, sad eyes and a faded blue dress"},
        ],
        "scenes": [
            {"image": "mansion living room; mrs_banana pours liquid gold over goldie's head while holding a rusty bucket of mud over lemmy",
             "lines": [{"who": "narrator", "text": "She poured gold on only one daughter.", "delivery": "normal"},
                       {"who": "mrs_banana", "text": "Goldie deserves to shine. You get the mud.", "delivery": "normal"}]},
            {"image": "school hallway; goldie laughs with friends while lemmy walks alone, covered in dried mud",
             "lines": [{"who": "narrator", "text": "At school, everyone loved the golden girl. Nobody sat with Lemmy.", "delivery": "sad"}]},
            {"image": "small attic bedroom at night; lemmy secretly painting a beautiful picture by candlelight",
             "lines": [{"who": "narrator", "text": "But every night, Lemmy painted in secret.", "delivery": "whisper"},
                       {"who": "lemmy", "text": "One day, they will see me.", "delivery": "sad"}]},
            {"image": "art contest stage; a judge holds up lemmy's painting while the crowd gasps",
             "lines": [{"who": "narrator", "text": "Then a famous art contest offered one million dollars.", "delivery": "fast"},
                       {"who": "narrator", "text": "Lemmy's painting won first place.", "delivery": "shout"}]},
            {"image": "mansion; mrs_banana grabs the prize cheque, smiling greedily, goldie behind her",
             "lines": [{"who": "mrs_banana", "text": "Give me that money, I am her mother!", "delivery": "shout"}]},
            {"image": "mansion doorway; lemmy stands proudly next to a kind old pineapple judge holding papers",
             "lines": [{"who": "narrator", "text": "But the judge had read the painting's secret title.", "delivery": "normal"},
                       {"who": "narrator", "text": "It was called: The Mother Who Chose Gold.", "delivery": "whisper"}]},
        ],
        "description": "One daughter got gold, the other got mud. Did the mother deserve what came next?",
        "hashtags": ["#shorts", "#brainrot", "#fruitdrama", "#aistory", "#karma"],
        "cliffhanger": "The judge reveals what he found out about Mrs Banana's past.",
    }
    return check_story(story, brief)
