"""Sends the finished video and its text to you through your Telegram bot."""

import os

import requests

from . import config

API = "https://api.telegram.org/bot{token}/{method}"


def ready():
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def _call(method, **kwargs):
    url = API.format(token=os.environ["TELEGRAM_BOT_TOKEN"], method=method)
    r = requests.post(url, timeout=300, **kwargs)
    if not r.ok:
        # Never print the URL: it contains the bot token.
        raise RuntimeError(f"Telegram said no to {method}: {r.status_code} {r.text[:300]}")
    return r.json()


def send(video_path, script):
    chat = os.environ["TELEGRAM_CHAT_ID"].strip()
    size_mb = video_path.stat().st_size / 1e6
    if size_mb > config.TELEGRAM_LIMIT_MB:
        raise RuntimeError(f"The video is {size_mb:.0f} MB, over Telegram's 50 MB limit for bots.")
    # Sent as a file, not a video, so Telegram doesn't shrink the quality.
    with open(video_path, "rb") as f:
        _call("sendDocument", data={"chat_id": chat, "caption": "New Short ready. Tap, share, Save Video."},
              files={"document": (f"{video_path.parent.name}.mp4", f, "video/mp4")})
    _call("sendMessage", data={"chat_id": chat, "text": script["title"]})
    _call("sendMessage", data={"chat_id": chat,
                               "text": f"{script['description']}\n\n{' '.join(script['hashtags'])}"})


def send_problem(message):
    """Lets you know when a run fails, so you're not left waiting."""
    if ready():
        _call("sendMessage", data={"chat_id": os.environ["TELEGRAM_CHAT_ID"].strip(),
                                   "text": f"Brainrot Shorts hit a problem and made no video this time:\n{message[:3500]}"})
