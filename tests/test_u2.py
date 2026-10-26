"""U2 tests: cassette store and budget guard. All offline — no API calls."""

import json
import tempfile
from pathlib import Path

import pytest

from surfacelab.providers.cassette import (
    CassetteMissingError,
    CassetteStaleError,
    CassetteStore,
    _key,
)
from surfacelab.budget import BudgetExceededError, check, estimate


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def test_same_bytes_same_key():
    assert _key(b"hello") == _key(b"hello")


def test_different_bytes_different_key():
    # Tool order is in the bytes — different order → different key
    req_a = json.dumps({"tools": ["A", "B", "C"]}).encode()
    req_b = json.dumps({"tools": ["B", "A", "C"]}).encode()
    assert _key(req_a) != _key(req_b)


def test_key_is_64_hex_chars():
    assert len(_key(b"x")) == 64


# ---------------------------------------------------------------------------
# CassetteStore — replay mode
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path: Path) -> CassetteStore:
    return CassetteStore(tmp_path / "cassettes", mode="replay")


def test_has_returns_false_for_missing(store: CassetteStore) -> None:
    assert store.has(b"never recorded") is False


def test_get_raises_missing_error(store: CassetteStore) -> None:
    with pytest.raises(CassetteMissingError) as exc_info:
        store.get(b"never recorded")
    assert "Record it first" in str(exc_info.value)


def test_call_raises_missing_in_replay_mode(store: CassetteStore) -> None:
    with pytest.raises(CassetteMissingError):
        store.call(b"new request", live_fn=lambda _: {})


def test_put_then_get_round_trips(store: CassetteStore) -> None:
    req = b'{"model":"claude","messages":[{"role":"user","content":"hi"}]}'
    resp = {"content": [{"type": "text", "text": "hello"}]}
    store.put(req, resp)
    assert store.has(req)
    assert store.get(req) == resp


def test_different_request_bytes_get_separate_entries(store: CassetteStore) -> None:
    req_a = json.dumps({"tools": ["A", "B"]}).encode()
    req_b = json.dumps({"tools": ["B", "A"]}).encode()
    store.put(req_a, {"answer": "a_first"})
    store.put(req_b, {"answer": "b_first"})
    assert store.get(req_a) == {"answer": "a_first"}
    assert store.get(req_b) == {"answer": "b_first"}


# ---------------------------------------------------------------------------
# CassetteStore — record mode
# ---------------------------------------------------------------------------

def test_record_mode_calls_live_fn_and_stores() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        recorder = CassetteStore(Path(tmp) / "cassettes", mode="record")
        req = b"new request bytes"
        fake_response = {"content": [{"type": "text", "text": "recorded"}]}

        result = recorder.call(req, live_fn=lambda _: fake_response)
        assert result == fake_response
        assert recorder.has(req)


def test_record_mode_uses_cassette_on_second_call() -> None:
    """Live fn should only be called once even in record mode."""
    with tempfile.TemporaryDirectory() as tmp:
        recorder = CassetteStore(Path(tmp) / "cassettes", mode="record")
        req = b"a request"
        call_count = 0

        def live(b: bytes) -> dict:  # type: ignore[type-arg]
            nonlocal call_count
            call_count += 1
            return {"n": call_count}

        recorder.call(req, live_fn=live)
        recorder.call(req, live_fn=live)
        assert call_count == 1  # second call hit the cassette


# ---------------------------------------------------------------------------
# doctor — staleness detection
# ---------------------------------------------------------------------------

def test_doctor_passes_when_key_matches(store: CassetteStore) -> None:
    req = b"some bytes"
    key = _key(req)
    store.doctor(req, stored_key=key)  # must not raise


def test_doctor_raises_when_surface_changed(store: CassetteStore) -> None:
    req_old = b'{"tools": ["get_weather"], "description": "old desc"}'
    req_new = b'{"tools": ["get_weather"], "description": "new desc"}'
    stored = _key(req_old)
    with pytest.raises(CassetteStaleError) as exc_info:
        store.doctor(req_new, stored_key=stored)
    assert "stale" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Budget guard
# ---------------------------------------------------------------------------

def test_estimate_returns_positive_cost() -> None:
    est = estimate("claude-sonnet-4-6", input_tokens=1000, max_output_tokens=256)
    assert est.estimated_usd > 0


def test_check_passes_within_budget() -> None:
    est = estimate("claude-sonnet-4-6", input_tokens=100, max_output_tokens=64)
    check(est, max_usd=1.0)  # must not raise


def test_check_raises_when_over_budget() -> None:
    est = estimate("claude-sonnet-4-6", input_tokens=1_000_000, max_output_tokens=1024)
    with pytest.raises(BudgetExceededError) as exc_info:
        check(est, max_usd=0.001)
    assert "max-usd" in str(exc_info.value)


def test_zero_budget_refuses_all_live_calls() -> None:
    """max_usd=0.0 is the CI offline sentinel — must refuse even tiny calls."""
    est = estimate("claude-haiku-5-5", input_tokens=1, max_output_tokens=1)
    with pytest.raises(BudgetExceededError):
        check(est, max_usd=0.0)
