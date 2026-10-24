"""Puts the video together with ffmpeg: one full-screen picture per scene with
a slow movie-style zoom and pan, the captions and the voices."""

import subprocess

from . import config

ZOOM = 0.14          # how far each picture zooms in or out over its scene
WORK_SCALE = 2       # zoom on a bigger copy so the movement is smooth

# Camera moves, used in turn: (start zoom, end zoom, x drift, y drift)
MOVES = [
    (1.0, 1 + ZOOM, 0.0, -0.3),
    (1 + ZOOM, 1.0, 0.3, 0.0),
    (1.0, 1 + ZOOM, -0.3, 0.2),
    (1 + ZOOM * 0.6, 1 + ZOOM, 0.4, 0.0),
]


def scene_filter(index, frames, move):
    w, h = config.WIDTH, config.HEIGHT
    big_w, big_h = w * WORK_SCALE, h * WORK_SCALE
    z0, z1, dx, dy = move
    p = f"(on/{max(frames - 1, 1)})"
    zoom = f"{z0}+({z1 - z0})*{p}"
    # Centre the crop, then drift it a little towards one side.
    x = f"(iw-iw/zoom)/2+({dx})*(iw-iw/zoom)/2*{p}"
    y = f"(ih-ih/zoom)/2+({dy})*(ih-ih/zoom)/2*{p}"
    return (f"[{index}:v]scale={big_w}:{big_h}:force_original_aspect_ratio=increase,crop={big_w}:{big_h},"
            f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={config.FPS},"
            f"setsar=1,format=yuv420p[s{index}]")


def render(images, spans, audio, ass_path, duration, out_path):
    """images: one picture per scene. spans: (start, end) seconds of each scene."""
    args = ["ffmpeg", "-v", "error", "-y"]
    for img in images:
        args += ["-i", str(img)]
    args += ["-i", str(audio)]

    filters, frames_so_far = [], 0
    for i, (start, end) in enumerate(spans):
        end_frame = round((duration if i == len(spans) - 1 else end) * config.FPS)
        frames = max(end_frame - frames_so_far, 1)
        frames_so_far += frames
        filters.append(scene_filter(i, frames, MOVES[i % len(MOVES)]))
    joined = "".join(f"[s{i}]" for i in range(len(images)))
    filters.append(f"{joined}concat=n={len(images)}:v=1:a=0[slides]")

    font_dir = str(config.FONT_FILE.parent)
    ass = str(ass_path).replace("\\", "/").replace(":", r"\:")
    filters.append(f"[slides]ass='{ass}':fontsdir='{font_dir}',format=yuv420p[v]")

    args += ["-filter_complex", ";".join(filters), "-map", "[v]", "-map", f"{len(images)}:a",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "7M", "-bufsize", "14M",
             "-profile:v", "high", "-r", str(config.FPS),
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-t", f"{duration:.2f}", "-movflags", "+faststart", str(out_path)]
    subprocess.run(args, check=True)
    return out_path
