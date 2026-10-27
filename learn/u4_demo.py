"""U4 demo: permute, balanced coverage, and paraphrase validation.

Run with:  uv run python learn/u4_demo.py
"""

from surfacelab.schema import Surface, Tool
from surfacelab.variants import (
    all_permutations,
    balanced_permutations,
    permute,
    paraphrase_valid,
)

# -----------------------------------------------------------------
# Demo surface: three tools
# -----------------------------------------------------------------
SURFACE = Surface(
    server_name="demo",
    tools=[
        Tool(name="get_weather", description="Return current weather for a city."),
        Tool(name="list_files",  description="List files in a directory."),
        Tool(name="run_query",   description="Run a SQL query on the database."),
    ],
)

# -----------------------------------------------------------------
# 1. all_permutations: exact balance for small N
# -----------------------------------------------------------------
print("--- 1. all_permutations (N=3, N!=6) ---")
perms = all_permutations(SURFACE)
print(f"Total orderings: {len(perms)}")
for pos in range(3):
    names_at_pos = [p.tools[pos].name for p in perms]
    counts = {n: names_at_pos.count(n) for n in ["get_weather","list_files","run_query"]}
    print(f"  position {pos}: {names_at_pos}  counts={counts}")

# -----------------------------------------------------------------
# 2. Random shuffles: no coverage guarantee
# -----------------------------------------------------------------
print("\n--- 2. Five independent random shuffles (no coverage guarantee) ---")
for seed in range(5):
    order = [t.name[:3] for t in permute(SURFACE, seed).tools]
    print(f"  seed={seed}: {order}")

at_pos0 = {permute(SURFACE, s).tools[0].name for s in range(5)}
print(f"  tools seen at position 0 across seeds 0-4: {at_pos0}")
print(f"  (3 tools; only {len(at_pos0)} appeared at position 0)")

# -----------------------------------------------------------------
# 3. permute is pure: original surface is unchanged
# -----------------------------------------------------------------
print("\n--- 3. permute is pure: original unchanged ---")
original_order = [t.name for t in SURFACE.tools]
_ = permute(SURFACE, seed=7)
after_order = [t.name for t in SURFACE.tools]
print(f"  before permute: {original_order}")
print(f"  after permute:  {after_order}  (same)")

# -----------------------------------------------------------------
# 4. balanced_permutations
# -----------------------------------------------------------------
print("\n--- 4. balanced_permutations(k=6) ---")
bperms = balanced_permutations(SURFACE, k=6, seed=42)
for pos in range(3):
    names = [p.tools[pos].name[:3] for p in bperms]
    print(f"  position {pos}: {names}")

# -----------------------------------------------------------------
# 5. paraphrase_valid: accept / reject candidates
# -----------------------------------------------------------------
print("\n--- 5. paraphrase_valid ---")
original = "What is the weather in Paris right now?"
cases = [
    ("What is the weather in Paris right now?",             "IDENTICAL"),
    ("What is the current weather in Paris?",               "GOOD (shorter, same entities)"),
    ("Hi!",                                                 "TOO SHORT"),
    ("What is the stock price of AAPL at market close?",    "WRONG ENTITY (AAPL, not Paris)"),
    ("Could you possibly check the weather conditions in the "
     "city of Paris for me at this moment in time, please?", "GOOD (longer, same entities)"),
]
for candidate, label in cases:
    ok, reason = paraphrase_valid(original, candidate)
    status = "pass" if ok else "FAIL"
    print(f"  [{status}] {label}: {reason if not ok else ''}")
