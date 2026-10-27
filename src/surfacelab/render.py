"""Render a Surface into the form the model receives, and measure the cost.

Two functions:
  render(surface)       -> list[dict] ready for anthropic client tools= param
  token_ledger(surface) -> per-tool and total token counts, broken down by field

The rendered form is stored verbatim in cassettes so replay sees the exact
bytes the model saw (ADR-005). Never post-process or reorder the fields here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import tiktoken

from .schema import Surface

# o200k_base is the tokenizer Claude uses (same family as GPT-4o).
# Using it here gives us approximate but consistent counts for comparisons.
# The Anthropic API's exact count can differ by a few tokens due to special
# tokens around the tools block; use client.beta.messages.count_tokens for
# the authoritative number when you have an API key.
_ENC = tiktoken.get_encoding("o200k_base")


def _count(text: str) -> int:
    return len(_ENC.encode(text))


def render(surface: Surface) -> list[dict[str, Any]]:
    """Return a tools list in OpenAI function-calling format.

    Shape: [{"type": "function", "function": {"name", "description", "parameters"}}]
    Compatible with all providers via ADR-021 (Groq, OpenRouter, Gemini, etc.).
    The rendered bytes are part of the cassette key (ADR-005).
    """
    out: list[dict[str, Any]] = []
    for tool in surface.tools:
        out.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        })
    return out


@dataclass
class ToolTokens:
    name: str
    name_tokens: int
    description_tokens: int
    schema_tokens: int

    @property
    def total(self) -> int:
        return self.name_tokens + self.description_tokens + self.schema_tokens


@dataclass
class TokenLedger:
    server_name: str
    rows: list[ToolTokens]

    @property
    def total(self) -> int:
        return sum(r.total for r in self.rows)

    @property
    def name_total(self) -> int:
        return sum(r.name_tokens for r in self.rows)

    @property
    def description_total(self) -> int:
        return sum(r.description_tokens for r in self.rows)

    @property
    def schema_total(self) -> int:
        return sum(r.schema_tokens for r in self.rows)

    def __str__(self) -> str:
        lines = [
            f"Surface: {self.server_name} ({len(self.rows)} tools, {self.total} tokens)\n",
            f"{'tool':<30} {'name':>5} {'desc':>6} {'schema':>7} {'total':>6}",
            "-" * 58,
        ]
        for r in self.rows:
            lines.append(
                f"{r.name:<30} {r.name_tokens:>5} {r.description_tokens:>6}"
                f" {r.schema_tokens:>7} {r.total:>6}"
            )
        lines.append("-" * 58)
        lines.append(
            f"{'TOTAL':<30} {self.name_total:>5} {self.description_total:>6}"
            f" {self.schema_total:>7} {self.total:>6}"
        )
        return "\n".join(lines)


def token_ledger(surface: Surface) -> TokenLedger:
    """Count tokens per field for every tool in the surface."""
    rows: list[ToolTokens] = []
    for tool in surface.tools:
        rows.append(ToolTokens(
            name=tool.name,
            name_tokens=_count(tool.name),
            description_tokens=_count(tool.description),
            schema_tokens=_count(json.dumps(tool.input_schema)),
        ))
    return TokenLedger(server_name=surface.server_name, rows=rows)
