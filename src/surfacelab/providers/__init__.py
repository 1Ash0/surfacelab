"""Provider protocol — the boundary between the runner and the model API.

A Provider knows how to take a Case and a Surface and return the tool name
the model emitted (or None for abstain). The runner knows nothing about how
that answer is obtained — live API call, cassette replay, or scripted fake.
"""

from __future__ import annotations

from typing import Protocol

from ..cases import Case
from ..schema import Surface


class Provider(Protocol):
    def call(self, case: Case, surface: Surface) -> str | None:
        """Return the emitted tool name, or None for abstain."""
        ...
