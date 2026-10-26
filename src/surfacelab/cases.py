"""Case schema and fixture loader.

A Case is the unit of evaluation: one user request, one gold set, one kind.
The gold set is a frozenset because order doesn't matter and duplicates don't
make sense — two identical tool names in the gold set would be a fixture error.

Surface coupling: a case is written for a named surface. Running it on a
different surface (even the same tools reordered) requires re-validating gold,
because a different surface may introduce new siblings that the gold set doesn't
account for.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, field_validator


class CaseKind(str, Enum):
    positive = "positive"   # one correct tool; model must call it
    sibling  = "sibling"    # one correct tool with near-duplicates; same grading as positive
    abstain  = "abstain"    # no tool should be called; model must emit nothing


class Case(BaseModel):
    id: str                      # stable identifier; never reuse after a case is recorded
    kind: CaseKind
    request: str                 # the user message shown to the model; must pass the leakage audit
    gold: frozenset[str]         # acceptable tool names; empty iff kind == abstain
    surface_name: str            # the surface this case was written for
    note: str = ""               # human note — siblings, why certain tools are wrong, etc.

    @field_validator("gold")
    @classmethod
    def gold_must_be_empty_iff_abstain(cls, v: frozenset[str], info: object) -> frozenset[str]:
        # Access the already-validated data via info.data if available
        data = getattr(info, "data", {})
        kind = data.get("kind")
        if kind == CaseKind.abstain and v:
            raise ValueError("abstain cases must have an empty gold set")
        if kind in (CaseKind.positive, CaseKind.sibling) and not v:
            raise ValueError("positive/sibling cases must have a non-empty gold set")
        return v


def load_cases(path: Path) -> list[Case]:
    """Load cases from a JSONL file. Each line is one Case."""
    cases: list[Case] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            cases.append(Case.model_validate(json.loads(line)))
        except Exception as exc:
            raise ValueError(f"{path}:{i+1}: {exc}") from exc
    return cases
