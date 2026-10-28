# Experiments EXP-001–005 run; follow-ups proposed — 2026-10-28

## What happened
- EXP-001 to EXP-005 were run on Groq's free tier (`gpt-oss-20b` and `gpt-oss-120b`, 7 orgs, 14 keys) and analysed. Each verdict, with its deviations, is in its `docs/experiments/` file.
- Fixes found while running, all committed:
  - abstain cases need `tool_choice="auto"`; with `"required"` Groq rejects them with a 400, which looked like a rate-limit stall at 1440/1800;
  - the progress counter skipped failed trials, hiding the failures;
  - refusals (`tool_use_failed`) were being retried until the model complied, which discarded real outcomes; they are now recorded;
  - the client had no timeout, so hung requests held workers for 10 minutes;
  - temperature was never set in EXP-001 (now `--temperature`, 0 for every later run);
  - EXP-004's H3 permutation test turned an undefined correlation into a tiny p-value.

## Failures worth remembering
- **Ceiling.** goodserver is solved (100% for both models), so EXP-003, EXP-004 and EXP-005 mostly could not move. The design flaw was choosing an easy base surface for experiments that need room to change.
- **Fixture bugs.** `goodserver_trim` is identical to the base, and EXP-003's held-out split had no case for the calendar edit (H2).
- **Plan bug.** EXP-005's H2 contrast had the wrong sign for its own verdict rule.
- **Gold ambiguity.** In EXP-005, some "errors" picked distractors that could do the job (`compose_email_9` for send-email). Single-tool gold overstates error on near-duplicates.

## What was learned
- The robust signal is near-duplicate tools: siblings "accuracy" is 25–37%, and at temperature 0 it falls from first third to last (120b +10.4 pp [+2.1, +19.8], 8 families, not preregistered). See the caveat below: on siblings this is a tie-breaking bias, not an error rate.
- Temperature 0 on Groq is mostly but not fully deterministic (7 of 8 repeat groups stable per model).
- Slash-qualified tool names made 120b call tools that do not exist (8 of 12 under `qualified` in EXP-004).

## Decision
ADR-023 (proposed): follow-ups EXP-009–012 on near-duplicate surfaces with 32 families, preceded by an independent gold-validation pass. Drafts await approval. Fixtures are now written (see below); no runs yet.

## Found while writing the follow-up fixtures
- The `siblings` surface is four synonyms: identical descriptions reworded, with gold chosen by request keywords. Its "accuracy" measures which synonym gets picked, and its position effect is a tie-breaking bias among equivalent tools. Recorded as a caveat in EXP-001; the new `nd_*` surfaces give each tool one stated difference so a right answer exists.
- ADR-023 now includes a stop rule: EXP-009–012 verdicts are final for v0.1.
