"""Render the Observatory film frame by frame (capture mode), then encode it.

The page is opened with ?cap=1, which replaces wall time with a virtual clock; each frame calls
capRender(t) and takes a screenshot, so the film is reproducible from recorded data alone.
Uses the system Microsoft Edge through Playwright (no browser download) and ffmpeg on PATH.

  python scripts/render_video.py --url http://127.0.0.1:8765/observatory.html --out out/observatory.mp4
  python scripts/render_video.py --url ... --only 0,3.5,9,18,27,36,45,52   # stills to check shots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H, FPS, DUR = 1920, 1080, 30, 55.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="out/observatory.mp4")
    ap.add_argument("--frames", default="out/frames")
    ap.add_argument("--only", help="comma-separated times in seconds: render stills only")
    args = ap.parse_args()
    frames = Path(args.frames)
    if frames.exists() and not args.only:
        shutil.rmtree(frames)
    frames.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True,
                                     args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(args.url + ("&" if "?" in args.url else "?") + "cap=1", wait_until="networkidle")
        page.wait_for_function("window.capReady === true", timeout=60000)
        page.evaluate("document.fonts.ready")
        times = [float(x) for x in args.only.split(",")] if args.only else [i / FPS for i in range(int(DUR * FPS))]
        for k, t in enumerate(times):
            if args.only:  # stills: play the preceding 3 s first so beams, lerps and the rack are in their real state
                page.evaluate(f"for(let x=Math.max(0,{t}-3);x<{t};x+=1/{FPS}) capRender(x)")
            page.evaluate(f"capRender({t:.5f})")
            name = f"still_{t:06.2f}.png" if args.only else f"{k:05d}.png"
            page.screenshot(path=str(frames / name))
            if not args.only and k % 150 == 0:
                print(f"frame {k}/{len(times)}", flush=True)
        browser.close()

    if args.only:
        print("stills written to", frames)
        return
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    vf = f"fade=t=in:st=0:d=0.35,fade=t=out:st={DUR - 0.7}:d=0.7"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%05d.png"),
                    "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-movflags", "+faststart", str(out)], check=True)
    shutil.copy(frames / "00093.png", out.with_name(out.stem + "_thumbnail.png"))
    print("wrote", out)


if __name__ == "__main__":
    main()
