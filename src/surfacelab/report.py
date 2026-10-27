"""Aggregate TrialResults into a structured experiment report.

make_report groups trials by case_id (families), computes per-family accuracy,
and computes aggregate accuracy with a Wilson confidence interval.

The Wilson CI is on raw trial proportions — it does not reweight by variant or
correct for clustering. Use stats.clustered_bootstrap for a clustered CI when
the within-family correlation matters.
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass

from .runner import TrialResult
from .stats import wilson_interval


@dataclass(frozen=True)
class FamilySummary:
    """Accuracy summary for one case (all its trials across variants)."""

    case_id: str
    n_trials: int
    n_correct: int
    n_errors: int
    accuracy: float   # n_correct / n_trials; 0.0 when n_trials == 0


@dataclass(frozen=True)
class ExperimentReport:
    """Aggregate report over all trials in a run."""

    n_cases: int
    n_trials: int
    n_correct: int
    n_errors: int
    accuracy: float
    ci_lower: float   # Wilson interval lower bound
    ci_upper: float   # Wilson interval upper bound
    families: list[FamilySummary]


def make_report(trials: list[TrialResult]) -> ExperimentReport:
    """Build an ExperimentReport from a flat list of TrialResults.

    Families are ordered by first appearance of the case_id in trials, which
    matches the runner's case-outer / variant-inner loop order.
    """
    # Group trials into families, preserving case order.
    seen: dict[str, list[TrialResult]] = {}
    for t in trials:
        seen.setdefault(t.case_id, []).append(t)

    families: list[FamilySummary] = []
    for case_id, fam in seen.items():
        n = len(fam)
        nc = sum(1 for t in fam if t.correct)
        ne = sum(1 for t in fam if t.error is not None)
        families.append(FamilySummary(
            case_id=case_id,
            n_trials=n,
            n_correct=nc,
            n_errors=ne,
            accuracy=nc / n if n > 0 else 0.0,
        ))

    n_trials = len(trials)
    n_correct = sum(1 for t in trials if t.correct)
    n_errors = sum(1 for t in trials if t.error is not None)
    ci_lower, ci_upper = wilson_interval(n_correct, n_trials)

    return ExperimentReport(
        n_cases=len(families),
        n_trials=n_trials,
        n_correct=n_correct,
        n_errors=n_errors,
        accuracy=n_correct / n_trials if n_trials > 0 else 0.0,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        families=families,
    )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_text(report: ExperimentReport) -> str:
    """Format an ExperimentReport as a plain-text table for the CLI."""
    lines: list[str] = []
    w = 32  # column width for case id
    lines.append(f"{'case_id':<{w}} {'trials':>7} {'correct':>8} {'errors':>7} {'acc':>6}")
    lines.append("-" * (w + 34))
    for fam in report.families:
        acc = f"{fam.accuracy:.0%}"
        lines.append(
            f"{fam.case_id:<{w}} {fam.n_trials:>7} {fam.n_correct:>8} {fam.n_errors:>7} {acc:>6}"
        )
    lines.append("-" * (w + 34))
    acc_str = f"{report.accuracy:.1%}"
    ci_str = f"[{report.ci_lower:.3f}, {report.ci_upper:.3f}]"
    lines.append(
        f"{'TOTAL':<{w}} {report.n_trials:>7} {report.n_correct:>8} {report.n_errors:>7} {acc_str:>6}"
    )
    lines.append(f"Wilson 95% CI: {ci_str}")
    return "\n".join(lines)


def render_html(report: ExperimentReport) -> str:
    """Render an ExperimentReport as a self-contained HTML page."""

    def esc(s: str) -> str:
        return _html.escape(str(s))

    rows: list[str] = []
    for fam in report.families:
        acc_pct = f"{fam.accuracy:.0%}"
        rows.append(
            f"<tr>"
            f"<td>{esc(fam.case_id)}</td>"
            f"<td>{fam.n_trials}</td>"
            f"<td>{fam.n_correct}</td>"
            f"<td>{fam.n_errors}</td>"
            f"<td>{acc_pct}</td>"
            f"</tr>"
        )

    family_rows = "\n        ".join(rows)
    total_acc = f"{report.accuracy:.1%}"
    ci = f"[{report.ci_lower:.3f}, {report.ci_upper:.3f}]"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>surfacelab report</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #111; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.25rem; }}
  .summary {{ font-size: 1.1rem; margin-bottom: 1.5rem; color: #444; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  th {{ text-align: left; padding: 0.4rem 0.6rem; border-bottom: 2px solid #ccc; }}
  td {{ padding: 0.35rem 0.6rem; border-bottom: 1px solid #eee; font-variant-numeric: tabular-nums; }}
  tr:last-child td {{ border-bottom: none; }}
  .tfoot td {{ font-weight: 600; border-top: 2px solid #ccc; }}
  .ci {{ font-size: 0.8rem; color: #666; margin-top: 0.5rem; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e8e8e8; background: #111; }}
    .summary {{ color: #aaa; }}
    th {{ border-bottom-color: #555; }}
    td {{ border-bottom-color: #2a2a2a; }}
    .tfoot td {{ border-top-color: #555; }}
    .ci {{ color: #888; }}
  }}
</style>
</head>
<body>
<h1>surfacelab experiment report</h1>
<div class="summary">
  {report.n_cases} cases &middot; {report.n_trials} trials &middot;
  accuracy <strong>{total_acc}</strong> &middot; Wilson 95% CI {esc(ci)}
</div>
<table>
  <thead>
    <tr>
      <th>case_id</th>
      <th>trials</th>
      <th>correct</th>
      <th>errors</th>
      <th>accuracy</th>
    </tr>
  </thead>
  <tbody>
        {family_rows}
  </tbody>
  <tfoot>
    <tr class="tfoot">
      <td>TOTAL</td>
      <td>{report.n_trials}</td>
      <td>{report.n_correct}</td>
      <td>{report.n_errors}</td>
      <td>{total_acc}</td>
    </tr>
  </tfoot>
</table>
<p class="ci">Wilson 95% CI on raw trial proportions. Does not reweight by family or correct for clustering.</p>
</body>
</html>
"""
