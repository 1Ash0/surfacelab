"""U11 tests: EmbedStore (caching, staleness) — no live API calls."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from surfacelab.embed import EmbedStalenessError, EmbedStore, _cache_key
from surfacelab.surface import load_fixture_surface

# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------


class TestCacheKey:
    def test_different_models_different_keys(self) -> None:
        k1 = _cache_key("text-embedding-3-small", "hello")
        k2 = _cache_key("text-embedding-ada-002", "hello")
        assert k1 != k2

    def test_same_model_same_text_same_key(self) -> None:
        k1 = _cache_key("model-x", "hello world")
        k2 = _cache_key("model-x", "hello world")
        assert k1 == k2

    def test_different_text_different_key(self) -> None:
        k1 = _cache_key("model-x", "foo")
        k2 = _cache_key("model-x", "bar")
        assert k1 != k2

    def test_key_is_hex_string(self) -> None:
        k = _cache_key("m", "t")
        assert all(c in "0123456789abcdef" for c in k)
        assert len(k) == 64


# ---------------------------------------------------------------------------
# EmbedStore (mocked live calls)
# ---------------------------------------------------------------------------


FAKE_VECTOR = [0.1, 0.2, 0.3]
FAKE_VECTOR_2 = [0.4, 0.5, 0.6]


class TestEmbedStore:
    def _store(self, tmp_path: Path, model: str = "emb-model-1") -> EmbedStore:
        return EmbedStore(
            provider_slug="gemini",
            model_id=model,
            cache_dir=tmp_path / "embeddings",
        )

    def test_embed_calls_live_on_miss(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        with patch.object(store, "_live_embed", return_value=FAKE_VECTOR) as mock_fn:
            result = store.embed("hello")
        mock_fn.assert_called_once_with("hello")
        assert result == FAKE_VECTOR

    def test_embed_uses_cache_on_hit(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        with patch.object(store, "_live_embed", return_value=FAKE_VECTOR):
            store.embed("hello")
        # Second call — live should NOT be called
        with patch.object(store, "_live_embed", return_value=FAKE_VECTOR_2) as mock_fn:
            result = store.embed("hello")
        mock_fn.assert_not_called()
        assert result == FAKE_VECTOR

    def test_different_text_different_cache_slot(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        with patch.object(store, "_live_embed", side_effect=[FAKE_VECTOR, FAKE_VECTOR_2]):
            v1 = store.embed("foo")
            v2 = store.embed("bar")
        assert v1 == FAKE_VECTOR
        assert v2 == FAKE_VECTOR_2

    def test_different_model_regenerates(self, tmp_path: Path) -> None:
        """Changing model_id must produce a different cache key → new file."""
        store_a = self._store(tmp_path, model="model-a")
        store_b = self._store(tmp_path, model="model-b")
        with patch.object(store_a, "_live_embed", return_value=FAKE_VECTOR):
            store_a.embed("hello")
        with patch.object(store_b, "_live_embed", return_value=FAKE_VECTOR_2) as mock_fn:
            result = store_b.embed("hello")
        mock_fn.assert_called_once()
        assert result == FAKE_VECTOR_2

    def test_stale_model_id_raises(self, tmp_path: Path) -> None:
        """If cache file was written by a different model, raise EmbedStalenessError."""
        store = self._store(tmp_path, model="model-a")
        key = _cache_key("model-a", "hello")
        bucket = (tmp_path / "embeddings") / key[:2]
        bucket.mkdir(parents=True, exist_ok=True)
        entry_path = bucket / f"{key}.json"
        # Write cache file claiming a different model
        entry_path.write_text(
            json.dumps({"model_id": "model-DIFFERENT", "text": "hello", "embedding": FAKE_VECTOR}),
            encoding="utf-8",
        )
        with pytest.raises(EmbedStalenessError, match="model-DIFFERENT"):
            store.embed("hello")

    def test_embed_surface_returns_one_vector_per_tool(self, tmp_path: Path) -> None:
        surface = load_fixture_surface("goodserver")
        store = self._store(tmp_path)
        vectors = [[float(i)] * 3 for i in range(surface.tool_count)]
        with patch.object(store, "_live_embed", side_effect=vectors):
            result = store.embed_surface(surface)
        assert len(result) == surface.tool_count

    def test_embed_surface_order_matches_tools(self, tmp_path: Path) -> None:
        """embed_surface must return vectors in the same order as surface.tools."""
        surface = load_fixture_surface("goodserver")
        store = self._store(tmp_path)
        vectors = [[float(i)] * 3 for i in range(surface.tool_count)]
        with patch.object(store, "_live_embed", side_effect=vectors):
            result = store.embed_surface(surface)
        # Each vector corresponds to the tool at the same index
        for i, vec in enumerate(result):
            assert vec == [float(i)] * 3
