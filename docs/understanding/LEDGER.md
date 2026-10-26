# Understanding Ledger

One row per gate attempt. Record first wrong answer and what fixed it — this is the trace that shows you learned it, not just passed it.

| Date | Unit | Gate | Result | First wrong answer | What fixed it |
|---|---|---|---|---|---|
| 2026-10-26 | U0 | G0 | Pass | Q1: missed "what tools/list does NOT tell you"; Q4: needed explanation rather than self-answering | Q1: surface is a static declaration, not a response to intent; Q4: we measure the choice not the execution (ADR-008) |
| 2026-10-27 | U1 | G1 | Pass | Q4: included a "tools" field in fixture JSON (surface concern, not case concern); positive and sibling share the same grading code path — kind is for analysis not routing | Surface and case are separate schemas; kind determines gold-set validation and result slicing, not a different grader branch |
