"""Probe variants: pure functions that transform a Surface or a Case.

All functions are pure — they return new objects and never mutate their inputs.
Each variant function corresponds to a study factor in an experiment.

U4: permute (order factor) and paraphrase_valid (semantic-equivalence check).
U5: edit (targeted one-field description changes, EXP-003).
"""

from __future__ import annotations

import itertools
import random
import re
from dataclasses import dataclass

from .schema import Surface, Tool

# ---------------------------------------------------------------------------
# Permutation variants (C04 — position effects)
# ---------------------------------------------------------------------------


def permute(surface: Surface, seed: int) -> Surface:
    """Return a new Surface with tools shuffled using the given seed. Pure."""
    tools = list(surface.tools)
    rng = random.Random(seed)
    rng.shuffle(tools)
    return Surface(server_name=surface.server_name, tools=tools)


def all_permutations(surface: Surface) -> list[Surface]:
    """Enumerate all N! orderings of the surface tools.

    Use for N<=5 (at most 120 surfaces). Each tool appears at each position
    exactly (N-1)! times — the only way to guarantee exact positional balance.
    """
    return [
        Surface(server_name=surface.server_name, tools=list(perm))
        for perm in itertools.permutations(surface.tools)
    ]


def balanced_permutations(
    surface: Surface,
    k: int,
    seed: int = 42,
) -> list[Surface]:
    """Return k permutations with approximately balanced position coverage.

    For N<=5 and k >= N!: returns every ordering once (complete enumeration).
    For N<=5 and k < N!:  samples k distinct orderings uniformly at random.
    For N>5:              uses N cyclic rotations (exact coverage for the first
                          N permutations) then adds random shuffles for the rest.

    Independent random shuffles (permute() called k times with different seeds)
    have no coverage guarantee: with bad luck the same tool could dominate
    position 0 across all k permutations. balanced_permutations avoids this.
    """
    n = len(surface.tools)
    if n == 0 or k <= 0:
        return []

    rng = random.Random(seed)

    if n <= 5:
        all_idx_perms = list(itertools.permutations(range(n)))
        if k >= len(all_idx_perms):
            # Complete enumeration — shuffle to avoid alphabetical-ordering bias.
            idx_list = list(all_idx_perms)
            rng.shuffle(idx_list)
        else:
            idx_list = rng.sample(all_idx_perms, k)
        return [
            Surface(server_name=surface.server_name,
                    tools=[surface.tools[i] for i in idx])
            for idx in idx_list
        ]

    # N > 5: cyclic rotations cover every tool at every position once,
    # then random shuffles fill the remainder.
    tools = list(surface.tools)
    result: list[Surface] = []

    for shift in range(min(n, k)):
        rotated = tools[shift:] + tools[:shift]
        result.append(Surface(server_name=surface.server_name, tools=rotated))

    for _ in range(k - len(result)):
        shuffled = list(tools)
        rng.shuffle(shuffled)
        result.append(Surface(server_name=surface.server_name, tools=shuffled))

    return result


# ---------------------------------------------------------------------------
# Paraphrase validation (C05 — metamorphic testing)
# ---------------------------------------------------------------------------

# Character-length ratio bounds for a valid paraphrase.
_MIN_LEN_RATIO = 0.40
_MAX_LEN_RATIO = 4.00


def _entities(text: str) -> frozenset[str]:
    """Extract key entities from text: mid-sentence title-case words (proper
    nouns), ALL-CAPS tokens (acronyms), and numeric values.

    Used as a proxy for the names and values that a paraphrase must preserve.
    Common sentence-starting capitalisation is excluded (index 0 in the token
    list).
    """
    tokens = re.findall(r'\S+', text)
    found: set[str] = set()
    for i, tok in enumerate(tokens):
        word = re.sub(r'[^\w]', '', tok)
        if not word:
            continue
        if word.isupper() and len(word) >= 2 or i > 0 and word[0].isupper() and not word.isupper():        # AAPL, SQL
            found.add(word.lower())
        elif re.match(r'\d', word):                   # 42, 3.14
            found.add(word)
    return frozenset(found)


def paraphrase_valid(original: str, candidate: str) -> tuple[bool, str]:
    """Check whether candidate is a valid paraphrase of original.

    Returns (valid, reason). valid=True means all constraints pass; reason is
    empty when valid and a human-readable failure message when not.

    Constraints (order: cheapest first):
    1. Not identical to original.
    2. Character-length ratio in [_MIN_LEN_RATIO, _MAX_LEN_RATIO].
    3. All key entities (proper nouns, acronyms, numbers) from original present
       in candidate.

    This is a necessary-but-not-sufficient filter. A model-generated paraphrase
    that passes these checks still requires a sampled human audit before use in
    a confirmatory experiment (EVAL_DESIGN §2, EXP-002).
    """
    if candidate.strip() == original.strip():
        return False, "identical to original"

    ratio = len(candidate) / max(len(original), 1)
    if ratio < _MIN_LEN_RATIO:
        return False, f"too short (length ratio {ratio:.2f} < {_MIN_LEN_RATIO})"
    if ratio > _MAX_LEN_RATIO:
        return False, f"too long (length ratio {ratio:.2f} > {_MAX_LEN_RATIO})"

    required = _entities(original)
    if required:
        present = _entities(candidate)
        missing = required - present
        if missing:
            return False, f"missing key entities: {sorted(missing)}"

    return True, ""


# ---------------------------------------------------------------------------
# Description edits (C03 — what influences selection; EXP-003)
# ---------------------------------------------------------------------------

# Catalogue of supported edit types. edit_id is stable across runs.
# Each entry: (edit_id, human description of the targeted smell / improvement).
EDIT_CATALOGUE: dict[str, str] = {
    "add_usage_clause":    "Append 'Use when: …' to clarify intended use cases.",
    "add_negation_clause": "Append 'Do not use for: …' to exclude common misuses.",
    "prepend_summary":     "Prepend a one-sentence summary before the existing text.",
    "set_description":     "Replace the entire description with a new one.",
    "trim_to_first_sentence": "Shorten to the first sentence only (no content arg).",
}


@dataclass(frozen=True)
class Edit:
    """A single targeted change to one tool's description.

    edit_id must be a key in EDIT_CATALOGUE. content is the text argument
    for edits that add or replace text; ignored for trim_to_first_sentence.
    edit_ids are stable: changing an edit means a new edit_id, not an update,
    so cassettes keyed on the rendered surface remain valid.
    """

    edit_id: str
    tool_name: str
    content: str = ""

    def __post_init__(self) -> None:
        if self.edit_id not in EDIT_CATALOGUE:
            raise ValueError(
                f"Unknown edit_id {self.edit_id!r}. "
                f"Valid ids: {sorted(EDIT_CATALOGUE)}"
            )


def _apply_action(edit_id: str, description: str, content: str) -> str:
    """Apply one edit action to a description string."""
    if edit_id == "add_usage_clause":
        suffix = f" Use when: {content}." if not content.endswith(".") else f" Use when: {content}"
        return description.rstrip() + suffix
    if edit_id == "add_negation_clause":
        suffix = f" Do not use for: {content}." if not content.endswith(".") else f" Do not use for: {content}"
        return description.rstrip() + suffix
    if edit_id == "prepend_summary":
        return f"{content.rstrip('.')}. {description}"
    if edit_id == "set_description":
        return content
    if edit_id == "trim_to_first_sentence":
        # Keep up to and including the first sentence-ending punctuation.
        m = re.search(r'[.!?]', description)
        return description[: m.end()].strip() if m else description
    raise ValueError(f"Unhandled edit_id: {edit_id!r}")  # unreachable after __post_init__


def apply_edit(surface: Surface, edit: Edit) -> Surface:
    """Apply one targeted description edit to a named tool. Pure.

    Raises ValueError if tool_name is not found in the surface.
    """
    found = False
    tools: list[Tool] = []
    for tool in surface.tools:
        if tool.name == edit.tool_name:
            found = True
            new_desc = _apply_action(edit.edit_id, tool.description, edit.content)
            tools.append(tool.model_copy(update={"description": new_desc}))
        else:
            tools.append(tool)
    if not found:
        raise ValueError(
            f"Tool {edit.tool_name!r} not found in surface {surface.server_name!r}. "
            f"Available: {[t.name for t in surface.tools]}"
        )
    return Surface(server_name=surface.server_name, tools=tools)
