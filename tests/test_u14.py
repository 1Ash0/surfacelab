"""U14 — concurrent runner + key rotation.

Two-sided tests per CLAUDE.md rule 8: one that must fire, one that must not.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from unittest.mock import patch

from surfacelab.cases import Case
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider, _collect_keys
from surfacelab.runner import run_experiment
from surfacelab.schema import Surface, Tool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _surface(tools: list[tuple[str, str]]) -> Surface:
    return Surface(
        server_name="test",
        tools=[Tool(name=n, description=d) for n, d in tools],
    )


def _case(cid: str, gold: list[str] = ("get_weather",)) -> Case:
    return Case(
        id=cid,
        kind="positive",
        request="What is the weather?",
        gold=list(gold),
        surface_name="test",
        note="",
    )


SURFACE = _surface([("get_weather", "weather"), ("search_web", "search")])
CASES = [_case(f"c{i:03d}") for i in range(4)]


# ---------------------------------------------------------------------------
# _collect_keys
# ---------------------------------------------------------------------------


class TestCollectKeys:
    def test_numbered_primary_only(self) -> None:
        env = {k: v for k, v in os.environ.items() if not k.startswith("MY_KEY")}
        env["MY_KEY_1"] = "key-a"
        with patch.dict(os.environ, env, clear=True):
            keys = _collect_keys("MY_KEY")
        assert keys == ["key-a"]

    def test_numbered_keys_collected(self) -> None:
        env = {k: v for k, v in os.environ.items() if not k.startswith("MY_KEY")}
        env.update({"MY_KEY_1": "key-a", "MY_KEY_2": "key-b", "MY_KEY_3": "key-c"})
        with patch.dict(os.environ, env, clear=True):
            keys = _collect_keys("MY_KEY")
        assert keys == ["key-a", "key-b", "key-c"]

    def test_unnumbered_primary_backward_compat(self) -> None:
        env = {k: v for k, v in os.environ.items() if not k.startswith("MY_KEY")}
        env["MY_KEY"] = "key-legacy"
        with patch.dict(os.environ, env, clear=True):
            keys = _collect_keys("MY_KEY")
        assert "key-legacy" in keys

    def test_deduplicates_same_key_value(self) -> None:
        env = {k: v for k, v in os.environ.items() if not k.startswith("MY_KEY")}
        env.update({"MY_KEY_1": "same", "MY_KEY": "same"})
        with patch.dict(os.environ, env, clear=True):
            keys = _collect_keys("MY_KEY")
        assert keys.count("same") == 1

    def test_missing_all_returns_empty_string(self) -> None:
        env = {k: v for k, v in os.environ.items() if not k.startswith("MY_KEY")}
        with patch.dict(os.environ, env, clear=True):
            keys = _collect_keys("MY_KEY")
        assert keys == [""]

    def test_not_more_than_10_numbered(self) -> None:
        env = {k: v for k, v in os.environ.items() if not k.startswith("MY_KEY")}
        for i in range(1, 15):
            env[f"MY_KEY_{i}"] = f"k{i}"
        with patch.dict(os.environ, env, clear=True):
            keys = _collect_keys("MY_KEY")
        # _1 through _10 only; _11.._14 ignored
        assert len(keys) == 10


# ---------------------------------------------------------------------------
# Key rotation on OpenAICompatProvider
# ---------------------------------------------------------------------------


class TestKeyRotation:
    def _make_provider(self, cassette_dir: Path, extra_env: dict[str, str]) -> OpenAICompatProvider:
        store = CassetteStore(cassette_dir, mode="replay")
        with patch.dict(os.environ, extra_env, clear=False):
            return OpenAICompatProvider(
                provider_slug="groq",
                model_id="llama-3.1-8b-instant",
                cassette_store=store,
            )

    def test_single_key_always_returned(self, tmp_path: Path) -> None:
        provider = self._make_provider(tmp_path, {"GROQ_API_KEY_1": "key-a"})
        assert provider._next_key() == "key-a"
        assert provider._next_key() == "key-a"

    def test_two_keys_rotate(self, tmp_path: Path) -> None:
        env = {"GROQ_API_KEY_1": "key-a", "GROQ_API_KEY_2": "key-b"}
        provider = self._make_provider(tmp_path, env)
        seen = [provider._next_key() for _ in range(4)]
        assert seen == ["key-a", "key-b", "key-a", "key-b"]

    def test_rotation_is_thread_safe(self, tmp_path: Path) -> None:
        env = {"GROQ_API_KEY_1": "key-a", "GROQ_API_KEY_2": "key-b"}
        provider = self._make_provider(tmp_path, env)
        results: list[str] = []
        lock = threading.Lock()

        def grab() -> None:
            k = provider._next_key()
            with lock:
                results.append(k)

        threads = [threading.Thread(target=grab) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        assert set(results) == {"key-a", "key-b"}

    def test_rotation_stays_within_known_keys(self, tmp_path: Path) -> None:
        env = {"GROQ_API_KEY_1": "ka", "GROQ_API_KEY_2": "kb", "GROQ_API_KEY_3": "kc"}
        provider = self._make_provider(tmp_path, env)
        for _ in range(30):
            assert provider._next_key() in {"ka", "kb", "kc"}


# ---------------------------------------------------------------------------
# Concurrent runner
# ---------------------------------------------------------------------------


class TestConcurrentRunner:
    def _scripted_harness(self, answers: dict[str, str]):
        """Harness that returns a fixed answer per case_id."""
        call_log: list[tuple[str, int]] = []
        lock = threading.Lock()

        def harness(case: Case, surface: Surface) -> str:
            with lock:
                call_log.append((case.id, threading.get_ident()))
            return answers.get(case.id, "get_weather")

        harness.call_log = call_log  # type: ignore[attr-defined]
        return harness

    def test_workers_1_same_as_sequential(self) -> None:
        harness = self._scripted_harness({c.id: "get_weather" for c in CASES})
        variants = [SURFACE]
        t_seq, e_seq = run_experiment(CASES, variants, harness, workers=1)
        harness2 = self._scripted_harness({c.id: "get_weather" for c in CASES})
        t_par, e_par = run_experiment(CASES, variants, harness2, workers=4)
        assert len(t_seq) == len(t_par)
        assert len(e_seq) == len(e_par)
        assert [t.case_id for t in t_seq] == [t.case_id for t in t_par]

    def test_total_trial_count_unchanged_with_workers(self) -> None:
        harness = self._scripted_harness({c.id: "get_weather" for c in CASES})
        variants = [SURFACE, SURFACE]
        trials, _ = run_experiment(CASES, variants, harness, workers=4)
        assert len(trials) == len(CASES) * len(variants)

    def test_errors_recorded_not_raised(self) -> None:
        def bad_harness(case: Case, surface: Surface) -> str:
            raise RuntimeError("injected error")

        trials, errors = run_experiment(CASES[:2], [SURFACE], bad_harness, workers=2)
        assert len(errors) == 2
        assert all(t.correct is False for t in trials)
        assert all(t.error is not None for t in trials)

    def test_workers_do_not_produce_extra_trials(self) -> None:
        harness = self._scripted_harness({c.id: "get_weather" for c in CASES})
        variants = [SURFACE]
        trials, _ = run_experiment(CASES, variants, harness, workers=8)
        assert len(trials) == len(CASES)

    def test_correct_answer_recorded_in_parallel(self) -> None:
        harness = self._scripted_harness({c.id: "get_weather" for c in CASES})
        variants = [SURFACE]
        trials, errors = run_experiment(CASES, variants, harness, workers=4)
        assert errors == []
        assert all(t.correct for t in trials)


# ---------------------------------------------------------------------------
# Thread-safe CassetteStore
# ---------------------------------------------------------------------------


class TestCassetteThreadSafety:
    def test_concurrent_replay_no_error(self, tmp_path: Path) -> None:
        store = CassetteStore(tmp_path, mode="record")
        req = b"test-request"
        store.put(req, {"result": "ok"})

        store_r = CassetteStore(tmp_path, mode="replay")
        results: list[dict] = []
        lock = threading.Lock()

        def read() -> None:
            r = store_r.get(req)
            with lock:
                results.append(r)

        threads = [threading.Thread(target=read) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        assert all(r == {"result": "ok"} for r in results)

    def test_concurrent_record_no_duplicate_live_calls(self, tmp_path: Path) -> None:
        call_count = 0
        lock = threading.Lock()

        def live_fn(req_bytes: bytes) -> dict:
            nonlocal call_count
            with lock:
                call_count += 1
            return {"result": "live"}

        store = CassetteStore(tmp_path, mode="record")
        req = b"unique-request"

        threads = [
            threading.Thread(target=store.call, args=(req, live_fn))
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Per-key lock ensures exactly one live call for the same request.
        assert call_count == 1
