"""Render the Observatory film frame by frame (capture mode), score it, and encode it.

The page is opened with ?cap=1, which replaces wall time with a virtual clock; each frame calls
capRender(t) and takes a screenshot, so the film is reproducible from recorded data alone. The page
also logs every beam landing and cut (window.capEvents); scripts/make_soundtrack.py scores the film
from that log. Uses the system Microsoft Edge through Playwright and ffmpeg on PATH.

  python scripts/render_video.py --url http://127.0.0.1:8765/observatory.html --out out/observatory.mp4
  python scripts/render_video.py --url ... --cut short --out out/observatory-20s.mp4
  python scripts/render_video.py --url ... --only 1,5,12      # stills to check shots
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H, FPS = 1920, 1080, 30


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="out/observatory.mp4")
    ap.add_argument("--cut", choices=["long", "short"], default="long")
    ap.add_argument("--frames", default="out/frames")
    ap.add_argument("--only", help="comma-separated times in seconds: render stills only")
    args = ap.parse_args()
    frames = Path(args.frames)
    if frames.exists() and not args.only:
        shutil.rmtree(frames)
    frames.mkdir(parents=True, exist_ok=True)
    url = args.url + ("&" if "?" in args.url else "?") + "cap=1" + ("&cut=short" if args.cut == "short" else "")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True,
                                     args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(url, wait_until="networkidle")
        page.wait_for_function("window.capReady === true", timeout=60000)
        page.evaluate("document.fonts.ready")
        dur = float(page.evaluate("window.capDuration"))
        times = [float(x) for x in args.only.split(",")] if args.only else [i / FPS for i in range(int(round(dur * FPS)))]
        for k, t in enumerate(times):
            if args.only:  # stills: play the preceding 3 s first so beams and lerps are in their real state
                page.evaluate(f"for(let x=Math.max(0,{t}-3);x<{t};x+=1/{FPS}) capRender(x)")
            page.evaluate(f"capRender({t:.5f})")
            name = f"still_{t:06.2f}.png" if args.only else f"{k:05d}.png"
            page.screenshot(path=str(frames / name))
            if not args.only and k % 150 == 0:
                print(f"frame {k}/{len(times)}", flush=True)
        events = page.evaluate("window.capEvents")
        browser.close()

    if args.only:
        print("stills written to", frames)
        return
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    ev_path = out.with_suffix(".events.json")
    ev_path.write_text(json.dumps({"duration": dur, "events": events}, indent=1))
    wav = out.with_suffix(".wav")
    subprocess.run([sys.executable, str(Path(__file__).with_name("make_soundtrack.py")), str(ev_path), str(wav)], check=True)
    vf = f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.8}:d=0.8"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%05d.png"),
                    "-i", str(wav), "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                   check=True)
    shutil.copy(frames / f"{min(int(2.6 * FPS), len(times) - 1):05d}.png", out.with_name(out.stem + "_thumbnail.png"))
    print("wrote", out)


if __name__ == "__main__":
    main()
