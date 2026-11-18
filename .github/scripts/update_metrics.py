"""Generate profile metrics from public GitHub data; no image service required."""

import argparse
import calendar
import html
import json
import os
import subprocess
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
USERNAME = "robert-cronin"
METRICS = (
    ("merged_prs", "Merged PRs", f"is:pr is:merged is:public author:{USERNAME}"),
    ("reviewed_prs", "PRs reviewed", f"is:pr is:public reviewed-by:{USERNAME} -author:{USERNAME}"),
    ("issues", "Issues opened", f"is:issue is:public author:{USERNAME}"),
)


def month_windows(today):
    """Twelve calendar months, with the current month ending at the snapshot date."""
    current = today.year * 12 + today.month - 1
    windows = []
    for offset in range(11, -1, -1):
        year, month_zero = divmod(current - offset, 12)
        month = month_zero + 1
        start = date(year, month, 1)
        end = min(date(year, month, calendar.monthrange(year, month)[1]), today)
        windows.append((start, end))
    return windows


def fetch_json(endpoint, use_gh=False):
    if use_gh:
        result = subprocess.run(["gh", "api", endpoint], check=True, capture_output=True, text=True, timeout=45)
        return json.loads(result.stdout)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-metrics"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(f"https://api.github.com/{endpoint}", headers=headers), timeout=30) as response:
        return json.load(response)


def search_count(query, use_gh=False):
    data = fetch_json("search/issues?" + urlencode({"q": query, "per_page": 1}), use_gh)
    if data.get("incomplete_results"):
        raise RuntimeError("Incomplete GitHub search results; keeping previous metrics.")
    count = data["total_count"]
    if not isinstance(count, int) or count < 0:
        raise ValueError("Invalid GitHub search count.")
    # Keep scheduled runs below GitHub's authenticated search rate limit.
    time.sleep(2.1)
    return count


def collect(today, use_gh=False):
    totals = {key: search_count(query, use_gh) for key, _, query in METRICS}
    repositories = []
    page = 1
    while True:
        batch = fetch_json(f"users/{USERNAME}/repos?per_page=100&type=owner&page={page}", use_gh)
        repositories.extend(repo for repo in batch if not repo["fork"] and not repo.get("private", False))
        if len(batch) < 100:
            break
        page += 1
    totals["stars"] = sum(repo["stargazers_count"] for repo in repositories)
    months = []
    for start, end in month_windows(today):
        count = search_count(METRICS[0][2] + f" merged:{start}..{end}", use_gh)
        months.append({"start": str(start), "end": str(end), "merged_prs": count})
    return {"username": USERNAME, "as_of": str(today), "scope": "Public GitHub activity",
            "totals": totals, "months": months,
            "star_repositories": [{"name": repo["full_name"], "stars": repo["stargazers_count"]}
                                  for repo in sorted(repositories, key=lambda repo: repo["full_name"])]}


def render_svg(data, theme, mobile=False):
    dark = theme == "dark"
    bg, panel, border = ("#0b1220", "#141d2e", "#26324a") if dark else ("#eef1f5", "#ffffff", "#c9d0db")
    fg, muted, accent = ("#eef1f5", "#94a0b5", "#ff6a2b") if dark else ("#0b1220", "#4d5768", "#ff6a2b")
    sans = "'Helvetica Neue', 'Segoe UI', Helvetica, Arial, sans-serif"
    mono = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
    width, height = (480, 590) if mobile else (960, 420)
    margin = 22 if mobile else 32
    cols = 2 if mobile else 4
    card_width = (width - margin * 2 - (cols - 1) * 12) / cols
    labels = [("merged_prs", "Merged PRs"), ("reviewed_prs", "PRs reviewed"), ("issues", "Issues opened"), ("stars", "Stars earned")]
    description = "; ".join(f"{label}: {data['totals'][key]}" for key, label in labels)
    description += ". Monthly merged PRs: " + ", ".join(f"{month['start'][:7]}: {month['merged_prs']}" for month in data['months'])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Public GitHub activity</title>', f'<desc id="desc">{html.escape(description)}</desc>',
             # The bars grow and the figures fade in once, when the image loads.
             '<style>.bar{transform-box:fill-box;transform-origin:50% 100%;animation:grow 1.1s cubic-bezier(.16,1,.3,1) both}'
             '.fade{animation:fade .9s ease both}@keyframes grow{from{transform:scaleY(0)}}@keyframes fade{from{opacity:0}}'
             '@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>',
             f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="23.5" fill="{bg}" stroke="{border}"/>']
    def text(x, y, value, size=14, color=muted, weight=400, anchor="start", family=sans, extra=""):
        parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="{family}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"{extra}>{html.escape(str(value))}</text>')
    spaced = ' letter-spacing="1.6"'
    text(margin, 40, "PUBLIC GITHUB ACTIVITY", 12, muted, 500, family=mono, extra=spaced)
    text(width-margin, 40, data["as_of"], 12, muted, 400, "end", mono)
    for index, (key, label) in enumerate(labels):
        x = margin + (index % cols) * (card_width + 12)
        y = 60 + (index // cols) * 112
        parts.append(f'<rect x="{x}" y="{y}" width="{card_width}" height="100" rx="16" fill="{panel}" stroke="{border}"/>')
        text(x+20, y+50, f"{data['totals'][key]:,}", 38, fg, 300, extra=f' letter-spacing="-1.2" class="fade" style="animation-delay:{index*0.08:.2f}s"')
        text(x+20, y+78, label, 14)
    chart_top = 342 if mobile else 228
    text(margin, chart_top-22, "Merged pull requests", 18, fg, 500)
    text(margin, chart_top-2, "Last 12 calendar months · current month partial", 12)
    chart_bottom = height-58
    chart_height = chart_bottom-chart_top-26
    max_value = max(1, max(month["merged_prs"] for month in data["months"]))
    step = (width-margin*2)/12
    for index, month in enumerate(data["months"]):
        x = margin + index*step + 6
        value = month["merged_prs"]
        bar_height = value/max_value*chart_height
        delay = f"{0.2+index*0.05:.2f}s"
        parts.append(f'<rect class="bar" style="animation-delay:{delay}" x="{x:.2f}" y="{chart_bottom-bar_height:.2f}" width="{step-12:.2f}" height="{bar_height:.2f}" rx="4" fill="{accent}" opacity="{0.45 if index==11 else 1}"/>')
        text(x+(step-12)/2, chart_bottom-bar_height-8, value, 11, fg, anchor="middle", family=mono, extra=f' class="fade" style="animation-delay:{0.7+index*0.05:.2f}s"')
        label = date.fromisoformat(month["start"]).strftime("%b").upper()
        text(x+(step-12)/2, chart_bottom+20, label, 10, anchor="middle", family=mono, extra=' letter-spacing="1"')
    text(margin, height-16, "All-time totals above · stars on owned, non-fork repositories", 11)
    parts.append('</svg>\n')
    return "\n".join(parts)


def render_definitions(data):
    rows = []
    for key, label, query in METRICS:
        link = "https://github.com/search?type=issues&q=" + quote(query, safe="")
        rows.append(f"| [{label}]({link}) | {data['totals'][key]:,} |")
    rows.append(f"| Stars on my public, non-fork repositories | {data['totals']['stars']:,} |")
    return (f"Snapshot: **{data['as_of']} (UTC)**. Totals cover public activity indexed by GitHub.\n\n"
            "| Metric | All-time total |\n| :--- | ---: |\n" + "\n".join(rows) +
            "\n\nPRs reviewed counts distinct pull requests by other authors, not individual review submissions. "
            "Stars cover repositories I own, excluding forks; stars on upstream projects are not attributed to me. "
            "Monthly bars count my authored PRs by merge date; the current month is incomplete.\n\n"
            "[Source data](assets/metrics.json) · [Generator](.github/scripts/update_metrics.py)")


def write_outputs(data, root=ROOT):
    # Validate and render everything before touching any existing output.
    date.fromisoformat(data["as_of"])
    if len(data["months"]) != 12:
        raise ValueError("Expected twelve monthly buckets.")
    values = list(data["totals"].values()) + [month["merged_prs"] for month in data["months"]]
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("Metric counts must be non-negative integers.")
    outputs = {root/"assets"/f"metrics-{theme}{'-mobile' if mobile else ''}.svg": render_svg(data, theme, mobile)
               for theme in ["light", "dark"] for mobile in [False, True]}
    outputs[root/"assets/metrics.json"] = json.dumps(data, indent=2) + "\n"
    path = root/"README.md"
    content = path.read_text(encoding="utf-8")
    start, end = "<!-- START_SECTION:metrics -->", "<!-- END_SECTION:metrics -->"
    if content.count(start) != 1 or content.count(end) != 1 or content.index(start) > content.index(end):
        raise ValueError("Expected one ordered metric marker pair.")
    before, rest = content.split(start)
    _, after = rest.split(end)
    outputs[path] = before+start+"\n"+render_definitions(data)+"\n"+end+after
    for path, value in outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != value:
            path.write_text(value, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-gh", action="store_true", help="Use the installed GitHub CLI for local reads")
    parser.add_argument("--from-json", type=Path, help="Regenerate assets from an existing public snapshot")
    args = parser.parse_args()
    data = json.loads(args.from_json.read_text()) if args.from_json else collect(datetime.now(timezone.utc).date(), args.use_gh)
    write_outputs(data)
    print("Updated public metrics and charts.")
