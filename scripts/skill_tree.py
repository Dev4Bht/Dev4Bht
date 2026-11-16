#!/usr/bin/env python3
"""Render assets/skill-tree.svg from live GitHub stats (stdlib only).

Auth: GITHUB_TOKEN env var, else `gh auth token`.
Usage: python3 scripts/skill_tree.py [login] [output.svg]
"""
import json
import math
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

LOGIN = sys.argv[1] if len(sys.argv) > 1 else "Dev4Bht"
OUT = sys.argv[2] if len(sys.argv) > 2 else "assets/skill-tree.svg"
INITIALS = "P.D"

TIERS = ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND"]
TIER_COLOR = ["#C97B3C", "#CBD5E1", "#E0A93B", "#7DB4F5", "#C4A1FF"]
TIER_POINTS = [10, 25, 50, 100, 200]

QUERY = """query($login:String!){user(login:$login){
  createdAt followers{totalCount} issues{totalCount} pullRequests{totalCount}
  repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC){totalCount nodes{stargazerCount}}
  contributionsCollection{totalCommitContributions
    contributionCalendar{weeks{contributionDays{contributionCount}}}}}}"""


def token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token()}", "User-Agent": "skill-tree"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]["user"]


def fmt(n):
    if isinstance(n, float):
        return f"{n:.1f}"
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def evaluate(value, thresholds):
    """Return (tier index or -1, progress 0..1 to next tier, next threshold or None)."""
    tier = -1
    for i, t in enumerate(thresholds):
        if value >= t:
            tier = i
    if tier == len(thresholds) - 1:
        return tier, 1.0, None
    lo = thresholds[tier] if tier >= 0 else 0
    hi = thresholds[tier + 1]
    return tier, max(0.0, min(1.0, (value - lo) / (hi - lo))), hi


def build_skills(u):
    c = u["contributionsCollection"]
    days = [d["contributionCount"] for w in c["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    best = cur = 0
    for n in days:
        cur = cur + 1 if n > 0 else 0
        best = max(best, cur)
    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    years = (datetime.now(timezone.utc) - created).days / 365.25
    repos = u["repositories"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])
    # (name, icon, value, unit, thresholds), clockwise from the top
    return [
        ("Commit Machine", "💾", c["totalCommitContributions"], "commits", [1, 100, 500, 1000, 4000]),
        ("Merge Master", "🔀", u["pullRequests"]["totalCount"], "pull requests", [1, 10, 100, 500, 1000]),
        ("Unbreakable", "🔥", best, "day streak", [3, 14, 30, 60, 100]),
        ("Veteran", "🎖️", round(years, 1), "years on GitHub", [1, 3, 5, 8, 10]),
        ("Service Architect", "🏗️", repos["totalCount"], "repositories", [1, 10, 20, 35, 50]),
        ("Bug Hunter", "🐛", u["issues"]["totalCount"], "issues opened", [1, 10, 25, 50, 100]),
        ("Crowd Puller", "👥", u["followers"]["totalCount"], "followers", [1, 10, 25, 50, 100]),
        ("Star Collector", "⭐", stars, "stars earned", [1, 10, 25, 50, 100]),
    ]


W, H = 871, 634
CX, CY = 428, 308
POS = [(428, 128), (634, 180), (720, 308), (634, 435), (428, 487), (221, 435), (135, 308), (221, 180)]


def hexpoints(cx, cy, r):
    pts = [(cx + r * math.cos(math.radians(60 * i - 90)), cy + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def node(skill, cx, cy, label_above):
    name, icon, value, unit, th = skill
    tier, prog, nxt = evaluate(value, th)
    locked = tier < 0
    col = "#3A4558" if locked else TIER_COLOR[tier]
    R = 37
    circ = 2 * math.pi * R
    o = []
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R+2}" fill="{col}" fill-opacity="{0.06 if locked else 0.16}"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#243047" stroke-width="4"/>')
    if prog > 0:
        o.append(
            f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{col}" stroke-width="4" stroke-linecap="round" '
            f'stroke-dasharray="{circ*prog:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>'
        )
    o.append(f'<polygon points="{hexpoints(cx, cy, 27)}" fill="#0E1626" stroke="{col}" stroke-width="2"/>')
    o.append(
        f'<text x="{cx}" y="{cy+8}" font-size="22" text-anchor="middle" opacity="{0.35 if locked else 1}">{"🔒" if locked else icon}</text>'
    )
    # label block
    ty = cy - 74 if label_above else cy + 56
    tier_txt = "LOCKED" if locked else TIERS[tier]
    unit_txt = {"issues opened": "issue opened", "pull requests": "pull request", "commits": "commit",
                "followers": "follower", "repositories": "repository", "stars earned": "star earned",
                "day streak": "day streak"}.get(unit, unit) if value == 1 else unit
    status = f"{fmt(value)} {unit_txt}"
    foot = "max tier ✦" if nxt is None else f"→ {TIERS[tier+1].capitalize()} at {fmt(nxt)}"
    tcol = "#64748B" if locked else col
    o.append(f'<text x="{cx}" y="{ty}" font-size="12" font-weight="700" fill="{"#64748B" if locked else "#E2E8F0"}" text-anchor="middle">{name}</text>')
    o.append(
        f'<text x="{cx}" y="{ty+15}" font-size="10" text-anchor="middle" fill="#64748B">'
        f'<tspan font-weight="700" fill="{tcol}">{tier_txt}</tspan> · {status}</text>'
    )
    o.append(f'<text x="{cx}" y="{ty+29}" font-size="9" text-anchor="middle" fill="#475569">{foot}</text>')
    return "\n".join(o), tier


def render(u):
    skills = build_skills(u)
    tiers = []
    body = []
    # connector lines first
    for (x, y), s in zip(POS, skills):
        t, _, _ = evaluate(s[2], s[4])
        col = "#2B3750" if t < 0 else TIER_COLOR[t]
        dash = ' stroke-dasharray="3 5"' if t < 0 else ""
        body.append(f'<line x1="{CX}" y1="{CY}" x2="{x}" y2="{y}" stroke="{col}" stroke-opacity="{0.35 if t>=0 else 0.6}" stroke-width="1.5"{dash}/>')
    for i, ((x, y), s) in enumerate(zip(POS, skills)):
        # labels go below nodes in the lower half and above in the upper-half top node
        label_above = i == 0
        svg, t = node(s, x, y, label_above)
        tiers.append(t)
        body.append(svg)
    unlocked = sum(1 for t in tiers if t >= 0)
    score = sum(TIER_POINTS[t] for t in tiers if t >= 0)
    level = 1 + score // 50
    stars = "".join(
        f'<circle cx="{(i*97)%W}" cy="{(i*53+17)%H}" r="{0.6 + (i%3)*0.4:.1f}" fill="#fff" fill-opacity="{0.15 + (i%4)*0.1:.2f}"/>'
        for i in range(1, 70)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
  <title id="t">{LOGIN} skill tree</title>
  <desc id="d">{unlocked} of 8 GitHub achievements unlocked, gamerscore {score}, level {level}</desc>
  <defs>
    <linearGradient id="frame" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#C97B3C"/><stop offset="0.35" stop-color="#38BDF8"/><stop offset="0.7" stop-color="#7DB4F5"/><stop offset="1" stop-color="#C4A1FF"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#38BDF8" stop-opacity="0.16"/><stop offset="1" stop-color="#38BDF8" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="hexring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#F59E0B"/><stop offset="0.5" stop-color="#38BDF8"/><stop offset="1" stop-color="#C4A1FF"/>
    </linearGradient>
  </defs>
  <g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace">
    <rect x="1.5" y="1.5" width="{W-3}" height="{H-3}" rx="22" fill="#0A1020" stroke="url(#frame)" stroke-width="2" stroke-opacity="0.8"/>
    {stars}
    <circle cx="{CX}" cy="{CY}" r="190" fill="url(#glow)"/>
    <text x="28" y="48" font-size="17" font-weight="700" fill="#E2E8F0" letter-spacing="1">SKILL TREE <tspan fill="#64748B">/</tspan> {LOGIN}</text>
    <text x="28" y="68" font-size="10" fill="#64748B">{unlocked}/8 unlocked · ring = progress to next tier</text>
    <rect x="690" y="34" width="150" height="40" rx="10" fill="#0E2A24" fill-opacity="0.7" stroke="#1F5B49"/>
    <text x="704" y="50" font-size="8" fill="#64748B" letter-spacing="1">GAMERSCORE</text>
    <text x="704" y="67" font-size="16" font-weight="700" fill="#4ADE80">G {score}</text>
    {chr(10).join(body)}
    <polygon points="{hexpoints(CX, CY, 44)}" fill="#0E1626" stroke="url(#hexring)" stroke-width="3"/>
    <text x="{CX}" y="{CY+2}" font-size="22" font-weight="700" fill="#E2E8F0" text-anchor="middle">{INITIALS}</text>
    <text x="{CX}" y="{CY+20}" font-size="10" font-weight="700" fill="#4ADE80" text-anchor="middle">LVL {level}</text>
    <g font-size="10" fill="#64748B">
      <circle cx="30" cy="607" r="4" fill="{TIER_COLOR[0]}"/><text x="40" y="611">Bronze</text>
      <circle cx="104" cy="607" r="4" fill="{TIER_COLOR[1]}"/><text x="114" y="611">Silver</text>
      <circle cx="178" cy="607" r="4" fill="{TIER_COLOR[2]}"/><text x="188" y="611">Gold</text>
      <circle cx="250" cy="607" r="4" fill="{TIER_COLOR[3]}"/><text x="260" y="611">Platinum</text>
      <circle cx="334" cy="607" r="4" fill="{TIER_COLOR[4]}"/><text x="344" y="611">Diamond</text>
    </g>
  </g>
</svg>
"""


if __name__ == "__main__":
    svg = render(fetch())
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT}")
