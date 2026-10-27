"""Probe variants: pure functions that transform a Surface or a Case.

All functions are pure — they return new objects and never mutate their inputs.
Each variant function corresponds to a study factor in an experiment.

U4: permute (order factor) and paraphrase_valid (semantic-equivalence check).
U5: edit (targeted one-field description changes, EXP-003).
"""

from __future__ import annotations

import itertools
import random
import re
from dataclasses import dataclass

from .schema import Surface, Tool

# ---------------------------------------------------------------------------
# Permutation variants (C04 — position effects)
# ---------------------------------------------------------------------------


def permute(surface: Surface, seed: int) -> Surface:
    """Return a new Surface with tools shuffled using the given seed. Pure."""
    tools = list(surface.tools)
    rng = random.Random(seed)
    rng.shuffle(tools)
    return Surface(server_name=surface.server_name, tools=tools)


def all_permutations(surface: Surface) -> list[Surface]:
    """Enumerate all N! orderings of the surface tools.

    Use for N<=5 (at most 120 surfaces). Each tool appears at each position
    exactly (N-1)! times — the only way to guarantee exact positional balance.
    """
    return [
        Surface(server_name=surface.server_name, tools=list(perm))
        for perm in itertools.permutations(surface.tools)
    ]


def balanced_permutations(
    surface: Surface,
    k: int,
    seed: int = 42,
) -> list[Surface]:
    """Return k permutations with approximately balanced position coverage.

    For N<=5 and k >= N!: returns every ordering once (complete enumeration).
    For N<=5 and k < N!:  samples k distinct orderings uniformly at random.
    For N>5:              uses N cyclic rotations (exact coverage for the first
                          N permutations) then adds random shuffles for the rest.

    Independent random shuffles (permute() called k times with different seeds)
    have no coverage guarantee: with bad luck the same tool could dominate
    position 0 across all k permutations. balanced_permutations avoids this.
    """
    n = len(surface.tools)
    if n == 0 or k <= 0:
        return []

    rng = random.Random(seed)

    if n <= 5:
        all_idx_perms = list(itertools.permutations(range(n)))
        if k >= len(all_idx_perms):
            # Complete enumeration — shuffle to avoid alphabetical-ordering bias.
            idx_list = list(all_idx_perms)
            rng.shuffle(idx_list)
        else:
            idx_list = rng.sample(all_idx_perms, k)
        return [
            Surface(server_name=surface.server_name,
                    tools=[surface.tools[i] for i in idx])
            for idx in idx_list
        ]

    # N > 5: cyclic rotations cover every tool at every position once,
    # then random shuffles fill the remainder.
    tools = list(surface.tools)
    result: list[Surface] = []

    for shift in range(min(n, k)):
        rotated = tools[shift:] + tools[:shift]
        result.append(Surface(server_name=surface.server_name, tools=rotated))

    for _ in range(k - len(result)):
        shuffled = list(tools)
        rng.shuffle(shuffled)
        result.append(Surface(server_name=surface.server_name, tools=shuffled))

    return result


# ---------------------------------------------------------------------------
# Paraphrase validation (C05 — metamorphic testing)
# ---------------------------------------------------------------------------

# Character-length ratio bounds for a valid paraphrase.
_MIN_LEN_RATIO = 0.40
_MAX_LEN_RATIO = 4.00


def _entities(text: str) -> frozenset[str]:
    """Extract key entities from text: mid-sentence title-case words (proper
    nouns), ALL-CAPS tokens (acronyms), and numeric values.

    Used as a proxy for the names and values that a paraphrase must preserve.
    Common sentence-starting capitalisation is excluded (index 0 in the token
    list).
    """
    tokens = re.findall(r'\S+', text)
    found: set[str] = set()
    for i, tok in enumerate(tokens):
        word = re.sub(r'[^\w]', '', tok)
        if not word:
            continue
        if word.isupper() and len(word) >= 2 or i > 0 and word[0].isupper() and not word.isupper():        # AAPL, SQL
            found.add(word.lower())
        elif re.match(r'\d', word):                   # 42, 3.14
            found.add(word)
    return frozenset(found)


def paraphrase_valid(original: str, candidate: str) -> tuple[bool, str]:
    """Check whether candidate is a valid paraphrase of original.

    Returns (valid, reason). valid=True means all constraints pass; reason is
    empty when valid and a human-readable failure message when not.

    Constraints (order: cheapest first):
    1. Not identical to original.
    2. Character-length ratio in [_MIN_LEN_RATIO, _MAX_LEN_RATIO].
    3. All key entities (proper nouns, acronyms, numbers) from original present
       in candidate.

    This is a necessary-but-not-sufficient filter. A model-generated paraphrase
    that passes these checks still requires a sampled human audit before use in
    a confirmatory experiment (EVAL_DESIGN §2, EXP-002).
    """
    if candidate.strip() == original.strip():
        return False, "identical to original"

    ratio = len(candidate) / max(len(original), 1)
    if ratio < _MIN_LEN_RATIO:
        return False, f"too short (length ratio {ratio:.2f} < {_MIN_LEN_RATIO})"
    if ratio > _MAX_LEN_RATIO:
        return False, f"too long (length ratio {ratio:.2f} > {_MAX_LEN_RATIO})"

    required = _entities(original)
    if required:
        present = _entities(candidate)
        missing = required - present
        if missing:
            return False, f"missing key entities: {sorted(missing)}"

    return True, ""


# ---------------------------------------------------------------------------
# Description edits (C03 — what influences selection; EXP-003)
# ---------------------------------------------------------------------------

# Catalogue of supported edit types. edit_id is stable across runs.
# Each entry: (edit_id, human description of the targeted smell / improvement).
EDIT_CATALOGUE: dict[str, str] = {
    "add_usage_clause":    "Append 'Use when: …' to clarify intended use cases.",
    "add_negation_clause": "Append 'Do not use for: …' to exclude common misuses.",
    "prepend_summary":     "Prepend a one-sentence summary before the existing text.",
    "set_description":     "Replace the entire description with a new one.",
    "trim_to_first_sentence": "Shorten to the first sentence only (no content arg).",
}


@dataclass(frozen=True)
class Edit:
    """A single targeted change to one tool's description.

    edit_id must be a key in EDIT_CATALOGUE. content is the text argument
    for edits that add or replace text; ignored for trim_to_first_sentence.
    edit_ids are stable: changing an edit means a new edit_id, not an update,
    so cassettes keyed on the rendered surface remain valid.
    """

    edit_id: str
    tool_name: str
    content: str = ""

    def __post_init__(self) -> None:
        if self.edit_id not in EDIT_CATALOGUE:
            raise ValueError(
                f"Unknown edit_id {self.edit_id!r}. "
                f"Valid ids: {sorted(EDIT_CATALOGUE)}"
            )


def _apply_action(edit_id: str, description: str, content: str) -> str:
    """Apply one edit action to a description string."""
    if edit_id == "add_usage_clause":
        suffix = f" Use when: {content}." if not content.endswith(".") else f" Use when: {content}"
        return description.rstrip() + suffix
    if edit_id == "add_negation_clause":
        suffix = f" Do not use for: {content}." if not content.endswith(".") else f" Do not use for: {content}"
        return description.rstrip() + suffix
    if edit_id == "prepend_summary":
        return f"{content.rstrip('.')}. {description}"
    if edit_id == "set_description":
        return content
    if edit_id == "trim_to_first_sentence":
        # Keep up to and including the first sentence-ending punctuation.
        m = re.search(r'[.!?]', description)
        return description[: m.end()].strip() if m else description
    raise ValueError(f"Unhandled edit_id: {edit_id!r}")  # unreachable after __post_init__


# ---------------------------------------------------------------------------
# Merge variants (C06 — cross-server collision; EXP-004)
# ---------------------------------------------------------------------------

Namespacing = str  # "none" | "prefix" | "qualified"
_VALID_NAMESPACING = frozenset({"none", "prefix", "qualified"})


def merge_surfaces(
    surfaces: list[Surface],
    namespacing: Namespacing = "none",
) -> Surface:
    """Union of surfaces into one. Tool names optionally namespaced.

    namespacing modes
    -----------------
    none       Tool names unchanged. Collisions possible — that's the point
               of EXP-004 (measuring collision rate).
    prefix     Prepend server_name + "_" to every tool name.
    qualified  Prepend server_name + "/" to every tool name (MCP-style).

    The merged server_name is the pipe-joined list of source server names.
    Pure — does not mutate any input.
    """
    if namespacing not in _VALID_NAMESPACING:
        raise ValueError(
            f"Unknown namespacing {namespacing!r}. Valid: {sorted(_VALID_NAMESPACING)}"
        )

    merged_tools: list[Tool] = []
    for surface in surfaces:
        for tool in surface.tools:
            if namespacing == "none":
                name = tool.name
            elif namespacing == "prefix":
                name = f"{surface.server_name}_{tool.name}"
            else:  # qualified
                name = f"{surface.server_name}/{tool.name}"
            merged_tools.append(tool.model_copy(update={"name": name}))

    server_name = "|".join(s.server_name for s in surfaces)
    return Surface(server_name=server_name, tools=merged_tools)


# ---------------------------------------------------------------------------
# Pad variants (C07 — tool-count dose-response; EXP-005)
# ---------------------------------------------------------------------------

PadKind = str  # "unrelated" | "same-domain" | "near-duplicate"
_VALID_PAD_KINDS = frozenset({"unrelated", "same-domain", "near-duplicate"})

# Distractor pool keyed by kind. Each entry is (name_template, description_template).
# name_template uses {i} for the distractor index; description_template likewise.
_DISTRACTOR_POOLS: dict[str, list[tuple[str, str]]] = {
    "unrelated": [
        ("play_music_{i}", "Play a music track by title or artist."),
        ("set_reminder_{i}", "Set a time-based reminder with a message."),
        ("convert_currency_{i}", "Convert an amount between two currency codes."),
        ("translate_text_{i}", "Translate text from one language to another."),
        ("resize_image_{i}", "Resize an image to given width and height in pixels."),
        ("compress_file_{i}", "Compress a file or directory into a zip archive."),
        ("get_stock_price_{i}", "Return the latest price for a given stock ticker symbol."),
        ("send_sms_{i}", "Send a short SMS message to a phone number."),
        ("run_sql_{i}", "Execute a SQL query against the connected database."),
        ("list_directory_{i}", "List the contents of a directory at a given path."),
        ("upload_file_{i}", "Upload a local file to remote object storage."),
        ("generate_qr_{i}", "Generate a QR code image from a text string or URL."),
        ("ping_host_{i}", "Check whether a host is reachable and return round-trip time."),
        ("hash_text_{i}", "Return the SHA-256 hash of a given text string."),
        ("decode_base64_{i}", "Decode a base64-encoded string and return the original bytes."),
        ("get_timezone_{i}", "Return the current date and time for a given timezone name."),
        ("read_clipboard_{i}", "Read the current text content of the system clipboard."),
        ("open_browser_{i}", "Open a URL in the system default browser."),
        ("get_battery_{i}", "Return the current battery level and charging status."),
        ("list_processes_{i}", "List running system processes with their PID and CPU usage."),
    ],
    "same-domain": [
        ("lookup_forecast_{i}", "Look up the weather forecast for a location over the next N days."),
        ("fetch_web_page_{i}", "Retrieve the HTML content of a web page at a given URL."),
        ("append_to_file_{i}", "Append text content to the end of a file at a given path."),
        ("reply_email_{i}", "Send a reply to an existing email thread by message ID."),
        ("update_calendar_event_{i}", "Update an existing calendar event by its event ID."),
        ("get_weather_history_{i}", "Return historical weather data for a location and date range."),
        ("browse_web_{i}", "Navigate to a URL and return visible text from the page."),
        ("write_file_{i}", "Write text content to a file, overwriting any existing content."),
        ("forward_email_{i}", "Forward an existing email to a new recipient."),
        ("delete_calendar_event_{i}", "Delete a calendar event by its event ID."),
        ("get_weather_alerts_{i}", "Return active weather alerts for a location."),
        ("search_emails_{i}", "Search emails by sender, subject or keyword."),
        ("copy_file_{i}", "Copy a file from one path to another."),
        ("list_calendar_events_{i}", "List calendar events for a given date range."),
        ("get_web_summary_{i}", "Fetch and summarise the content of a web page."),
    ],
    "near-duplicate": [
        ("get_current_weather_{i}", "Get current weather conditions for a specified location. Returns temperature, humidity and a conditions summary."),
        ("web_search_{i}", "Search the web for a given query. Returns ranked URLs with titles and excerpts."),
        ("load_file_{i}", "Load and return the text contents of a file at a given path."),
        ("compose_email_{i}", "Compose and send an email to a recipient with subject and body."),
        ("add_calendar_event_{i}", "Add a new event to the user calendar with title, date and start time."),
        ("check_weather_{i}", "Check the weather at a location and return current conditions."),
        ("internet_search_{i}", "Perform an internet search and return the top results."),
        ("open_file_{i}", "Open and read a file from the filesystem at the given path."),
        ("mail_send_{i}", "Send an email message to a specified address."),
        ("schedule_event_{i}", "Schedule a calendar event for a given date and time."),
        ("weather_lookup_{i}", "Look up weather information for a city or region."),
        ("query_web_{i}", "Query the web for information on a topic and return results."),
        ("file_read_{i}", "Read the contents of a file specified by its path."),
        ("email_message_{i}", "Send an email with the given subject and body to a recipient."),
        ("calendar_create_{i}", "Create a calendar entry with a title and scheduled time."),
    ],
}


def pad_surface(
    surface: Surface,
    n: int,
    kind: PadKind,
    seed: int = 42,
) -> Surface:
    """Add n distractor tools of the specified kind to the surface.

    kind
    ----
    unrelated     Tools from a completely different domain (music, currency, SMS…).
    same-domain   Tools from the same domain with different operations.
    near-duplicate  Tools with almost identical descriptions to the existing tools.

    Distractors are drawn from the pool for that kind, cycling if n exceeds pool
    size, with index disambiguation. The result is a new Surface with the
    original tools first, distractors appended. Pure — does not mutate input.
    """
    if kind not in _VALID_PAD_KINDS:
        raise ValueError(
            f"Unknown pad kind {kind!r}. Valid: {sorted(_VALID_PAD_KINDS)}"
        )
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")

    pool = _DISTRACTOR_POOLS[kind]
    rng = random.Random(seed)
    pool_copy = list(pool)
    rng.shuffle(pool_copy)

    extras: list[Tool] = []
    for i in range(n):
        name_tpl, desc_tpl = pool_copy[i % len(pool_copy)]
        extras.append(Tool(
            name=name_tpl.format(i=i),
            description=desc_tpl.format(i=i),
        ))

    return Surface(server_name=surface.server_name, tools=list(surface.tools) + extras)


def apply_edit(surface: Surface, edit: Edit) -> Surface:
    """Apply one targeted description edit to a named tool. Pure.

    Raises ValueError if tool_name is not found in the surface.
    """
    found = False
    tools: list[Tool] = []
    for tool in surface.tools:
        if tool.name == edit.tool_name:
            found = True
            new_desc = _apply_action(edit.edit_id, tool.description, edit.content)
            tools.append(tool.model_copy(update={"description": new_desc}))
        else:
            tools.append(tool)
    if not found:
        raise ValueError(
            f"Tool {edit.tool_name!r} not found in surface {surface.server_name!r}. "
            f"Available: {[t.name for t in surface.tools]}"
        )
    return Surface(server_name=surface.server_name, tools=tools)
