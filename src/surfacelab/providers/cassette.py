"""Cassette store: record a live API call once, replay it forever.

The cache key is sha256(rendered_request_bytes). "Rendered request bytes" means
the exact bytes that would be sent to the model API — including the tools list
in the order the harness produced it. Tool order is therefore part of the key,
which is what makes cassettes usable as the storage layer for order-sweep
experiments: each permutation gets its own entry (ADR-005).

Storage layout: cassettes/{key[:2]}/{key}.json  (two-char prefix for filesystem
performance on directories with many files; otherwise some filesystems slow down
at 10k+ entries in one directory).

Mode "replay" (default): raises CassetteMissingError if no entry found.
Mode "record": makes the live call (via the callable you supply), stores it,
returns the response. Never falls through silently from replay to live.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal


class CassetteMissingError(Exception):
    """Raised when replay mode has no cassette for this request.

    Carry the key so the caller can tell the user exactly which cassette is
    missing and what --record command would create it.
    """
    def __init__(self, key: str, store_path: Path) -> None:
        self.key = key
        self.store_path = store_path
        super().__init__(
            f"No cassette for key {key[:12]}… in {store_path}\n"
            f"Record it first: surfacelab run --record"
        )


class CassetteStaleError(Exception):
    """Raised by doctor() when the stored key no longer matches the current render."""
    def __init__(self, stored_key: str, current_key: str) -> None:
        self.stored_key = stored_key
        self.current_key = current_key
        super().__init__(
            f"Cassette is stale: stored key {stored_key[:12]}… does not match "
            f"current render {current_key[:12]}…\n"
            f"Re-record with: surfacelab run --record"
        )


def _key(request_bytes: bytes) -> str:
    return hashlib.sha256(request_bytes).hexdigest()


class CassetteStore:
    """Read/write cassettes from a directory on disk."""

    def __init__(
        self,
        path: Path,
        mode: Literal["replay", "record"] = "replay",
    ) -> None:
        self.path = path
        self.mode = mode
        path.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, key: str) -> Path:
        # Two-char prefix bucket keeps each subdirectory small.
        bucket = self.path / key[:2]
        bucket.mkdir(exist_ok=True)
        return bucket / f"{key}.json"

    def has(self, request_bytes: bytes) -> bool:
        return self._entry_path(_key(request_bytes)).exists()

    def get(self, request_bytes: bytes) -> dict[str, Any]:
        """Return the stored response, or raise CassetteMissingError."""
        key = _key(request_bytes)
        entry_path = self._entry_path(key)
        if not entry_path.exists():
            raise CassetteMissingError(key, self.path)
        data: dict[str, Any] = json.loads(entry_path.read_text(encoding="utf-8"))
        return data["response"]

    def put(self, request_bytes: bytes, response: dict[str, Any]) -> None:
        """Store a response. Overwrites any existing entry for this key."""
        key = _key(request_bytes)
        try:
            request_stored: Any = json.loads(request_bytes)
        except json.JSONDecodeError:
            request_stored = request_bytes.decode("utf-8", errors="replace")

        entry: dict[str, Any] = {
            "key": key,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "request": request_stored,  # structured dict for real requests; string fallback
            "response": response,
        }
        self._entry_path(key).write_text(
            json.dumps(entry, indent=2), encoding="utf-8"
        )

    def doctor(self, request_bytes: bytes, stored_key: str) -> None:
        """Raise CassetteStaleError if the current render no longer matches the stored key.

        Call this at test time with the key you read from the cassette file to
        verify the surface hasn't changed since recording.
        """
        current = _key(request_bytes)
        if current != stored_key:
            raise CassetteStaleError(stored_key, current)

    def call(
        self,
        request_bytes: bytes,
        live_fn: Callable[[bytes], dict[str, Any]],
    ) -> dict[str, Any]:
        """Replay if cassette exists; record via live_fn if mode == 'record'.

        Never falls through to live_fn in replay mode — raises instead.
        This is the only call site for live model calls in the harness.
        """
        if self.has(request_bytes):
            return self.get(request_bytes)
        if self.mode == "replay":
            key = _key(request_bytes)
            raise CassetteMissingError(key, self.path)
        # record mode: call live, store, return
        response = live_fn(request_bytes)
        self.put(request_bytes, response)
        return response
