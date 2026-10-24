"""Paths and settings. Anything secret comes from environment variables
(GitHub Secrets on the robot), never from this file."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONT_FILE = ASSETS / "fonts" / "Anton-Regular.ttf"
FONT_NAME = "Anton"
CHARACTER_DIR = ASSETS / "characters"
GAMEPLAY_DIR = ASSETS / "gameplay"
OUTPUT_DIR = Path(os.environ.get("BRAINROT_OUT", ROOT / "output"))

WIDTH, HEIGHT, FPS = 1080, 1920, 30
MAX_SECONDS = 58.0       # YouTube Shorts limit is 60s; keep a little room
GAP_SECONDS = 0.12       # pause between two lines of dialogue
TELEGRAM_LIMIT_MB = 49   # bots can send files up to 50 MB

STORY_MODEL = os.environ.get("STORY_MODEL") or "claude-opus-5-5"

# "edge" = free Microsoft voices (used on GitHub). "espeak" = robotic offline
# voice, only for testing on a computer that can't reach Microsoft.
VOICE_ENGINE = os.environ.get("BRAINROT_VOICE") or "edge"
