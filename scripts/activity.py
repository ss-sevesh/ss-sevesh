"""Generate public GitHub activity artwork; publish only after every fetch succeeds."""
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = "ss-sevesh"
COLORS = ["#182d27", "#0e4429", "#006d32", "#26a641", "#39d353"]
LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]
LABELS = {"PushEvent": "Pushed updates", "ReleaseEvent": "Published a release",
          "CreateEvent": "Created a repository or ref", "IssuesEvent": "Updated an issue",
          "PullRequestEvent": "Updated a pull request"}


def api(endpoint, *args):
    return json.loads(subprocess.check_output(["gh", "api", endpoint, *args], text=True, encoding="utf-8"))


def svg(title, body, height, css=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title">
<title id="title">{escape(title)}</title><style>
text{{font-family:'Segoe UI',Arial,sans-serif;fill:#f3eee5}}.muted{{fill:#a3bdb5}}
{css}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style><rect width="1000" height="{height}" rx="12" fill="#0d1718"/>{body}</svg>'''


def calendar_svg(calendar, stamp):
    cells = []
    weeks = calendar["weeks"]
    if not 1 <= len(weeks) <= 54:
        raise ValueError("Unexpected calendar length")
    for x, week in enumerate(weeks):
        for day in week["contributionDays"]:
            date = datetime.strptime(day["date"], "%Y-%m-%d")
            count = day["contributionCount"]
            if not isinstance(count, int) or count < 0:
                raise ValueError("Invalid contribution count")
            color = COLORS[LEVELS.index(day["contributionLevel"]) ]
            row = (date.weekday() + 1) % 7
            cells.append(f'<rect x="{40+x*17}" y="{98+row*17}" width="13" height="13" rx="3" fill="{color}"><title>{day["date"]}: {count} contributions</title></rect>')
    total = calendar["totalContributions"]
    if not isinstance(total, int) or total < 0:
        raise ValueError("Invalid total")
    body = f'<text x="40" y="42" font-size="24" font-weight="700">THE BUILD HISTORY</text><text x="40" y="72" font-size="15" class="muted">{total} contributions · GitHub calendar snapshot</text>'
    body += ''.join(cells)
    body += '<rect class="sweep" x="40" y="94" width="3" height="126" rx="1" fill="#ffb078" opacity=".65"/>'
    body += f'<text x="40" y="254" font-size="13" class="muted">Updated {escape(stamp)} · Color represents actual contribution level</text>'
    for i, color in enumerate(COLORS):
        body += f'<rect x="{850+i*18}" y="240" width="13" height="13" rx="3" fill="{color}"/>'
    return svg("Real GitHub contribution calendar with a decorative scanning line", body, 280,
               '.sweep{animation:sweep 9s ease-in-out infinite}@keyframes sweep{50%{transform:translateX(899px)}}')


def select_events(events):
    result = []
    for event in events:
        if event.get("public") is not True or event.get("type") not in LABELS:
            continue
        if event.get("actor", {}).get("login", "").lower() != USER:
            continue
        repo = event.get("repo", {}).get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            continue
        if repo == f"{USER}/{USER}" and event.get("payload", {}).get("ref") in ("refs/heads/output", "output"):
            continue
        datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        result.append(event)
    return sorted(result, key=lambda e: e["created_at"], reverse=True)[:5]


def activity_svg(events, stamp):
    body = '<text x="40" y="44" font-size="24" font-weight="700">RECENT PUBLIC ACTIVITY</text><path d="M50 90V350" stroke="#29483e" stroke-width="2"/>'
    links = ["# Recent public activity", "", f"Snapshot: {stamp}. GitHub's events feed can be delayed.", ""]
    for i, event in enumerate(events):
        y = 100 + i * 57
        repo = event["repo"]["name"]
        label = LABELS[event["type"]]
        body += f'<circle class="pulse" style="animation-delay:-{i}s" cx="50" cy="{y}" r="6" fill="#39d353"/>'
        body += f'<text x="74" y="{y+2}" font-size="18">{escape(label)} · {escape(repo)}</text><text x="74" y="{y+23}" font-size="13" class="muted">{escape(event["created_at"].replace("T", " ").replace("Z", " UTC"))}</text>'
        links.append(f'- {event["created_at"][:10]} — {label}: [{repo}](https://github.com/{repo})')
    if not events:
        body += '<text x="74" y="105" font-size="18">No recent public development events.</text>'
        links.append("No recent public development events.")
    body += f'<text x="40" y="405" font-size="13" class="muted">Snapshot {escape(stamp)} · Public events only · Feed may be delayed</text>'
    return svg("Latest public development events", body, 435,
               '.pulse{animation:pulse 3s ease-in-out infinite}@keyframes pulse{50%{opacity:.35}}'), '\n'.join(links)+'\n'


def generate():
    query = 'query { user(login: "ss-sevesh") { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount contributionLevel } } } } } }'
    response = api("graphql", "-f", "query=" + query)
    calendar = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    events = select_events(api(f"users/{USER}/events/public?per_page=100"))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    heatmap = calendar_svg(calendar, stamp)
    activity, links = activity_svg(events, stamp)
    ET.fromstring(heatmap)
    ET.fromstring(activity)
    output = Path("generated")
    output.mkdir(exist_ok=True)
    for name, content in {"contributions.svg": heatmap, "activity.svg": activity, "activity.md": links}.items():
        (output / name).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    generate()
