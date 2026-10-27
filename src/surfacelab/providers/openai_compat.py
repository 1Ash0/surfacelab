"""OpenAI-compatible provider: live API calls via any free-tier endpoint.

All supported providers (OpenRouter, Groq, Gemini, NVIDIA, Mistral) expose
an OpenAI-compatible API.  We use the openai package with a custom base_url
and api_key drawn from environment variables (ADR-021).

Cassette key: sha256(f"{provider_slug}|{model_id}|{serialized_request}")
The provider_slug + model_id prefix prevents entries from different providers
or models from colliding (two models can return different outputs for the same
prompt; mixing them would corrupt replay).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from ..cases import Case
from ..render import render
from ..schema import Surface
from .cassette import CassetteStore

# ---------------------------------------------------------------------------
# Provider registry (free-tier endpoints)
# ---------------------------------------------------------------------------

PROVIDER_CONFIGS: dict[str, dict[str, str]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_var": "OPENROUTER_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_var": "GROQ_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_var": "GEMINI_API_KEY",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_var": "NVIDIA_API_KEY",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "env_var": "MISTRAL_API_KEY",
    },
}


class ProviderContractError(Exception):
    """Raised when the API response violates the tool_choice contract.

    tool_choice='required' guarantees at least one tool call. An empty
    tool_calls list is a contract violation, not a legitimate abstention.
    Returning None here would conflate a broken response with a genuine
    abstain, silently corrupting the accuracy denominator.
    """


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


@dataclass
class OpenAICompatProvider:
    """Live model calls via any OpenAI-compatible endpoint, backed by cassettes."""

    provider_slug: str
    """Registry key in PROVIDER_CONFIGS (e.g. 'openrouter', 'groq')."""

    model_id: str
    """Exact model identifier pinned per experiment (e.g. 'meta-llama/llama-3-8b-instruct:free')."""

    cassette_store: CassetteStore
    """Replay or record mode. Never falls through silently in replay mode."""

    tool_choice: str = "required"
    """'required' forces ≥1 tool call. 'auto' allows abstain (use for abstain cases)."""

    def _build_request(self, case: Case, surface: Surface) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "messages": [{"role": "user", "content": case.request}],
            "tools": render(surface),
            "tool_choice": self.tool_choice,
        }

    def _request_bytes(self, request: dict[str, Any]) -> bytes:
        # Include provider_slug and model_id in the key so cassette entries
        # from different providers or models never share a slot.
        # The CassetteStore sha256s these bytes for the file key — no need to
        # pre-hash here; just keep the bytes valid UTF-8.
        prefix = f"{self.provider_slug}|{self.model_id}|"
        body = json.dumps(request, sort_keys=True, separators=(",", ":"))
        return (prefix + body).encode()

    def _make_live_call(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.provider_slug not in PROVIDER_CONFIGS:
            raise ValueError(
                f"Unknown provider {self.provider_slug!r}. "
                f"Known: {list(PROVIDER_CONFIGS)}"
            )
        config = PROVIDER_CONFIGS[self.provider_slug]
        api_key = os.environ.get(config["env_var"], "")
        client = OpenAI(base_url=config["base_url"], api_key=api_key)
        from typing import cast as _cast
        resp = client.chat.completions.create(**request)  # type: ignore[arg-type]
        return _cast(dict[str, Any], resp.model_dump())  # type: ignore[no-untyped-call]

    def call(self, case: Case, surface: Surface) -> str | None:
        request = self._build_request(case, surface)
        req_bytes = self._request_bytes(request)

        def live_fn(_bytes: bytes) -> dict[str, Any]:
            return self._make_live_call(request)

        raw: dict[str, Any] = self.cassette_store.call(req_bytes, live_fn)

        choices: list[dict[str, Any]] = raw.get("choices") or []
        if not choices:
            raise ProviderContractError(
                f"Response had no choices (model={self.model_id}, case={case.id})"
            )

        message: dict[str, Any] = choices[0].get("message") or {}
        tool_calls: list[dict[str, Any]] = message.get("tool_calls") or []
        if not tool_calls:
            if self.tool_choice == "required":
                raise ProviderContractError(
                    f"tool_choice='required' but response had no tool_calls "
                    f"(model={self.model_id}, case={case.id})"
                )
            return None  # legitimate abstain — only when tool_choice='auto'

        fn: dict[str, Any] = tool_calls[0].get("function") or {}
        return str(fn.get("name", ""))
