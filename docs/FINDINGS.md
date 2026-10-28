# FINDINGS — what surfacelab measured (v0.1, 2026-10-28)

One page for the whole evaluation. Every row cites the results file it comes from; the experiment docs hold designs, deviations and full tables. Labels: **confirmed** / **not confirmed** / **absent** follow each experiment's preregistered verdict rule; **inconclusive** means the interval could not decide; **exploratory** results were not preregistered as confirmatory and are reported as leads, not claims.

Models: `openai/gpt-oss-20b`, `openai/gpt-oss-120b` (all experiments), `qwen/qwen3.8-27b` (EXP-013, EXP-014), on the Groq free tier at temperature 0 unless noted. Intervals are 95%, clustered over case families (10,000 bootstrap resamples, seed 42) unless marked Wilson.

---

## The short version

1. **On surfaces we wrote, where each tool states a distinct job, tool choice is nearly perfect and robust.** List order, reworded requests, description edits, up to 50 distractors and namespacing schemes made no measurable difference (EXP-001–005, EXP-009–012), and this held on a second model family (EXP-014).
2. **Where tools do the same job, list position breaks the tie.** On four synonym tools, the first-listed tool won more often: +10.4 pp for gpt-oss-120b and +12.5 pp for Qwen (EXP-001 follow-up, EXP-014).
3. **On real MCP servers loaded together, models miss the only right tool far more often:** about 1 in 4 times for gpt-oss, 1 in 11 for Qwen, against under 1 in 100 on our surfaces (EXP-013).
4. **When they miss, they pick a tool whose description resembles the right one's** (EXP-013 H4, both embedding models). Description similarity, which surfacelab measures, predicts real confusions.
5. **When two real servers could both do the job, order did not measurably decide the winner; each model kept its own favourite server** (EXP-013 H1 inconclusive, H3).
6. **Co-loading one server can change what the agent does first:** with Chrome DevTools next to Playwright, gpt-oss-120b opened 14 of 24 browser requests by listing pages, including jobs only Playwright could do (EXP-013, exploratory).

---

## Findings by question

### Does tool order matter?
| Finding | Evidence | Label |
|---|---|---|
| No position effect on a server of distinct tools (goodserver) | gap first − last third: 20b +1.2 pp [−0.6, +4.2], 120b +0.9 pp [−0.5, +2.8]; `results/exp001_analysis.json` | absent (driven by ceiling) |
| First-listed advantage among synonym tools (`siblings`, T = 0) | 120b +10.4 pp [+2.1, +19.8]; 20b +13.5 pp [−1.0, +31.3]; `results/exp001_siblings_t0_analysis.json` | exploratory (8 families) |
| …replicated on Qwen | +12.5 pp [+2.1, +25.0]; `results/exp014_analysis.json` | replicated (EXP-014 R1) |
| No position effect on near-duplicate tools with distinct scopes | 20b 99.9%, 120b 99.6% accurate; gap −0.3 / −0.8 pp, upper bounds 0.0; `results/exp009_analysis.json` | absent (at ceiling) |
| …replicated on Qwen | 768/768 correct; `results/exp014_analysis.json` | replicated (R2) |
| On real servers that share a job, the first-listed server wins above chance | excess over chance: 20b +2.7 pp [−10.8, +15.8], 120b +0.0 [−7.1, +7.9], Qwen +7.3 [−3.3, +17.4]; `results/exp013_analysis.json` | inconclusive (16 shared families) |
| Chosen server changes with order | 19–25% of shared families; `results/exp013_analysis.json` | exploratory |

### Do request wording and description edits matter?
| Finding | Evidence | Label |
|---|---|---|
| Paraphrased requests rarely change the choice | mean flip rate 20b 2.6% [0, 7.7], 120b 5.1% [0, 12.8]; every flip was a refusal; `results/exp002_analysis.json` | inconclusive |
| Description edits (usage, negation, summary, trim, vague) | base at 100%, so no edit could show a gain; `results/exp003_analysis.json` | inconclusive (ceiling) |
| Contrast and negation clauses on near-duplicate surfaces | not run: base ≥ 0.99, past the 0.90 ceiling rule; `docs/experiments/EXP-010.md` | not run (by rule) |

### Do co-loaded servers collide?
| Finding | Evidence | Label |
|---|---|---|
| Wrong-server picks with two co-loaded servers | 0 collisions in 72 trials; `results/exp004_analysis.json` | not confirmed |
| …with overlapping servers whose requests name the server | 1 collision in 288 trials; `results/exp011_analysis.json` | not confirmed |
| …replicated on Qwen | 0 in 48; Wilson [0, 0.074]; `results/exp014_analysis.json` | replicated (R3) |
| Slash-qualified names (`server/tool`) broke 120b once | 120b missed 8 of 12 vs 3 under other schemes; `results/exp004_analysis.json` | exploratory; **did not recur** in EXP-011 (0 non-existent calls), so not a general claim |

### Do distractors hurt?
| Finding | Evidence | Label |
|---|---|---|
| Up to 50 distractors on goodserver | accuracy 92–100% in every cell; `results/exp005_analysis.json` | not confirmed |
| Up to 20 same-domain distractors on near-duplicate surfaces | at most 2 of 32 wrong per cell; `results/exp012_analysis.json` | not confirmed |

### What happens on real servers?
| Finding | Evidence | Label |
|---|---|---|
| Servers that start in a no-network sandbox | 15 of 19 curated servers [0.57, 0.91] Wilson; the 4 failures come from our offline setup; `results/exp006.json` | descriptive (curated list, not a sample) |
| Real tool lists are large | Notion 21.7K, Firecrawl 16.6K, MongoDB 15.6K, GitHub 13.8K tokens (local `o200k_base` count), each over one free-tier request; `docs/experiments/EXP-006.md` | descriptive |
| Providers count the same tools differently | browser loadout: gpt-oss 3,493 vs Qwen 6,232 prompt tokens; `results/exp013_prompt_tokens.json` | measured |
| Only one server can do the job: right tool found | 20b 0.78 [0.66, 0.88], 120b 0.77 [0.63, 0.88], Qwen 0.91 [0.82, 0.98]; `results/exp013_analysis.json` | gpt-oss: **not confirmed** (below 0.90); Qwen inconclusive |
| Wrong picks resemble the right tool | wrong tool's similarity percentile among non-gold tools: 0.71 (text-embedding-3-small, Wilcoxon p = 0.0007) and 0.67 (gemini-embedding-001, p = 0.007), 20 families; `results/exp013_h4.json` | exploratory |
| Each model favours its own server on shared jobs | e.g. Qwen chose Playwright 10/10; 120b chose Brave 11, DuckDuckGo 7, Tavily 0 on shared web searches; `results/exp013_analysis.json` | exploratory |
| Co-loading Chrome DevTools changed the first action | first call was `list_pages` in 14/24 (120b), 9/24 (20b), 4/24 (Qwen) browser trials; `docs/experiments/EXP-013.md` | exploratory |

### Supporting measurements
| Finding | Evidence | Label |
|---|---|---|
| Instruction-like text detector | precision 1.000, recall 0.929 on 38 descriptions; `results/exp007.json` | measured |
| Temperature 0 is not fully deterministic on Groq | 7 of 8 repeated groups stable per model; 3 of 80 answers differed; `results/determinism_probe.json` | measured |
| Refusals under forced tool choice | Groq returns `tool_use_failed`; recorded and scored incorrect, never retried (EXP-001 deviations) | method |

---

## What this means for surfacelab

- **The product should measure overlap between tool descriptions**, across every server a user loads, not tool order or tool count. On our surfaces, distinct descriptions were enough for near-perfect choice; on real servers, the wrong picks clustered on similar descriptions.
- **Test with the servers users actually combine.** Single-server and hand-written surfaces overstated accuracy by 20+ pp for gpt-oss.
- **Report first actions, not only right or wrong.** The `list_pages` detour is invisible to a right/wrong score but changes agent behaviour and cost.
- **Size is a real constraint.** Several popular servers do not fit one free-tier request on their own; tool-selection options matter.

## Limits
- Three open models on one provider; results may differ for Claude, GPT or Gemini.
- EXP-013 has 48 families (16 shared); H1 intervals are wide.
- Surfaces are taken from servers as they stood on 2026-10-28 with pinned versions; the EXP-006 re-probe will check drift.
- First-call scoring: multi-step behaviour is not measured.
- Gold sets were validated by one person who did not write the cases; disagreements were resolved by widening gold to the union.
