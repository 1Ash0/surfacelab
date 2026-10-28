# ADR-027 — The Plate Room: one visual language for surfacelab

**Status:** proposed (2026-10-28), to be accepted together with ADR-026 and confirmed by the M0 look-test · **Revises:** ADR-017 (identity) · **Amends:** ADR-015 (where depth is used) · **Keeps:** every honesty rule in DESIGN §1, ADR-016, ADR-018, ADR-019, ADR-020
**Specimen:** the visual sample published with this ADR uses only recorded data (`results/exp013_120b.json`, `fixtures/surfaces/real_browser.json`).

This is a design review written as a lesson: what each early decision got right, where it would have gone wrong, and the direction it converges on.

---

## Part 1 · What the design has to do

surfacelab measures one thing: **a list of tools goes in, one tool call comes out, and we change what goes in** (ADR-026). The findings are all of one shape: *the same request, under two conditions, landed on the same tool or a different one.*

So the visual job is narrow and hard:

1. Make **one decision** visible: which tool the model called.
2. Make **a change in that decision** visible: did it move when the conditions changed?
3. Make the viewer **believe** it: the count, the interval and the source are always next to the picture.

Everything below is judged against those three. A visual choice that helps none of them is decoration, and DESIGN §1 already forbids decoration.

## Part 2 · The audit: every early decision, re-read against the findings

| Decision (source) | Verdict | Reasoning |
|---|---|---|
| The Observatory is an instrument you operate, not a report (ADR-017 concept) | **Keep: this is the core** | It is the right frame. Our method is observation: we don't build the model; we watch where its choice lands under controlled changes. |
| Honesty rules: every visual encodes a measurement, evidence rail, channel discipline, `simulated` badge (DESIGN §1, ADR-018) | **Keep, unchanged** | These are what make a deep dive on evaluation credible. They bind more tightly now that two chapters rest on exploratory results. |
| 3D for space, flow and time; never for quantities (ADR-015) | **Keep the rule, narrow its use** | Our strongest findings are comparisons (same request, two conditions). Comparisons read best side by side or overlaid, not orbiting. Depth is used where it means something physical: the order of a stack, and two layers laid over each other. See Part 5. |
| Seven scenes, one per planned experiment (ADR-015) | **Replaced by ADR-026** | The data chose a different story. |
| Stage: indigo-to-horizon gradient sky, slow parallax, depth fog (DESIGN §2) | **Drop** | A gradient sky is mood, and mood is the most common filler in generated interfaces. It also competes with the one thing that should catch the eye: the decision. |
| Marks as glowing glass beads with SDF highlight (DESIGN §2) | **Revise** | Glow on every mark means nothing glows. Marks become flat and exact. **Light is reserved for one thing: the model's call.** |
| Brass hairlines, reticle, mono readouts (DESIGN §2) | **Keep: these are the most original part of the plan** | Reticles and scales come from real measuring instruments. They stay, and become the whole visual vocabulary rather than an accent on top of glass and glow. |
| Frosted-glass evidence rail with blur (DESIGN §2) | **Drop the glass; keep the rail** | Blur panels read as generic app chrome, cost frame time on phones, and lower text contrast. The rail becomes an opaque, ruled record card (Part 4). |
| Film grain, optional bloom (DESIGN §2) | **Drop** | Neither carries data. Grain also blurs into noise once LinkedIn compresses a screenshot. |
| Semantic colours: mint = correct, vermilion = wrong, brass = possible (DESIGN §2) | **Revise** | Bright mint and vermilion on near-black is one of the most common generated looks. More important: correctness must read **without colour**. Shape carries it (Part 4); colour only confirms. |
| Six server hues (amber, teal, coral, lilac, lime, sky) + shapes (DESIGN §2) | **Revise to two primary hues + four reserve** | Most chapters show one or two servers. Two strong, distinguishable hues carry them; the reserve appears only in the web and workspace loadouts (three servers each). Fewer hues, more legible. |
| Daylight variant: cream ground, deep ink (DESIGN §2) | **Revise** | Warm cream with a serif is another common generated look, and it is not from our subject. Daylight becomes the light-box (Part 3): cool, clear, ink-dark marks. |
| Display face: refined grotesk or high-contrast serif (DESIGN §2) | **Decide now** (Part 4) | Leaving it open invites the default. |
| Motion: slow, damped, inertia; one easing family (DESIGN §2) | **Keep for the camera; add the blink** | The camera settles. Comparisons do not morph; they **blink** (Part 3). |
| No sound (DESIGN §2) | **Keep** | |
| Captures inherit the look; number and interval burned into a corner (DESIGN §2, ADR-019) | **Keep, and make it the post format** | The record card *is* the corner. |
| Vanilla three.js, own engine, custom shaders (ADR-016) | **Keep** | The revised marks are simpler (flat discs, rings, lines), which lowers shader and frame-time risk on phones. |
| Perception check EXP-008 (ADR-020) | **Keep, retargeted** (ADR-026) | It now tests chapter 4. |

### What the early plan would have shipped, without this review

A dark indigo sky with glowing glass beads, a frosted panel and a mint-and-vermilion palette. Each of those choices was reasonable alone. Together they look like many generated interfaces of 2025–26. And none of them comes from the thing we study.

## Part 3 · The converged idea: the Plate Room

### Where it comes from

From the 1880s to the 1990s, observatories photographed the sky onto glass plates. People found things by comparing plates of the same field:

- **The blink comparator** showed two plates of the same sky in rapid alternation. Anything that moved or changed appeared to jump. Clyde Tombaugh found Pluto this way in 1930.
- A plate was **measured** under a measuring engine: a reticle placed over each image, positions read off a scale.
- Every plate had a **record**: an envelope or log entry with the date, exposure, instrument and observer.

### Why it fits surfacelab, part by part

| Plate room | surfacelab | Where it shows |
|---|---|---|
| A plate of one field of sky | One request: its tool list, laid out | Every chapter |
| The blink comparator: same field, two plates, what jumped? | A metamorphic test: same request, two conditions, did the call move? | Chapters 2, 3, 5 and the coda |
| The reticle placed on an image | The tool the model called, marked | Every chapter |
| The plate's record card | The evidence rail: n, families, interval, source file | Every chapter |
| A plate stack in a drawer | The tool list in order, each plate as thick as its tokens | Chapter 1 |
| Two plates overlaid | Two servers loaded together | Chapter 5 |
| The same field re-photographed years later | The EXP-006 drift re-probe | S7, after 2026-11-11 |

This metaphor is not imported for mood. The blink comparator is the same method as our experiments, found by astronomers for the same reason: **the eye is bad at absolute judgment and very good at noticing what changed.**

### Two themes, both from the plate room

- **Night (the Tour default, phones, posts).** A positive print of the night sky: deep blue-black ground, pale marks, one warm light for the call. Dark reads well in a white feed and on a phone at night.
- **Light-box (embeds, docs, print).** A glass negative on a light table: clear cool-white ground, ink-dark marks, the call in deep warm ink. This is what an astronomer actually looked at.

The **geometry, marks and copy are identical** in both themes. Only the ground and the ink swap.

## Part 4 · The system

### The one rule of light

> **Only the model's call is lit.**

Tools are flat marks. Gridlines, scales and reticles are thin ink. The one luminous element on any frame is the **call**: a fine line from the request to the tool it landed on, ending in a reticle. When the viewer's eye goes to the brightest thing on screen, it lands on the decision. This replaces glow-everything with a single, meaningful light.

### Marks and states (shape first, colour second)

| State | Mark | Colour (confirms only) |
|---|---|---|
| A tool on the surface | flat disc, or a slab in the stack | server hue at reduced strength |
| The call (any outcome) | lit line + four-tick reticle | `--call` |
| Correct call | reticle closed (ticks join into a ring) | `--call` |
| Wrong call | reticle with a cross through it, **and** the right tool ringed with a dashed ring | `--miss` on the cross only |
| Refusal (`tool_use_failed`) | call line stops short, ends in an open bracket | `--muted` |
| Possible (drift flags, exploratory) | hollow diamond | `--possible` |
| Interval | thin bar with end ticks, never a shaded blob | ink |

A viewer with no colour vision reads every state. A greyscale screenshot keeps every state.

### Colour tokens

Named by role, not by hue. Two server hues carry most chapters; four more are held in reserve for three-server loadouts.

| Token | Night | Light-box | Role |
|---|---|---|---|
| `--ground` | `#0E1320` | `#EEF2F3` | the plate |
| `--ink` | `#D9DEE6` | `#18202B` | text and marks |
| `--ink-2` | `#8A93A3` | `#5A6472` | secondary text |
| `--rule` | `#26304180` | `#18202B26` | réseau grid and scales |
| `--call` | `#F2C46D` | `#9A5B00` | the lit call: the only light |
| `--miss` | `#E0707A` | `#A3243A` | the cross on a wrong call |
| `--possible` | `#B9A2E8` | `#5B3FA0` | exploratory / possible |
| `--srv-a` | `#7FB2D9` | `#1F5F8F` | first server in a chapter |
| `--srv-b` | `#9CC8A1` | `#2E6B3A` | second server |
| reserve | `#D7A8C8`, `#C9C27A`, `#9FB7B5`, `#D8B08C` | darker equivalents | third to sixth servers |

The call is a warm lamp yellow on night and a dark amber-brown ink on the light-box: the observer's lamp, and a pencil mark. Neither is a pop colour. Final values are fixed by the look-test (Part 7).

### Type

| Role | Face | Why this one |
|---|---|---|
| Claims and chapter titles | **Spectral** (Production Type, designed for screens) | A book serif made for reading on screens, with a scientific name that fits a lab about spectra of behaviour. Claims are full sentences; they deserve a reading face. |
| Interface, labels, rail text | **B612** | Designed for Airbus cockpit displays, where a misread label is a hazard. An instrument face, used as one. |
| Numbers, ids, tool names | **B612 Mono** | Same family, so numbers and labels share a voice; tabular figures for counts and intervals. |

Scale (rem): 0.75 · 0.875 · 1 · 1.25 · 1.75 · 2.5. Claims at 1.75–2.5 in Spectral; everything operated in B612. Tool names are always mono: they are code.

### The réseau and the scale

The ground carries a faint **réseau**: a square reference grid, like the one etched on astronomical plates so positions could be measured. It is reference, not data: fixed spacing, never moving, never varying with a measurement. Along one edge runs a **scale** with real units for the chapter (tokens in chapter 1, list position in chapter 3, trial count elsewhere). This is the hand-made detail the old plan wanted from grain and bloom, and it is functional.

### The record card (the evidence rail, redesigned)

An opaque card, ruled like a plate envelope, docked beside the plate on desktop and below it on phones:

```
EXP-013 · real_browser · gpt-oss-120b              exploratory
────────────────────────────────────────────────────────────
First call was list_pages        14 / 24 browser requests
                                 families 12 · orderings 2
Models   gpt-oss-120b (Groq) · temperature 0
Source   results/exp013_120b.json
Does not show   whether a later call would have done the task
```

Same fields as DESIGN §5, now laid out as a record. The label (confirmed, exploratory…) sits top right, in the same size as the experiment id. **The card is also the post caption**: a capture burns this card into the frame.

### Motion

- **The blink.** Every comparison alternates between its two conditions in place, about 1.5 times per second when playing, or on a single tap or keypress when the viewer drives it. Marks that stay put sit still; marks that change *jump*. No interpolation: an animated morph would invent intermediate states we never measured.
- **The settle.** Camera moves are slow and damped and then rest. Nothing loops on its own.
- **Reduced motion.** Every blink becomes the two conditions side by side, with the changed marks outlined.

## Part 5 · Where depth is used (amends ADR-015)

ADR-015's rule stays: depth never encodes a quantity. The plate room makes *where* depth is used concrete:

| Use of depth | Chapter | Why it is honest |
|---|---|---|
| A stack of plates, in list order | 1 | Depth is the order the model reads, which is spatial and physical. Plate thickness = tokens is read face-on, with a scale, never through perspective. |
| Two plates overlaid | 5 | Loading a second server *is* laying another layer on top. Lifting the top plate away shows what each server holds. |
| Tilting a plate to look along it | 4 (optional) | The Galaxy starts as a **flat plate**: a 2D similarity map read like a star chart, with the caption *similarity, not confusion*. Tilting is an interaction, not the default. A 3D embedding cloud adds occlusion and misreading on a phone for no gain in information. |

Everywhere else the camera faces the plate square-on. This is a deliberate narrowing of "3D leads": **space leads; depth is earned.** EXP-008 will test whether the tilted view helps anyone; if not, it goes.

## Part 6 · The Tour in this language

| Chapter | The plate | What blinks or moves | Record card headline |
|---|---|---|---|
| 1 · The Request | 31 plates stacked in list order, edge-on to face-on; thickness = tokens on a scale | The camera rotates the stack once, then rests | 3,493 / 6,232 prompt tokens (gpt-oss / Qwen) |
| 2 · What didn't matter | One request; the call holds still as the list shuffles, the request rewords, distractors fill in | Blink between conditions: nothing jumps. Then the flat **Null Wall**: six intervals on one zero line | six tiles, each with its own interval |
| 3 · Ties | The four synonym tools in a row, each ordering in turn | Blink between orderings: the call jumps with the slot, not the tool; a slot strip fills in | +10.4 pp [+2.1, +19.8] · +12.5 pp [+2.1, +25.0] |
| 4 · Real servers | Flat similarity plate of the real loadouts, clusters by server | Tap your guess; the recorded wrong call lights; the right tool gets its dashed ring; most misses land next door | 0.78 / 0.77 / 0.91 right tool; misses at the 71st similarity percentile |
| 5 · A second server | Playwright plate; Chrome DevTools plate lowered on top | Blink Playwright-first vs Chrome-first: calls jump to `list_pages` | 14 / 24 first calls were `list_pages` |
| Coda · Who wins | Three search servers side by side | Blink orderings: the winner barely moves | inconclusive, said at full size |

## Part 7 · The M0 look-test, rewritten

Run on a real mid-range phone and a desktop, both themes, from the same recorded data:

1. **Find the call in under one second.** Show a frame to someone for one second. Can they point to the tool the model chose? If not, the call is not the brightest thing.
2. **Greyscale.** Every state in the marks table must read with colour removed.
3. **Compression.** A screenshot squeezed to the size LinkedIn shows in a feed must still show the reticle and read the card's headline number.
4. **The blink.** On chapter 5, can a viewer say which requests changed tool without reading the card?
5. **Two themes, one geometry.** Night and light-box from the same frame: nothing moves, only ground and ink.
6. **Colour-vision simulation** of `--srv-a`, `--srv-b`, `--call` and `--miss` (protanopia, deuteranopia, tritanopia).
7. **The decoration test.** Point at any element and ask "what measurement drives this?" Anything without an answer is removed, except the réseau, which is labelled as reference in the help.

## Part 8 · What would make this bad

The plate room fails if it becomes a costume:

- sepia, scratches, fake aged glass or a "vintage" filter: the reference is the *method*, not nostalgia;
- more than one lit element per frame;
- a blink that animates through invented in-between states;
- the réseau moving, pulsing or tightening with data;
- star-colour (spectral class) hues for servers, which would imply an order that categories do not have;
- any copy that turns "the model's first call changed" into "this server is bad";
- the record card hiding the interval, or the label smaller than the number.
