# ADR-027 — The Dusk Observatory, built

**Status:** proposed (2026-10-28), with ADR-026 · **Confirms and sharpens:** ADR-015 (3D leads), ADR-017 (Dusk Observatory) · **Keeps:** every honesty rule in DESIGN §1, ADR-016, ADR-018, ADR-019, ADR-020
**Prototype:** `docs/design/observatory-prototype.html` (recorded data only; three.js r128, no build step)

## History
A first draft of this ADR (the "Plate Room": a flat, print-like blink-comparator style) was rejected by the project owner on 2026-10-28: it lost the 3D observatory that was the intent from the start (MASTER_PROMPT, PROJECT, ADR-015). That draft is in git history (commit `12a323e`). This ADR replaces it.

## Decision
The Tour is a **scroll-driven 3D observatory at dusk**:

1. **The hero is a place.** A dome on the horizon at dusk, its slit open and lit from inside, a brass azimuth ring with graduations on the ground, and a telescope pointing out of the slit at the sky. Scrolling flies the camera up out of the dome into that sky.
2. **The sky is the data.** Every star is one real tool from the EXP-013 loadouts (82 tools: Playwright, Chrome DevTools, Brave, Tavily, DuckDuckGo, Filesystem, Git, GitHub, Context7, AWS Documentation, Fetch). Position = a 3D projection of description embeddings (`text-embedding-3-small`, PCA), captioned *similarity, not confusion*; size = tokens; hue = server. Hover shows the tool's real description.
3. **The telescope's beam is the model's call.** Every beam is one recorded first call, drawn from the telescope tip to the tool it landed on, ending in a reticle (closed ring = right; crossed = wrong, with a dashed ring on the accepted tool; a short grey stub = refusal). This is the thread through every chapter.
4. **Confusions are filaments** between the right tool and the wrong pick, opacity by trial count, and appear only where trials recorded them.
5. **Chapters follow ADR-026**, each with a predict-then-reveal hook and a docked evidence rail (number, interval, label, source file, "does not show"). Flat comparisons (the Null Wall, the slot bars) are 2D panels over the sky, as ADR-015 requires.
6. **The Lab** lets the viewer pick a model, a loadout and a request, fire the recorded call, switch which server is listed first, and orbit the sky.

## Second pass (2026-10-28)
- **Two times of day.** Dusk (default) and Morning: the sky, ridge, dome, stars and threads transition together; in Morning, stars become ink marks on a cream dawn and blending switches from additive to normal so marks stay legible. System light mode opens in Morning.
- **Shaders.** Sky with scattering-like gradient, sun glow, a two-layer procedural ridge and a faint, low-contrast Milky Way band (scenery only, captioned as such in the footer); dome shaded by a sky rim light; lamp light pooled on the ground in front of the slit; stars with core, halo and diffraction spikes; beams and threads as tubes with a travelling pulse.
- **Understanding.** A "how an agent picks a tool" chapter before any data; a persistent legend; named chapter navigation; each chapter's "what you're looking at" line; chapter V plays two waves (Playwright first, then Chrome DevTools first) with the recorded count.

## What the review kept from the rejected draft
- State by shape as well as colour (ring / cross / dashed ring / stub).
- The rail as a record: label as prominent as the number, source path, limit line.
- Bloom on marks only: the sky and stage are kept below the bloom threshold, so only stars, beams and the slit glow.

## What is still open (M0 look-test)
Frame time on a mid-range phone; legibility of the rail over the sky; colour-vision simulation of the server hues; whether the hover and lab work by touch; `prefers-reduced-motion` path (beams appear without growth, no drift). The prototype is a direction, not the shipped engine: ADR-016's own `engine/` (instancing, GPU picking, tiers, context-loss recovery) replaces its single-file code.
