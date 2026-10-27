# 08 — Runner, report, and the harness boundary

## The harness boundary

The runner accepts a `Harness = Callable[[Case, Surface], str | None]`. This
is the only place in the codebase where a live API call may cross. Everything
the runner does — grading, recording, grouping into families — operates on
the harness's return value, not on the API directly.

This separation has two consequences:

1. **Testability**: any fake function that returns a scripted tool name is a
   valid harness. Tests never need an API key or a network connection.

2. **Budget enforcement**: the harness itself enforces `budget.check` before
   calling the API. The runner knows nothing about cost; the harness decides
   whether to proceed.

## Error handling

Harness exceptions are caught with `except Exception`. `KeyboardInterrupt`
and `SystemExit` inherit from `BaseException`, not `Exception`, so they
propagate naturally — the user can always abort with Ctrl-C.

Each caught exception produces:
- A `TrialResult` with `correct=False`, `emitted=None`, and `error` set to
  the exception message. The trial is **present** in the results.
- A `RunError` in the parallel errors list for inspection.

Silently dropping a failed trial is worse than recording it as incorrect:
a dropped trial removes an observation from the denominator. `make_report`
computes accuracy as `n_correct / n_trials`; if a failed trial is excluded,
the denominator shrinks without disclosure and the reported accuracy is
biased toward the surviving trials.

## Trial layout and families

The runner's outer loop is cases, inner loop is variants. This guarantees
that all K variant trials of one case are contiguous in the output list — a
property `make_report` exploits when it groups by `case_id`.

Swapping the loops (outer = variants, inner = cases) produces the same set
of (case, variant) pairs and the same family groupings, so `make_report`
returns the same report. The loop order is a runner-internal choice, not
observable in the report.

## Wilson CI vs. clustered bootstrap in the report

`make_report` uses `wilson_interval(n_correct, n_trials)` for the aggregate
CI. This is correct for a first-pass report, but it treats all trials as
independent Bernoulli draws.

Within-family correlation arises because all trials of one case share the
same underlying request difficulty. A case that is hard for the model will
fail across most variants; a case that is easy will pass most. Trials within
a family are not independent — they are clustered.

Wilson underestimates uncertainty when within-family correlation is
substantial because it assumes the effective sample size equals the trial
count. The actual effective sample size is smaller. `stats.clustered_bootstrap`
resamples entire families (not individual trials) to preserve this dependence
and produce a calibrated CI.

For a run with high within-family correlation, a Wilson CI that says
(0.55, 0.85) might become (0.45, 0.90) under clustered bootstrap — a
materially wider interval that correctly reflects the uncertainty.

## What differs between Wilson CIs at n=4 and n=100

Both at 0.75 accuracy:
- n=4: Wilson CI ≈ (0.30, 0.95) — very wide; 4 trials is almost no
  information.
- n=100: Wilson CI ≈ (0.65, 0.83) — narrow; the proportion is well-estimated.

The width scales roughly as 1/√n. This is why the planned trial count
(determined by `n_cases × n_variants`) must be chosen to achieve adequate
power before data collection (preregistration rule).
