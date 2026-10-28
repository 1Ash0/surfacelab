"""Measure provider-reported prompt tokens for each EXP-013 loadout (one call per loadout and
model, max_tokens=16, a neutral request). The cap in EXP-013 is on this number, not the local count."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

from surfacelab.render import render
from surfacelab.schema import Surface

MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
LOADOUTS = ["browser", "web", "workspace", "docs"]


def main() -> None:
    load_dotenv(Path(".env"))
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY_12"], timeout=60)
    out: dict = {}
    for name in LOADOUTS:
        tools = render(Surface.model_validate_json(Path(f"fixtures/surfaces/real_{name}.json").read_text()))
        for m in MODELS:
            for _ in range(5):
                try:
                    r = client.chat.completions.create(model=m, messages=[{"role": "user", "content": "hi"}],
                                                       tools=tools, max_tokens=16, temperature=0)
                    break
                except RateLimitError:
                    time.sleep(65)  # per-minute window; a sweep shares the org with other runs
            out.setdefault(name, {})[m] = r.usage.prompt_tokens
            print(name, m, r.usage.prompt_tokens, flush=True)
    Path("results/exp013_prompt_tokens.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
