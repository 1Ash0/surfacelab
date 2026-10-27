# 04 — Metamorphic probes: order and paraphrase

Classical testing needs a known correct output for every input — infeasible
when the oracle is a language model with no closed-form answer. Metamorphic
testing sidesteps this by defining an *invariance relation*: a transformation
of the input that should leave the output unchanged. For tool selection, two
relations matter. Order invariance: reordering the surface should not change
which tool is chosen. Semantic invariance: rephrasing the request without
changing its meaning should not change which tool is chosen. A *violation* is
when the output does change — it is not a bug in the grader, it is a measured
fragility in the model's selection.

`all_permutations` gives exact positional balance: for an N-tool surface it
returns all N! orderings, so each tool appears at each position exactly (N−1)!
times. Calling `permute` with K different seeds has no such guarantee — with
bad luck the same tool could dominate position 0 across all K runs, making
position 0 look unfairly good. Balance is required because any uneven coverage
confounds position with tool identity.

`paraphrase_valid` checks structural constraints on a candidate rewording of a
*request* (not a tool description): not identical to the original, within a
character-length ratio, and all named entities present. It does not check
semantic equivalence — a candidate can pass every constraint while subtly
changing meaning. That gap is why a sampled human audit is required before
using paraphrase results in a confirmatory experiment.
