# PROJECT — surfacelab

Working name (PyPI `surfacelab` returned 404, i.e. unclaimed, when checked on 2026-10-26; re-check npm, GitHub and trademarks in the first session; renaming allowed, see ADR-009).

## The question
When an agent is handed a set of MCP tools, **how fragile is its choice of tool**? Fragile to the order the tools are listed in, to how the user words the request, to a one-line edit of a description, to which other servers happen to be loaded beside it, and to whether the server is even alive.

Existing tools already answer "is this description well written?" and "does the model pick the right tool on my fixed test set?" (see `PRIOR_ART.md`). Nobody we found measures **robustness, composition and availability**. That is the project.

## Thesis
> A tool surface is not good because its descriptions pass a lint. It is good if the agent's choice stays correct when things that *should not matter* change. Selection accuracy on one fixed prompt in one fixed order is a point estimate of something that has a spread. We measure the spread.

## What we build (three layers, each standalone, shipped in this order)

| Layer | CLI | Question | Novel part |
|---|---|---|---|
| **A. Robustness** | `surfacelab probe` | Does selection survive reordering, rephrasing, and single description edits? | Metamorphic order and paraphrase sweeps with clustered intervals; per-edit accuracy delta **and** cost delta |
| **B. Composition** | `surfacelab cross` | When N servers are loaded together, which tools steal each other's tasks? | Cross-server confusion graph; tests whether description similarity predicts confusion; namespacing as a measured intervention |
| **C. Availability and drift** | `surfacelab pulse` | Does the server start, and did its surface change since last week, and how? | Sandboxed start-rate SLO plus a drift classifier that separates harmless edits from instruction-like injected text |

Plus two co-equal pillars:
- the **Lab**: preregistered experiments EXP-001..008 (`EVAL_DESIGN.md`).
- the **Observatory**: the web experience, led by 3D (`DESIGN.md`). Seven hand-built scenes (Request Anatomy, Surface Galaxy, Shuffle Rack, Merge Collider, Selection Rain, Edit Migration, Pulse Ribbons), a scroll-driven **Tour**, a **Bench** where anyone drops their own surface and sees it in the browser, a **Replay Theatre** for single trials, an embeddable web component, and deterministic capture for posts and videos.

## The Observatory (why the frontend is half the project)
The numbers are for engineers; the scenes are for everyone else, and they are also how the numbers become *understood*: where tokens go, what sits near what, where tasks land, how a surface drifts. Rules (DESIGN §1): 3D is for space, flow and time, never for reading quantities by depth; every visual encodes a measurement; a flat evidence rail always carries the exact numbers and intervals; recorded vs simulated is always visible. Whether 3D actually helps people is itself measured (EXP-008) and reported even if the answer is no.

## Product stance (adoption)
- **Complement, not competitor.** README says plainly: lint and fixed-set eval already exist (mcp-toolgauge, mcpolish and others). `surfacelab` consumes their case format if licence allows (ADR-003) and adds what they do not.
- Zero-config entry: `surfacelab probe -- <your server command>` prints a robustness report.
- CI: a GitHub Action that fails on robustness regression and publishes the report to Pages, plus a badge.
- Offline by design: reports and recordings are static JSON, browsable forever with no API key.
- The first public artifact is a **measurement**, not a feature list, shown as a scene.
- **Adoption surfaces:** `<surfacelab-galaxy>` embed for maintainers' docs, PR comments with a rendered still of the changed scene, badges, Pages-hosted report sites, and a Bench that works without installing anything.

## Non-goals
- Not a gateway or proxy (Later list; revisit only if EXP results show a view policy clearly wins).
- Not another description linter. We reuse existing lint output as an input signal, we do not re-implement 22 rules.
- Not a security scanner. Pulse's drift classifier reports *possible* injected instructions with explicit false-positive rates. It does not replace mcp-scan.
- Not a claim about "all MCP servers". Every result is scoped to the servers, models and task sets measured.
- Not a novel-algorithm paper. Replicate, extend, productize.

## Success criteria
1. **Usable by a stranger:** from the README alone, someone runs `surfacelab probe` on their own server offline-replay and live (with `--max-usd`) and gets a report.
2. **Credible:** at least two preregistered experiments completed with intervals, deviations logged, nulls published.
3. **A result worth quoting:** at least one finding that survives an adversarial reread (for example "reordering alone moves selection accuracy by X pp on server Y, CI [..]").
4. **Evolvable:** new probe types plug in without touching the harness core.
5. **Defensible by Asmit:** every core line passes its gate (`LEARNING.md`).
6. **Presentable:** at least five of the seven scenes ship, hand-built, interactive on a mid-range phone, each with a table fallback and evidence rail; the Tour holds a stranger for the whole scroll; posts and videos use deterministic captures of real measured moments.
7. **Honest visuals:** a hostile reviewer cannot find a scene that implies a measurement we did not make; EXP-008 reported whatever it found.

## Relationship to the project set
Project 1 (`ctxcheck`) gives reusable pieces: cassette provider, budget guard, Wilson/bootstrap/McNemar, epistemic tags, preregistration template. Copy in v0.1 (ADR-004), extract a shared package only if Project 3 also needs it. Shared design identity, different theme (`DESIGN.md`).

## The Atlan angle (hypothesis, not a finding)
The `atlan-search` skill available in Asmit's Claude environment exists to tell an agent which of `semantic_search`, `search_assets`, `get_assets`, `traverse_lineage`, `resolve_metadata`, `get_users` (and others) to use. That suggests routing help is needed on that surface. **We have not measured anything.** First check what Atlan publishes about its MCP server (open source? public tool list?). Only a publicly obtainable surface may be used. The outreach artifact is a measurement with methodology, framed "tell me where this is wrong", never a claim that their product is bad.

## Glossary
- **Surface:** the complete list of tool names, descriptions and schemas the model sees in one request.
- **Case:** a user request with a gold label (`positive`, `sibling`, or `abstain`).
- **Sweep:** one case evaluated under K controlled variations of one factor.
- **Flip:** the chosen tool differs between two variants of the same case that should be equivalent.
- **Collision:** the agent picks a tool from server B for a case whose gold tool lives on server A.
