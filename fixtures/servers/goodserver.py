#!/usr/bin/env python3
"""goodserver — fixture MCP server with clear, distinct tool descriptions.

Responds to initialize and tools/list. Returns JSON-RPC error for unknown
methods (per JSON-RPC 2.0 spec). Never calls tools/call (ADR-008).
Run as: python fixtures/servers/goodserver.py
"""
from __future__ import annotations
import json
import sys
from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_weather",
        "description": (
            "Get current weather conditions for a specified location. "
            "Returns temperature, humidity, wind speed, and a short conditions summary."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    },
    {
        "name": "search_web",
        "description": (
            "Search the web for information on a given query. "
            "Returns a ranked list of URLs with titles and short excerpts."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the text contents of a file at a specified path on the local filesystem.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email to a recipient with a specified subject and body text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": (
            "Create a new event on the user's calendar with a title, date, "
            "start time, and optional description."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string"},
                "time": {"type": "string"},
            },
            "required": ["title", "date", "time"],
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
                    "serverInfo": {"name": "goodserver", "version": "0.1"},
                },
            })
        elif method == "initialized":
            pass  # notification — no response
        elif method == "tools/list":
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"tools": TOOLS},
            })
        elif msg_id is not None:
            # Unknown method with an id — return method-not-found error
            _send(_error(msg_id, -32601, f"Method not found: {method!r}"))
        # Unknown notifications (no id) are silently ignored per JSON-RPC spec


if __name__ == "__main__":
    main()
