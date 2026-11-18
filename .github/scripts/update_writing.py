"""Refresh the list of recent blog posts from the site's public post index."""

import html
import json
import re
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

README = Path(__file__).resolve().parents[2] / "README.md"
FEED = "https://robertcronin.com/posts.json"
START = "<!-- START_SECTION:writing -->"
END = "<!-- END_SECTION:writing -->"
POST_URL = re.compile(r"https://robertcronin\.com/blog/[a-z0-9-]+")
LIMIT = 5


def escape_markdown(text):
    text = html.escape(" ".join(text.split()), quote=False)
    return re.sub(r"([\\`*_\[\]])", lambda match: "\\" + match[0], text)


def fetch_posts():
    request = Request(FEED, headers={"Accept": "application/json", "User-Agent": "profile-readme"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def render_posts(posts):
    """Show the newest LIMIT posts, newest first."""
    if not isinstance(posts, list):
        raise ValueError("Expected a list of posts.")
    lines = []
    for post in sorted(posts, key=lambda item: item["date"], reverse=True)[:LIMIT]:
        if not POST_URL.fullmatch(post["url"]):
            raise ValueError("Expected a blog post URL on robertcronin.com.")
        day = date.fromisoformat(post["date"])
        lines.append(f"- [{escape_markdown(post['title'])}]({post['url']})<br><sub>{day.day} {day:%b %Y}</sub>")
    if not lines:
        raise ValueError("No posts returned; keeping the existing README.")
    return "\n".join(lines)


def update_readme(posts, path=README):
    content = path.read_text(encoding="utf-8")
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError("README must contain exactly one writing marker pair.")
    start = content.index(START) + len(START)
    end = content.index(END)
    if end < start:
        raise ValueError("Writing markers are out of order.")
    updated = content[:start] + "\n" + render_posts(posts) + "\n" + content[end:]
    if updated == content:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


if __name__ == "__main__":
    try:
        posts = fetch_posts()
    except (OSError, ValueError) as error:
        # The site answers unknown paths with its HTML shell, so a missing index is not JSON.
        print(f"Post index unavailable ({error}); keeping the existing list.")
    else:
        print("Updated recent writing." if update_readme(posts) else "No writing changes.")
