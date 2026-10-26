# LEARNING — how this project teaches you

The deal: **Claude Code writes code; you must be able to defend every core line.** Chat is for depth; Claude Code is for proof. A unit is finished when you pass its gate, not when the code compiles.

- **Chat (claude.ai):** concepts, derivations, reading primary sources together, arguing. Use `LEARNING_CHAT_PROMPT.md`.
- **Claude Code:** the Teach-First Protocol, then building, then checking your understanding on the actual code.
- **You:** predictions, explain-backs, decisions.

## Core vs plumbing
- **Core** (deep gate): everything in `src/surfacelab/` except `report`, `export`, `cli`; and the hand-built WebGL views.
- **Plumbing** (5-line explanation, no gate): CI YAML, Typer wiring, report HTML templating, Tailwind chrome, deploy config. You may opt into depth anywhere. Say "everything deep" to switch the plumbing lane off.

## Teach-First Protocol (every core unit)
1. **Brief.** Five lines: what, why, concepts, the gate.
2. **Primer.** At most 400 words. Anchor to what you know (DDIA, OS/xv6, LangGraph, RAG, FastAPI), then say exactly **where the analogy breaks**.
3. **Demo.** A runnable script of at most 30 lines in `learn/`. You run it.
4. **Predict.** 1-3 questions about what it will do. **You answer before anything is revealed.**
5. **Implement.** Small diffs. For each non-obvious choice: what, why, the alternative.
6. **Break it.** A deliberate bug. You predict which test fails and why.
7. **Explain back.** 5-10 lines in `docs/understanding/NN-topic.md`, your words. Claude critiques plainly: factual errors, hand-waving, unsupported claims.
8. **Gate.** Questions below, answered without notes. Record in `docs/understanding/LEDGER.md` (date, unit, what you got wrong first).

"I get it, just do it" triggers one warning, then a short oral check for core work.

## Concept map

| ID | Concept | Why here |
|---|---|---|
| C01 | MCP protocol: JSON-RPC, `initialize`, `tools/list`, `tools/call`, stdio vs streamable HTTP, capabilities | What a "surface" physically is |
| C02 | How tools reach the model: provider tool parameter vs prompt text, JSON Schema, `tool_choice`, token cost of schemas | Rendering is a variable |
| C03 | Tool selection as classification under a prompt: what influences it (name, description, order, count, similarity) | The object of study |
| C04 | Position effects and primacy/recency in LLM context; lost-in-the-middle | Order sweeps |
| C05 | Metamorphic testing: test oracles without ground truth, invariance relations | Paraphrase and order probes |
| C06 | Case design: positives, siblings, abstentions; leakage; gold sets | Eval validity |
| C07 | Event sourcing, cassettes, deterministic replay (DDIA log-as-truth) | Offline CI |
| C08 | Proportions and intervals: Wilson, clustered bootstrap, why trials are not independent | Honest numbers |
| C09 | Paired tests: McNemar, discordant pairs; permutation tests; Cochran's Q | Comparing variants |
| C10 | Multiple comparisons, preregistration, optional stopping, power by simulation | Not fooling yourself |
| C11 | Text embeddings, cosine similarity, and what UMAP/t-SNE distances do **not** mean | Galaxy view honesty |
| C12 | Retrieval over tools: BM25, embeddings, top-k; deferred loading | EXP-005 arms |
| C13 | Tool poisoning, rug pulls, schema drift; threat model of untrusted descriptions | Pulse |
| C14 | Sandboxing untrusted code: containers, no-network, resource limits | Pulse safety |
| C15 | GPU rendering basics: buffers, instancing, shaders, picking, draw calls | Hand-built scenes |
| C17 | Visual encoding and perception: channel ranking (position > length > angle > area > colour), why depth is a poor quantitative channel, colour-blind-safe palettes, redundancy | Honest 3D |
| C18 | Scene choreography: camera rails, easing, damping, scroll-driven timelines, deterministic clocks | The Tour and capture |
| C19 | Web performance and robustness: bundle splitting, quality tiers, context loss, memory, frame-time measurement | Phones are the audience |
| C20 | Capture and reproducibility: fixed timestep, software GL, visual regression, OG images | Posts and CI |
| C16 | Packaging and adoption: CLI ergonomics, semantic versioning, GitHub Actions, schema versioning | Product |

## Units (sized by understanding, not days)

### U0 — What is physically in a tool-selection request
C01, C02, C03. Build: `mcpclient` (initialize + tools/list), `render`, a **token ledger** of a surface (names / descriptions / schemas).
**Gate G0:**
1. Draw the MCP handshake. What does `tools/list` return and what does it not tell you?
2. Where do the tokens of a 30-tool surface go (names vs descriptions vs schemas)? How did you measure it?
3. Why is "the model saw tool 3 before tool 7" a statement about rendering, not about the server?
4. Why does this project never call `tools/call` on real servers in v0.1?

### U1 — Cases, graders and leakage
C06. Build: `cases`, `grading`, handwritten fixtures.
**Gate G1:**
1. Why is gold a set? Give a case where a single gold tool would be wrong.
2. What is lexical leakage, how does it inflate accuracy, and which control removes it?
3. Why is the primary grade the tool name emitted, and not a judge's opinion? What does that lose?
4. Write one fixture that must trigger the sibling grader and one that must not.

### U2 — Providers, cassettes, budgets
C07. Build: `providers/cassette`, budget guard, dry-run estimator.
**Gate G2:**
1. How is the cassette key formed? Why must tool order be part of it?
2. What makes a replay silently stale, and how does `doctor` detect it?
3. Why can CI never fall through to the network?
4. Explain event sourcing to someone who knows DDIA: what is the log, what is derived?

### U3 — Statistics and experiment design (the spine)
C08, C09, C10. Build: `stats` (Wilson, clustered bootstrap, McNemar, permutation test, Cochran's Q) tested against hand-computed cases; power simulation script.
**Gate G3:**
1. 18/27 vs 8/27: compute Wilson intervals; explain why overlap does not settle significance and why a paired design is stronger.
2. Why is bootstrapping over trials wrong when families repeat? Demonstrate with a simulation where it gives a too-narrow interval.
3. Name three ways an order experiment could mislead you, and the control for each.
4. What does preregistration prevent that "being careful" does not?

### U4 — Metamorphic probes: order and paraphrase
C04, C05. Build: `variants.permute` (balanced) and `variants.paraphrase` (validated), EXP-001 and EXP-002 harness.
**Gate G4:**
1. Why enumerate all N! for small N and balance for large N? What goes wrong with independent shuffles?
2. What is an invariance relation? State two for this project and what a violation means.
3. How do you know a paraphrase preserved intent, and what happens to a family that fails the audit?
4. Predict, then check: if you pad with `unrelated` tools, does position effect grow or shrink? Why?

### U5 — Edits, cost, and verdicts
C03, C10. Build: `variants.edit` catalogue, verdict rules, EXP-003.
**Gate G5:**
1. Why is "accuracy went up" an incomplete verdict? What is the cost side?
2. Why Holm and not nothing, for E edits?
3. What is overfitting a description to the test set, and how does the split prevent it?
4. When is `inconclusive` the honest answer?

### U6 — Embeddings, similarity and the Galaxy
C11, C12. Build: `embed`, similarity matrices, BM25 baseline, UMAP export, EXP-004 analysis.
**Gate G6:**
1. What does cosine similarity between two descriptions measure, and what does it not?
2. Why can UMAP place two tools close together that are not similar (and vice versa)? What must the UI say about this?
3. Why repeat the similarity-vs-confusion test with a second embedding and a lexical baseline?
4. What is a permutation test for Spearman and why is it appropriate here?

### U7 — Drift, poisoning and sandboxes
C13, C14. Build: `pulse` (sandboxed handshake, snapshot store, drift classifier), EXP-007.
**Gate G7:**
1. Describe a rug pull step by step. What does hash pinning catch and miss?
2. Why does Pulse run servers in a container with no network? What could go wrong otherwise?
3. What is the false-positive cost of `instruction_like`, and how is it measured?
4. Why do we say "possible" in every output string?

### U8a — GPU rendering fundamentals
C15. Build: the W0 engine spike by hand: instanced points, custom shader sprites, screen-space-width edges, GPU id-buffer picking, orbit rig.
**Gate G8a:**
1. Why instanced points and one segment buffer instead of one mesh per tool? What is a draw call and why does it matter?
2. Explain GPU picking without per-object raycasts. What breaks it (antialiasing, blending)?
3. Why are native GL lines unusable here, and what replaces them?
4. What happens on context loss and how does the engine recover?

### U8b — Encoding data honestly
C17. Build: channel declarations (`channels.ts`) for S1 and S3, the evidence rail, and the table/describe modes.
**Gate G8b:**
1. For each of two scenes: which variable is on which channel, and why is that the best available channel for it?
2. Why must depth never carry a quantity? Give the counter-case where 3D is the right tool.
3. What does distance in the Galaxy mean and not mean, and where is that said on screen?
4. Show one case where colour alone would fail a colour-blind user and what redundancy you added.

### U8c — Choreography, motion and the Tour
C18. Build: camera rails as data, scroll-driven timeline, transitions that preserve object identity (Galaxy → Merge Collider), reduced-motion path.
**Gate G8c:**
1. What makes a transition aid comprehension rather than decorate? Defend one cut and one continuous move you chose.
2. How is determinism kept (clock, seeds), and why does capture depend on it?
3. What does `prefers-reduced-motion` change in each chapter?
4. Where does the Tour degrade when WebGL fails, and what does the user still get?

### U8d — Performance, capture and embeds
C19, C20. Build: quality tiers with measured frame time on a real phone, bundle budget check, Playwright capture, visual regression in CI, the web component.
**Gate G8d:**
1. Show measured frame time and bundle size per tier. What did you cut and why?
2. How do software-GL screenshots stay stable enough for regression? What tolerance did you choose and why?
3. How does the embed avoid breaking a host page (isolation, lazy load, failure mode)?
4. Which visual claim in the Tour traces to which result file? Demonstrate with one.

### U9 — Packaging and adoption
C16. Build: PyPI package, GitHub Action, report site on Pages, README, badge.
**Gate G9 (lightweight):** run the install from a clean machine/container following only the README; list three places a stranger would get stuck and fix them.

## Reading list (chat, in order; mark what you actually read)
1. MCP specification: lifecycle and tools sections.
2. Wang et al. (arXiv 2602.18914) and Hasan et al. (arXiv 2602.14878): methods first, then results.
3. BiasBusters (arXiv 2510.00307): how they shuffle and measure.
4. mcp-toolgauge README and source of `eval`.
5. RAG-MCP (arXiv 2505.03275) and HumanMCP (arXiv 2602.23367): compare setups before comparing numbers.
6. MCPTox (arXiv 2508.14925) and mcp-scan docs, for U7.
7. A short text on metamorphic testing and one on clustered standard errors.

## Ledger
`docs/understanding/LEDGER.md`: date, unit, gate result, first wrong answer, what fixed it.
