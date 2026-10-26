# PRIOR ART — what exists, what is verified, what is open

Verification levels used below:
- **[read]** the full page or paper was read in the research session
- **[read-summary]** read in the research session; numbers come from my notes, re-verify before quoting
- **[snippet]** seen only as a search snippet or abstract
- **[secondhand]** reported by an article or another document, not seen at source

Rule: nothing from this file goes into a README, post or UI without being upgraded to [read] and re-checked at source. Claude Code's first job is to do that (see "Open verification tasks").

## 1. Tools that already ship (the crowded lanes)

| Tool | What it does | Level | Consequence for us |
|---|---|---|---|
| **mcp-toolgauge** (PyPI, MIT, released 2026-08-24) | `inspect`, `lint` (22 rules, 5 families), `eval` (positive / sibling / abstain cases, confusion matrix, hash-keyed cache, offline replay), `ci` (0-100 score, badge, GitHub Action), static `dashboard`. Score covers lint plus selection accuracy only | **[read]** (full PyPI page) | Closest prior art. Nearly the original "lint + bench" plan. We do **not** rebuild it. Check licence and case schema; consume it (ADR-003) |
| **mcpolish** (PyPI) | 23 static rules citing Wang et al. | [read-summary] | Use as optional input signal, not a rebuild |
| **mcp-doctor / mcp-server-lint** | Static audit plus GitHub Action | [snippet] | Same |
| **agent-friend** | validate / audit / optimize / grade (A+ to F) across providers; reports grading 200 real servers | [snippet] | Do not duplicate grading |
| **openapi-agent-ready** | OpenAPI to MCP scaffold plus quality rubric | [snippet] | Out of scope |
| **mcp-tool-selection-bench** (PyPI) | LLM-generated suites, confusion heatmaps, CI | [snippet] | Same lane as toolgauge eval |
| **mcp-eval** (lastmile-ai) | Task framework, `Expect` assertions, perf and cost metrics | [snippet] | Task-level, different from selection robustness |
| **MCPJam** | Cross-client testing, OAuth, LLM evals, CI | [snippet] | Commercial plus OSS; adjacent |
| **mcp-scan** (Invariant Labs) | Hash pinning (rug-pull detection), tool poisoning, cross-origin, toxic flows | [read-summary] | Pulse's drift classifier must not claim to replace it; interoperate in the README |
| **Anthropic Tool Search Tool + `defer_loading`** | Regex/BM25 retrieval of tool definitions; vendor-reported gains and token cuts | [read-summary] | A treatment arm in EXP-005, and a reason the dose-response curve may flatten for clients that use it |

## 2. Papers and what they license us to do

| Paper | Finding (from notes) | Level | How we use it |
|---|---|---|---|
| Wang et al., arXiv 2602.18914 | 18 description smells across 10,831 servers; controlled mutation moved selection accuracy by 52 pp (p<0.001) | [read-summary] | Motivates EXP-003; our edits come from this smell catalogue |
| Hasan et al., arXiv 2602.14878 | 97.1% of 856 tools had at least one defect; augmenting all description components raised median task success by 5.85 pp but increased execution steps by 67.46%, with regressions in 16.67% of cases | [read-summary] | **Central to Layer A.** The fix has a cost and sometimes hurts. Nobody ships a tool that tells you per edit. EXP-003 replicates direction on controlled fixtures |
| BiasBusters, arXiv 2510.00307 (ICLR 2026) | Systematic position bias and API bias in tool selection; strong sensitivity to the tool subset shown at K=2; weaker open models worse | [read-summary] | Basis of EXP-001. Our extension: measure it **per server per model on your own surface**, not in aggregate |
| ToolTweak, arXiv 2510.02554 | Earlier-listed tools are preferred; description manipulation can steer choice | [read-summary] | Position effect corroboration; also a security-adjacent warning |
| RAG-MCP, arXiv 2505.03275 | Retrieval raised selection from 13.62% to 43.13% and halved prompt tokens | [read-summary] | EXP-005 retrieval arm. **Note** its treatment is retrieval, not deferred loading |
| MCP-Zero, arXiv 2506.01056 | Active tool discovery; dual matching | [read-summary] | Related design; Later |
| LiveMCPBench, arXiv 2508.01780 | 95 real tasks over a large MCP ecosystem | [read-summary] | Candidate task source for EXP-005; check licence |
| HumanMCP, arXiv 2602.23367 | Hit rate falls roughly 10 pp from 10 to 100 tools (gpt-4o-mini row: 98.2 / 92.4 / 88.2) | **[snippet]** | Contradicts the "collapse to near random at 100 tools" story. See section 3 |
| MCPTox, arXiv 2508.14925 | High attack success of tool poisoning across many agents and real servers | [read-summary] | Pulse's drift classifier threat model |
| arXiv 2609.10962 (Beri et al.) | Of 400 sampled npm/stdio servers about half complete the handshake; 37.5% never start; 13.3% blocked by credentials; real descriptions rarely duplicate each other while benchmarks repeat heavily | **[read-summary]** (ID confirmed 2026-10-26; numbers from abstract/summary) | Layer C's motivation. Do not quote individual percentages without reading the methods section first |
| AlphaSignal Substack on tool-count budgets | One model 91% at 10 tools, 87% at 15; another at or above 90% up to 20, below by 30 | **[secondhand]** | Context only |

## 3. The literature disagrees, and that is the opportunity
Reported "how many tools is too many" numbers conflict: near-random past ~100 tools in one setup (RAG-MCP baseline, 13.62%), about a 10 pp drop from 10 to 100 in another (HumanMCP), a 49-to-74 and 79.5-to-88.1 improvement from search in vendor figures. Plausible reasons: model strength, how tools are rendered, whether distractors are similar to the target, task style (synthetic vs human-like), and metric. **No source we found separates these factors.** EXP-005 does, by crossing tool count with distractor type and with the treatment arm. Treat "43% to under 14%" as an unverified claim until reproduced.

## 4. Gaps we believe are open (each must survive the verification tasks)
1. Order-sweep position-bias measurement packaged for a user's own server. Papers measure it, no shipped tool found.
2. Paraphrase-robustness (flip rate) as a reported metric.
3. Per-edit accuracy **and** cost deltas for description rewrites, with a verdict (helps / costs / regresses).
4. Cross-server confusion graph for N servers loaded together.
5. Sandboxed start-rate SLO over time, plus drift classification beyond hash equality.
6. A reproduction of the tool-count dose-response with distractor type and retrieval arm crossed.
7. Interactive visualization of any of the above.

"We believe" is deliberate. A tool may exist that we missed.

## Open verification tasks (first session, report before building)
1. Search PyPI, npm, GitHub, arXiv for: order or position sweeps for MCP tools; paraphrase robustness for tool selection; cross-server collision; MCP server start-rate monitoring; description drift classification. Record query, date, hits, verdict. If gap 1 or 2 is already shipped, tell me; Layer A shrinks.
2. Install mcp-toolgauge, run it on its bundled good and bad fixtures. Record: licence, case file schema, how it renders tools to the model, whether tool order is fixed, model support, whether it supports multi-server. Decide ADR-003.
3. Read primary sources for every [read-summary], [snippet] and [secondhand] row you intend to quote. Upgrade the level here with the date.
4. Find the primary source for the server start-rate claim. If not found, drop the number.
5. Read BiasBusters' method: how they shuffle, K, models, metric. Our order sweep must be at least as careful.
6. Check Anthropic's docs for Tool Search and `defer_loading`: which models, API surface, whether usable inside our harness. Update EXP-005.
7. Check LiveMCPBench and HumanMCP licences and whether task sets can be redistributed or only referenced.
8. Check what Atlan publicly documents about its MCP server. No private or internal surface is ever used.
9. Check mcp-scan's current features so Pulse does not misstate them.
10. Confirm name availability on npm and GitHub; trademark sanity check.

Report format: a table of claim, source, level, date, and a list of surprises.
