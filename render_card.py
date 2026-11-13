"""Generate the GitHub profile cards from the portrait and public account data."""

from html import escape
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
OWNER = "CHENyiru3"
WIDTH, HEIGHT = 1000, 512
PORTRAIT_X, PORTRAIT_Y = 27, 44
DETAIL_X, DETAIL_RIGHT = 401, 966
DETAIL_CHAR_WIDTH = 10.1
CHARACTERS = ";;rrs++xxooOO#%@"


def github_json(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CHENyiru3-profile-card",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com{path}", headers=headers)
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def public_stats():
    user = github_json(f"/users/{OWNER}")
    stars, page = 0, 1
    while True:
        repositories = github_json(f"/users/{OWNER}/repos?per_page=100&page={page}")
        stars += sum(repo["stargazers_count"] for repo in repositories)
        if len(repositories) < 100:
            break
        page += 1
    contributions = {}
    for field, kind in (("public_prs", "pr"), ("public_issues", "issue")):
        query = urlencode({"q": f"author:{OWNER} is:{kind} is:public", "per_page": 1})
        result = github_json(f"/search/issues?{query}")
        if result["incomplete_results"]:
            raise RuntimeError(f"GitHub returned incomplete results for {kind}")
        contributions[field] = result["total_count"]

    return {
        "username": user["login"],
        "repos": user["public_repos"],
        "stars": stars,
        **contributions,
    }


def label(x, y, value, color, **attrs):
    attributes = "".join(
        f' {key.replace("_", "-")}="{escape(str(value), quote=True)}"'
        for key, value in attrs.items()
    )
    return f'<text x="{x}" y="{y}" fill="{color}"{attributes}>{escape(str(value))}</text>'


def render(art, config, stats, dark):
    bg, border, text, key, value, faint = (
        ("#151b23", "#303942", "#d9e2ec", "#ffac67", "#badbff", "#58677a")
        if dark else
        ("#f5f7fa", "#d8dfe6", "#222d39", "#914006", "#133b68", "#a0aebb")
    )

    def resolve(value):
        for name, replacement in stats.items():
            value = value.replace("{{" + name + "}}", str(replacement))
        return value

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<title>Yiru Chen Neofetch profile</title>',
        '<desc>An ASCII portrait beside education, contact details, and public GitHub statistics.</desc>',
        f'<rect x="1" y="1" width="{WIDTH-2}" height="{HEIGHT-2}" rx="14" fill="{bg}" stroke="{border}"/>',
        '<g font-family="Menlo, Consolas, monospace" xml:space="preserve" font-size="8.8">',
    ]
    for row, line in enumerate(art):
        spans = []
        for column, character in enumerate(line):
            if character == " ":
                continue
            shade = int(character, 16)
            density = shade if dark else 15 - shade
            intensity = (67 + density * 12) if dark else (160 - density * 9)
            color = f"#{intensity:02x}{intensity:02x}{intensity:02x}"
            spans.append(
                f'<tspan x="{PORTRAIT_X + column * 5.24:.1f}" fill="{color}">{escape(CHARACTERS[density])}</tspan>'
            )
        if spans:
            svg.append(f'<text y="{PORTRAIT_Y + row * 9.05:.2f}">{"".join(spans)}</text>')

    svg.extend([
        '</g>',
        f'<path d="M 385 27 V 485" stroke="{border}"/>',
        '<g font-family="Menlo, Consolas, monospace" font-size="16.8">',
    ])

    def heading(y, title):
        title = resolve(title)
        svg.append(label(DETAIL_X, y, title, text, font_weight="bold"))
        start = round(DETAIL_X + len(title) * DETAIL_CHAR_WIDTH + 16)
        svg.append(f'<path d="M {start} {y-5} H {DETAIL_RIGHT}" stroke="{border}"/>')

    def field(y, left, right, item):
        name = item["key"] + ":"
        resolved = resolve(item["value"])
        dots_left = round(left + len(name) * DETAIL_CHAR_WIDTH + 8)
        dots_right = round(right - len(resolved) * DETAIL_CHAR_WIDTH - 8)
        if dots_right > dots_left:
            svg.append(f'<path d="M {dots_left} {y-4} H {dots_right}" stroke="{faint}" stroke-width="1.8" stroke-linecap="round" stroke-dasharray="0 6"/>')
        svg.append(label(left, y, name, key))
        svg.append(label(right, y, resolved, value, text_anchor="end"))

    y = 48
    for section in config["sections"]:
        heading(y, section["title"])
        for item in section["fields"]:
            y += 22
            field(y, DETAIL_X, DETAIL_RIGHT, item)
        y += 32
    heading(y, config["stats"]["title"])
    for row in config["stats"]["rows"]:
        y += 22
        field(y, DETAIL_X, 653, row["left"])
        svg.append(label(672, y, "|", faint))
        field(y, 695, DETAIL_RIGHT, row["right"])

    svg.extend(["</g>", "</svg>"])
    return "\n".join(svg) + "\n"


def main():
    assets = ROOT / "assets"
    art = (assets / "portrait.txt").read_text(encoding="ascii").splitlines()
    config = json.loads((ROOT / "neofetch.json").read_text(encoding="utf-8"))
    stats = public_stats()
    for theme in ("light", "dark"):
        svg = render(art, config, stats, dark=theme == "dark")
        (assets / f"profile-{theme}-66x49.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
