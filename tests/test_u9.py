"""U9 tests: Provider protocol, FakeProvider, OpenAICompatProvider (offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from surfacelab.cases import Case, CaseKind
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.fake import FakeProvider, FakeProviderError
from surfacelab.providers.openai_compat import (
    OpenAICompatProvider,
    ProviderContractError,
)
from surfacelab.schema import Surface, Tool
from surfacelab.snapshot import surface_hash

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _surface(tools: list[tuple[str, str]]) -> Surface:
    return Surface(
        server_name="test",
        tools=[Tool(name=n, description=d) for n, d in tools],
    )


def _case(case_id: str = "c1", gold: frozenset[str] | None = None) -> Case:
    return Case(
        id=case_id,
        kind=CaseKind.positive,
        request="Find the weather in Paris.",
        gold=gold or frozenset(["get_weather"]),
        surface_name="test",
    )


# ---------------------------------------------------------------------------
# FakeProvider
# ---------------------------------------------------------------------------

class TestFakeProvider:
    def test_returns_scripted_tool(self) -> None:
        surface = _surface([("get_weather", "Get weather")])
        case = _case()
        fp = FakeProvider({(case.id, surface_hash(surface)): "get_weather"})
        assert fp.call(case, surface) == "get_weather"

    def test_scripted_abstain(self) -> None:
        surface = _surface([("get_weather", "Get weather")])
        case = _case()
        fp = FakeProvider({(case.id, surface_hash(surface)): None})
        assert fp.call(case, surface) is None

    def test_raises_on_missing_key(self) -> None:
        surface = _surface([("get_weather", "Get weather")])
        case = _case()
        fp = FakeProvider({})
        with pytest.raises(FakeProviderError, match="No scripted response"):
            fp.call(case, surface)

    def test_key_uses_surface_hash(self) -> None:
        """Same case, different surface order → different keys."""
        surface_a = _surface([("x", "X"), ("y", "Y")])
        surface_b = _surface([("y", "Y"), ("x", "X")])
        case = _case()
        fp = FakeProvider({
            (case.id, surface_hash(surface_a)): "x",
            (case.id, surface_hash(surface_b)): "y",
        })
        assert fp.call(case, surface_a) == "x"
        assert fp.call(case, surface_b) == "y"

    def test_different_surfaces_different_keys(self) -> None:
        """surface_a and surface_b must have different hashes."""
        surface_a = _surface([("x", "X"), ("y", "Y")])
        surface_b = _surface([("y", "Y"), ("x", "X")])
        assert surface_hash(surface_a) != surface_hash(surface_b)

    def test_empty_responses_raises(self) -> None:
        surface = _surface([("get_weather", "Get weather")])
        case = _case("c99")
        fp = FakeProvider({})
        with pytest.raises(FakeProviderError):
            fp.call(case, surface)

    def test_error_message_contains_case_id(self) -> None:
        surface = _surface([("get_weather", "Get weather")])
        case = _case("my-case-id")
        fp = FakeProvider({})
        with pytest.raises(FakeProviderError, match="my-case-id"):
            fp.call(case, surface)


# ---------------------------------------------------------------------------
# OpenAICompatProvider (offline: replay from manually written cassette)
# ---------------------------------------------------------------------------

_FAKE_RESPONSE = {
    "choices": [{
        "message": {
            "role": "assistant",
            "tool_calls": [{"function": {"name": "get_weather"}, "id": "call_1", "type": "function"}],
        },
        "finish_reason": "tool_calls",
    }]
}

_FAKE_RESPONSE_NO_TOOLS = {
    "choices": [{"message": {"role": "assistant", "content": "I don't know."}, "finish_reason": "stop"}]
}

_FAKE_RESPONSE_EMPTY_CHOICES: dict = {"choices": []}


class TestOpenAICompatProvider:
    def _make_provider(self, tmp_path: Path, tool_choice: str = "required") -> tuple[OpenAICompatProvider, CassetteStore]:
        store = CassetteStore(tmp_path / "cassettes", mode="replay")
        prov = OpenAICompatProvider(
            provider_slug="openrouter",
            model_id="meta-llama/llama-3-8b-instruct:free",
            cassette_store=store,
            tool_choice=tool_choice,
        )
        return prov, store

    def _seed_cassette(self, store: CassetteStore, prov: OpenAICompatProvider, case: Case, surface: Surface, response: dict) -> None:
        req = prov._build_request(case, surface)
        req_bytes = prov._request_bytes(req)
        store.put(req_bytes, response)

    def test_replay_returns_tool_name(self, tmp_path: Path) -> None:
        surface = _surface([("get_weather", "Get weather"), ("search_web", "Search")])
        case = _case()
        prov, store = self._make_provider(tmp_path)
        self._seed_cassette(store, prov, case, surface, _FAKE_RESPONSE)
        assert prov.call(case, surface) == "get_weather"

    def test_cassette_key_differs_by_tool_order(self, tmp_path: Path) -> None:
        """Two surfaces with swapped tool order must get different cassette slots."""
        surface_a = _surface([("get_weather", "Get weather"), ("search_web", "Search")])
        surface_b = _surface([("search_web", "Search"), ("get_weather", "Get weather")])
        case = _case()
        prov, store = self._make_provider(tmp_path)
        self._seed_cassette(store, prov, case, surface_a, _FAKE_RESPONSE)

        req_a = prov._build_request(case, surface_a)
        req_b = prov._build_request(case, surface_b)
        assert prov._request_bytes(req_a) != prov._request_bytes(req_b)

    def test_missing_cassette_raises(self, tmp_path: Path) -> None:
        from surfacelab.providers.cassette import CassetteMissingError
        surface = _surface([("get_weather", "Get weather")])
        case = _case()
        prov, _ = self._make_provider(tmp_path)
        with pytest.raises(CassetteMissingError):
            prov.call(case, surface)

    def test_required_with_no_tool_calls_raises_contract_error(self, tmp_path: Path) -> None:
        surface = _surface([("get_weather", "Get weather")])
        case = _case()
        prov, store = self._make_provider(tmp_path, tool_choice="required")
        self._seed_cassette(store, prov, case, surface, _FAKE_RESPONSE_NO_TOOLS)
        with pytest.raises(ProviderContractError, match="required"):
            prov.call(case, surface)

    def test_auto_with_no_tool_calls_returns_none(self, tmp_path: Path) -> None:
        surface = _surface([("get_weather", "Get weather")])
        case = _case()
        prov, store = self._make_provider(tmp_path, tool_choice="auto")
        self._seed_cassette(store, prov, case, surface, _FAKE_RESPONSE_NO_TOOLS)
        assert prov.call(case, surface) is None

    def test_empty_choices_raises(self, tmp_path: Path) -> None:
        surface = _surface([("get_weather", "Get weather")])
        case = _case()
        prov, store = self._make_provider(tmp_path)
        self._seed_cassette(store, prov, case, surface, _FAKE_RESPONSE_EMPTY_CHOICES)
        with pytest.raises(ProviderContractError, match="no choices"):
            prov.call(case, surface)

    def test_provider_slug_in_request_bytes(self, tmp_path: Path) -> None:
        """Different provider slugs must produce different cassette keys."""
        surface = _surface([("get_weather", "Get weather")])
        case = _case()
        store = CassetteStore(tmp_path / "cassettes", mode="replay")
        prov_or = OpenAICompatProvider("openrouter", "m1", store)
        prov_gr = OpenAICompatProvider("groq", "m1", store)
        req = prov_or._build_request(case, surface)
        assert prov_or._request_bytes(req) != prov_gr._request_bytes(req)
