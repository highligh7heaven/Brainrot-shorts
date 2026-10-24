"""Makes one finished Short.

    python -m brainrot.main                 # trend or random idea, real story from Claude
    python -m brainrot.main --idea "..."    # your own idea
    python -m brainrot.main --sample        # built-in test story, no API key needed
"""

import argparse
import json
import subprocess
import time
import wave
from datetime import datetime

from . import captions, config, story, video, voice
from .cast import BY_ID


def join_audio(clips, out_path):
    """Glues the voice clips together with a short pause between lines.
    Returns where each clip starts in the joined audio."""
    starts, t = [], 0.0
    with wave.open(str(out_path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(48000)
        gap = b"\x00\x00" * int(48000 * config.GAP_SECONDS)
        for i, clip in enumerate(clips):
            with wave.open(clip.path, "rb") as w:
                frames = w.readframes(w.getnframes())
                seconds = w.getnframes() / w.getframerate()
            starts.append(t)
            out.writeframes(frames)
            t += seconds
            if i < len(clips) - 1:
                out.writeframes(gap)
                t += config.GAP_SECONDS
    return starts, t


def finish_audio(raw, out_path, speed):
    """Speeds up a too-long story a little and evens out the loudness."""
    chain = (f"atempo={speed:.3f}," if speed > 1.001 else "") + "loudnorm=I=-14:TP=-1.5:LRA=11"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", chain, "-ar", "48000", "-ac", "2",
                    str(out_path)], check=True)


def make_video(script, workdir, seed=None):
    workdir.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, line in enumerate(script["lines"]):
        character = BY_ID[line["who"]]
        clips.append(voice.speak(line["text"], character, line["delivery"], str(workdir / f"line{i:02d}")))

    starts, total = join_audio(clips, workdir / "voices_raw.wav")
    speed = 1.0
    if total > config.MAX_SECONDS:
        speed = total / (config.MAX_SECONDS - 0.5)
        if speed > 1.25:
            raise RuntimeError(f"The story is {total:.0f}s long, too long for a Short even sped up.")
    finish_audio(workdir / "voices_raw.wav", workdir / "voices.wav", speed)
    duration = total / speed + 0.6     # a beat of silence at the end

    segments, turns = [], []
    for line, clip, start in zip(script["lines"], clips, starts):
        words = [(w, (start + a) / speed, (start + b) / speed) for w, a, b in clip.words]
        segments.append((BY_ID[line["who"]], words))
        turns.append((line["who"], start / speed, (start + clip.duration) / speed))
    # The talking character stays up front through the short pause after their line.
    turns = [(cid, s, (turns[i + 1][1] if i + 1 < len(turns) else duration)) for i, (cid, s, _) in enumerate(turns)]

    ass_path = workdir / "captions.ass"
    ass_path.write_text(captions.build(segments, script["on_screen_title"], duration), encoding="utf-8")

    characters = [BY_ID[i] for i in script["brief"]["characters"]]
    out = workdir / "short.mp4"
    video.render(turns, characters, workdir / "voices.wav", ass_path, duration, out, seed=seed)
    return out, duration


def post_text(script):
    return (f"{script['title']}\n\n"
            f"{script['description']}\n\n"
            f"{' '.join(script['hashtags'])}")


def run(idea=None, sample=False, topic_finder=None):
    started = time.time()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    workdir = config.OUTPUT_DIR / stamp
    if sample:
        script = story.sample_story()
    else:
        topic = idea or (topic_finder() if topic_finder else None)
        script = story.write_story(story.pick_brief(topic))
    path, duration = make_video(script, workdir)
    (workdir / "story.json").write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    (workdir / "post.txt").write_text(post_text(script), encoding="utf-8")
    size = path.stat().st_size / 1e6
    print(f"Made {path} ({duration:.1f}s, {size:.1f} MB) in {time.time() - started:.0f}s")
    print(post_text(script))
    return path, script


def main():
    parser = argparse.ArgumentParser(description="Make one brainrot Short.")
    parser.add_argument("--idea", default="", help="your own idea in a few words")
    parser.add_argument("--sample", action="store_true", help="use the built-in test story")
    args = parser.parse_args()
    run(idea=args.idea.strip() or None, sample=args.sample)


if __name__ == "__main__":
    main()
