"""Generate languages.svg: a compact bar chart of language usage across public owned repositories of a
user's repositories (public only), built directly from the GitHub API.

Env vars:
  GH_TOKEN  optional GitHub token for API rate limits
  GH_USER   GitHub username (default: farshadrhni)
"""
import json
from html import escape
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "farshadrhni")
EXCLUDE = set()  # Show every detected language.
OUT = "languages.svg"

COLORS = {
    "MATLAB": "#e16737", "Python": "#3572A5", "Julia": "#a270ba",
    "C++": "#f34b7d", "C": "#555555", "Fortran": "#4d41b1",
    "TeX": "#3D6117", "Jupyter Notebook": "#DA5B0B", "JavaScript": "#f1e05a",
    "Shell": "#89e051", "CSS": "#563d7c", "Objective-C": "#438eff",
    "Mathematica": "#dd1100", "R": "#198CE7", "Other": "#8b8b8b",
}
FALLBACK = ["#fe428e", "#a9fef7", "#f8d847", "#9d7cf5", "#5ad1a3", "#ff9e64", "#7aa2f7", "#e0af68"]


def api(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if os.environ.get("GH_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GH_TOKEN"])
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    totals, page, count = {}, 1, 0
    while True:
        repos = api(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo.get("private") or repo.get("fork") or repo["owner"]["login"].lower() != USER.lower():
                continue
            count += 1
            for lang, size in api(repo["languages_url"]).items():
                totals[lang] = totals.get(lang, 0) + size
        page += 1
    print(f"Scanned {count} public owned non-fork repositories; {len(totals)} languages.")
    return totals


def render(totals):
    items = sorted(((k, v) for k, v in totals.items() if v > 0),
                   key=lambda kv: (-kv[1], kv[0]))
    total = sum(v for _, v in items)
    height = 130 + 30 * ((len(items) + 1) // 2)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{height}" viewBox="0 0 720 {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Repository languages</title>',
             '<desc id="desc">Share of detected code bytes in public owned, non-fork repositories.</desc>',
             '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#24292f}.muted{fill:#57606a;font-size:12px}@media(prefers-color-scheme:dark){text{fill:#e6edf3}.muted{fill:#9da7b3}}</style>',
             '<text x="16" y="28" font-size="17" font-weight="600">Repository languages</text>',
             '<text x="16" y="49" class="muted">Detected code by size · accessible owned repositories · forks excluded</text>']
    x = 16.0
    for i, (name, size) in enumerate(items):
        color = COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        width = 688 * size / total
        parts.append(f'<rect x="{x:.4f}" y="66" width="{width:.4f}" height="12" fill="{color}"/>')
        x += width
        lx, ly = 16 + (i % 2) * 350, 107 + (i // 2) * 30
        pct = size / total * 100
        share = "&lt;0.1%" if pct < 0.1 else f"{pct:.1f}%"
        parts.append(f'<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{color}"/>'
                     f'<text x="{lx+18}" y="{ly}" font-size="13">{escape(name)}</text>'
                     f'<text x="{lx+320}" y="{ly}" font-size="13" text-anchor="end">{share}</text>')
    if not items:
        parts.append('<text x="16" y="105" class="muted">No language data available.</text>')
    parts.append('</svg>')
    return "".join(parts)


def render_html(totals, svg):
    """Standalone HTML page: the chart plus a full table (every language,
    bytes and percentage). Open it directly or host it on GitHub Pages."""
    items = sorted(((k, v) for k, v in totals.items() if k not in EXCLUDE),
                   key=lambda kv: -kv[1])
    total = sum(v for _, v in items) or 1
    rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{size:,}</td><td>{size / total * 100:.2f}%</td></tr>"
        for name, size in items)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Language usage - {USER}</title>
<style>
body{{margin:0;padding:24px;background:#0d1117;color:#e6edf3;font:15px/1.5 'Segoe UI',Ubuntu,sans-serif}}
main{{max-width:560px;margin:auto}}
h1{{font-size:20px}} table{{border-collapse:collapse;width:100%;margin-top:16px}}
th,td{{padding:6px 10px;border-bottom:1px solid #30363d;text-align:left}}
td:nth-child(n+2),th:nth-child(n+2){{text-align:right}}
</style></head><body><main>
<h1>Language usage across accessible owned repositories</h1>
{svg}
<table><tr><th>Language</th><th>Bytes</th><th>Share</th></tr>{rows}</table>
<p style="color:#8b949e">Updated automatically from the GitHub API.</p>
</main></body></html>'''


if __name__ == "__main__":
    data = collect()
    if not data:
        sys.exit("No public repository language data returned.")
    svg = render(data)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    with open("languages.html", "w", encoding="utf-8") as f:
        f.write(render_html(data, svg))
    print("Wrote", OUT, "and languages.html")

