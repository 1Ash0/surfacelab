# ARCHITECTURE — surfacelab

Principles: trace is the source of truth; everything derived (scores, reports, web data) is rebuilt from recorded runs; no network in tests; models and schemas are pydantic v2; the harness core knows nothing about specific probes.

## 1. Components

```
 surface source            probe plan              runner                 store              views
┌──────────────┐     ┌──────────────────┐   ┌───────────────┐    ┌────────────────┐   ┌──────────────┐
│ MCP server   │     │ Cases (gold set) │   │ Provider      │    │ runs/*.jsonl   │   │ CLI report   │
│ (stdio/http) │──▶  │ Variants:        │──▶│  live | cassette│─▶ │ (events)       │──▶│ HTML report  │
│ or fixture   │     │  order, paraphr, │   │ Selection grade│    │ results/*.json │   │ web playground│
│ or snapshot  │     │  edit, merge     │   │ Budget guard   │    │ (derived)      │   │ (static)     │
└──────────────┘     └──────────────────┘   └───────────────┘    └────────────────┘   └──────────────┘
```

| Module (`src/surfacelab/`) | Responsibility | Core? |
|---|---|---|
| `schema` | pydantic models for Surface, Tool, Case, Variant, Trial, Event, Result. Single source of truth; JSON Schema exported and checked for drift | yes |
| `mcpclient` | Minimal MCP client: spawn stdio server, `initialize`, `tools/list`, snapshot to a `Surface`. **Never calls `tools/call` on a real server** in v0.1 | yes |
| `surface` | Load a Surface from live server, snapshot file, or fixture; normalize; compute stable hashes; apply variants | yes |
| `render` | Turn a Surface into what the model sees (provider tool param or prompt text). Records the exact rendering used. Rendering is a studied variable, not an implementation detail | yes |
| `cases` | Case file format, validation, import from mcp-toolgauge format, task generators with deterministic validators | yes |
| `variants` | Pure functions: `permute(surface, seed)`, `paraphrase(case)`, `edit(surface, edit_id)`, `merge(surfaces, namespacing)`, `pad(surface, n, kind)` | yes |
| `providers` | `Provider` protocol; `anthropic`, `cassette` (record/replay), `fake` (scripted for tests) | yes |
| `grading` | Deterministic selection grader, abstention grader, argument-schema validity check | yes |
| `runner` | Executes (case x variant x trial) with budget guard, writes events as they happen | yes |
| `stats` | Wilson, clustered bootstrap, McNemar, permutation tests, Cochran's Q, Spearman, multiple-comparison helpers | yes |
| `embed` | Embedding of descriptions, pairwise similarity, UMAP projection export. Cached, version-pinned | yes |
| `pulse` | Sandboxed handshake probe, snapshot store, drift classifier | yes |
| `report` | Build `results/` from `runs/`; render CLI table and HTML | no (plumbing) |
| `export` | Build `web/public/data` binary and JSON from `results/` | no |
| `cli` | Typer commands | no |

## 2. Data model (sketch; the code is authoritative)

```python
class Tool:        server_id; name; description; input_schema; annotations
class Surface:     surface_id (hash of normalized tools); tools: list[Tool]; source: live|snapshot|fixture|merged; captured_at
class Case:        case_id; kind: positive|sibling|abstain; text; gold: list[ToolRef]  # a SET, some tasks have several valid tools
                   family_id  # paraphrases and variants of one intent share a family, used for clustering
                   provenance: handwritten|generated|imported; lexical_overlap: float
class Variant:     variant_id; factor: order|paraphrase|edit|merge|pad|baseline; params; parent_surface_id
class Trial:       case_id; variant_id; model; trial_index; seed
class Event:       ts; trial_key; type: request|response|grade|error; payload   # append-only
class Result:      derived. cell aggregates with n, hits, Wilson interval, links to trials
```

Clustering rule: **the unit of analysis is the case family, not the trial.** Ten permutations of one case are not ten independent observations.

## 3. Determinism and replay (inherited from ctxcheck)
- Cassette key = hash(model id, rendered request bytes, sampling params, trial_index). Rendered request bytes include tool order, so a permuted surface correctly gets a different key.
- CI replays never fall through to the network; a missing cassette fails the test.
- Staleness: cassette header stores provider, model id, library version, date. `surfacelab doctor` flags cassettes older than a configured age or from a different model id.
- Live runs require `--max-usd` and print a dry-run estimate (n calls, estimated tokens, estimated cost) first. Pricing table is data, versioned, and dated.

## 4. Variant semantics (the part to get exactly right)

- **permute:** K orderings per surface drawn from a seeded generator. For small N (N<=5) enumerate all N! (or a balanced Latin-square subset) so each tool appears at each position equally often. For large N use balanced sampling: each tool at each position approximately equally often, not independent shuffles.
- **paraphrase:** N rewordings per case, generated by a model with constraints (keep all entities and values), then validated: required entities present, no new entities, not identical, length within bounds. A sampled subset is audited by hand and the audit rate is reported.
- **edit:** exactly one smell-targeted change to one tool description (for example add "use when..." clause, remove an overlapping sentence, add parameter docs). Edit ids are stable. Each edit records its token delta.
- **merge:** union of surfaces with `none | prefix | server-qualified` namespacing.
- **pad:** adds inert distractors of a declared kind: `unrelated`, `same-domain`, `near-duplicate`. Padding kind is a factor, because tool count and tool similarity are confounded in the literature.

## 5. Grading
- **Hit** (positive): first tool call is in `gold` (set). **Miss-in-sibling** (sibling case): chose a named sibling instead. **Abstain-correct**: made no tool call when none applies. **Collision** (merged surfaces): chose a tool whose server differs from the gold server.
- Only the first tool call is graded in v0.1 single-turn mode. Multi-step agentic mode (step cost) is M6+ and runs against fixture servers with canned tool results, never real side effects.
- Argument validity is a secondary metric, checked by JSON Schema, never folded into the primary outcome.
- **No LLM judge** for the primary outcome.

## 6. Pulse design (safety first)
- A server command is untrusted code. Pulse runs it inside a container: no network by default, read-only filesystem, no host credentials, CPU, memory and wall-clock limits, non-root.
- v0.1 targets the user's own servers and a small curated list. No bulk crawling of third-party registries from a laptop. Any bulk measurement is a separate, reviewed design (ADR needed).
- Handshake outcome taxonomy (single attempt, fixed timeout, no repair): `ok | spawn_error | timeout | needs_credentials | protocol_error | no_tools`. Classification rules are code with fixtures for each.
- Drift classes between snapshots: `none | whitespace | wording | param_change | tool_added | tool_removed | instruction_like`. `instruction_like` is a heuristic flag (imperative second-person text addressed to the model, mentions of other tools or file paths, hidden-text markers), reported as *possible*, with false-positive rate measured on a labelled corpus (EXP-007).

## 7. Web data contract
`make export` writes:
- `web/public/data/index.json` runs and experiments index
- `web/public/data/run-<id>.json` per-run summary (intervals, cells)
- `web/public/data/galaxy-<surface>.bin` float32 positions (x,y,z), uint8 server ids, uint16 edge list + float32 weights, with a JSON sidecar describing byte layout and the UMAP/embedding versions
- `web/public/data/trials-<run>.bin` compact per-trial records (case id, family id, variant id, chosen tool index, correct flag) so scenes such as Selection Rain and Shuffle Rack draw **real trials**, not aggregates
- `web/public/data/layout-<scene>.json` authored camera rails and scene parameters (data, not code)
- `schema/*.json` JSON Schema generated from pydantic; TS types generated from it; CI fails on drift
- No server, no DB, no keys.

## 8. Repo layout
```
surfacelab/
  CLAUDE.md  MASTER_PROMPT.md  README.md  Makefile  pyproject.toml
  src/surfacelab/{schema,mcpclient,surface,render,cases,variants,providers,grading,runner,stats,embed,pulse,report,export,cli}/
  tests/  cassettes/  fixtures/{servers,surfaces,cases}/  runs/  results/
  web/{src/{engine,scenes,ui,data,capture,embed},public/data}  learn/  scripts/
  docs/{PROJECT,PRIOR_ART,ARCHITECTURE,EVAL_DESIGN,LEARNING,ROADMAP,DESIGN,DECISIONS}.md
  docs/{understanding,notebook,experiments}/
```

## 9. Fixtures (needed from the first milestone)
- `fixtures/servers/` three tiny local MCP servers written by us: `goodserver` (clear descriptions), `badserver` (known smells, deliberately), `siblings` (four near-duplicate tools). Deterministic, no network.
- `fixtures/surfaces/` snapshots of public servers (only if licence permits redistribution; otherwise reference by pinned version and rebuild).
- Fixtures are two-sided test inputs: each detector and grader has at least one case that must fire and one that must not.

## 10. Extensibility contract
Adding a probe means: a variant function, a grader (or reuse), an experiment template, a report section. It must not require edits to `runner` or `providers`. If it does, the abstraction is wrong; write an ADR.

## 11. Web architecture (details and rules in DESIGN.md)
```
web/src/
  engine/    renderer, camera rig, loader (binary + schema checks), GPU picking, quality tiers, context-loss recovery, deterministic clock
  scenes/    anatomy/ galaxy/ rack/ collider/ rain/ migration/ ribbons/   (each: scene.ts, shaders/, channels.ts, fallback.tsx, describe.ts)
  ui/        chrome only: tabs, evidence rail, tables, tooltips, command palette
  data/      generated types, decoders, selectors
  capture/   Playwright capture script, OG renderer
  embed/     <surfacelab-galaxy> web component
```
- **Scene contract:** `init(ctx, data) → { update(t), pick(id), setState(s), dispose(), channels, describe(), table() }`. A new scene adds a folder and a registry line; nothing else changes.
- **Single source of truth:** pydantic → JSON Schema → TS types. Scenes never read raw run files, only decoded selectors.
- **Determinism:** time comes from the engine clock; layout seeds are in data; capture mode freezes both.
- **Static export, lazy loading:** three and scene code load per route; data loads per scene.
- **No scene logic in the rail and no numbers computed in scenes:** statistics come only from `results/` (computed in Python); the web only displays them.
