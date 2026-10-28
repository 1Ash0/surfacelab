# CLAUDE.md — surfacelab

Working name: a lab and tool for measuring MCP tool-choice robustness to tool order, request wording, description edits, co-loaded servers, and server availability. See `docs/PROJECT.md` for motivation.

**Keep this file short. Details live in `docs/`; open only what the task requires. Never preload everything.**

## Docs index
- `docs/PROJECT.md` — research question, layers, non-goals, success criteria
- `docs/PRIOR_ART.md` — existing work, verification levels, open verification tasks
- `docs/ARCHITECTURE.md` — components, data model, variants, Pulse safety, repo layout
- `docs/EVAL_DESIGN.md` — cases, EXP-001–008, statistics, threats
- `docs/LEARNING.md` — concept map, Teach-First Protocol, units, gates
- `docs/ROADMAP.md` — milestones, exit criteria, scope fence
- `docs/DESIGN.md` — Observatory: 3D rules, seven scenes, Tour, Bench, capture, embeds, accessibility
- `docs/DECISIONS.md` — append-only ADRs
- `docs/understanding/` — explain-backs, `LEDGER.md`
- `docs/notebook/` — lab notebook, including failures
- `docs/experiments/` — preregistrations
- `docs/FINDINGS.md` — one-page synthesis of every result, with sources

## Commands
- `make check` — offline lint, types, tests, schema-drift checks
- `make test` — replay mode; no network
- `make web` / `make export` — run web app / rebuild `web/public/data`
- `make web-check` — types, unit tests, capture-mode visual regression, axe, bundle budget
- `make posts` — stills and captures from completed experiments
- `surfacelab run --dry-run ...` — required before every live run

## Non-negotiable rules
1. **Teach first:** Follow the Teach-First Protocol for all core code (`docs/LEARNING.md`). Never proceed past an unpassed gate.
2. **Evidence for every number:** Every figure in docs, UI, README, or posts must trace to `results/` or `runs/`. Otherwise verify it or label it `[unverified]`. Prior-art claims retain their verification level until upgraded.
3. **Preregister:** Before live experiments, fix sample size `n` and the primary outcome.
4. **Correct statistical unit:** Analyze case families, using clustered intervals. Never treat repeated trials as independent.
5. **Control pivots:** Every directional change requires an ADR, documentation updates, and a notebook entry.
6. **Enforce scope:** Put out-of-scope ideas in Later in `docs/ROADMAP.md`.
7. **Safety:** Never run untrusted MCP servers outside the sandbox, call `tools/call` on real servers in v0.1, use private/internal surfaces, or commit secrets.
8. **Test offline:** Tests must work offline. Live calls require `--max-usd` and a preceding dry run. Test every grader and detector with two-sided tests.
9. **Keep diffs small:** Changes exceeding ~150 lines require an approved plan. Commits must be conventional and explainable by me.
10. **Label evidence:** Distinguish recorded from simulated, possible from confirmed (including drift flags), and report measured `n` and case families.
11. **Honest 3D:** Never encode quantities in depth. Drive every visual from a result field. Every scene needs an evidence rail, table mode, and describe mode. The web displays statistics but never computes them. Caption projections as similarity.
12. **Deterministic scenes:** Hand-build scenes; do not use a scene component library. Use the engine's deterministic clock, declare channels in `channels.ts`, and test on a real phone before closing each milestone.

## Layout
See `docs/ARCHITECTURE.md` for details.
`src/surfacelab/{schema,mcpclient,surface,render,cases,variants,providers,grading,runner,stats,embed,pulse,report,export,cli}/` · `tests/` · `cassettes/` · `fixtures/` · `runs/` · `results/` · `web/` · `learn/` · `scripts/`

## Style
Python 3.12; uv; Pydantic v2 as the single schema source of truth; Pyright strict on `src/`. Prefer readable code over cleverness. Comments explain why, not what.