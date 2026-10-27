"""Embedding store: API calls with content-addressed cache and version pinning.

Cache key: sha256(model_id + "|" + text) stored as
  embeddings/<key[:2]>/<key>.json

Version pinning: the cached file stores the model_id used. On load, we verify
that the stored model_id matches the requested one. A mismatch raises
EmbedStalenessError — silently reusing vectors from a different model would
produce a similarity matrix of incompatible representations that looks valid
but isn't (two embeddings from different models live in different vector spaces
and their cosine similarities are meaningless).

umap_project is visualization-only. The projected coordinates go into
web/public/data/ for the Galaxy scene. Never use UMAP distances in stats.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from .schema import Surface
from .similarity import similarity_matrix

PROVIDER_EMBED_CONFIGS: dict[str, dict[str, str]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_var": "OPENROUTER_API_KEY",
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


class EmbedStalenessError(Exception):
    """Raised when a cached embedding was produced by a different model.

    Silently reusing a stale embedding would mix vectors from incompatible
    spaces, producing cosine similarities that look valid but are not.
    """


def _cache_key(model_id: str, text: str) -> str:
    payload = f"{model_id}|{text}".encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass
class EmbedStore:
    """Embedding store with content-addressed cache. One file per (model, text) pair."""

    provider_slug: str
    model_id: str
    cache_dir: Path

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, key: str) -> Path:
        bucket = self.cache_dir / key[:2]
        bucket.mkdir(exist_ok=True)
        return bucket / f"{key}.json"

    def _live_embed(self, text: str) -> list[float]:
        if self.provider_slug not in PROVIDER_EMBED_CONFIGS:
            raise ValueError(
                f"Unknown embedding provider {self.provider_slug!r}. "
                f"Known: {list(PROVIDER_EMBED_CONFIGS)}"
            )
        config = PROVIDER_EMBED_CONFIGS[self.provider_slug]
        api_key = os.environ.get(config["env_var"], "")
        client = OpenAI(base_url=config["base_url"], api_key=api_key)
        resp = client.embeddings.create(model=self.model_id, input=[text])
        return resp.data[0].embedding

    def embed(self, text: str) -> list[float]:
        """Return embedding for text. Uses cache if available; calls API otherwise."""
        key = _cache_key(self.model_id, text)
        entry_path = self._entry_path(key)

        if entry_path.exists():
            stored: dict[str, Any] = json.loads(
                entry_path.read_text(encoding="utf-8")
            )
            if stored.get("model_id") != self.model_id:
                raise EmbedStalenessError(
                    f"Cached embedding was produced by model {stored.get('model_id')!r} "
                    f"but {self.model_id!r} was requested. "
                    f"Delete {entry_path} to regenerate."
                )
            return list(stored["embedding"])

        vector = self._live_embed(text)
        entry: dict[str, Any] = {
            "model_id": self.model_id,
            "provider_slug": self.provider_slug,
            "text": text,
            "embedding": vector,
        }
        entry_path.write_text(json.dumps(entry), encoding="utf-8")
        return vector

    def embed_surface(self, surface: Surface) -> list[list[float]]:
        """Return embeddings for all tool descriptions, in surface.tools order."""
        return [self.embed(tool.description) for tool in surface.tools]

    def surface_similarity_matrix(self, surface: Surface) -> list[list[float]]:
        """Embed all tool descriptions and return the NxN cosine similarity matrix."""
        return similarity_matrix(self.embed_surface(surface))


def umap_project(
    embeddings: list[list[float]],
    n_components: int = 3,
    seed: int = 42,
) -> list[list[float]]:
    """Project embeddings to lower dimension via UMAP. Visualization only.

    UMAP distances are NOT semantic similarity. Two points close in the
    projection may have low cosine similarity; two distant points may be
    very similar. The UI must label this as 'projected position' not
    'similarity'. Never pass UMAP coordinates to stats functions.
    """
    try:
        import numpy as np  # type: ignore[import-untyped]
        import umap  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "umap_project requires umap-learn and numpy. "
            "Install with: uv add umap-learn numpy"
        ) from exc

    reducer = umap.UMAP(n_components=n_components, random_state=seed)  # type: ignore[misc]
    coords: Any = reducer.fit_transform(np.array(embeddings))  # type: ignore[misc]
    return [list(map(float, row)) for row in coords]  # type: ignore[misc]
