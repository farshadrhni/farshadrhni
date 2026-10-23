"""Generate languages.svg: a donut chart of language usage across ALL of a
user's repositories (public + private), built directly from the GitHub API.

Env vars:
  GH_TOKEN  classic personal access token with `repo` scope (required)
  GH_USER   GitHub username (default: farshadrhni)
"""
import json
import math
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "farshadrhni")
EXCLUDE = {"HTML", "Jupyter Notebook"}   # edit to taste
MAX_SLICES = 8                           # the rest are grouped as "Other"
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
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    totals, page = {}, 1
    while True:
        repos = api("https://api.github.com/user/repos?affiliation=owner"
                    f"&visibility=all&per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo.get("fork") or repo["owner"]["login"].lower() != USER.lower():
                continue
            for lang, size in api(repo["languages_url"]).items():
                totals[lang] = totals.get(lang, 0) + size
        page += 1
    return totals


def render(totals):
    items = sorted(((k, v) for k, v in totals.items() if k not in EXCLUDE),
                   key=lambda kv: -kv[1])
    total = sum(v for _, v in items) or 1
    top, rest = items[:MAX_SLICES], items[MAX_SLICES:]
    if rest:
        top.append(("Other", sum(v for _, v in rest)))

    cx, cy, R, r = 110, 115, 80, 48
    paths, legend, angle = [], [], -math.pi / 2
    for i, (name, size) in enumerate(top):
        frac = size / total
        color = COLORS.get(name, FALLBACK[i % len(FALLBACK)])
        if frac >= 0.9999:
            paths.append(f'<circle cx="{cx}" cy="{cy}" r="{(R + r) / 2}" fill="none" '
                         f'stroke="{color}" stroke-width="{R - r}"/>')
        else:
            a0, a1 = angle, angle + frac * 2 * math.pi
            large = 1 if frac > 0.5 else 0
            p = lambda rad, a: (cx + rad * math.cos(a), cy + rad * math.sin(a))
            x0, y0 = p(R, a0); x1, y1 = p(R, a1)
            x2, y2 = p(r, a1); x3, y3 = p(r, a0)
            paths.append(f'<path d="M{x0:.2f},{y0:.2f} A{R},{R} 0 {large} 1 {x1:.2f},{y1:.2f} '
                         f'L{x2:.2f},{y2:.2f} A{r},{r} 0 {large} 0 {x3:.2f},{y3:.2f} Z" fill="{color}"/>')
        angle += frac * 2 * math.pi
        y = 62 + i * 22
        legend.append(
            f'<rect x="235" y="{y - 10}" width="12" height="12" rx="3" fill="{color}"/>'
            f'<text x="255" y="{y}" class="t">{name}</text>'
            f'<text x="440" y="{y}" class="t" text-anchor="end">{frac * 100:.1f}%</text>')

    height = max(230, 62 + len(top) * 22 + 20)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="{height}" viewBox="0 0 495 {height}">
<style>.t{{font:400 13px 'Segoe UI',Ubuntu,Sans-Serif;fill:#a9fef7}}.h{{font:600 18px 'Segoe UI',Ubuntu,Sans-Serif;fill:#fe428e}}</style>
<rect x="0.5" y="0.5" width="494" height="{height - 1}" rx="4.5" fill="#141321"/>
<text x="25" y="35" class="h">Most Used Languages</text>
{''.join(paths)}
{''.join(legend)}
</svg>'''


def render_html(totals, svg):
    """Standalone HTML page: the chart plus a full table (every language,
    bytes and percentage). Open it directly or host it on GitHub Pages."""
    items = sorted(((k, v) for k, v in totals.items() if k not in EXCLUDE),
                   key=lambda kv: -kv[1])
    total = sum(v for _, v in items) or 1
    rows = "".join(
        f"<tr><td>{name}</td><td>{size:,}</td><td>{size / total * 100:.2f}%</td></tr>"
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
<h1>Language usage across all repositories (public and private)</h1>
{svg}
<table><tr><th>Language</th><th>Bytes</th><th>Share</th></tr>{rows}</table>
<p style="color:#8b949e">Updated automatically from the GitHub API.</p>
</main></body></html>'''


if __name__ == "__main__":
    data = collect()
    if not data:
        sys.exit("No language data returned; check token scope.")
    svg = render(data)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    with open("languages.html", "w", encoding="utf-8") as f:
        f.write(render_html(data, svg))
    print("Wrote", OUT, "and languages.html")
