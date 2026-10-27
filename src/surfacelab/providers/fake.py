"""FakeProvider: scripted responses for offline tests.

Maps (case_id, surface_hash) -> tool_name. Raises FakeProviderError for any
pair not in the map so a misconfigured test fails loudly rather than silently
returning None and masquerading as a legitimate abstention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from ..cases import Case
from ..schema import Surface
from ..snapshot import surface_hash as _surface_hash


class FakeProviderError(Exception):
    """Raised when the fake has no scripted response for a (case, surface) pair."""


@dataclass
class FakeProvider:
    """Returns pre-scripted tool names. No network, no disk, no bytes."""

    responses: dict[tuple[str, str], str | None] = field(
        default_factory=lambda: cast("dict[tuple[str, str], str | None]", {})
    )
    """Map of (case_id, surface_hash) → tool_name (or None for scripted abstain)."""

    def call(self, case: Case, surface: Surface) -> str | None:
        key = (case.id, _surface_hash(surface))
        if key not in self.responses:
            h = _surface_hash(surface)
            raise FakeProviderError(
                f"No scripted response for case {case.id!r} "
                f"on surface {h[:12]}… — add it to FakeProvider.responses"
            )
        return self.responses[key]
