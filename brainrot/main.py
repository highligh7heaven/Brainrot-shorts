"""Makes one finished Short.

    python -m brainrot.main                 # trend or random idea, real story from Claude
    python -m brainrot.main --idea "..."    # your own idea
    python -m brainrot.main --sample        # built-in test story, no story key needed
"""

import argparse
import json
import os
import subprocess
import time
import wave
from datetime import datetime

from . import captions, config, images, memory, story, telegram, trends, video, voice
from .cast import pick_narrator, speakers_for


def join_audio(clips, out_path):
    """Glues the voice clips together with a short pause between lines.
    Returns where each clip starts in the joined audio, and the total length."""
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


def make_voices(script, workdir):
    speakers = speakers_for(script)
    print(f"Narrator voice: {speakers['narrator'].engine} {speakers['narrator'].voice}")
    clips, owners = [], []
    for si, scene in enumerate(script["scenes"]):
        for line in scene["lines"]:
            stem = str(workdir / f"line{len(clips):02d}")
            clips.append(voice.speak(line["text"], speakers[line["who"]], line["delivery"], stem))
            owners.append(si)
    return clips, owners


def make_video(script, workdir, part_label=None, refs_dir=None):
    workdir.mkdir(parents=True, exist_ok=True)
    clips, owners = make_voices(script, workdir)
    starts, total = join_audio(clips, workdir / "voices_raw.wav")
    speed = 1.0
    if total > config.MAX_SECONDS:
        speed = total / (config.MAX_SECONDS - 0.5)
        if speed > 1.25:
            raise RuntimeError(f"The story is {total:.0f}s long, too long for a Short even sped up.")
    finish_audio(workdir / "voices_raw.wav", workdir / "voices.wav", speed)
    duration = total / speed + 0.6     # a beat of silence at the end

    words, spans = [], []
    for clip, start, scene in zip(clips, starts, owners):
        words += [(w, (start + a) / speed, (start + b) / speed) for w, a, b in clip.words]
        if len(spans) <= scene:
            spans.append([start / speed, (start + clip.duration) / speed])
        spans[scene][1] = (start + clip.duration) / speed
    # Each picture stays until the next scene begins.
    spans = [(0.0 if i == 0 else s, spans[i + 1][0] if i + 1 < len(spans) else duration)
             for i, (s, _) in enumerate(spans)]

    ass_path = workdir / "captions.ass"
    ass_path.write_text(captions.build(words, duration, part_label), encoding="utf-8")
    pictures = images.make_images(script, workdir / "images", refs_dir)
    out = workdir / "short.mp4"
    video.render(pictures, spans, workdir / "voices.wav", ass_path, duration, out)
    return out, duration


def post_text(script):
    return (f"{script['title']}\n\n"
            f"{script['description']}\n\n"
            f"{' '.join(script['hashtags'])}")


def choose_narrator(series):
    forced = os.environ.get("NARRATOR", "").strip()
    if forced.isdigit() and int(forced) > 0:
        return int(forced) - 1
    if series and series.get("narrator") is not None:
        return series["narrator"]      # same narrator for every part of a series
    return pick_narrator()


def run(idea=None, sample=False):
    """Makes one video. Real runs continue the current series (or start a new
    one from your idea or today's trends) and update the memory file."""
    started = time.time()
    workdir = config.OUTPUT_DIR / datetime.now().strftime("%Y-%m-%d_%H%M")
    mem, series, refs_dir = None, None, None
    if sample:
        script = story.sample_story()
    else:
        mem = memory.load()
        series = None if idea else memory.continuing(mem)
        brief = story.pick_brief(None, avoid=memory.avoid_list(mem))
        if not series:
            # Your idea, or today's trends, starts a new series.
            series = memory.new_series(datetime.now().strftime("%Y%m%d_%H%M"))
            brief["topic"] = idea or trends.as_topic(trends.today())
        brief["series"] = series
        refs_dir = memory.refs_dir(series["id"])
        script = story.write_story(brief)
    script["narrator"] = choose_narrator(series)
    part_label = f"PART {series['part'] + 1}" if series else None
    if series:
        script["title"] = f"{script['title']} (Part {series['part'] + 1})"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "story.json").write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(script, indent=2, ensure_ascii=False))
    path, duration = make_video(script, workdir, part_label, refs_dir)
    (workdir / "post.txt").write_text(post_text(script), encoding="utf-8")
    size = path.stat().st_size / 1e6
    print(f"Made {path} ({duration:.1f}s, {size:.1f} MB) in {time.time() - started:.0f}s")
    print(post_text(script))
    if mem is not None:
        memory.record(mem, script, series)
        memory.mark_slot(mem, os.environ.get("SLOT", "").strip())
        memory.save(mem)
    return path, script


def main():
    parser = argparse.ArgumentParser(description="Make one brainrot Short.")
    parser.add_argument("--idea", default=os.environ.get("IDEA", ""), help="your own idea in a few words")
    parser.add_argument("--sample", action="store_true", help="use the built-in test story")
    args = parser.parse_args()
    try:
        path, script = run(idea=args.idea.strip() or None, sample=args.sample)
    except Exception as e:
        if not args.sample:
            telegram.send_problem(str(e))
        raise
    if telegram.ready() and not args.sample:
        telegram.send(path, script)
        print("Sent to Telegram.")


if __name__ == "__main__":
    main()
