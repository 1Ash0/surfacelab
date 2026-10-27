"""Generate derived surface fixtures from base fixtures.

Run: uv run python scripts/gen_fixtures.py

Writes:
  fixtures/surfaces/goodserver_add_usage.json
  fixtures/surfaces/goodserver_add_negation.json
  fixtures/surfaces/goodserver_prepend_summary.json
  fixtures/surfaces/goodserver_trim.json
  fixtures/surfaces/merged_none.json
  fixtures/surfaces/merged_prefix.json
  fixtures/surfaces/merged_qualified.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure src/ is on the path when run from project root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from surfacelab.surface import load_fixture_surface
from surfacelab.variants import Edit, apply_edit, merge_surfaces

FIXTURES = Path(__file__).parent.parent / "fixtures" / "surfaces"


def write(surface_dict: dict, name: str) -> None:  # type: ignore[type-arg]
    path = FIXTURES / f"{name}.json"
    path.write_text(json.dumps(surface_dict, indent=2), encoding="utf-8")
    print(f"  wrote {path.name}")


def main() -> None:
    good = load_fixture_surface("goodserver")
    bad = load_fixture_surface("badserver")
    sibs = load_fixture_surface("siblings")

    print("Generating edit surfaces for EXP-003...")

    # add_usage_clause on get_weather
    e1 = apply_edit(good, Edit("add_usage_clause", "get_weather",
                               "the user asks about temperature, rain, wind, humidity, or general conditions"))
    write(e1.model_dump(by_alias=True), "goodserver_add_usage")

    # add_negation_clause on get_weather
    e2 = apply_edit(good, Edit("add_negation_clause", "get_weather",
                               "historical data, forecasts, or climate statistics"))
    write(e2.model_dump(by_alias=True), "goodserver_add_negation")

    # prepend_summary on search_web
    e3 = apply_edit(good, Edit("prepend_summary", "search_web",
                               "Use this to find information, articles, or URLs on any topic"))
    write(e3.model_dump(by_alias=True), "goodserver_prepend_summary")

    # trim_to_first_sentence on send_email
    e4 = apply_edit(good, Edit("trim_to_first_sentence", "send_email"))
    write(e4.model_dump(by_alias=True), "goodserver_trim")

    # set_description on create_calendar_event (deliberately vague — regression test)
    e5 = apply_edit(good, Edit("set_description", "create_calendar_event",
                               "Creates an event."))
    write(e5.model_dump(by_alias=True), "goodserver_set_desc_vague")

    print("\nGenerating merged surfaces for EXP-004...")
    for ns in ("none", "prefix", "qualified"):
        m = merge_surfaces([good, bad, sibs], ns)
        write(m.model_dump(by_alias=True), f"merged_{ns}")

    print("\nDone.")


if __name__ == "__main__":
    main()
