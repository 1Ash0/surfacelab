# 00 — MCP surface and rendering (U0 explain-back)

A surface is the complete ordered list of tools the model sees in one request —
names, descriptions, and parameter schemas. It comes from an MCP server but the
server has no say in the order; that is the harness's choice.

The handshake is three steps: the client sends `initialize` and the server replies;
the client sends an `initialized` notification (no reply expected); the client sends
`tools/list` and the server replies with the tool array. The server never pushes and
never knows which model will read the tools.

`tools/list` tells you what tools exist and what their schemas look like. It does not
tell you token cost, rendering order, or whether the server is healthy.

Rendering is the harness's job: it takes the tool array, puts it in whatever order it
wants, and passes it to the model API as the `tools=` parameter. "Tool 3 before tool 7"
is a statement about what the harness did, not what the server sent. This is why order
is a variable we can control and measure — it has nothing to do with the server.

Token cost is dominated by schemas and descriptions, not names. A 30-tool surface with
verbose schemas can exceed 10 000 tokens before the user message appears.

This project never calls `tools/call` on real servers in v0.1 because calling a tool
executes it — writes, deletes, sends, charges. We only need to know which tool the model
chose, which we can read from its output without running anything.
