"""Lay a music track under a rendered film, with a few quiet chimes on its key moments.

The track is trimmed from an offset, faded out over the end card, accented with chimes at the
given times (the film's key beats), mixed and loudness-normalised, and muxed onto the video
without re-encoding the picture.

  python scripts/mix_music.py --video out/x.mp4 --music track.mp3 --offset 2 --chimes 0.78:hit,37.4:miss,41.3:miss --out out/x_music.mp4
"""

from __future__ import annotations

import argparse
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48_000


def chime(kind: str) -> np.ndarray:
    if kind == "hit":
        k = int(2.4 * SR); t = np.arange(k) / SR; f = 659.25
        s = np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 2 * f * t) + .1 * np.sin(2 * np.pi * 3.01 * f * t)
    else:  # a softer, lower bell for the list_pages moments
        k = int(2.4 * SR); t = np.arange(k) / SR; f = 392.0
        s = np.sin(2 * np.pi * f * t) + .45 * np.sin(2 * np.pi * 1.5 * f * t) + .12 * np.sin(2 * np.pi * 2.01 * f * t)
    env = np.minimum(1, t / .006) * np.exp(-t / .7)
    return s * env


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--music", required=True)
    ap.add_argument("--offset", type=float, default=0.0)
    ap.add_argument("--chimes", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", args.video],
                               capture_output=True, text=True, check=True).stdout)
    n = int(dur * SR) + SR
    bus = np.zeros(n)
    for item in filter(None, args.chimes.split(",")):
        t, kind = item.split(":")
        i = int(float(t) * SR); c = chime(kind); e = min(n, i + len(c)); bus[i:e] += c[: e - i]
    if bus.any():
        bus *= .5 / np.abs(bus).max()
    accents = Path(args.out).with_suffix(".accents.wav")
    pcm = (np.stack([bus, bus]).T * 32767).astype(np.int16)
    with wave.open(str(accents), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    fade_st = dur - 3.2
    fc = (f"[1:a]atrim=start={args.offset}:duration={dur},asetpts=PTS-STARTPTS,aresample={SR},"
          f"afade=t=in:st=0:d=0.4,afade=t=out:st={fade_st:.2f}:d=3.2[m];"
          f"[2:a]volume=0.22[c];[m][c]amix=inputs=2:normalize=0:duration=first,"
          f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.video, "-i", args.music, "-i", str(accents),
                    "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", args.out], check=True)
    accents.unlink()
    print("wrote", args.out)


if __name__ == "__main__":
    main()
