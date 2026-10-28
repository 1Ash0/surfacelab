"""Score the Observatory film from its event log (written by render_video.py).

Synthesised in numpy, no samples or licences:
  - a dusk pad (A minor add9, slowly breathing, stereo-detuned) with a faint air bed;
  - a chime when a beam lands: bright pentatonic for a right call, a darker detuned pair for a wrong one,
    a soft tick for a refusal; dense passages are attenuated so the rack does not clatter;
  - typewriter ticks for the opening request, a whoosh through the dome's slit, a swell into each cut;
  - one shared convolution reverb for space; peak-normalised to -1 dBFS.

  python scripts/make_soundtrack.py out/observatory.events.json out/observatory.wav
"""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48_000
RNG = np.random.default_rng(42)


def env_adsr(n: int, a: float, d: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def smooth(x: np.ndarray, k: int) -> np.ndarray:
    return np.convolve(x, np.ones(k) / k, mode="same")


def main(ev_path: str, out_path: str) -> None:
    spec = json.loads(Path(ev_path).read_text())
    dur, events = float(spec["duration"]), spec["events"]
    n = int(dur * SR) + SR
    t = np.arange(n) / SR
    L, R = np.zeros(n), np.zeros(n)
    wet = np.zeros((2, n))  # bus sent to the reverb

    # --- pad: A minor add9 voicing, two detuned voices per note, slow breathing ---
    notes = [(55.0, .34), (82.41, .26), (110.0, .2), (123.47, .12), (164.81, .1), (220.0, .05)]
    breathe = .78 + .22 * np.sin(2 * np.pi * .07 * t - 1.2)
    master = np.minimum(1, t / 2.2) * np.minimum(1, (dur + .2 - t) / 1.6).clip(0, 1)
    for f, a in notes:
        for side, det in ((0, -.18), (1, .18)):
            v = a * (np.sin(2 * np.pi * (f + det) * t) + .18 * np.sin(2 * np.pi * 2 * (f + det) * t + .7))
            (L if side == 0 else R)[:] += v * breathe * master * .26
    # --- air: brown noise, low and moving ---
    for ch in (L, R):
        b = np.cumsum(RNG.standard_normal(n)); b -= smooth(b, 4801); b /= np.abs(b).max() + 1e-9
        ch += b * .05 * (.6 + .4 * np.sin(2 * np.pi * .05 * t + RNG.uniform(0, 6))) * master

    cuts = [e for e in events if e["k"] == "cut"]
    beats = sorted([e for e in events if e["k"] in ("hit", "miss", "refuse")], key=lambda e: e["t"])
    times = np.array([e["t"] for e in beats]) if beats else np.array([])

    # --- swell into each cut, a soft low thump on it ---
    for c in cuts:
        if c["t"] < .1:
            continue
        i = int(c["t"] * SR); m = int(.55 * SR)
        nz = smooth(RNG.standard_normal(m), 24) * np.linspace(0, 1, m) ** 2.2 * .16
        s = max(0, i - m); L[s:i] += nz[-(i - s):]; R[s:i] += nz[-(i - s):][::-1] * .9
        k = int(.9 * SR); th = .28 * np.sin(2 * np.pi * 46 * np.arange(k) / SR) * env_adsr(k, .006, .22)
        e = min(n, i + k); wet[0, i:e] += th[: e - i]; wet[1, i:e] += th[: e - i]; L[i:e] += th[: e - i] * .6; R[i:e] += th[: e - i] * .6
        # whoosh through the slit
        if c["name"] == "fly":
            m2 = int(2.6 * SR); w = RNG.standard_normal(m2)
            w = smooth(w, 30) * .5 + smooth(w, 6) * np.linspace(0, .5, m2)
            shape = np.sin(np.linspace(0, np.pi, m2)) ** 1.6 * .22
            e2 = min(n, i + m2); L[i:e2] += (w * shape)[: e2 - i]; R[i:e2] += (w * shape)[: e2 - i][::-1]

    # --- typewriter: the opening request types in over 0.75 s ---
    q = 27
    for j in range(q):
        i = int((j / q * .75 + .02) * SR); k = int(.012 * SR)
        click = np.diff(RNG.standard_normal(k + 1)) * env_adsr(k, .0005, .003) * .06
        L[i:i + k] += click; R[i:i + k] += click * .8

    # --- chimes on beam landings ---
    penta = [440.0, 554.37, 659.25, 880.0, 739.99, 987.77]
    for idx, e in enumerate(beats):
        i = int(e["t"] * SR)
        if i >= n or i < 0:
            continue
        dense = int(((times > e["t"] - .18) & (times < e["t"] + .18)).sum()) if len(times) else 1
        g = 1 / np.sqrt(max(1, dense))
        if e["k"] == "hit":
            f = penta[idx % len(penta)]; k = int(2.2 * SR); tt = np.arange(k) / SR
            s = (np.sin(2 * np.pi * f * tt) + .32 * np.sin(2 * np.pi * 2.0 * f * tt) + .12 * np.sin(2 * np.pi * 3.01 * f * tt)) * env_adsr(k, .004, .55)
            s *= .30 * g
        elif e["k"] == "miss":
            f = 311.13; k = int(1.6 * SR); tt = np.arange(k) / SR
            s = (np.sin(2 * np.pi * f * tt) + .8 * np.sin(2 * np.pi * f * 1.013 * tt) + .2 * np.sin(2 * np.pi * f * .5 * tt)) * env_adsr(k, .006, .38)
            s *= .24 * g
        else:
            k = int(.05 * SR); s = np.diff(RNG.standard_normal(k + 1)) * env_adsr(k, .001, .01) * .05 * g
        pan = .5 + .35 * np.sin(idx * 2.399)
        e2 = min(n, i + len(s)); seg = s[: e2 - i]
        L[i:e2] += seg * (1 - pan) * .9; R[i:e2] += seg * pan * .9
        wet[0, i:e2] += seg * (1 - pan); wet[1, i:e2] += seg * pan

    # --- shared reverb: 2.6 s exponentially decaying noise impulse ---
    k = int(2.6 * SR); ir_t = np.arange(k) / SR
    for ch, dst in ((0, L), (1, R)):
        ir = RNG.standard_normal(k) * np.exp(-ir_t / .62); ir = smooth(ir, 3); ir /= np.sqrt((ir ** 2).sum())
        size = 1 << int(np.ceil(np.log2(n + k)))
        rev = np.fft.irfft(np.fft.rfft(wet[ch], size) * np.fft.rfft(ir, size), size)[:n]
        dst += rev * .42

    mix = np.stack([L, R])[:, : int(dur * SR)]
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    mix /= np.abs(mix).max() / 10 ** (-1 / 20)
    pcm = (mix.T * 32767).astype(np.int16)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(f"wrote {out_path}: {dur:.1f} s, {len(beats)} chimes, {len(cuts)} cuts")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
