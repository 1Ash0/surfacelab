"""Pydantic models that mirror the MCP wire format exactly.

These are the single source of truth: render, grading, and stats all take
or return these types. Do not add fields that have no MCP counterpart here;
put analysis-only fields in result types.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class Tool(BaseModel):
    """One tool as returned by tools/list.

    Field names match the MCP JSON keys (snake_case after Pydantic alias).
    input_schema is kept as a raw dict so the exact bytes sent to the model
    are preserved — parsing it into a Python type would lose ordering and
    extra keys that affect token count.
    """

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")

    model_config = {"populate_by_name": True}


class Surface(BaseModel):
    """An ordered list of tools from one MCP server.

    Order matters: it is a variable under study, not an implementation detail.
    The server_name is the label shown in reports and scenes.
    """

    server_name: str
    tools: list[Tool]

    @property
    def tool_count(self) -> int:
        return len(self.tools)
