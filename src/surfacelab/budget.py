"""Budget guard: refuse live calls that exceed the --max-usd limit.

Token prices are approximate and model-specific. The guard is intentionally
conservative (it uses the input-token price for a rough total estimate) — the
goal is to prevent accidental runaway spending, not to predict the exact bill.

For an authoritative estimate before spending, use the Anthropic
client.beta.messages.count_tokens endpoint in dry-run mode.
"""

from __future__ import annotations

from dataclasses import dataclass


# Approximate prices per million tokens (input / output) as of 2026-10.
# These are illustrative; update when pricing changes, and pin model ids
# per experiment (ADR-011).
_PRICES: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6":     (3.00,  15.00),
    "claude-opus-5-5":       (15.00, 75.00),
    "claude-haiku-5-5":      (0.80,   4.00),
}
_FALLBACK_PRICE = (3.00, 15.00)  # use sonnet pricing when model unknown


class BudgetExceededError(Exception):
    """Raised before a live call when the estimated cost exceeds max_usd."""
    def __init__(self, estimated: float, max_usd: float) -> None:
        self.estimated = estimated
        self.max_usd = max_usd
        super().__init__(
            f"Estimated cost ${estimated:.4f} exceeds --max-usd ${max_usd:.4f}. "
            f"Pass a higher --max-usd or use --dry-run to inspect the estimate."
        )


@dataclass
class CostEstimate:
    model: str
    input_tokens: int
    max_output_tokens: int
    estimated_usd: float

    def __str__(self) -> str:
        return (
            f"model={self.model}  "
            f"input={self.input_tokens} tok  "
            f"max_output={self.max_output_tokens} tok  "
            f"estimated=${self.estimated_usd:.4f}"
        )


def estimate(
    model: str,
    input_tokens: int,
    max_output_tokens: int = 1024,
) -> CostEstimate:
    """Return a cost estimate without making any API call."""
    price_in, price_out = _PRICES.get(model, _FALLBACK_PRICE)
    cost = (input_tokens * price_in + max_output_tokens * price_out) / 1_000_000
    return CostEstimate(
        model=model,
        input_tokens=input_tokens,
        max_output_tokens=max_output_tokens,
        estimated_usd=cost,
    )


def check(est: CostEstimate, max_usd: float) -> None:
    """Raise BudgetExceededError if estimated cost exceeds max_usd.

    Call this before every live model call. With max_usd=0.0 (the CI default)
    all live calls are refused, enforcing offline-only mode.
    """
    if est.estimated_usd > max_usd:
        raise BudgetExceededError(est.estimated_usd, max_usd)
