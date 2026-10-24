"""Writes each video's script with Claude.

Variety comes from random picks for the story format, the place and the kind
of twist, a random 2-3 character line-up, and a list of past stories that
Claude is told not to repeat.
"""

import json
import os
import random

from . import config
from .cast import BY_ID, CAST

FORMATS = [
    "breaking news report that keeps going wrong",
    "cooking show where the recipe fights back",
    "courtroom drama over something tiny",
    "job interview that escalates",
    "nature documentary narrated by one of the characters",
    "dating show with a terrible twist",
    "horror movie trailer about something harmless",
    "sports commentary of an everyday chore",
    "heist plan that falls apart",
    "school detention confession",
    "tech product launch of a useless gadget",
    "talent show audition",
    "detective interrogation",
    "pirate radio call-in show",
    "group chat argument read out loud",
    "space mission countdown",
]

PLACES = [
    "a supermarket at 3am", "the moon", "a sinking pizza boat", "a gym", "a haunted laundromat",
    "the inside of a microwave", "a volcano spa", "a school bus", "a wedding", "a submarine",
    "a dentist's office", "a castle made of pasta", "the airport security line", "a farm",
    "a library where talking is illegal", "a theme park ride that won't stop",
]

TWISTS = [
    "the narrator turns out to be involved",
    "it was all a misunderstanding about one word",
    "the smallest character secretly runs everything",
    "the ending loops perfectly back into the first line",
    "a ridiculous object saves the day",
    "everyone was wrong except the dumbest character",
    "the villain just wanted a snack",
]

SYSTEM = """You write scripts for a YouTube Shorts channel of short, funny, chaotic "brainrot" stories.
The channel has its own original cast of absurd characters (in the spirit of Italian brainrot memes,
but never the famous existing ones like Tralalero Tralala, Tung Tung Tung Sahur, Bombardiro
Crocodilo or Ballerina Cappuccina, which belong to other creators).

Rules for every script:
- The FIRST line is the hook: at most 8 words, said by a character, shocking or absurd enough
  that a scroller stops in the first 2 seconds. No greetings, no "today we", no setup.
- 95 to 125 words in total (30-50 seconds read aloud), 8 to 14 lines, each line under 22 words.
- Fast, chaotic, escalating, with a clear punchline at the end. Characters stay in personality.
- Written to be spoken: no stage directions, emojis, hashtags or brackets inside lines.
- Family-friendly (PG). No real people mocked, no politics, tragedies, disasters, violence or
  brand names. If the trending topic is sad, serious or political, ignore it and only borrow
  a harmless word or vibe from it.
- Never mention AI, the script, or the channel.
- title: a curiosity-gap YouTube title under 70 characters, no hashtags, no emojis.
- on_screen_title: 2-5 words in CAPITALS, shown at the top of the video the whole time.
- description: 1-2 short sentences plus a question that invites comments.
- hashtags: 4-6 tags, each starting with #, always including #shorts and #brainrot."""


def schema(ids):
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "on_screen_title": {"type": "string"},
            "lines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "who": {"type": "string", "enum": ids},
                        "text": {"type": "string"},
                        "delivery": {"type": "string", "enum": ["normal", "shout", "whisper", "fast", "sad"]},
                    },
                    "required": ["who", "text", "delivery"],
                    "additionalProperties": False,
                },
            },
            "description": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "on_screen_title", "lines", "description", "hashtags"],
        "additionalProperties": False,
    }


def pick_brief(topic=None, rng=random, avoid=()):
    """Random ingredients for one story."""
    lineup = rng.sample(CAST, rng.choice([2, 2, 3]))
    return {
        "topic": topic,
        "format": rng.choice(FORMATS),
        "place": rng.choice(PLACES),
        "twist": rng.choice(TWISTS),
        "characters": [c.id for c in lineup],
        "avoid": list(avoid)[-30:],
    }


def brief_prompt(brief):
    people = "\n".join(
        f"- {BY_ID[i].name} (id: {i}): {BY_ID[i].look}. Personality: {BY_ID[i].personality}."
        for i in brief["characters"])
    topic = brief["topic"] or "no specific topic, invent something fresh"
    avoid = "\n".join(f"- {a}" for a in brief["avoid"]) or "- (nothing yet)"
    return (f"Topic or trend to riff on: {topic}\n"
            f"Story format: {brief['format']}\n"
            f"Where it happens: {brief['place']}\n"
            f"Kind of twist: {brief['twist']}\n"
            f"Characters (use all of them, refer to them by name):\n{people}\n\n"
            f"Past stories, do NOT repeat their premise or jokes:\n{avoid}")


def write_story(brief):
    """Asks Claude for the script. Needs the ANTHROPIC_API_KEY secret."""
    import anthropic

    client = anthropic.Anthropic()
    request = dict(
        model=config.STORY_MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": brief_prompt(brief)}],
        output_config={"effort": "medium",
                       "format": {"type": "json_schema", "schema": schema(brief["characters"])}},
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
    story = json.loads(text)
    return check_story(story, brief)


def check_story(story, brief):
    story["lines"] = [l for l in story["lines"] if l["text"].strip()]
    if len(story["lines"]) < 4:
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
    brief = {"topic": "test", "format": "breaking news report that keeps going wrong",
             "place": "a supermarket at 3am", "twist": "the villain just wanted a snack",
             "characters": ["spaghettino", "frigorifero", "gattino"], "avoid": []}
    story = {
        "title": "The Fridge King Lost His Crown at 3AM",
        "on_screen_title": "FRIDGE KING ROBBED",
        "lines": [
            {"who": "frigorifero", "text": "Someone stole my crown. I am now just a fridge.", "delivery": "shout"},
            {"who": "spaghettino", "text": "Breaking news! Spaghettino Turbino live from aisle seven, going two hundred miles an hour!", "delivery": "fast"},
            {"who": "gattino", "text": "Slow down. You crashed into the cereal three times. Zero out of ten.", "delivery": "normal"},
            {"who": "frigorifero", "text": "Without my crown, my ice cubes refuse to obey me. They are melting out of disrespect.", "delivery": "sad"},
            {"who": "spaghettino", "text": "Suspect spotted! Small, round, red, and suspiciously calm!", "delivery": "shout"},
            {"who": "gattino", "text": "That's me. I'm literally the reporter's camera crew.", "delivery": "normal"},
            {"who": "spaghettino", "text": "Then why is there a crown on your head?", "delivery": "whisper"},
            {"who": "gattino", "text": "Because it's a magnet, and I'm a tomato with a fridge problem.", "delivery": "normal"},
            {"who": "frigorifero", "text": "Traitor! I kept you cold for three whole weeks!", "delivery": "shout"},
            {"who": "gattino", "text": "Exactly. I just wanted to open the door myself and grab a snack.", "delivery": "normal"},
            {"who": "spaghettino", "text": "Breaking news! The crime was snacks! Back to you, fridge!", "delivery": "fast"},
            {"who": "frigorifero", "text": "Someone stole my crown. Again.", "delivery": "shout"},
        ],
        "description": "A royal fridge, a turbo noodle and a very suspicious tomato. Who was really guilty here?",
        "hashtags": ["#shorts", "#brainrot", "#funny", "#animation", "#comedy"],
    }
    return check_story(story, brief)


def has_api_key():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
