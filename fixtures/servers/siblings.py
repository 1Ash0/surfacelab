#!/usr/bin/env python3
"""siblings — fixture MCP server with four near-duplicate file-search tools.

All four tools do the same thing (find files matching a query) but use
different verbs in their names and descriptions. Used to test sibling-
confusion detection and order-sweep robustness on maximally similar tools.
"""
from __future__ import annotations
import json
import sys
from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_files",
        "description": "Search for files matching a query in the file system. Returns matching file paths.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "find_files",
        "description": "Locate files matching a query in the file system. Returns matching file paths.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "locate_files",
        "description": "Find files matching a query across the file system. Returns matching file paths.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "query_files",
        "description": "Query for files matching a search term in the file system. Returns matching file paths.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def _send(msg: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _error(id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def main() -> None:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            _send(_error(None, -32700, "Parse error"))
            continue

        method = msg.get("method", "")
        msg_id = msg.get("id")

        if method == "initialize":
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "siblings", "version": "0.1"},
                },
            })
        elif method == "initialized":
            pass
        elif method == "tools/list":
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"tools": TOOLS},
            })
        elif msg_id is not None:
            _send(_error(msg_id, -32601, f"Method not found: {method!r}"))


if __name__ == "__main__":
    main()
