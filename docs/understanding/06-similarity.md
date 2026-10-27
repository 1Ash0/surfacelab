# 06 — Similarity: embeddings, BM25, and what they measure

## What cosine similarity measures — and what it does not

Cosine similarity measures the angle between two embedding vectors. Two tool
descriptions with similar cosine similarity have been mapped to nearby
directions in the embedding space — the model that produced the embeddings
thinks they are semantically related.

What it does **not** establish:
- That the tools are interchangeable. Two tools can be semantically close and
  still be correctly distinguishable by a model given the right request.
- That a model will confuse them. Confusion is a measurement from selection
  trials; cosine similarity is a prior, not a result.
- Actual selection accuracy. The similarity matrix predicts *expected* hard
  cases; the experiments measure actual ones.

For `similarity_matrix` to return valid cosine similarities (values in [-1,1]),
all input vectors must be normalized to unit length first. Without
normalization, the dot product equals the product of magnitudes times the
cosine — a number that grows with vector scale and has no upper bound. The
diagonal of an unnormalized matrix is not 1.0; it is the squared magnitude of
each vector.

## BM25 and what the lexical baseline measures

BM25 ranks tool descriptions by keyword overlap with the request. High score =
many of the query terms appear in the description, weighted by rarity (IDF).

The baseline answers: *could a keyword search have made the right call?* If
model accuracy ≈ BM25 accuracy, the model is not doing more than keyword
matching. If model accuracy >> BM25, the model generalizes beyond word overlap.
If model accuracy < BM25, the model is ignoring obvious lexical signals.

BM25 has known failure modes:
- **Rare-term overweighting**: a term that appears in only one description gets
  high IDF. If that term matches the request accidentally (or via a negation
  clause — "Do not use for: weather"), BM25 misdirects.
- **No semantic generalization**: a request asking for "temperature" scores
  zero on a description containing "weather" — BM25 cannot bridge synonyms.

## UMAP

UMAP reduces N-dimensional embedding vectors to 2D for visualization. It
approximately preserves local neighborhoods (nearby points stay near), but
global distances are distorted. Two tools that are far apart in 2D may be
closer in the original space than they appear, and vice versa.

In surfacelab, UMAP is a visualization export only:
- Run once in a script, coordinates saved as fixtures.
- The Observatory renders the 2D plot; it does not compute UMAP.
- UI must label the plot "exploratory — distances are approximate."

Never cite a UMAP distance as evidence of similarity. Use the cosine similarity
matrix for that.

## Checking robustness: second embedding + BM25

A single embedding model's results are tied to that model's biases. Running a
second embedding model checks whether the finding replicates across models. If
both agree, the result is more trustworthy. If they disagree, the effect is
model-specific, not a general property of the surface.

BM25 serves the same role for lexical vs. semantic decomposition: if the result
holds for BM25, it was achievable without dense representations. If it holds
only for the embedding model, the model is doing genuine semantic work.

## Permutation test for Spearman correlation

EXP-004 asks: does selection accuracy correlate with surface spread (average
pairwise cosine distance)? Spearman's ρ measures the rank correlation between
spread and accuracy across surfaces. To test whether the observed ρ is
significant, a permutation test is used:

1. Compute observed ρ on the real data.
2. Shuffle one variable (e.g. accuracy values) randomly, recompute ρ. Repeat
   many times (e.g. 10,000).
3. The p-value is the fraction of shuffled ρ values as extreme as the observed.

This is non-parametric: it makes no distributional assumptions. It tests
whether spread and confusion are associated beyond chance, without assuming
normal residuals or linear relationships.
