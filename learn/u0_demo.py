# learn/u0_demo.py — MCP handshake and token ledger, stdlib only
# Run: python learn/u0_demo.py
import json, subprocess, sys

SERVER = """\
import json, sys
TOOLS = [
    {"name": "get_weather",
     "description": "Return current weather for a city by name.",
     "inputSchema": {"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}},
    {"name": "list_files",
     "description": "List files in a directory path on the local filesystem.",
     "inputSchema": {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
    {"name": "run_query",
     "description": "Execute a read-only SQL query and return result rows as JSON.",
     "inputSchema": {"type":"object","properties":{"sql":{"type":"string"}},"required":["sql"]}},
]
for line in sys.stdin:
    r = json.loads(line)
    if r["method"] == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":r["id"],"result":{
            "protocolVersion":"2024-11-05","capabilities":{},"serverInfo":{"name":"demo","version":"0.1"}
        }}), flush=True)
    elif r["method"] == "tools/list":
        print(json.dumps({"jsonrpc":"2.0","id":r["id"],"result":{"tools":TOOLS}}), flush=True)
"""

def rpc(proc, id, method, params={}):
    proc.stdin.write(json.dumps({"jsonrpc":"2.0","id":id,"method":method,"params":params}) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())

tok = lambda s: max(1, len(s) // 4)   # rough: 1 token ≈ 4 chars (good enough to see the shape)

proc = subprocess.Popen([sys.executable, "-c", SERVER],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
rpc(proc, 1, "initialize", {"protocolVersion":"2024-11-05","capabilities":{}})
tools = rpc(proc, 2, "tools/list")["result"]["tools"]
proc.stdin.close(); proc.wait()

print(f"\n{len(tools)}-tool surface\n")
print(f"{'tool':<20} {'name':>5} {'desc':>5} {'schema':>6} {'total':>6}")
print("-" * 46)
grand = 0
for t in tools:
    n = tok(t["name"])
    d = tok(t["description"])
    s = tok(json.dumps(t["inputSchema"]))
    row = n + d + s
    grand += row
    print(f"{t['name']:<20} {n:>5} {d:>5} {s:>6} {row:>6}")
print("-" * 46)
print(f"{'TOTAL':<20} {'':>5} {'':>5} {'':>6} {grand:>6}")
print(f"\n(token estimates are rough: 1 token ~= 4 chars)")
