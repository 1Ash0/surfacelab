# 05 — Description edits and verdict rules

## The edit catalogue

The edit catalogue is a closed list of five targeted changes to a single tool's
description. Each edit has a stable `edit_id`; changing the semantics of an
edit means a new id, because cassettes are keyed on the rendered surface and
must not silently change.

The five edits and what they do:

| edit_id | Operation |
|---|---|
| `add_usage_clause` | Appends "Use when: {content}." — narrows scope positively |
| `add_negation_clause` | Appends "Do not use for: {content}." — narrows scope negatively |
| `prepend_summary` | "{content}. {original description}" — adds a lead sentence |
| `set_description` | Replaces the entire description with content |
| `trim_to_first_sentence` | Keeps only up to the first [.!?] — shortens; no content arg |

`apply_edit` is pure: it takes a Surface and an Edit, returns a new Surface,
and never mutates its input. If the named tool is not in the surface, it raises
ValueError. Internally it uses `tool.model_copy(update={"description": …})` to
produce the modified tool — the idiomatic Pydantic v2 way to create a near-copy
with one field changed.

## Verdict rules (EXP-003)

A verdict maps `(accuracy delta CI, token delta)` to one of four outcomes. The
rule is written into the preregistration *before* any data is collected. This
matters because if you wait until you can see the results, you can unconsciously
choose thresholds that confirm the edits you prefer. Pre-declaration locks the
goalposts in place.

Decision tree evaluated in order (default params: margin=0.05,
token_threshold=50):

```
1. ci_lower > margin          →  helps        (CI entirely above practical threshold)
2. ci_upper < −margin         →  regresses    (CI entirely below threshold)
3. token_delta > threshold    →  costs        (ambiguous accuracy, high token cost)
4. otherwise                  →  inconclusive
```

**`helps` requires the lower bound to exceed margin.** The lower bound
represents the pessimistic end of the confidence interval. If `ci_lower > 0.05`,
the entire interval — pessimistic end included — is above the minimum
practically significant improvement. Using the upper bound instead would allow
a result like CI=(−0.03, 0.09) to be called "helps", even though the true
effect might easily be negative.

**`inconclusive` is not a failure.** It means the evidence is insufficient to
distinguish the edit's effect from noise at this sample size. The honest answer
when `n` is small is often `inconclusive`. Rerunning with more data is correct;
declaring a verdict that the CI does not support is not.

**`costs` is the costs-without-benefit case.** When accuracy is ambiguous (CI
not established positive or negative) AND the edit adds more than
`token_threshold` tokens, `costs` is the verdict: the edit consumes resources
without demonstrated benefit. This is operationally actionable — token cost
maps directly to latency and API cost.

**Multiple edits need Holm correction.** Running five edits raises the expected
number of false positives to 5 × 0.05 = 0.25 under Wald; with Holm, the
step-down threshold at rank k (0-indexed, sorted ascending by p-value) is
α/(m − k). For p=[0.02, 0.03, 0.04] and α=0.05: threshold at rank 0 is
0.05/3 ≈ 0.0167; 0.02 > 0.0167 → fail; Holm stops, 0 declared significant.
Even the smallest p-value does not clear the adjusted threshold when m=3.

## Overfitting risk

Repeatedly tuning description text to perform well on the same test cases makes
the description exploit the wording or patterns of those specific cases. A
dev/held-out split prevents this: edits are designed and selected on the
development set, then evaluated once on the held-out set. Paraphrase variants
of a request must stay in the same split as their original — otherwise the
model's familiarity with the original leaks into the held-out evaluation.
