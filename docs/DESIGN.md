# DESIGN — the Observatory (web experience)

The Observatory is half the project, not a skin on it. Someone lands from a post, usually on a phone, and within 30 seconds sees a **3D scene made of real measurements** that they can touch, and that is unmistakably made by a person. Then they can go as deep as an engineer wants: numbers, intervals, trials, methodology.

## 1. Position on 3D (decision, ADR-015)
3D leads the experience. It is used where it genuinely beats 2D, and kept honest by four rules.

**3D is for:** space and topology (what is near what, what is entangled with what), flow (where tasks land), and time (how a surface drifts).
**3D is never for:** reading off quantities by depth, comparing bars, or stacking values. Those stay flat.

Four rules:
1. **Every visual encodes a measurement.** No ambient decoration. If a particle, glow or motion is on screen, a field in `results/` or `runs/` drives it.
2. **Evidence rail.** Every 3D scene has a persistent 2D panel (DOM, not canvas) with the exact numbers: n, families, rates, intervals, epistemic tags. The scene gives intuition; the rail gives the claim. The rail is always one tap away and open by default on desktop.
3. **Channel discipline.** Each scene declares which visual channel encodes which variable (section 4). No channel is reused for two meanings in one scene. Colour is never the only channel.
4. **Recorded vs simulated, always visible.** A scene driven by anything other than recorded trials shows a `simulated` badge that cannot be dismissed.

Distances in projected spaces (embeddings) are **not** measurements of confusion. Scenes that use them say so in a persistent caption, and show confusion only as explicit edges.

## 2. Identity ("Dusk Observatory")
This project does **not** inherit the formal, document-like look of ctxcheck and the other projects. Those are reports; this is an **instrument you operate**. It shares only the epistemic tags and the honesty rules with them. The goal is one step above: atmospheric, tactile and a little cinematic, so the 3D scenes feel like looking through something precise, while the evidence rail stays calm and exact.

Brainstormed and rejected: paper stage (still reads as a formal document), neon nebula on black (generic, glow means nothing), pure specimen-cabinet (kept only as a materials idea).

### Concept
You are at an observatory at dusk. The scene is the sky; the rail is the instrument panel. Tools are small lit objects hanging in depth; measurements are the only things that move or glow.

### Stage (atmosphere is allowed; meaning is not)
- **Backdrop:** a deep indigo-to-warm-horizon vertical gradient with very slow, subtle parallax against camera movement, plus depth fog that fades distant points and edges. Proposed tokens: `--sky-top #0B1020`, `--sky-mid #151B33`, `--horizon #3A2A3C`, `--horizon-glow #6B4A4F` (final values chosen in the W0 look-test on a real phone, then recorded).
- **Rule:** backdrop, fog and parallax are *stage*, never data. They may not vary with any measurement, and no data mark may be coloured by them. Anything that glows, pulses or moves because of data is a mark.
- **Daylight variant** (for embeds on light docs sites, print and screenshots): same geometry, cream ground, deep-ink marks, no gradient. It is a first-class theme, not an afterthought. The embed picks it automatically from the host's colour scheme.

### Marks (the "lit glass" material)
- Points are small **glass beads**: a soft inner highlight, a thin rim, and a gentle falloff, drawn as SDF sprites in the fragment shader (no textures). Hover or selection adds a *reticle* ring, not a bigger glow.
- **Edges** are fine luminous filaments with width and opacity driven by the measured rate; a floor hides zeros. No edge is drawn without a measurement.
- Contact depth is faked cheaply (a faint ground haze, soft occlusion by fog) so the scene feels spatial without costly shadows. High tier may add a restrained bloom on marks only; low tier has none.
- **Server colours:** six hues chosen to hold up on both the dusk and daylight stages and for colour-vision deficiency, each with a shape. Candidate set to test: amber, teal, coral, lilac, lime, sky. Vermilion-red is reserved for failure and is excluded from this set.
- **Semantic colours:** correct/measured = a bright **mint**; wrong/collision/regression/failed start = a **vermilion-coral** with an icon; "possible" (drift flags) = a hollow **brass** marker with an icon. Never colour alone.

### Instrument details (what makes it feel hand-made)
- **Brass hairlines:** thin warm-metal lines (`--brass #C9A26B`, tuned per stage) used for reticles, tick marks on sliders and axes, coordinate readouts, and the border of the evidence rail. Used sparingly; they are the signature accent.
- **Selection mark = the reticle:** a small four-tick ring with a notch showing the chosen tool; filled mint when correct, vermilion with an icon when wrong. It appears in every scene, rail and post image.
- **Readouts:** a quiet monospace HUD in the corners (camera, selection id, n, tier) styled like instrument coordinates. Informative first, decorative second; it can be hidden.
- **Grain:** a very light film grain on the backdrop only, off on low tier and in reduced-motion.

### Evidence rail and chrome (the "instrument panel")
- Frosted-glass panel over the stage (blurred backdrop, 1px brass-tinted edge), with a solid-surface fallback when blur is unavailable or on low tier. Text on it must hold WCAG AA contrast in both themes.
- Controls feel physical: sliders with tick marks and detents, toggles that click, scrubbers with inertia. Buttons are quiet; the scene is the star.
- Numbers use tabular mono figures; the headline number is large, with its interval set directly beneath it on the same baseline grid. The interval is never smaller than "secondary text" and never hidden behind a tap.

### Type
- **Display:** an expressive but legible face with character for chapter titles and the big numbers (a refined grotesk or a high-contrast serif; two candidates compared in the look-test). Used at large sizes only.
- **Text:** a clean humanist sans for rail and body.
- **Data:** a mono for labels, ids, coordinates and figures.
- Labels in the scene are HTML overlays (crisp, selectable, accessible), not baked into textures.

### Motion language
Slow, damped, with inertia. Things *settle* and then rest; when the user stops, the camera eases to a still frame and the caption appears. Cursor/touch gently influences light and parallax (never data). One consistent easing family. Chapter transitions preserve object identity so the eye follows the same tools. Nothing loops without a reason; `prefers-reduced-motion` replaces motion with jump cuts and static frames.

### Sound
None by default. (An optional, off-by-default subtle tick on detents is Later.)

### Posts and video
Captures inherit this look directly: a still from the Tour is already a finished post image. Number and interval burned into a corner in the display and mono faces.

### Checks before this identity is accepted (M0 look-test)
1. A real phone, outdoors-bright and indoors-dim: can you read the rail and tell correct from wrong without colour?
2. A screenshot compressed for LinkedIn: do the beads and filaments survive?
3. A colour-vision-deficiency simulation of the six server hues and the three semantic colours.
4. Dusk vs Daylight rendered side by side from the same data.
5. Does the stage ever look like it *means* something? If so, tone it down.

## 3. Experience architecture
| Mode | What it is | Route |
|---|---|---|
| **The Tour** | One continuous 3D canvas. Scroll moves a camera along rails through 5 chapters and a coda, each one finding from `docs/FINDINGS.md` opened by a predict-then-reveal hook (ADR-026): The Request → What didn't matter → Ties → Real servers → A second server → Who wins. Ends in "run it on your servers" (the Bench) | `/` |
| **The Observatory** | Free exploration of all scenes for a chosen surface or experiment: scene switcher, evidence rail, filters, URL-addressable state | `/o/[surface]/[scene]` |
| **The Bench** | Drop your own surface (tools/list JSON or a surfacelab snapshot). Everything computable in the browser runs locally: Request Anatomy, lexical-similarity Galaxy, description stats. Measured scenes need a report file generated by the CLI. File never leaves the browser | `/bench` |
| **Replay Theatre** | Step through one recorded trial: what the model saw, in what order, what it chose, how it was graded | `/replay/[run]` |
| **Reports** | Flat, printable 2D reports: intervals, ladders, matrices (the engineer's view) | `/report/[id]` |
| **Lab** | Preregistrations, results, deviations, notebook | `/lab`, `/notebook` |

Landing must work with the 3D layer failing (no WebGL, reduced motion, slow device): it degrades to the static chapters with 2D figures and the same evidence rails.

## 4. Scenes (each declares channels; each has a fallback and a table)

> **ADR-026 (proposed) changes this list:** S1 runs on real loadouts; S2 v1 uses EXP-013 confusions; S4 is repurposed to "add a server" (edges = where the first call landed, not cross-server collision); a flat **Null Wall** is added; S5 is Observatory-only; S6 moves to Later; S7 waits for the EXP-006 re-probe. Scene specs below are updated when ADR-026 is accepted.

Legend of channels: **pos** position, **size**, **hue**, **shape**, **edge** width/opacity, **motion**, **z-time** depth as time axis.

### S1 Request Anatomy (M1, real data, no model calls needed)
A single request unrolled in space: system prompt, user message, and the **tool list as a stack of slabs**; slab thickness = description+schema tokens (exact count). Order = position along the stack. You see immediately where the tokens go (a handful of tools often dominate). Later, a "beam" shows which slab the agent chose.
- Channels: pos(z along stack)=list position; size(thickness)=tokens; hue=server; selection mark=chosen.
- Data: `Surface` + token ledger (+ trial result when present). Fallback: stacked horizontal bar + table.

### S2 Surface Galaxy (v0 M2 similarity only; v1 M4 with measured collisions)
Tools as instanced points positioned by a 3D projection of description embeddings (precomputed offline). Edges appear **only** for measured mis-selection, with width/opacity = confusion rate and a floor so zero is invisible.
- Channels: pos=embedding projection (caption: "similarity, not confusion"); hue+shape=server; size=tokens or defect score (toggle); edge=measured confusion; motion=none except on selection.
- Interactions: orbit/zoom, hover label, click → panel (description, tasks it stole, tasks it lost), filter by server, "show only confused pairs", search by tool name. Picking via GPU id buffer.
- Fallback: 2D canvas projection + sortable pair table.

### S3 Shuffle Rack (M2, EXP-001)
The tool list as a **rack of cards** in perspective. A beam drops onto the card the agent chose for a case. A scrubber steps through permutations of the same case; the rack reorders with damped motion and the beam shows whether the choice follows the tool or follows the slot. A **position ghost row** accumulates hits by slot across all permutations (the position-bias signature, drawn in 2D inside the scene as a flat strip).
- Channels: pos=list slot; hue=server; selection mark=chosen; accumulation strip height=hit rate by slot (flat, with whiskers).
- Fallback: the Order strip (flat heatmap, families × positions).

### S4 Merge Collider (M4, EXP-004)
Two or more server clusters are pulled together (a controlled force animation, deterministic from a seed). Namespacing arms (`none | prefix | server-qualified`) toggle live from recorded results. Collision edges appear between clusters where tasks were stolen; thick = frequent. Watching `prefix` thin the edges but not remove them is the point.
- Channels: pos=force layout seeded from the Galaxy; hue+shape=server; edge=measured cross-server collision rate; motion=the merge transition (user-triggered, skippable).
- Fallback: collision matrix heatmap with whiskers.

### S5 Selection Rain (M6, EXP-005)
Task particles fall through a shelf of tools and **land on the tool the agent chose**. Sliders for N (tool count), distractor kind and arm (`full | retrieval | deferred`). Every particle is a recorded trial; the particle count and interval for the current cell are always in the rail. Wrong landings turn vermilion and settle in a pile by wrong-tool.
- Channels: pos(x)=tool; motion=fall, landing; hue=correct/wrong; size=none.
- Fallback: stacked bars with intervals.

### S6 Edit Migration (M3, EXP-003)
Pick an edit from the ladder. Particles of the same cases flow before → after: those that **change** landing tool are traced; tool slabs resize to the edit's token delta so the cost is visible as mass. Verdict chip shown.
- Channels: pos=tool; motion=migration path; size=tokens; hue=correct/wrong after.
- Fallback: edit verdict ladder (flat).

### S7 Pulse Ribbons (M5, Layer C)
Time runs along the z axis. Each server is a ribbon whose thickness is solid when alive and breaks into dashes when failing; drift events are bursts on the ribbon with class glyphs; `instruction_like` is drawn as a hollow "possible" marker with an icon, never as a verdict.
- Channels: z-time; lane=server; ribbon style=outcome class; glyph=drift class; size of burst=token delta.
- Fallback: flat timeline grid.

## 5. Evidence rail (spec)
Always includes: scene title; epistemic tag(s); n (cases, families, trials); the headline number with interval; the model ids and rendering used; a link to the run/experiment; "download data" (JSON); a "what this does not show" line. Interactions in the scene update the rail. The rail is keyboard reachable and read by screen readers.

## 6. Choreography and camera
- Camera rails per chapter (authored as data: position, target, fov, easing, hold), scroll-driven in the Tour, button-driven in the Observatory.
- Free orbit with damping and clamped zoom; **reset view** always visible; double-tap/double-click to focus a tool.
- One depth-of-field-like cue only: fade distant labels and edges, no heavy post-processing. Optional restrained bloom on marks only (never on the stage), high tier only; off on medium and low.
- Transitions between scenes reuse the same instanced points where the entity is the same (a tool stays a tool as you move Galaxy → Merge Collider), so the viewer's eye follows objects instead of a cut.
- Everything deterministic from (data, seed, time): no hidden randomness in layout, so screenshots and captures are reproducible.

## 7. Rendering decisions (ADR-016; hand-built so you can defend every line)
- **three.js vanilla** (no react-three-fiber) wrapped in a small `engine/` of our own: renderer, camera rig, loader, picking, quality tiers, context-loss recovery. React only for page chrome. Reason: understanding and control; fewer abstraction layers between you and the GPU.
- **Custom `ShaderMaterial`s** for instanced points (size, shape sprites via SDF in the fragment shader) and for edges (screen-space-width lines, because native GL lines are 1px). Default materials only for prototyping.
- **Instancing** for points, cards and particles; one segment buffer for edges. Targets in the low thousands of points, not millions.
- **Picking:** GPU id-buffer for points; spatial index fallback. No per-object raycasting.
- **Layout:** Galaxy positions precomputed in Python (UMAP) and shipped in a binary buffer; Merge Collider force layout is a small deterministic simulation in a Web Worker (our own, a few dozen lines, so it can be explained).
- **Labels:** HTML overlays positioned from projected coordinates, decluttered, capped in count.
- **Data:** typed arrays from the binary buffers; TS types generated from the pydantic JSON Schema (single source of truth; drift check in CI).
- **WebGPU:** out of scope for v1 (Later).

### Quality tiers and budgets (targets, to be measured and recorded; never stated as achieved until measured)
| Tier | Selected when | Behaviour |
|---|---|---|
| `high` | desktop GPU, no data saver | full instancing, faint ground haze, restrained mark bloom option |
| `medium` | integrated GPU / modern phone | no shadows, fewer particles, labels capped |
| `low` | slow device, data saver, `prefers-reduced-motion` | static frames, 2D figures with rails |
Targets: first meaningful frame on a mid-range phone within a stated JS budget; interactive frame rate at `medium`; initial route JS (excluding lazily loaded three chunk) within a budget set once a baseline exists; regressions in CI are bugs. Context loss is handled by rebuilding from the loader, not by an error screen.

## 8. Accessibility
- **Table mode (`t`)** and **describe mode (`d`)** on every scene: the same data as a sortable table, and a plain-language summary ("12 tools, 3 servers, 4 confused pairs; strongest: …").
- Keyboard: arrows orbit/step, `+/-` zoom, `Tab` through tools, `Enter` focus, `?` help, `r` reset, `g` toggle graphics.
- `prefers-reduced-motion`: no auto-play, no damped drift; static camera positions with jump cuts.
- Colour: never the only channel; shapes, icons and labels; colour-blind-safe sets; WCAG AA contrast for text and focus states.
- Screen readers: rail and tables are real DOM; canvas has an `aria-label` and points to the table.

## 9. Capture and share (turns the Observatory into posts and videos)
- **Deterministic capture mode:** `?capture=1&seed=…&t=…` freezes time, fixes the viewport and quality tier, hides UI. A Playwright script steps the scene at fixed timestep and writes frames, stills and OG images. This feeds the demo videos in the design subsystem with real measured scenes rather than mock ups.
- **OG cards:** each report/scene permalink gets a build-time still of the exact moment (selected tool, camera, rail headline).
- **Permalinks:** scene, camera, selection, filters and slider values in the URL.
- **Post kit:** `make posts` generates stills and a short capture per finished experiment with the number and its interval burned into the corner.

## 10. Embeds and adoption
- `<surfacelab-galaxy src="…">` web component (Shadow DOM, lazy three chunk) so a server maintainer can embed their galaxy and report badge in a README site or docs.
- GitHub Action publishes the report site to Pages and comments on a PR with a still of the changed scene plus the delta table.
- Static SVG badge (robustness score, availability).

## 11. Testing the frontend
- Data decode unit tests (buffers, schema version, bad files).
- **Visual regression** of scenes in capture mode with software GL in CI (fixed seed, fixed tier); tolerance set once, diffs reviewed by a human.
- Performance smoke: frame-time and bundle-size checks recorded in CI.
- Accessibility: automated axe checks on chrome and rails; manual keyboard walk-through checklist per scene.
- Two-sided tests for any visual rule that encodes a state (e.g. a scene must show vermilion for wrong choice and must not for correct).

## 12. Perception check (EXP-008, see EVAL_DESIGN)
Does the 3D Galaxy actually help? A small preregistered, exploratory study with peers: find the most confusable pair on a surface using (a) Galaxy + rail, (b) table only. Measure time and correctness. Report honestly, including a null. If 3D does not help, the scene stays but our claims about it change.

## 13. Component sources
Chrome only: tabs, tables, dialogs, command palette, tooltip, slider, toggles, rail layout. Search first; retrieve only what you will use (quota). Adapt to the identity; no default styling left. Record licence and attribution. **Scenes are never built from component libraries.**

### Component register
| Component | Source | Licence | Used in | Modified how |
|---|---|---|---|---|
| (fill as used) | | | | |

## 14. What would make this bad
Default shadcn look; neon nebula that means nothing; glow on anything that is not a measured mark (glass-bead glow on data marks is the one allowed exception, stage glow never); a stage that looks like it carries meaning; 3D bars; labels baked into textures; animation that replays every visit; a hero GIF instead of a live scene; scenes that only work on the author's laptop; an evidence rail that hides the interval; proximity implying confusion; a fallback that is a broken page.
