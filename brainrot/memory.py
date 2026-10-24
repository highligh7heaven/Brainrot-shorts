"""The robot's memory, kept in state/memory.json in the repository and saved
back after every real run:

- the series that's running (characters, story so far, which part is next,
  narrator voice and character pictures), so the next video continues it;
- past stories, so Claude never repeats one;
- which scheduled times have already had their video.
"""

import json
import random
import shutil

from . import config

STATE_DIR = config.ROOT / "state"
MEMORY_FILE = STATE_DIR / "memory.json"
SERIES_DIR = STATE_DIR / "series"
KEEP_HISTORY = 60


def load():
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {"series": None, "history": [], "done_slots": []}


def save(mem):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(mem, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def avoid_list(mem):
    return [h["premise"] for h in mem.get("history", [])]


def refs_dir(series_id):
    path = SERIES_DIR / series_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def continuing(mem):
    """The series to continue, or None if it's time to start a new one."""
    s = mem.get("series")
    if s and s["part"] < s["total"]:
        return s
    return None


def new_series(series_id, rng=random):
    return {"id": series_id, "part": 0, "total": rng.choice([3, 3, 4]), "title": "",
            "characters": [], "so_far": [], "cliffhanger": "", "narrator": None}


def record(mem, script, series):
    """Saves what this video added to the story."""
    series["part"] += 1
    if series["part"] == 1:
        series["title"] = script["series_title"]
    series["narrator"] = script["narrator"]
    known = {c["id"] for c in series["characters"]}
    series["characters"] += [c for c in script["characters"] if c["id"] not in known]
    series["so_far"].append(f"Part {series['part']}: {script['summary']}")
    series["cliffhanger"] = script["cliffhanger"]
    mem["history"] = (mem.get("history", []) + [{
        "title": script["title"],
        "premise": f"{series['title']} (part {series['part']}): {script['summary']}",
    }])[-KEEP_HISTORY:]
    if series["part"] >= series["total"]:
        # Series finished: its character pictures aren't needed any more.
        shutil.rmtree(SERIES_DIR / series["id"], ignore_errors=True)
        mem["series"] = None
    else:
        mem["series"] = series


def mark_slot(mem, slot):
    if slot:
        mem["done_slots"] = (mem.get("done_slots", []) + [slot])[-20:]
