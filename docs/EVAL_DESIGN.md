# EVAL DESIGN — surfacelab

This is the part that makes the project credible. Every experiment is preregistered in `docs/experiments/EXP-NNN.md` (template included) before any live run. Numbers below are **plans and hypotheses**, not results.

## 1. Cases

### Kinds
| Kind | Meaning | Grade |
|---|---|---|
| `positive` | A request with one or more valid tools | Hit if first call is in the gold set |
| `sibling` | A request where a near-duplicate tool is the wrong answer | Hit only on the specified tool; picking the named sibling is logged as a sibling-confusion |
| `abstain` | A request no tool should serve | Correct if no tool call is made |

### Where cases come from (three tiers, always labelled)
1. **handwritten** by me for fixture servers. Small, high-quality, the ground truth for validating generators.
2. **generated** by a model from tool schemas, then filtered by deterministic validators and a sampled manual audit. Report audit pass rate.
3. **imported** from existing sets (mcp-toolgauge case files, LiveMCPBench, HumanMCP) only where licence permits.

### The leakage problem (most important validity threat in this lane)
Cases generated from a description tend to reuse its words. A tool then looks "easy" because of lexical overlap, not because the description is good. Defences:
- Compute `lexical_overlap(case, gold tool description)` for every case; report accuracy stratified by overlap tercile.
- Include a **name-blind** variant: tool names replaced by neutral ids (`tool_01`) so selection must rely on descriptions.
- Include a **human-like** tier (short, vague, typo-ridden requests) at least for fixtures.
- Never tune descriptions against the same cases used to report their accuracy (train/test split of case families; fixed before running).

### Gold sets
Many requests have more than one valid tool. Gold is a **set**. Cases where graders cannot decide validity are removed, not forced.

## 2. Experiments

Common design: unit of analysis = **case family**. Primary outcome = selection accuracy (hit rate). Intervals are clustered-bootstrap over families (10,000 resamples) with Wilson shown for simple proportions. Paired comparisons use McNemar on matched (case, trial) pairs, reported with the discordant counts, and the clustered paired-difference interval as the headline. Primary outcome, n and analysis are fixed in the preregistration. Everything else is exploratory and labelled so.

### EXP-001 — Order sensitivity (position bias on your own surface)
- **Question:** how much does selection accuracy depend on where the correct tool sits in the list?
- **Treatments:** K balanced permutations per surface (enumerate all N! for N<=5; balanced sampling for larger N). Factor crossing: server (3 fixtures at least) x model (>=2) x tool count (small N, medium N).
- **Primary outcome:** gap in hit rate between the correct tool in the first third and in the last third of the list, with clustered CI. Secondary: Cochran's Q across position bins; per-case flip rate under reordering.
- **Hypotheses (directional, from BiasBusters-style findings):** H1 earlier is better; H2 effect larger at small K with similar tools; H3 effect shrinks with stronger models. Null result is acceptable and publishable.
- **Controls:** name-blind variant; `unrelated` padding to separate position from count.
- **Threat:** provider tool rendering may reorder or alter formatting; log the exact rendering (ADR-005).

### EXP-002 — Paraphrase fragility
- **Question:** if the same intent is worded differently, how often does the chosen tool change?
- **Treatments:** N=5 validated paraphrases per case family; fixed surface order.
- **Primary outcome:** per-family flip rate (fraction of paraphrase pairs with different chosen tool), averaged over families, clustered CI. Secondary: accuracy by paraphrase style; relation to lexical overlap.
- **Validity:** a flip is only meaningful if paraphrases preserve intent. Report constraint-validator pass rate and manual audit rate. Exclude families where audit fails.
- **Hypothesis:** flip rate is higher for tools with defective descriptions (as scored by an external linter) than for clean ones.

### EXP-003 — Single-edit tradeoff
- **Question:** for each description edit, what happens to accuracy and to cost?
- **Treatments:** the base surface plus one edit at a time, drawn from the smell catalogue (add usage clause, add "not for" clause, remove overlap, document parameters, shorten). Edit ids stable.
- **Primary outcome:** paired accuracy delta vs base (McNemar, clustered CI). **Cost outcomes:** description tokens delta (exact), and in agentic mode (M6) tool-call steps and tokens. Verdict rule fixed in advance: `helps` if CI above +margin, `regresses` if CI below -margin, `costs` if accuracy flat but cost up beyond threshold, otherwise `inconclusive`.
- **Replication target:** direction of Hasan et al. (gain with higher step count; occasional regression). We do **not** expect the same magnitudes: different setup. We say so.
- **Multiple comparisons:** E edits means E tests. Pre-declare the family; use Holm correction for confirmatory claims, label the rest exploratory.
- **Overfitting guard:** edits evaluated on held-out case families.

### EXP-004 — Cross-server collision and namespacing
- **Question:** when servers are loaded together, which tool pairs steal each other's tasks, and is that predicted by description similarity?
- **Treatments:** merge 3 servers (>=20 tools total) under `none | prefix | server-qualified` namespacing; cases are gold-labelled to a specific server's tool.
- **Primary outcome:** cross-server collision rate with clustered CI; per-pair confusion matrix. **Predictive test:** Spearman correlation between pairwise description embedding cosine and pairwise confusion rate, with a permutation-test p-value and a pre-declared embedding model.
- **Hypothesis:** collisions concentrate in a few high-similarity pairs; prefix namespacing reduces them but not to zero.
- **Threat:** embedding choice drives the similarity result; repeat with a second embedding and with a lexical (BM25/Jaccard) baseline.

### EXP-005 — Tool-count dose-response with distractor type and retrieval arm
- **Question:** the literature disagrees on how accuracy falls as tool count rises. Which factors explain it?
- **Design:** fixed target tools; add N distractors, N in {5, 10, 20, 50, 100, 200 if budget allows}; distractor kind in {`unrelated`, `same-domain`, `near-duplicate`}; arm in {`full list`, `top-k retrieval (BM25 or embedding, k fixed)`, `deferred loading / tool search` where the provider API supports it in our harness}. Models: >=2.
- **Primary outcome:** hit rate vs N per (kind, arm) with clustered CI. Fit a simple logistic curve per cell and report slope with CI; no curve-fitting without n to support it.
- **Cost (reported alongside):** prompt tokens per call, so "accuracy per token" is visible.
- **What this can and cannot say:** it speaks to the synthetic surfaces and models tested. It does **not** reproduce RAG-MCP (different tasks and models); if we want a reproduction, it is a separate arm using their published protocol, only if the protocol is public.
- **Confound control:** tool count is tied to prompt length; the `unrelated` kind with equal token count is the length control.

### EXP-006 — Server availability (Later, needs an ADR before any bulk run)
Measure handshake outcomes on a bounded, curated, consented list inside the sandbox. Do not publish a headline "X% of servers are broken" without a sampling frame we can defend.

### EXP-007 — Drift classifier validity (offline)
Build a labelled corpus of description edits (real diffs plus synthetic injected-instruction edits). Report per-class precision/recall, and the false-positive rate of `instruction_like` on benign edits. Two-sided fixtures required. Output language everywhere says "possible".

### EXP-008 — Does the 3D view help? (exploratory perception check; M7)
Question: do people find the most confusable pair on a surface faster or more accurately with Galaxy + evidence rail than with a sortable table alone? Design: within-subject, counterbalanced order, 2 surfaces, peers (target n preregistered, small; labelled exploratory, not generalisable). Primary outcome: correct pair identified (binary) and time to answer. Analysis: paired, intervals not just p; report null results. Consequence rule fixed in advance: if 3D does not help, the scene remains but copy and claims about it change, and the finding is published.

### EXP-009–012 — Follow-ups on near-duplicate surfaces (accepted, ADR-023)
Order (009), disambiguating edits (010), overlapping servers (011) and distractor dose (012), rerun on near-duplicate tools with 32 validated families, because goodserver was at ceiling in EXP-003–005. Preregistrations in `docs/experiments/EXP-009.md` to `EXP-012.md`.

## 3. Statistics notes (the spine; see LEARNING U4)
- **Why clustered:** repeated trials and variants of one case family are correlated. Treating them as independent shrinks intervals dishonestly.
- **Trials:** temperature fixed and recorded; at temperature 0, repeated trials give little extra information, so spend budget on families, not repeats.
- **Power:** before running, simulate. Given a baseline hit rate p0 and a target detectable difference d, find the number of families so the clustered CI half-width is below d. The simulation script is committed; the preregistration quotes its output.
- **Multiple comparisons:** declare confirmatory hypotheses up front; Holm correction for those; everything else labelled exploratory.
- **No optional stopping:** n is fixed in the preregistration.
- **Effect sizes first:** report differences in percentage points with intervals before any p-value.

## 4. Threats to validity (the standing list)
- **Construct:** single-turn first-call selection is not full agent behaviour (step cost, recovery from a wrong call).
- **Internal:** rendering differences, provider-side changes, cassette staleness, case leakage, paraphrase drift.
- **External:** fixture servers are tidier than the wild; few models; one provider by default.
- **Statistical:** small n of families; multiple comparisons; embedding-dependence of similarity results.
- **Ethical:** never run untrusted servers unsandboxed; never use private or internal surfaces; never publish a result that names a vendor as "bad" from a surface we could not fully reproduce.

## 5. Preregistration template (`docs/experiments/TEMPLATE.md`) fields
Question, hypotheses (directional, labelled confirmatory/exploratory), design table, primary outcome, secondary outcomes, n and power script, models and exact ids, rendering used, cases and split, analysis plan, verdict rules, stopping rule, budget cap, what would change my mind, deviations (filled after).

## 6. Reporting rules
Each figure carries an epistemic tag: `recorded`, `simulated`, `measured n=… families=…`, `reproduced`, `reasoned`, `broke`. Null and negative results get a notebook entry and a results page. A result that depends on a single seed is not a result.

**Web fidelity rules.** Every scene is reproducible from files in `results/` and `runs/`. Numbers shown in a scene or rail are read from those files, never recomputed in the browser. Anything not driven by recorded trials carries the permanent `simulated` badge. Projections (UMAP) are captioned as similarity, never as confusion; confusion appears only as measured edges.
