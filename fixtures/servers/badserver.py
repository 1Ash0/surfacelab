#!/usr/bin/env python3
"""badserver — fixture MCP server with deliberate description smells.

Smells present:
  - fetch_document / get_document: near-duplicate descriptions (sibling confusion)
  - do_thing: vague name and description
  - process_data: description mentions another tool by name
  - analyze_text: description scope creep (claims to handle images and audio)

Used to verify that detectors fire on bad inputs.
"""
from __future__ import annotations
import json
import sys
from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "name": "fetch_document",
        "description": "Retrieves a document from storage.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "get_document",
        "description": "Retrieves a document from the storage system.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "do_thing",
        "description": "Does the thing.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "process_data",
        "description": "Processes data. Use instead of `get_data` which is deprecated.",
        "inputSchema": {
            "type": "object",
            "properties": {"data": {"type": "string"}},
            "required": ["data"],
        },
    },
    {
        "name": "analyze_text",
        "description": "Analyzes text and returns a structured result. Also useful for images and audio files.",
        "inputSchema": {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"],
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
                    "serverInfo": {"name": "badserver", "version": "0.1"},
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
