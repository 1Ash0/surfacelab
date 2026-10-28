"""Generate fixtures for EXP-009–012 (ADR-023) from the tables below. Deterministic.

Near-duplicate surfaces: 4 tools each, near-identical names, one stated difference
in scope, so exactly one tool fits each case (checked by gold validation).

Writes:
  fixtures/surfaces/nd_<name>.json                      base surfaces (EXP-009, 010, 012)
  fixtures/surfaces/nd_<name>_contrast.json / _negation  EXP-010 edits
  fixtures/surfaces/xo_<pair>_{none,prefix,qualified}.json  EXP-011 merged servers
  fixtures/surfaces/distractors/nd_<name>.json          EXP-012 near-duplicate pool (20)
"""

from __future__ import annotations

import json
from pathlib import Path

SURF = Path("fixtures/surfaces")
Q = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}

# name: [(tool, description, short scope used by the edit clauses)]
NEAR_DUP: dict[str, list[tuple[str, str, str]]] = {
    "files": [
        ("search_files", "Search for files by name on the local disk of this computer. Matches file names only, not their contents.", "finding a local file by its name"),
        ("find_files", "Find text inside files on the local disk. Returns each file and line where the phrase appears; does not match file names.", "finding text inside local files"),
        ("locate_files", "Locate files by name in the user's cloud drive (synced online storage). Does not look at the local disk.", "finding a file in the cloud drive"),
        ("query_files", "List files on the local disk that were modified within the last N days, newest first.", "listing recently modified local files"),
    ],
    "messaging": [
        ("send_message", "Send an email to one or more email addresses, with a subject and body.", "emailing someone"),
        ("post_message", "Post a message to a team chat channel such as #general. Cannot send email.", "posting in a team chat channel"),
        ("push_message", "Send a push notification to the current user's own phone. Cannot reach anyone else.", "notifying the user's own phone"),
        ("dispatch_message", "Send an SMS text message to a phone number.", "texting a phone number"),
    ],
    "documents": [
        ("get_document", "Get a page from the company's internal wiki by its page title.", "a wiki page by title"),
        ("fetch_document", "Download a file from a public web address (an http or https URL).", "a file at a web URL"),
        ("read_document", "Read a PDF stored on the local disk and return its text.", "a PDF on the local disk"),
        ("open_document", "Open a signed contract from the contracts archive by contract ID (format CT-12345).", "a contract by its CT- ID"),
    ],
    "calendar": [
        ("create_event", "Create an entry on the user's own calendar. No other people are invited.", "the user's own calendar entries"),
        ("schedule_event", "Set up a meeting with other people and email them invitations.", "meetings that invite other people"),
        ("book_event", "Reserve a meeting room for a time slot. Does not add anything to a calendar.", "reserving a meeting room"),
        ("add_event", "Add a task with a due date to the user's to-do list. Does not create calendar entries.", "to-do list tasks"),
    ],
}

# EXP-012 near-duplicate distractors: same domain, scopes no case asks for. 10 scopes x 2 names = 20.
DISTRACTOR_TEMPLATE = {
    "files": "Search for files by name on {s}. Does not look at the local disk or the cloud drive.",
    "messaging": "Send a message to {s}. Cannot send email, chat, push notifications or SMS.",
    "documents": "Get a document from {s}.",
    "calendar": "Use for {s}. Does not create calendar entries, meetings, room bookings or to-do tasks.",
}
DISTRACTOR_SCOPES: dict[str, tuple[list[str], list[str]]] = {
    "files": (["scan_files", "browse_files"], ["a USB drive", "a network share (NAS)", "the recycle bin", "email attachments",
              "the photo library", "the nightly backup archive", "git commit history", "an SD card", "a connected phone",
              "an FTP server"]),
    "messaging": (["relay_message", "deliver_message"], ["a fax number", "a pager", "a printed letter", "a Slack direct message",
                  "a WhatsApp contact", "a Teams call", "a voicemail box", "a smart speaker", "a desk display", "a radio channel"]),
    "documents": (["load_document", "pull_document"], ["the HR policy binder", "a scanned image (OCR)", "the legal hold archive",
                  "a Word file in email", "the print queue", "the support ticket system", "a spreadsheet's comments",
                  "the code review system", "a whiteboard photo", "the board-meeting minutes vault"]),
    "calendar": (["plan_event", "set_event"], ["booking a desk", "ordering catering", "booking travel", "reserving a parking spot",
                 "a shared team holiday calendar", "a habit tracker", "a project Gantt chart", "an alarm clock",
                 "a car-sharing slot", "a gym class"]),
}

# EXP-011: 3 pairs of overlapping servers with identical tool names.
PAIRS: dict[str, list[tuple[str, list[tuple[str, str]]]]] = {
    "files": [
        ("local_fs", [("search_files", "Search file names on this computer's local disk."),
                      ("read_file", "Read a text file from this computer's local disk."),
                      ("delete_file", "Delete a file from this computer's local disk.")]),
        ("cloud_drive", [("search_files", "Search file names in the user's cloud drive."),
                         ("read_file", "Read a document stored in the user's cloud drive."),
                         ("delete_file", "Move a file in the user's cloud drive to its trash.")]),
    ],
    "mail": [
        ("work_mail", [("send_email", "Send an email from the user's work account (@acme.com)."),
                       ("search_inbox", "Search the user's work inbox (@acme.com)."),
                       ("archive_email", "Archive a message in the user's work inbox (@acme.com).")]),
        ("personal_mail", [("send_email", "Send an email from the user's personal account (@gmail.com)."),
                           ("search_inbox", "Search the user's personal inbox (@gmail.com)."),
                           ("archive_email", "Archive a message in the user's personal inbox (@gmail.com).")]),
    ],
    "knowledge": [
        ("team_wiki", [("search", "Search the team's internal wiki pages."),
                       ("get_page", "Get an internal wiki page by title."),
                       ("list_recent", "List recently edited internal wiki pages.")]),
        ("public_web", [("search", "Search the public web."),
                        ("get_page", "Get a public web page by URL."),
                        ("list_recent", "List the latest public news headlines.")]),
    ],
}


def tool(name: str, desc: str) -> dict:
    return {"name": name, "description": desc, "inputSchema": Q}


def write(path: Path, server: str, tools: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"server_name": server, "tools": tools}, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    for name, rows in NEAR_DUP.items():
        server = f"nd_{name}"
        write(SURF / f"{server}.json", server, [tool(t, d) for t, d, _ in rows])
        contrast, negation = [], []
        for t, d, scope in rows:
            others = [(o, s) for o, _, s in rows if o != t]
            contrast.append(tool(t, f"{d} Use this for {scope}. " + " ".join(f"For {s}, use `{o}`." for o, s in others)))
            negation.append(tool(t, f"{d} Do not use this for " + ", ".join(s for _, s in others[:-1]) + f" or {others[-1][1]}."))
        write(SURF / f"{server}_contrast.json", server, contrast)
        write(SURF / f"{server}_negation.json", server, negation)

        verbs, scopes = DISTRACTOR_SCOPES[name]
        pool = [tool(f"{v}_{i}", DISTRACTOR_TEMPLATE[name].format(s=s)) for v in verbs for i, s in enumerate(scopes)]
        write(SURF / "distractors" / f"{server}.json", f"{server}_distractors", pool)

    for pair, servers in PAIRS.items():
        none, prefix, qualified = [], [], []
        for idx, (server, tools) in enumerate(servers):
            for t, d in tools:
                none.append(tool(t if idx == 0 else f"{t}_2", d))  # uninformative suffix: clients must dedupe names
                prefix.append(tool(f"{server}_{t}", d))
                qualified.append(tool(f"{server}/{t}", d))
        for scheme, tools in [("none", none), ("prefix", prefix), ("qualified", qualified)]:
            write(SURF / f"xo_{pair}_{scheme}.json", f"xo_{pair}", tools)
    print("fixtures written")


if __name__ == "__main__":
    main()
