.PHONY: check test install gen-fixtures exp007 \
        exp001-dry-run exp001-record \
        exp002-dry-run exp002-record \
        exp003-dry-run exp003-record \
        exp004-dry-run exp004-record \
        exp005-dry-run exp005-record \
        exp006-preflight exp006-record \
        power-sim

# ---- dev ---------------------------------------------------------------

install:
	uv sync --all-groups

check:
	uv run ruff check src/ tests/
	uv run pyright
	uv run pytest tests/ -x -q

test:
	uv run pytest tests/ -x -q

# ---- fixture generation ------------------------------------------------

gen-fixtures:
	uv run python scripts/gen_fixtures.py

# ---- power simulation --------------------------------------------------

power-sim:
	uv run python scripts/power_sim.py

# ---- EXP-007 (offline — runs in CI) ------------------------------------

exp007:
	uv run python scripts/run_exp007.py

# ---- EXP-001: order sensitivity ----------------------------------------
# Models: openai/gpt-oss-20b and openai/gpt-oss-120b on Groq
# Requires GROQ_API_KEY in .env

exp001-dry-run:
	uv run surfacelab run fixtures/cases/core.jsonl \
	  --surface goodserver --provider groq \
	  --model openai/gpt-oss-20b \
	  --variants 5 --dry-run
	uv run surfacelab run fixtures/cases/siblings.jsonl \
	  --surface siblings --provider groq \
	  --model openai/gpt-oss-20b \
	  --variants 4 --dry-run

exp001-record:
	@echo "--- EXP-001: small model (8b) ---"
	uv run surfacelab run fixtures/cases/core.jsonl \
	  --surface goodserver --provider groq \
	  --model openai/gpt-oss-20b \
	  --variants 120 --record --max-usd 5.00 --workers 8
	uv run surfacelab run fixtures/cases/siblings.jsonl \
	  --surface siblings --provider groq \
	  --model openai/gpt-oss-20b \
	  --variants 24 --record --max-usd 5.00 --workers 8
	@echo "--- EXP-001: large model (120b) ---"
	uv run surfacelab run fixtures/cases/core.jsonl \
	  --surface goodserver --provider groq \
	  --model openai/gpt-oss-120b \
	  --variants 120 --record --max-usd 5.00 --workers 8
	uv run surfacelab run fixtures/cases/siblings.jsonl \
	  --surface siblings --provider groq \
	  --model openai/gpt-oss-120b \
	  --variants 24 --record --max-usd 5.00 --workers 8

# ---- EXP-002: paraphrase fragility -------------------------------------

exp002-dry-run:
	uv run surfacelab run fixtures/cases/core.jsonl \
	  --surface goodserver --provider groq \
	  --model openai/gpt-oss-20b \
	  --variants 1 --dry-run

exp002-record:
	@echo "EXP-002: generate paraphrases first (scripts/gen_paraphrases.py), then run"
	@echo "Paraphrase generation not yet automated — see EXP-002.md for manual steps"

# ---- EXP-003: single-edit tradeoff -------------------------------------

exp003-dry-run:
	@for surface in goodserver goodserver_add_usage goodserver_add_negation \
	                goodserver_prepend_summary goodserver_trim goodserver_set_desc_vague; do \
	  uv run surfacelab run fixtures/cases/core.jsonl \
	    --surface $$surface --provider groq \
	    --model openai/gpt-oss-20b \
	    --variants 1 --dry-run; \
	done

exp003-record:
	@for surface in goodserver goodserver_add_usage goodserver_add_negation \
	                goodserver_prepend_summary goodserver_trim goodserver_set_desc_vague; do \
	  uv run surfacelab run fixtures/cases/core.jsonl \
	    --surface $$surface --provider groq \
	    --model openai/gpt-oss-20b \
	    --variants 1 --record --max-usd 2.00 --workers 8; \
	  uv run surfacelab run fixtures/cases/core.jsonl \
	    --surface $$surface --provider groq \
	    --model openai/gpt-oss-120b \
	    --variants 1 --record --max-usd 2.00 --workers 8; \
	done

# ---- EXP-004: cross-server collision -----------------------------------

exp004-dry-run:
	@for surface in merged_none merged_prefix merged_qualified; do \
	  uv run surfacelab run fixtures/cases/cross_server.jsonl \
	    --surface $$surface --provider groq \
	    --model openai/gpt-oss-20b \
	    --variants 1 --dry-run; \
	done

exp004-record:
	@for surface in merged_none merged_prefix merged_qualified; do \
	  uv run surfacelab run fixtures/cases/cross_server.jsonl \
	    --surface $$surface --provider groq \
	    --model openai/gpt-oss-20b \
	    --variants 1 --record --max-usd 2.00 --workers 8; \
	  uv run surfacelab run fixtures/cases/cross_server.jsonl \
	    --surface $$surface --provider groq \
	    --model openai/gpt-oss-120b \
	    --variants 1 --record --max-usd 2.00 --workers 8; \
	done

# ---- EXP-005: tool-count dose-response (M6; uses pad_surface at runtime)

exp005-dry-run:
	uv run surfacelab run fixtures/cases/core.jsonl \
	  --surface goodserver --provider groq \
	  --model openai/gpt-oss-20b \
	  --variants 1 --dry-run

exp005-record:
	@echo "EXP-005: dose-response run requires scripts/run_exp005.py (not yet written)"
	@echo "See EXP-005.md for design. Implement in M6."

# ---- EXP-006: server availability probe (Docker required) --------------

exp006-preflight:
	@echo "Checking Docker..."
	docker ps
	@echo "Probing fixture servers inside Docker..."
	uv run surfacelab probe \
	  python fixtures/servers/goodserver.py \
	  --server-name goodserver-preflight
	uv run surfacelab probe \
	  python fixtures/servers/badserver.py \
	  --server-name badserver-preflight

exp006-record:
	@echo "EXP-006: requires curated target list (see EXP-006.md pre-conditions)"
	@echo "Build a per-server Docker image, then use: uv run python scripts/run_exp006.py"
