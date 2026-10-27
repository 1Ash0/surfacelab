# 07 — Snapshots, drift, and content-addressed identity

## Why content addressing

A Snapshot records a surface at a point in time. Its stable identity is a
sha256 of the rendered surface bytes — the same bytes used as the cassette
key (ADR-005). This is content addressing: the hash encodes *what* the surface
is, not *when* it was captured or *who* captured it.

Content addressing gives three properties that timestamps do not:

1. **Deduplication**: identical surfaces — captured on different days or by
   different processes — produce the same hash and occupy one file in the
   store. No redundant storage, no ambiguity about which is "canonical."

2. **Direct lookup**: `store.load("server", hash)` is a single file read with
   no scanning. The filename *is* the hash.

3. **Immutability by construction**: a file named by its content hash can
   never be silently modified — any change would change the hash and produce a
   different filename. Idempotent save (skip if file exists) relies on this.

The `captured_at` timestamp is metadata: it records when a surface was
observed, not the surface's identity. Two snapshots with the same hash but
different timestamps are the same surface observed twice.

## The drift classifier

`classify_drift` compares two snapshots and returns a list of `DriftEvent`
objects, one per structural change:

| DriftKind | When |
|---|---|
| `unchanged` | Hashes are equal — short-circuit, no comparison needed |
| `added` | Tool present in new snapshot but not old |
| `removed` | Tool present in old snapshot but not new |
| `description_changed` | Same tool name, different description |
| `reordered` | Common tools appear in different relative order |

**Rename is not a drift kind.** A rename is observationally identical to
remove + add. Without a stable tool identifier (a UUID or a monotonic id that
survives renames), the classifier cannot distinguish them. Attempting to infer
renames from string similarity would be unreliable and introduce a new
failure mode — the classifier instead reports the observable facts.

**Why filter to common tools for the reorder check.** The reorder check
compares `common_old` (tools present in both snapshots, in old order) to
`common_new` (same tools, in new order). This isolates genuine ordering
changes among stable tools from the noise introduced by adds and removes. A
broken version that compares the full name lists would fire `reordered`
whenever any add or remove occurred, even if the relative order of the
unchanged tools was identical.

**Why the hash check is not optional.** The hash establishes the complete
identity contract: it encodes tool names, descriptions, order, and any other
serialized fields. The comparison loop names specific change *kinds* but
cannot enumerate all possible future fields. Skipping the hash check would
mean that a field added to `Tool` later would be silently ignored by the loop
while the hash would have caught it. The correct contract is: equal hashes →
`unchanged`, always, without running the loop.

## What drift means for the runner

When the runner detects drift before an experiment run:

- **`unchanged`**: proceed. The surface is the same as last time; existing
  cassettes keyed on this hash are valid.
- **`added` or `removed`**: the surface identity changed. Treat as a new
  surface. Old results keyed on the old hash do not apply.
- **`description_changed`**: cassettes keyed on the old surface are
  invalidated (the cassette key includes the description bytes). Re-run.
- **`reordered`**: the cassette key includes tool order (ADR-005), so old
  cassettes are invalidated for the new order. Results from the old order
  can still be used for the old order; they are not portable to the new one
  without re-running.
