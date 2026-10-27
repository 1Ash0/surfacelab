"""U0 tests: schema, mcpclient, render, token_ledger.

All tests run offline. The "server" is a tiny Python -c script so there are
no fixture files to maintain yet.
"""

import asyncio
import sys

from surfacelab.mcpclient import fetch_surface
from surfacelab.render import render, token_ledger
from surfacelab.schema import Surface, Tool

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_tool_parses_mcp_wire_format():
    """Tool must accept the inputSchema alias the MCP wire uses."""
    raw = {
        "name": "get_weather",
        "description": "Return weather for a city.",
        "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}},
    }
    tool = Tool.model_validate(raw)
    assert tool.name == "get_weather"
    assert "properties" in tool.input_schema


def test_surface_preserves_order():
    """Tool order in a Surface must be the order the server sent."""
    tools = [Tool(name=f"tool_{i}", description="x", input_schema={}) for i in range(5)]
    surface = Surface(server_name="demo", tools=tools)
    assert [t.name for t in surface.tools] == [f"tool_{i}" for i in range(5)]


# ---------------------------------------------------------------------------
# mcpclient (spawns a real subprocess)
# ---------------------------------------------------------------------------

_SERVER_SRC = """\
import json, sys
TOOLS = [
    {"name":"search","description":"Search the web for a query string.","inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}},
    {"name":"summarise","description":"Summarise a document given its URL.","inputSchema":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}},
]
for line in sys.stdin:
    r = json.loads(line)
    if r.get("method") == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":r["id"],"result":{"protocolVersion":"2024-11-05","capabilities":{},"serverInfo":{"name":"test","version":"0.1"}}}), flush=True)
    elif r.get("method") == "tools/list":
        print(json.dumps({"jsonrpc":"2.0","id":r["id"],"result":{"tools":TOOLS}}), flush=True)
"""


def test_fetch_surface_returns_correct_tools():
    surface = asyncio.run(
        fetch_surface([sys.executable, "-c", _SERVER_SRC], server_name="test")
    )
    assert surface.server_name == "test"
    assert surface.tool_count == 2
    assert surface.tools[0].name == "search"
    assert surface.tools[1].name == "summarise"


def test_fetch_surface_preserves_order():
    surface = asyncio.run(
        fetch_surface([sys.executable, "-c", _SERVER_SRC], server_name="test")
    )
    names = [t.name for t in surface.tools]
    assert names == ["search", "summarise"]


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def test_render_produces_anthropic_shape():
    """render() must return list[dict] with name, description, input_schema."""
    surface = asyncio.run(
        fetch_surface([sys.executable, "-c", _SERVER_SRC], server_name="test")
    )
    rendered = render(surface)
    assert isinstance(rendered, list)
    for item in rendered:
        assert "name" in item
        assert "description" in item
        assert "input_schema" in item


def test_render_preserves_order():
    surface = asyncio.run(
        fetch_surface([sys.executable, "-c", _SERVER_SRC], server_name="test")
    )
    rendered = render(surface)
    assert rendered[0]["name"] == "search"
    assert rendered[1]["name"] == "summarise"


# ---------------------------------------------------------------------------
# token_ledger
# ---------------------------------------------------------------------------

def test_token_ledger_totals_are_positive():
    surface = asyncio.run(
        fetch_surface([sys.executable, "-c", _SERVER_SRC], server_name="test")
    )
    ledger = token_ledger(surface)
    assert ledger.total > 0
    for row in ledger.rows:
        assert row.name_tokens > 0
        assert row.total == row.name_tokens + row.description_tokens + row.schema_tokens


def test_token_ledger_name_is_cheapest_field():
    """For these tools, name tokens < description tokens (typical real-world shape)."""
    surface = asyncio.run(
        fetch_surface([sys.executable, "-c", _SERVER_SRC], server_name="test")
    )
    ledger = token_ledger(surface)
    for row in ledger.rows:
        assert row.name_tokens < row.description_tokens
