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

## Third pass, after a design critique (2026-10-28)
- **All four loadouts, not one pair.** Chapter I has a loadout switcher; chapter V became "Who gets the call", with recorded first-call shares by server for every loadout, model and ordering, and a recorded callout per loadout (e.g. workspace shares were identical under all three orderings for gpt-oss-120b). The lab opens on web search.
- **List → sky.** In chapter I the chosen loadout unrolls into the literal list the model reads, in snapshot order, with names; scrolling on folds it into the similarity sky. Only the visual position animates between two real layouts (list order, embedding projection); no intermediate state is presented as data.
- **Dynamic transitions.** Highlight changes ease instead of snapping; the camera blends continuously between chapter keyframes along a lifted arc; cards rise into place from a visible resting state; screen-space picking works on tap and follows the morph.
- **Accessibility.** Muted text darkened/lightened for AA in both themes; buttons, case rows and nav targets at least 40px; the legend folds after the hero; Null Wall states each tile's own scale.
- **Coda** is now "What it means": three takeaways tied to chapters II, IV and V, with the inconclusive order-effect numbers kept at full size.

## Chapter III in 3D (2026-10-28)
- **Shuffle rack.** The four `siblings` tools stand as glass cards above the dome and step through all 24 recorded orderings (`balanced_permutations(siblings, 24)`, the EXP-001 order). Per ordering, all 8 requests fire their recorded first call as beams; ring = keyword-gold tool, cross + dashed ring on the gold card = other tool, stub = refusal. Model switch: gpt-oss-20b, gpt-oss-120b, qwen3.8-27b.
- **Slot strip.** Flat bars under the rack accumulate accuracy for requests whose gold sat in each slot, over the orderings played so far; at 24/24 for gpt-oss-120b it reads 22/48, 18/48, 16/48, 15/48 (sum 71/192, matching `results/exp001_siblings_120b_t0.json`). The preregistered thirds and the clustered-bootstrap gap stay in the DOM rail.
- **Data.** Per-trial calls are replayed from cassettes (`scripts/analyze_exp001.py` collect, temperature 0) into `docs/design/observatory-siblings-data.json`; replay totals match the recorded results for all three models (48, 71, 79 of 192).

## Instruments (2026-10-28)
Built from `scripts/build_observatory_data.py` (replay only) into `docs/design/observatory-data.json`, plus `observatory-archive.json` and `observatory-siblings-data.json`. The template takes `__DATA__` and `__SIB__` from those files.
- **Tool eyepiece** (click any star): full description split into token-weighted segments, nearest descriptions by embedding cosine, recorded calls as first call and as right answer, which tools it lost its job to and took the job of, and every trial involving it.
- **Mistake spectrograph** (from any lost/took chip): the two descriptions side by side with shared words marked, the recorded count by model, cosine and similarity percentile.
- **Request eyepiece** (from trials, or "Open this call" in the lab): the exact ordered tool list the model saw, the raw call it returned from the cassette (name and arguments, or the failed generation), and the grade; links to other orderings and models.
- **Lab modes:** "All three models" fires one beam per model from three telescopes on the dome; "Guess first" asks the viewer to pick before revealing (kept in the page only).
- **VII Plate archive:** all 14 experiments, nulls and not-run ones included, each with question, sample, verdict, key number, source and lesson.
- **VIII How sure we are:** a live bootstrap over the 8 recorded siblings families (badged simulated; seeded in the browser, so it approximates rather than equals the recorded 10,000-resample interval shown beside it) and seeing conditions from the determinism probe (the recorded 3 of 80 answers off the majority).
- **IX Your server:** drop a `tools/list` JSON; tools join the sky by TF-IDF similarity computed in the browser, with a token estimate (4 characters per token, labelled), the most alike pairs and the CLI to measure for real. Nothing is uploaded.
- **Star chart** (HUD): sortable table of all 82 tools with recorded counts. **Capture** (HUD): a still of the current view with its headline and source burned in.

## Real and shareable (2026-10-29)
- **EXP-008 live.** Chapter X runs the preregistered perception check (`docs/experiments/EXP-008.md`): sky vs table, counterbalanced by user id, accuracy and time per task. Stored with the artifact's `db` capability: `exp008/<user id>`, written and read only by that participant (rule level `interact`, so participants need the page shared as "can interact"); only the owner reads the collection. Checked after publish: empty collection; a probe row written as owner was invisible at `interact` level, then deleted.
- **Deep links.** Any eyepiece or chapter has a link: `#tool.<i>`, `#pair.<a>.<b>`, `#trial.<model>.<case>.<ordering>`, or a chapter id. "Copy link" in the HUD and in every eyepiece.
- **Story.** The hero opens on a recorded failure (rb09: "Click the Sign up button" → `list_pages`), which recurs as the running example in chapters I, IV and V; chapter II explains clustered intervals in plain words; the coda is a maintainer checklist linked to the chapters that prove each point.
- **Fly-through.** Scrolling the hero moves the camera on a Bézier path to the slit, up along the telescope and out above the sky.
- **UMAP layout.** Star positions use UMAP (cosine, 10 neighbours, seed 42) when installed, PCA otherwise; the footer names the layout used. Mistakes are attributed to the accepted tool most similar to the wrong call, so the data file is identical on every build.
- **Quality tiers** (auto/high/medium/low: pixel ratio, bloom, threads) and a recover banner on WebGL context loss.

## What the review kept from the rejected draft
- State by shape as well as colour (ring / cross / dashed ring / stub).
- The rail as a record: label as prominent as the number, source path, limit line.
- Bloom on marks only: the sky and stage are kept below the bloom threshold, so only stars, beams and the slit glow.

## What is still open (M0 look-test)
Frame time on a mid-range phone; legibility of the rail over the sky; colour-vision simulation of the server hues; whether the hover and lab work by touch; `prefers-reduced-motion` path (beams appear without growth, no drift). The prototype is a direction, not the shipped engine: ADR-016's own `engine/` (instancing, GPU picking, tiers, context-loss recovery) replaces its single-file code.
