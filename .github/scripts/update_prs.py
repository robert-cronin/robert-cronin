# Copyright 2024 Robert Cronin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Refresh the compact public contribution list without touching curated content."""

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERNAME = "robert-cronin"
README = Path(__file__).resolve().parents[2] / "README.md"
START = "<!-- START_SECTION:prs -->"
END = "<!-- END_SECTION:prs -->"
PR_URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/pull/\d+")


def escape_markdown(text):
    text = html.escape(" ".join(text.split()), quote=False)
    return re.sub(r"([\\`*_\[\]])", lambda match: "\\" + match[0], text)


def get_latest_prs(username):
    query = urlencode({
        "q": f"author:{username} is:pr is:merged is:public -repo:{username}/{username}",
        "sort": "updated",
        "order": "desc",
        "per_page": 20,
    })
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/search/issues?{query}", headers=headers)
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
    if data.get("incomplete_results"):
        raise RuntimeError("GitHub returned incomplete results; keeping the existing README.")
    return data["items"]


def render_prs(prs):
    """Show up to three projects, ordered by their most recently updated merged PR."""
    lines, seen = [], set()
    for pr in sorted(prs, key=lambda item: item["updated_at"], reverse=True):
        if not pr.get("pull_request", {}).get("merged_at"):
            continue
        match = PR_URL.fullmatch(pr["html_url"])
        if not match:
            raise ValueError("Expected a public GitHub pull request URL.")
        repository = match[1]
        if repository in seen:
            continue
        seen.add(repository)
        date = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00")).date()
        title = escape_markdown(pr["title"])
        lines.append(
            f"- **{escape_markdown(repository)}** — [{title}]({pr['html_url']}) · Updated {date}"
        )
        if len(lines) == 3:
            break
    if not lines:
        raise ValueError("No merged pull requests returned; keeping the existing README.")
    return "\n".join(lines)


def update_readme(prs, path=README):
    content = path.read_text(encoding="utf-8")
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError("README must contain exactly one contribution marker pair.")
    start = content.index(START) + len(START)
    end = content.index(END)
    if end < start:
        raise ValueError("Contribution markers are out of order.")
    updated = content[:start] + "\n" + render_prs(prs) + "\n" + content[end:]
    if updated == content:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


if __name__ == "__main__":
    changed = update_readme(get_latest_prs(USERNAME))
    print("Updated recent contributions." if changed else "No contribution changes.")
