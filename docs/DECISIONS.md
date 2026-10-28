# DECISIONS — ADRs (append-only)

Format: **ADR-NNN Title** — Status (proposed / accepted / superseded by ADR-X) — Context — Decision — Consequences — Revisit trigger.
Changes of direction follow the pivot protocol: new ADR, update affected docs, notebook entry.

---

**ADR-001 Measure robustness, composition and availability; do not rebuild lint or fixed-set eval** — accepted
Context: mcp-toolgauge and several linters ship lint and fixed-set selection eval (see PRIOR_ART). Original plan was a lint+bench+gateway product.
Decision: scope the project to what shipped tools did not cover when checked: order and paraphrase robustness, per-edit tradeoffs, cross-server collision, sandboxed availability and drift.
Consequences: smaller overlap, clearer novelty claim, dependent on verification task 1 being honest.
Revisit: if verification finds the gaps already shipped, shrink or pivot (measurement-only reports).

**ADR-002 Selection graded deterministically by the emitted tool name** — accepted
Context: judge reliability problems (Project 1); the quantity of interest is which tool is chosen.
Decision: primary outcome = first tool call in the gold set; no LLM judge for primary outcomes.
Consequences: cannot grade multi-step quality or "reasonable alternative" tools; gold sets must be curated.
Revisit: agentic mode (M6) may add secondary graders, never replacing the primary.

**ADR-003 Consume mcp-toolgauge case format if licence and schema permit** — accepted (2026-10-26)
Context: adoption is easier if users can reuse existing cases.
Decision: consume. Licence is MIT (confirmed 2026-10-26). Case schema uses `kind` ∈ {positive, sibling, abstain}, compatible with surfacelab's model. Critical difference: toolgauge's cache key excludes tool order; surfacelab's must include it (per ADR-005). Cases imported from toolgauge must be re-recorded under surfacelab's harness before being used in any order sweep.
Consequences: import adapter in `cases`; document the re-recording requirement; README states clearly that surfacelab complements rather than replaces toolgauge.
Revisit: schema changes upstream.

**ADR-004 Copy Project 1 pieces (cassette, stats, budget, tags); no shared package yet** — accepted
Context: extracting a shared library early couples two moving projects.
Decision: copy with attribution; extract only if Project 3 needs the same pieces.
Consequence: drift between copies is possible; track in notebook.

**ADR-005 Rendering is a recorded, studied variable** — accepted
Context: how tools are presented (provider tool param vs prompt text, ordering, formatting) may alter selection.
Decision: `render` stores exact bytes sent; cassette key includes them; EXP-001 reports the rendering used.
Consequence: results are scoped to the renderings tested.

**ADR-006 Unit of analysis is the case family; intervals are clustered** — accepted
Decision: bootstrap over families; Wilson for simple proportions only when independence holds; McNemar for paired comparisons with discordant counts shown.
Consequence: needs more families, fewer trials per family.

**ADR-007 Pulse runs untrusted servers only in a sandbox; no bulk registry crawl in v0.1** — accepted
Context: starting arbitrary npm/PyPI servers executes untrusted code.
Decision: container with no network, read-only FS, no host credentials, limits, non-root; targets are the user's own servers and a curated list. Bulk measurement needs a separate ADR and a defensible sampling frame.
Consequence: no headline ecosystem-wide start-rate in v0.1.

**ADR-008 No `tools/call` against real servers in v0.1** — accepted
Context: calling real tools can cause side effects.
Decision: v0.1 reads surfaces only. Agentic mode uses fixture servers with canned results.
Consequence: cannot study end-to-end behaviour on real servers yet.

**ADR-009 Name is `surfacelab`** — accepted (2026-10-26)
Context: name checked on 2026-10-26.
Decision: `surfacelab`. PyPI: unclaimed (404 confirmed). npm: unclaimed (confirmed). No obvious trademark conflict found.
Consequences: claim PyPI and npm at v0.1 release. Name can still change before that if a conflict surfaces, but treat it as settled for building.
Revisit: if a conflict is reported before v0.1.

**ADR-010 Single-turn first-call selection in v0.1** — accepted
Decision: grade the first tool call only; step cost and recovery deferred to M6.
Consequence: EXP-003 cost reporting in v0.1 is token cost only.

**ADR-011 Default provider is Anthropic via the cassette layer; models pinned by exact id per experiment** — proposed
Consequence: results are scoped to the models run; add providers only after cassette layer is proven.

**ADR-012 Hero views are WebGL; flat comparisons stay 2D** — superseded by ADR-015 (the 3D rejection of terrain/bars still stands)
Decision: Galaxy and Rain use WebGL because of point count and motion; order strip, ladder, matrices stay SVG/canvas. 3D terrain and 3D bars rejected.

**ADR-013 Gateway deferred** — accepted
Decision: view-serving proxy is Later with an evidence trigger (ROADMAP).

**ADR-014 EXP-005 crosses count x distractor kind x arm, not just count** — accepted
Context: literature numbers conflict; tool count and tool similarity are confounded.
Consequence: larger design; cap N levels by budget.

**ADR-015 3D leads the Observatory; seven scenes; evidence rail mandatory** — accepted
Context: the frontend is half the project and should be memorable and experiential, but 3D can mislead.
Decision: seven hand-built scenes (Anatomy, Galaxy, Shuffle Rack, Merge Collider, Rain, Edit Migration, Pulse Ribbons) plus Tour, Bench, Replay Theatre. 3D is for space, flow and time only; depth never encodes a quantity; every scene has a flat DOM evidence rail, table and describe modes; recorded vs simulated is always visible.
Consequence: more frontend work and a hard honesty rule set. Flat figures (order strip, edit ladder, collision matrix, timeline) remain as reports and fallbacks.

**ADR-016 Vanilla three.js with our own engine layer and custom shaders** — proposed (decide after W0 spike)
Context: you must be able to defend every core line; scenes are few and custom.
Decision: three.js without react-three-fiber; own `engine/`; custom ShaderMaterials for sprites and screen-space lines; React only for chrome; WebGPU Later.
Alternatives: raw WebGL2 (more learning, slower), R3F (faster, more abstraction), regl/deck.gl.
Revisit: W0 spike results (frame time on a phone, effort).

**ADR-017 Identity is "Dusk Observatory" (dark atmospheric stage, glass-bead marks, brass instrument details) with a first-class Daylight variant** — proposed (confirm after the W0 look-test)
Context: the Observatory should feel like an instrument, not a formal report, and must not inherit the ctxcheck look. Neon-on-black is generic; paper reads as a document. Embeds and print need a light theme.
Decision: stage atmosphere is allowed but never encodes data; only measured marks glow or move; Daylight variant is selected automatically for embeds on light hosts. Tokens, display font and server hues are fixed by the look-test in DESIGN §2 and recorded here.
Supersedes: the earlier "paper default, night toggle" proposal.

**ADR-018 Each scene must run from recorded data with a labelled simulation fallback only for development** — accepted
Decision: built early on fixtures; anything simulated carries a permanent `simulated` badge; no simulated scene ships in the Tour.

**ADR-019 Capture mode and deterministic clock from the start** — accepted
Decision: all scenes take time and seeds from the engine; Playwright capture and visual regression are part of the build, not a late add-on. Reason: posts, videos and CI depend on it.

**ADR-020 EXP-008 perception check is exploratory and reported either way** — accepted
Decision: small, preregistered, peer-run; a null result is published and changes copy, not hides.

**ADR-022 Docker sandbox for EXP-006 and untrusted server probes** — accepted (2026-10-27)
Context: ADR-007 accepted the goal but deferred the sandbox design ("Docker sandboxing is a v0.2 extension" note in pulse.py). EXP-006 requires probing a curated list of third-party servers; plain subprocess is not safe for untrusted code.
Decision: `probe_docker(image, server_command, ...)` wraps `probe()` with fixed security flags: `--network=none --read-only --memory=256m --cpus=0.5 --user=1000:1000 --tmpfs=/tmp:size=32m --security-opt=no-new-privileges --init`. If the Docker daemon is not running, `DockerNotAvailableError` is raised immediately. `probe()` (plain subprocess) remains the path for fixture servers. If Docker is available, EXP-006 is unblocked.
Consequences: fixture server tests in CI continue using `probe()` with no Docker dependency. An image must be built or pulled per server type. Revisit for Podman, gVisor, or non-Python servers.

**ADR-021 Live providers use free-tier models only; all are accessed via OpenAI-compatible API** — accepted (2026-10-27)
Context: direct Anthropic billing requires a paid account; the project is student-budget. OpenRouter, Groq, NVIDIA, and Gemini all expose an OpenAI-compatible endpoint; Mistral does too. ADR-011 (Anthropic default) is superseded by this.
Decision: use the `openai` Python package with provider-specific `base_url` and `api_key` from environment. Model ids are pinned per experiment as before. The cassette key includes `(provider_slug, model_id, request_bytes)` — not `request_bytes` alone — so entries from different providers never collide.
Consequences: results are scoped to free-tier models (rate-limited, smaller context windows, may differ from paid tiers); cassette key schema widens by one field; AnthropicProvider is renamed to OpenAICompatProvider; ARCHITECTURE.md updated.
Revisit: if a free-tier rate limit blocks an experiment, add a paid-tier path with `--max-usd` guard unchanged.

**ADR-023 Follow-up experiments EXP-009–012 move to near-duplicate surfaces, with validated gold** — accepted (2026-10-28)
Context: EXP-003, EXP-004 and EXP-005 were mostly uninformative because goodserver is solved: both models score 100% on it, and its five distinct tools never compete. The one effect found (a position effect on `siblings` at temperature 0, `results/exp001_siblings_t0_analysis.json`) comes from near-duplicate tools, but only 8 families existed. EXP-005 also showed that some "wrong" answers picked a tool that could arguably do the job, so single-tool gold can mislabel defensible choices.
Decision:
1. Follow-ups EXP-009 (order), EXP-010 (description edits), EXP-011 (cross-server overlap) and EXP-012 (distractor dose) are preregistered separately; the original EXP-001–005 verdicts stand unchanged.
2. New fixtures, written and committed before any run: 3 more near-duplicate surfaces of 4 tools (to join `siblings`), 8 cases per surface (32 families), and 3 pairs of overlapping servers with 24 cross-server cases for EXP-011.
3. **Gold validation:** before any live run, a person who did not write the case reads each request with the full surface and marks every tool that would correctly satisfy it. Cases where the marking disagrees with the author's gold are rewritten or the gold set widened (multi-tool gold is already supported), and the outcome is logged in `fixtures/cases/gold_validation.csv`.
4. All runs use temperature 0, record refusals rather than retrying them, and use the analysis scripts from the original experiments where the statistic is the same.
5. **Surfaces must have a right answer.** The original `siblings` tools turned out to be synonyms (same description reworded), so its gold was set by keywords, not meaning. New surfaces (`nd_*`) give each tool near-identical names but one stated difference in scope.
6. **Stop rule.** Whatever verdicts EXP-009–012 reach (confirmed, absent or inconclusive), they are the final answers to these four questions in v0.1. No further follow-ups; inconclusive results are published as inconclusive. The only exception is the Revisit clause below, which would change the question, not extend it.
Consequences: about 3,200 trials, estimated at roughly 1.1–1.3M tokens from measured per-call sizes (vs about 2.3M recorded for EXP-001–005), within a day of the 7-org free-tier budget. Gold validation is a human step and gates every run.
Revisit: if gold validation shows the near-duplicate cases are too ambiguous to have a single right answer, the order and edit questions should be asked as "which of the acceptable tools" rather than "right vs wrong".

**ADR-024 Real-server surfaces and a second model family (EXP-006 targets, EXP-013, EXP-014)** — accepted (2026-10-28)
Context: EXP-009–012 closed under the ADR-023 stop rule: on surfaces we wrote, with distinct scopes, gpt-oss selects almost perfectly; the only order effect is synonym tie-breaking. Two gaps remain: all surfaces are ours, and all models are one family.
Decision (if accepted):
1. EXP-006 uses the curated list in `fixtures/targets/exp006_targets.json`: 19 open-source servers from the MCP steering group and named vendors, chosen to be recognisable and to include servers that overlap (two browser servers, four web/search servers, three databases). Probes stay inside `probe_docker()`; only `initialize` and `tools/list` are sent. Servers that demand a credential get the literal placeholder `surfacelab-placeholder` in a `--network=none` container.
2. EXP-013 asks a **new** question (real loadouts, similarity vs confusion); it is not a follow-up to EXP-009–012, so ADR-023's stop rule does not apply. Same gold validation as ADR-023.
3. EXP-014 replicates three earlier findings on `qwen/qwen3.8-27b`, the only non-gpt-oss chat model with tool calls on the Groq free tier (checked 2026-10-28). Earlier verdicts stand; EXP-014 reports whether they generalise.
4. Reporting: findings describe description patterns, never a vendor as bad (existing rule); quotes come only from committed snapshots.
Consequences: about 1,400 model trials plus 19 container builds; one human gold-validation step gates EXP-013. Loadouts must render under 6,000 tokens to fit the 8K TPM free-tier limit.

**ADR-025 EXP-013 asks which real server wins a tie, not only right vs wrong** — accepted (2026-10-28, revised before any EXP-013 trial)
Context: real servers overlap, so many realistic requests have accepted tools on two or more servers; scoring them only as right or wrong would hide the one effect that replicated across both model families (first-listed preference among equivalent tools, EXP-001 follow-up and EXP-014). The first EXP-013 draft also lost its most visible overlaps to the free-tier size limit, and an attempted gold sheet was filled without the tool descriptions and invented tool names, so it was discarded.
Decision: EXP-013 is revised (docs/experiments/EXP-013.md): H1 is first-listed server share on shared cases, H2 is accuracy on unique cases; server blocks are rotated; loadouts are Playwright + Chrome DevTools, Brave + Tavily + DuckDuckGo, Filesystem + Git + GitHub, Context7 + AWS Documentation + Fetch, all under 6,500 provider tokens for every model. The gold sheet shows each candidate tool's full description beside the request.
Consequences: 396 trials. The case class (shared or unique) is set by gold validation, not by the author. The headline is about model behaviour, never a vendor's quality.

**ADR-026 The Tour follows the findings, not the experiment list** — proposed (2026-10-28); full text `docs/adr/ADR-026-tour-follows-findings.md`
Context: the planned Tour (Anatomy → Galaxy → Shuffle → Collision → Rain) mapped one scene to each planned experiment; three of those five chapters now rest on null or inconclusive results, while the strongest findings (misses on real servers landing on look-alike descriptions; a second server changing the first action) have no scene.
Decision: one primitive (the Request: tool slabs and the beam of the chosen call). Five chapters plus a coda, each exactly one row of `docs/FINDINGS.md`, each opened by a predict-then-reveal hook: 1 Request Anatomy on real servers; 2 a flat Null Wall of everything that did not matter; 3 Shuffle Rack on synonym tools; 4 Galaxy v1 on real loadouts; 5 Merge Collider repurposed to "add a server"; coda on server preference. S5 moves to the Observatory only, S6 to Later, S7 waits for the EXP-006 re-probe. A `Finding` record (Pydantic, exported to JSON) is the only data the Tour reads; CI checks every number against its source.
Consequences: Merge Collider's edges change meaning (documented in DESIGN §4); the Tour leans on two exploratory results, which the rail and posts must label as such; EXP-008 retargets to chapter 4.
Revisit: drift found by the re-probe; a confirmatory follow-up on chapter 4 or 5; EXP-008 shows the Galaxy does not help.

**ADR-027 The Plate Room: one visual language for surfacelab** — proposed (2026-10-28); full text `docs/adr/ADR-027-plate-room.md`; specimen `docs/design/plate-room-specimen.html`
Context: re-read against the findings, the ADR-017 identity kept the right concept (an instrument you operate) but took its materials from generic interfaces (gradient sky, glowing glass beads, frosted panels, mint/vermilion on near-black, cream daylight), none from the subject.
Decision: the observatory plate room. A request is a plate; comparisons use the blink comparator (two conditions alternated in place, no morphing), the same method as our metamorphic tests; the evidence rail becomes an opaque record card; a fixed réseau grid is reference, never data. **Only the model's call is lit.** State is carried by shape (closed reticle, crossed reticle + dashed ring on the right tool, open bracket for refusals), colour only confirms. Themes: night print (Tour, posts) and light-box (embeds, docs), same geometry. Type: Spectral for claims, B612 for interface, B612 Mono for data. Depth is used for the plate stack (ch. 1) and overlaid plates (ch. 5); the Galaxy starts as a flat plate with optional tilt (amends ADR-015).
Consequences: simpler shaders (flat discs, rings, lines); drop grain, bloom, blur and gradient; the M0 look-test is rewritten (find the call in one second, greyscale, feed compression, blink legibility).
Revisit: look-test fails; EXP-008 shows tilt or blink does not help.
