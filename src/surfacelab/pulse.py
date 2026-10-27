"""Pulse: sandboxed MCP handshake probe with drift detection.

Spawns a server process, runs initialize + tools/list under a wall-clock
timeout, and classifies the outcome. In v0.1, the sandbox is a plain
subprocess with a timeout (Docker sandboxing is a v0.2 extension — ADR-007).
Fixture servers are our own code, so the subprocess path is safe for them.

Outcome taxonomy (code has fixtures for each class):
  ok                 handshake completed; ≥1 tool returned
  no_tools           handshake completed; tool list was empty
  spawn_error        process failed to start (missing runtime, bad command)
  timeout            process started but didn't respond within wall-clock limit
  needs_credentials  process exited with auth-indicating text in stderr
  protocol_error     process returned non-JSON-RPC bytes or wrong message ids

instruction_like_flags checks each tool description for manipulation patterns.
It reports *possible* matches only — false-positive rate is measured in EXP-007.
The flag 'Use this tool when...' is NOT a match; only explicit manipulation
language (ignore other tools, you must always use this, etc.) fires.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

from .schema import Surface, Tool
from .snapshot import DriftEvent, Snapshot, SnapshotStore, classify_drift

# ---------------------------------------------------------------------------
# Outcome taxonomy
# ---------------------------------------------------------------------------


class ProbeOutcome(str, Enum):
    ok = "ok"
    no_tools = "no_tools"
    spawn_error = "spawn_error"
    timeout = "timeout"
    needs_credentials = "needs_credentials"
    protocol_error = "protocol_error"


@dataclass(frozen=True)
class ProbeResult:
    outcome: ProbeOutcome
    server_name: str
    surface: Surface | None
    """Set when outcome is ok or no_tools; None otherwise."""
    error_message: str | None
    instruction_like_flags: list[tuple[str, str]]
    """(tool_name, matched_pattern_id) for each suspicious description."""
    drift_events: list[DriftEvent] = field(
        default_factory=lambda: cast(list[DriftEvent], [])
    )
    """Drift relative to the last stored snapshot; empty if no prior snapshot."""


# ---------------------------------------------------------------------------
# instruction_like heuristics
# ---------------------------------------------------------------------------

_INSTRUCTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ignore\s+(?:all\s+)?other\s+tools", re.IGNORECASE), "ignore_other_tools"),
    (re.compile(r"always\s+use\s+this\s+(?:tool\s+)?instead", re.IGNORECASE), "always_use_instead"),
    (re.compile(r"you\s+must\s+(?:always\s+)?(?:use|call)\s+this", re.IGNORECASE), "must_use_directive"),
    (re.compile(r"do\s+not\s+use\s+(?:any\s+)?other", re.IGNORECASE), "do_not_use_other"),
    (re.compile(r"never\s+use\s+(?:other|any\s+other)", re.IGNORECASE), "never_use_other"),
    (re.compile(r"(?:^|\s)(\/[a-zA-Z_][a-zA-Z0-9_\/.\-]{2,})", re.MULTILINE), "file_path_reference"),
    (re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]"), "hidden_text_marker"),
]


def instruction_like_flags(surface: Surface) -> list[tuple[str, str]]:
    """Return (tool_name, pattern_id) for each tool with a suspicious description.

    Reports *possible* matches only. 'Use this tool when...' is benign and does
    NOT fire here. Only explicit manipulation language fires.
    """
    flags: list[tuple[str, str]] = []
    for tool in surface.tools:
        for pattern, pattern_id in _INSTRUCTION_PATTERNS:
            if pattern.search(tool.description):
                flags.append((tool.name, pattern_id))
                break  # one flag per tool per scan
    return flags


# ---------------------------------------------------------------------------
# MCP handshake (synchronous, with wall-clock timeout)
# ---------------------------------------------------------------------------

_PROTOCOL_VERSION = "2024-11-05"
_CRED_SIGNALS = re.compile(
    r"auth|token|credential|api.?key|secret|login|password|permission denied",
    re.IGNORECASE,
)


def _send(proc: subprocess.Popen[bytes], msg: dict[str, Any]) -> None:
    assert proc.stdin is not None
    line = (json.dumps(msg) + "\n").encode()
    proc.stdin.write(line)
    proc.stdin.flush()


def _recv(proc: subprocess.Popen[bytes], timeout: float) -> dict[str, Any]:
    """Read one JSON-RPC line from stdout with a timeout."""
    assert proc.stdout is not None
    import select as _select

    if sys.platform != "win32":
        ready, _, _ = _select.select([proc.stdout], [], [], timeout)
        if not ready:
            raise TimeoutError("no data on stdout")

    line = proc.stdout.readline()
    if not line:
        raise EOFError("stdout closed")
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Non-JSON response: {line!r}") from exc


def probe(
    command: list[str],
    server_name: str,
    timeout: float = 10.0,
    snapshot_store: SnapshotStore | None = None,
) -> ProbeResult:
    """Spawn server, run handshake, classify outcome, detect drift.

    On Windows, stdout line-reading blocks (no select); the timeout is applied
    via proc.wait() after stdin close, not during readline. This is safe for
    fixture servers that exit promptly but may not classify 'timeout' precisely
    on Windows for servers that hang.
    """
    surface: Surface | None = None

    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (FileNotFoundError, PermissionError, OSError) as exc:
        return ProbeResult(
            outcome=ProbeOutcome.spawn_error,
            server_name=server_name,
            surface=None,
            error_message=str(exc),
            instruction_like_flags=[],
        )

    try:
        # 1. initialize
        _send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "surfacelab", "version": "0.1"},
            },
        })
        _recv(proc, timeout)  # discard capabilities response

        # 2. initialized notification
        _send(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})

        # 3. tools/list
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        response = _recv(proc, timeout)

    except TimeoutError:
        proc.kill()
        _, stderr_bytes = proc.communicate()
        stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""
        outcome = (
            ProbeOutcome.needs_credentials
            if _CRED_SIGNALS.search(stderr)
            else ProbeOutcome.timeout
        )
        return ProbeResult(
            outcome=outcome,
            server_name=server_name,
            surface=None,
            error_message=f"Timeout after {timeout}s. stderr: {stderr[:200]}",
            instruction_like_flags=[],
        )
    except (ValueError, EOFError) as exc:
        proc.kill()
        proc.communicate()
        return ProbeResult(
            outcome=ProbeOutcome.protocol_error,
            server_name=server_name,
            surface=None,
            error_message=str(exc),
            instruction_like_flags=[],
        )
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.wait(timeout=2)
        except Exception:  # noqa: BLE001
            proc.kill()

    result_block: dict[str, Any] = response.get("result") or {}
    raw_tools: list[dict[str, Any]] = result_block.get("tools") or []
    tools = [Tool.model_validate(t) for t in raw_tools]
    surface = Surface(server_name=server_name, tools=tools)
    outcome = ProbeOutcome.ok if tools else ProbeOutcome.no_tools

    flags = instruction_like_flags(surface)

    # Snapshot and drift
    drift_events: list[DriftEvent] = []
    if snapshot_store is not None:
        snap = Snapshot.capture(surface)
        try:
            old = snapshot_store.load_latest(server_name)
            drift_events = classify_drift(old, snap)
        except (FileNotFoundError, KeyError):
            pass  # no prior snapshot — first run
        snapshot_store.save(snap)

    return ProbeResult(
        outcome=outcome,
        server_name=server_name,
        surface=surface,
        error_message=None,
        instruction_like_flags=flags,
        drift_events=drift_events,
    )
