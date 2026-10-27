"""Minimal MCP client: spawns a stdio server and collects its surface.

Only implements initialize + tools/list (the read-only handshake).
tools/call is never used in v0.1 (ADR-008).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from .schema import Surface, Tool

_PROTOCOL_VERSION = "2024-11-05"


async def fetch_surface(command: list[str], server_name: str) -> Surface:
    """Spawn *command* as an MCP stdio server and return its Surface.

    Sends initialize → initialized → tools/list, then closes stdin so the
    server exits cleanly. The process is waited on before returning so no
    zombie processes are left behind.
    """
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,  # silence server-side log noise
    )

    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("subprocess missing stdio streams")

    stdin = proc.stdin
    stdout = proc.stdout

    async def send(msg: dict[str, Any]) -> None:
        line = json.dumps(msg) + "\n"
        stdin.write(line.encode())
        await stdin.drain()

    async def recv() -> dict[str, Any]:
        raw = await stdout.readline()
        return json.loads(raw)

    # 1. initialize — server replies with its capabilities
    await send({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "surfacelab", "version": "0.1"},
        },
    })
    await recv()  # discard: we don't gate on server capabilities yet

    # 2. initialized — notification, no reply expected (id omitted)
    await send({"jsonrpc": "2.0", "method": "initialized", "params": {}})

    # 3. tools/list — the surface
    await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    response = await recv()

    stdin.close()
    await proc.wait()

    raw_tools: list[dict[str, Any]] = response.get("result", {}).get("tools", [])
    tools = [Tool.model_validate(t) for t in raw_tools]
    return Surface(server_name=server_name, tools=tools)
