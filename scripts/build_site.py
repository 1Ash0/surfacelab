"""Build the public Observatory site (GitHub Pages) from the template and the data files.

  python scripts/build_site.py        # writes site/index.html, site/og.jpg, site/.nojekyll

The template's __DATA__ and __SIB__ placeholders are filled from docs/design/observatory-data.json
and docs/design/observatory-siblings-data.json (rebuild those with build_observatory_data.py).
"""

from __future__ import annotations

import shutil
from pathlib import Path

SITE = Path("site")
URL = "https://1ash0.github.io/surfacelab/"
DESC = ("An open evaluation of how AI agents choose MCP tools: 82 real tools, 396 recorded calls, "
        "12 preregistered experiments, drawn as an observatory.")

HEAD = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{DESC}">
<meta property="og:type" content="website">
<meta property="og:title" content="surfacelab Observatory">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="{URL}og.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{URL}og.jpg">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%2305070F'/%3E%3Cpath d='M6 24a10 10 0 0 1 20 0z' fill='%23D2AA6E'/%3E%3Crect x='15' y='8' width='2' height='9' fill='%23F4B860'/%3E%3C/svg%3E">
<style>html,body{{margin:0}}</style>
"""


def main() -> None:
    t = Path("docs/design/observatory-prototype.template.html").read_text(encoding="utf-8")
    data = Path("docs/design/observatory-data.json").read_text(encoding="utf-8")
    sib = Path("docs/design/observatory-siblings-data.json").read_text(encoding="utf-8")
    body = t.replace("__DATA__", data).replace("__SIB__", sib)
    assert "__DATA__" not in body and "__SIB__" not in body
    body = body.replace('<meta charset="utf-8">\n', "", 1)
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(HEAD + body + "\n</html>\n", encoding="utf-8")
    (SITE / ".nojekyll").write_text("")
    shutil.copy("docs/media/observatory.jpg", SITE / "og.jpg")
    print(f"wrote {SITE / 'index.html'} ({(SITE / 'index.html').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
