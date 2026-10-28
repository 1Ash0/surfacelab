# ADR-026 — The Tour follows the findings, not the experiment list

**Status:** proposed (2026-10-28) · **Supersedes:** the Tour order in DESIGN §3 and the milestone-to-scene mapping in DESIGN §4 / ROADMAP · **Keeps:** ADR-015 (3D leads, evidence rail mandatory), ADR-016 (vanilla three.js), ADR-017 (Dusk Observatory), ADR-018 (recorded data only), ADR-019 (deterministic capture)
**Sources:** every number below is a row of `docs/FINDINGS.md`, which cites its results file.

---

## 1. The one idea

surfacelab measures one thing:

> **A list of tools goes in. One tool call comes out. What changes that call?**

That is the whole product. Every experiment was the same request with one thing changed: the order of the list, the wording of the request, a description, the number of distractors, the servers loaded beside it. Every result is a count of which tool came out.

So the Tour gets **one primitive**, the *Request*: a stack of tool slabs and a beam that lands on the chosen one. Every chapter is that Request with one manipulation and the recorded outcomes. No composite "robustness score", no index, no abstraction the data does not have. If a viewer remembers one picture, it is a beam landing on a tool, and the tool being the wrong one.

## 2. Why decide this now

The current Tour (Request Anatomy → Galaxy → Shuffle → Collision → Rain) was written before any run, one scene per planned experiment. The data has since chosen a different story:

| Planned chapter | What the data says | Consequence |
|---|---|---|
| Shuffle (order bias) | Absent where tools are distinct (99.6–100% at every position); present only among synonym tools (+10.4 pp, +12.5 pp) | Keep, but the reveal is "order only matters when tools are the same" |
| Collision (namespacing) | 1 collision in 288 trials; namespacing made no difference | Demote to a tile in the null-results chapter |
| Rain (distractors) | No dose-response up to 50 distractors | Demote to a tile in the null-results chapter |
| (not planned) | On real servers, gpt-oss misses the only right tool 22–23% of the time; misses land on look-alike descriptions | New centre of the Tour |
| (not planned) | Co-loading Chrome DevTools changed the first action in 14 of 24 browser requests (gpt-oss-120b) | New chapter |

A Tour that follows the old order would spend three of five chapters on effects we did not find. For a deep dive on evaluation, nulls must be shown, but as the evidence that makes the positive findings believable, not as the plot.

## 3. Principles, and where they come from

Each principle is borrowed from work that does this well, adapted to our rules.

1. **Claim first, scene second.** Each chapter is exactly one row of `FINDINGS.md`, stated as a sentence before anything moves. The scene earns the claim; it does not replace it. *(Distill: the figure carries the argument, but the argument is written.)*
2. **Predict, then reveal.** Before a number appears, the viewer commits a guess: drag a slider, tap a tool. Then the recorded result lands next to their guess. People remember the gap between what they expected and what happened. *(The New York Times Upshot, "You Draw It", 2015.)*
3. **The reader works the instrument.** The viewer shuffles the list, swaps servers, adds a server, and watches the recorded beam respond. Nothing is simulated; every state they can reach has recorded trials behind it. *(Bret Victor, "Explorable Explanations", 2011.)*
4. **Every figure carries its source and its uncertainty.** The evidence rail shows n, families, the interval and the results file path, and a "download data" link, on every chapter. *(Our World in Data: each chart links its source and data.)*
5. **Nulls are findings.** One chapter shows everything that did *not* matter, each with its interval reaching zero. It is the control group for the whole Tour: it is why the viewer should believe the effects that remain.
6. **Say what the model did, never what a vendor did wrong.** Copy describes model behaviour on combinations of servers. Allowed form: "with Chrome DevTools loaded next to Playwright, the model's first call was a page listing in 14 of 24 browser requests". Never "Chrome DevTools breaks agents".

## 4. The Tour (five chapters and a coda)

Each chapter: a **hook** (the question the viewer answers before the reveal), the **reveal** (the recorded number), the **scene**, and the **limit line** the rail must show.

| # | Claim (FINDINGS row) | Hook | Reveal | Scene | Label |
|---|---|---|---|---|---|
| 1 | Before reading your request, the model reads every tool you installed | "Two browser servers. How long is the tool list the model reads before your message?" (slider in tokens) | 3,493 prompt tokens on gpt-oss and 6,232 on Qwen for the same 31 tools (Groq-reported) | **S1 Request Anatomy** on `real_browser` | measured |
| 2 | When each tool states a distinct job, the choice barely moves | "Shuffle the list. Reword the request. Add 50 distractors. How often does the answer change?" (guess a %) | A wall of six tiles, each an interval at or near zero: order (99.6–100% at every slot), wording (2.6–5.1% flips, all refusals), edits (ceiling), distractors (92–100%), namespacing (1 collision in 288), second model family (768/768) | **Null Wall** (new, flat 2D inside the stage) | absent / not confirmed / replicated |
| 3 | When tools do the same job, position breaks the tie | "Four tools that do the same thing. How often does the first one win?" (drag on the slot strip) | First third beats last third by +10.4 pp [+2.1, +19.8] (gpt-oss-120b) and +12.5 pp [+2.1, +25.0] (Qwen) | **S3 Shuffle Rack** on `siblings` | exploratory, replicated on a second family |
| 4 | On real servers, the model misses the one right tool, and misses land on look-alikes | "Here is a request only one tool can do. Tap the tool you think the model picked instead." | Right tool found 0.78 / 0.77 / 0.91 (20b / 120b / Qwen), against 0.99+ on our surfaces; wrong picks sit at the 71st percentile of similarity to the right tool (67th with a second embedding) | **S2 Galaxy v1** on the four real loadouts, edges = measured confusions | not confirmed (gpt-oss); exploratory (similarity) |
| 5 | Installing a second server can change what the agent does first | "Add Chrome DevTools next to Playwright. Ask the agent to click a button. What does it do first?" (tap a tool) | First call was Chrome DevTools' page listing in 14/24 (120b), 9/24 (20b), 4/24 (Qwen) browser requests, including jobs only Playwright can do | **S4 Merge Collider**, repurposed: the second server's cluster arrives, first-call beams shift | exploratory |
| Coda | Which server wins a shared job is a model habit, not list position | "Brave, Tavily, DuckDuckGo all search. Which one does the model use?" | Order moved the winner in 19–25% of shared cases (H1 inconclusive); otherwise each model keeps its own favourite (e.g. Qwen: Playwright 10 of 10) | Merge Collider, order toggle | inconclusive / exploratory |

The Tour ends at **"Run it on your servers"**: the Bench (drop a `tools/list`) and the one CLI command that produces the files these chapters read.

### Chapter scripts

**1 · The Request.** The camera starts on the user's one-line message, then pulls back to reveal what sits in front of it: 31 slabs, thickness = tokens, hue = server. The hook slider asks for a guess; the stack's real token count lands beside it. Limit line: *"Token counts are what Groq reported for these tools; other providers count differently."*

**2 · What didn't matter.** The Request reappears, and the viewer can shuffle it, reword it, pad it with distractors. The beam does not move. Then the scene flattens into the Null Wall: six tiles, each a point and interval on a shared zero line, each linked to its experiment. This chapter is deliberately 2D: it is a comparison, and comparisons stay flat (ADR-015). Limit line: *"These surfaces were written by us, with one clear job per tool."*

**3 · Ties.** The four `siblings` tools are near-synonyms. The scrubber steps through all 24 orderings; the beam follows the slot, not the tool, and the ghost strip fills in by position. The viewer's guess for the first slot is drawn on the strip before the recorded bars rise. Limit line: *"8 families; the second family (Qwen) replicates the direction."*

**4 · Real servers.** The four real loadouts appear as clusters in the Galaxy, positioned by description similarity (caption: *similarity, not confusion*). Edges appear only where a recorded trial picked the wrong tool. The viewer taps their guess for a request; the recorded wrong pick lights up, usually a near neighbour. Limit line: *"48 families, 3 open models, one provider; first call only."*

**5 · A second server.** Playwright alone; then Chrome DevTools' cluster drifts in (deterministic, skippable). Requests that only Playwright can serve fire beams; many now land first on `list_pages`. The rail shows the per-model counts. Limit line: *"Scored on the first call. In a multi-step agent the next call may be right; this measures the first action, not the outcome."*

**Coda · Who wins.** A toggle swaps which search server is listed first. The winners barely change; the rail says *inconclusive* in the same type size as the number.

## 5. The scene ledger

| Scene | Decision | Why |
|---|---|---|
| S1 Request Anatomy | **Keep**, now on real servers | Shows the primitive; no model calls needed; first thing the M0 spike renders |
| S2 Galaxy | **Keep**, v1 on real loadouts | Carries finding 4; the one place similarity and confusion meet, so the caption rule matters most here |
| S3 Shuffle Rack | **Keep** | Carries finding 3 |
| S4 Merge Collider | **Repurpose**: from namespacing to "add a server" | Namespacing found nothing; adding a server changed behaviour |
| Null Wall | **New** (flat) | Nulls get one honest chapter instead of three hopeful ones |
| S5 Selection Rain | **Observatory only** | EXP-005/012 are nulls; they live as a Null Wall tile and as a scene for the curious |
| S6 Edit Migration | **Later** | No edit was ever measured to help or hurt (EXP-003 ceiling, EXP-010 not run); a scene about edit effects would decorate |
| S7 Pulse Ribbons | **After the EXP-006 re-probe** | A drift scene needs two snapshots; the second is planned for 2026-11-11 |

## 6. The data contract (what makes "no stats in the browser" real)

One record type, defined once in Pydantic and exported as JSON Schema (TS types generated from it, as ADR-016 requires):

```text
Finding
  id               "f4-real-servers-miss"     stable, used in URLs
  claim            one sentence, as in FINDINGS.md
  label            confirmed | not_confirmed | absent | inconclusive | exploratory | replicated | measured
  experiments      ["EXP-013"]
  models           ["openai/gpt-oss-20b", ...]
  n_families, n_trials
  estimate         { point, lower, upper, unit, interval_method }   per model when it differs
  source           "results/exp013_analysis.json"  + the JSON path of each number
  limits           the chapter's limit line
  scene_data       path to the scene's binary/JSON payload
```

`surfacelab export findings` reads `results/` and writes `web/public/data/findings/*.json`. A CI check fails if any number in `FINDINGS.md` or in a chapter's copy is not present in its `source` file. The web app formats numbers; it never computes one.

## 7. Hook rules

- A guess is never stored or sent anywhere; it lives in the page and is gone on reload.
- The reveal always shows the recorded number **and its interval**, beside the guess, in the same type size.
- No scoring, streaks or "you were wrong" copy. The point is the gap, not the grade.
- Every hook has a skip that goes straight to the reveal, and a reduced-motion path with no animation.
- Hooks never ask the viewer to guess something we did not measure.

## 8. What this decision costs

- **Merge Collider changes job.** Its force-layout code is reused; its edges now mean "first call landed here" instead of "cross-server collision". DESIGN §4 is updated so no channel means two things.
- **Null Wall is new work**, but flat and small: six tiles, one zero line, links out.
- **S2 Galaxy v1 needs embeddings of real loadouts**, already cached for both models from EXP-013 H4.
- **The Tour leans on exploratory results** (chapters 4 and 5). The rail must say "exploratory" as loudly as the number, and the post copy must too. If a later preregistered run fails to replicate either one, the chapter changes, and we say so.

## 9. How we will know it worked

- **EXP-008 (perception check)** is retargeted to chapter 4: can a peer, using Galaxy + rail, name the pair of tools the model confused faster or more accurately than with the table alone? Reported either way (ADR-020).
- On a mid-range phone, each chapter's claim and number are readable within 30 seconds of arriving, with the 3D layer off.
- Every number in the Tour resolves to a `source` path (CI check above).

## 10. Build order

1. **M0 spike** renders Chapter 1 (S1 on `real_browser`): instanced slabs, picking, quality tiers, on a real phone.
2. `Finding` schema + `surfacelab export findings` + the CI trace check.
3. Chapter 2 (Null Wall) and Chapter 3 (Shuffle Rack): the flat chapter and the simplest motion.
4. Chapter 4 (Galaxy v1) and Chapter 5 (Merge Collider, add-a-server).
5. Coda, Bench handoff, capture mode and post stills per chapter.

## 11. Revisit if

- The EXP-006 re-probe finds drift: S7 Pulse Ribbons returns as a coda chapter.
- A preregistered follow-up confirms or overturns chapter 4 or 5.
- EXP-008 shows the Galaxy does not help people find confused pairs: chapter 4 becomes a ranked pair table with the Galaxy as an optional view.
