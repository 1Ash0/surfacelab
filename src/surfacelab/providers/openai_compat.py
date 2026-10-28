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
import random
import os
import re
import time
import threading
from dataclasses import dataclass, field
from typing import Any

import openai
from openai import OpenAI

from ..cases import Case, CaseKind
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


@dataclass
class _KeyState:
    key: str
    cooldown_until: float = 0.0  # time.monotonic() deadline; 0 = available


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


def _collect_keys(env_var: str) -> list[str]:
    """Collect all API keys for a provider from environment variables.

    Accepts two naming conventions (whichever is present wins):
      GROQ_API_KEY_1, GROQ_API_KEY_2, ... GROQ_API_KEY_10  (1-indexed)
      GROQ_API_KEY, GROQ_API_KEY_2, ... GROQ_API_KEY_10    (legacy: unnumbered primary)

    Both are checked; duplicates are dropped. Returns at least one entry
    (may be empty string if no key is found at all).
    """
    seen: set[str] = set()
    keys: list[str] = []

    def _add(k: str) -> None:
        if k and k not in seen:
            seen.add(k)
            keys.append(k)

    # Allow skipping exhausted orgs: set {env_var}_START=N to begin at key N.
    start = int(os.environ.get(f"{env_var}_START", "1"))
    # 1-indexed: GROQ_API_KEY_1 … GROQ_API_KEY_20
    for i in range(start, 21):
        _add(os.environ.get(f"{env_var}_{i}", ""))

    # Unnumbered primary (backward-compat): GROQ_API_KEY
    _add(os.environ.get(env_var, ""))

    return keys or [""]


@dataclass
class OpenAICompatProvider:
    """Live model calls via any OpenAI-compatible endpoint, backed by cassettes.

    Supports round-robin key rotation across multiple API keys.
    Set GROQ_API_KEY_1 … GROQ_API_KEY_20 to enable rotation.
    """

    provider_slug: str
    """Registry key in PROVIDER_CONFIGS (e.g. 'openrouter', 'groq')."""

    model_id: str
    """Exact model identifier pinned per experiment (e.g. 'llama-3.1-8b-instant')."""

    cassette_store: CassetteStore
    """Replay or record mode. Never falls through silently in replay mode."""

    tool_choice: str = "required"
    """'required' forces ≥1 tool call. 'auto' allows abstain (use for abstain cases)."""

    # Set in __post_init__ — not part of the public API.
    _key_states: list[_KeyState] = field(default_factory=list, init=False, repr=False)
    _key_index: int = field(default=0, init=False, repr=False)
    _key_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _throttle_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _last_call_time: float = field(default=0.0, init=False, repr=False)
    _min_call_interval: float = field(default=1.5, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.provider_slug not in PROVIDER_CONFIGS:
            raise ValueError(
                f"Unknown provider {self.provider_slug!r}. "
                f"Known: {list(PROVIDER_CONFIGS)}"
            )
        env_var = PROVIDER_CONFIGS[self.provider_slug]["env_var"]
        self._key_states = [_KeyState(key=k) for k in _collect_keys(env_var)]

    def _next_key(self) -> str:
        """Round-robin without cooldown check. Used in tests."""
        with self._key_lock:
            idx = self._key_index % len(self._key_states)
            self._key_index += 1
            return self._key_states[idx].key

    _MAX_COOLDOWN: float = 30.0  # cap per-key sleep to avoid multi-minute stalls

    def _next_available_key(self) -> tuple[str, int]:
        """Return (key, index) skipping cooling keys; sleeps only when all orgs saturated."""
        n = len(self._key_states)
        while True:
            sleep_until = 0.0
            with self._key_lock:
                now = time.monotonic()
                for _ in range(n):
                    idx = self._key_index % n
                    self._key_index += 1
                    state = self._key_states[idx]
                    if now >= state.cooldown_until:
                        return state.key, idx
                # Every key cooling — sleep until the earliest wakes up
                sleep_until = min(s.cooldown_until for s in self._key_states) + 0.05
            remaining = sleep_until - time.monotonic()
            if remaining > 0:
                import sys
                jitter = random.uniform(0.0, 2.0)
                total = remaining + jitter
                print(f"  [rate-limit] all keys cooling, sleeping {total:.1f}s", file=sys.stderr, flush=True)
                time.sleep(total)

    def _throttle(self) -> None:
        """Enforce a minimum gap between API calls across all workers combined.

        The lock is held only for the instant check-and-claim; sleeping happens
        outside so other workers are not blocked while one sleeps.
        At 1.5 s gap: 40 req/min total → org-A (6/14 keys = 43%) = 17 req/min
        × 370 tokens ≈ 6300 TPM, safely under Groq's 8000 TPM/org free-tier.
        """
        while True:
            with self._throttle_lock:
                now = time.monotonic()
                next_allowed = self._last_call_time + self._min_call_interval
                if now >= next_allowed:
                    self._last_call_time = now  # claim this slot
                    return
                wait = next_allowed - now
            time.sleep(wait)  # sleep OUTSIDE lock so other workers can check

    def _mark_cooldown(self, key_idx: int, retry_after: float) -> None:
        capped = min(retry_after, self._MAX_COOLDOWN)
        with self._key_lock:
            self._key_states[key_idx].cooldown_until = time.monotonic() + capped

    def _tool_choice_for(self, case: Case) -> str:
        # 'required' makes abstaining impossible (Groq returns 400 tool_use_failed).
        return "auto" if case.kind == CaseKind.abstain else self.tool_choice

    def _build_request(self, case: Case, surface: Surface) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "messages": [{"role": "user", "content": case.request}],
            "tools": render(surface),
            "tool_choice": self._tool_choice_for(case),
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
        """Call the API with per-key cooldown tracking.

        On 429, the offending key is cooled individually. _next_available_key
        immediately returns a key from a different org if one is free, so cross-org
        failover costs zero sleep time. Sleep only happens when every key in every
        org is cooling simultaneously.
        """
        config = PROVIDER_CONFIGS[self.provider_slug]
        max_attempts = len(self._key_states) * 8
        for attempt in range(max_attempts):
            api_key, key_idx = self._next_available_key()
            # SDK default timeout is 600s; one hung request would stall a worker for 10 min.
            client = OpenAI(base_url=config["base_url"], api_key=api_key, timeout=60.0)
            try:
                self._throttle()
                from typing import cast as _cast
                resp = client.chat.completions.create(**request)  # type: ignore[arg-type]
                return _cast(dict[str, Any], resp.model_dump())  # type: ignore[no-untyped-call]
            except openai.BadRequestError as exc:
                body: Any = exc.body if isinstance(exc.body, dict) else {}
                err: dict[str, Any] = body.get("error", body) if isinstance(body.get("error", body), dict) else {}
                if err.get("code") != "tool_use_failed":
                    raise
                # The model's own output (a refusal or malformed call) is a real
                # outcome; record it instead of retrying until it complies.
                return {
                    "choices": [{"message": {"content": err.get("failed_generation"), "tool_calls": []}}],
                    "surfacelab_tool_use_failed": err,
                }
            except openai.RateLimitError as exc:
                m = re.search(r"try again in ([0-9.]+)s", str(exc))
                retry_after = float(m.group(1)) + 0.5 if m else 5.0
                self._mark_cooldown(key_idx, retry_after)
                if attempt == max_attempts - 1:
                    raise
        raise RuntimeError("unreachable")

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

        if raw.get("surfacelab_tool_use_failed"):
            return None  # graded like any no-tool answer

        message: dict[str, Any] = choices[0].get("message") or {}
        tool_calls: list[dict[str, Any]] = message.get("tool_calls") or []
        if not tool_calls:
            if request["tool_choice"] == "required":
                raise ProviderContractError(
                    f"tool_choice='required' but response had no tool_calls "
                    f"(model={self.model_id}, case={case.id})"
                )
            return None  # legitimate abstain — only when tool_choice='auto'

        fn: dict[str, Any] = tool_calls[0].get("function") or {}
        return str(fn.get("name", ""))
