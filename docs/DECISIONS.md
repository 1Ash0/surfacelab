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
