#!/usr/bin/env python3
"""
Build a 3D isometric contribution calendar as a self-contained animated SVG.

Reads the public contribution grid straight from github.com (no token, no API
quota) and writes an SVG whose animation is pure CSS, so it works inside a
GitHub README. Private contributions are included only if the account has
Settings > Public profile > Contributions & Activity > "Include private
contributions on my profile" switched on.

    python tools/build_contrib.py B-Soumya assets/contrib.svg
"""
import html
import re
import sys
import urllib.request
from datetime import date

XS, YS = 0.866, 0.30          # dimetric camera, matches the other assets
CELL = 15.0
ZH = 74.0                     # height of a maximum-level column
FLOOR = 3.0                   # so empty days still read as ground, not a hole
W, H = 1200, 418

PALETTE = [(0x1C, 0x24, 0x3A),   # 0  empty
           (0x9D, 0x4D, 0xFF),   # 1
           (0x4D, 0x9D, 0xFF),   # 2
           (0x00, 0xF5, 0xFF),   # 3
           (0x00, 0xD6, 0x8F)]   # 4
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SERIF = "Georgia,'Iowan Old Style','Palatino Linotype',serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def fetch(user):
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")

    days = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"', page)
    if not days:
        flipped = re.findall(r'data-level="(\d)"[^>]*data-date="(\d{4}-\d{2}-\d{2})"', page)
        days = [(d, l) for l, d in flipped]
    if not days:
        raise SystemExit(f"no contribution grid found for {user}")

    counts = {}
    for tip in re.findall(r'<tool-tip[^>]*>([^<]{0,80})</tool-tip>', page):
        t = html.unescape(tip)
        m = re.match(r'\s*(\d+)\s+contribution', t)
        counts[t] = int(m.group(1)) if m else 0

    total = 0
    m = re.search(r'([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year', page)
    if m:
        total = int(m.group(1).replace(",", ""))
    return [(date.fromisoformat(d), int(l)) for d, l in days], total


def shade(rgb, k):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c * k))) for c in rgb)


def build(user, days, total):
    # column = week index, row = weekday (Monday..Sunday as GitHub lays it out)
    first = days[0][0]
    start = first - __import__("datetime").timedelta(days=(first.weekday() + 1) % 7)
    grid = {}
    for d, lvl in days:
        wk = (d - start).days // 7
        wd = (d.weekday() + 1) % 7
        grid[(wk, wd)] = (lvl, d)
    weeks = max(k[0] for k in grid) + 1

    span_u = weeks * CELL
    ox = 92 + 6 * CELL * XS
    oy = 136

    def iso(u, v):
        return (u - v) * XS + ox, (u + v) * YS + oy

    def r2(v):
        return round(v, 1)

    cells, months = [], []
    seen = set()
    order = sorted(grid.items(), key=lambda kv: kv[0][0] + kv[0][1])
    for (wk, wd), (lvl, d) in order:
        u, v = wk * CELL, wd * CELL
        w = CELL * 0.40
        h = FLOOR + (lvl / 4.0) * ZH
        A = iso(u - w, v - w); B = iso(u + w, v - w)
        C = iso(u + w, v + w); D = iso(u - w, v + w)
        up = lambda p: (p[0], p[1] - h)
        rgb = PALETTE[lvl]
        top, rgt, lft = shade(rgb, 1.0), shade(rgb, .62), shade(rgb, .40)
        pts = lambda ps: " ".join(f"{r2(a)},{r2(b)}" for a, b in ps)
        cls = "cl" if lvl else "cl z"
        cells.append(
            f'<g class="{cls}" style="animation-delay:{round((wk + wd) * 0.014, 3)}s">'
            f'<polygon class="fc" points="{pts([B, C, up(C), up(B)])}" fill="{rgt}"/>'
            f'<polygon class="fc" points="{pts([D, C, up(C), up(D)])}" fill="{lft}"/>'
            f'<polygon class="tp" style="--h:{r2(h)}px" points="{pts([up(A), up(B), up(C), up(D)])}" '
            f'fill="{top}"{"" if lvl else " fill-opacity=\'.85\'"}/></g>')
        if d.day <= 7 and wd == 0 and d.month not in seen:
            seen.add(d.month)
            mx, my = iso(u, -CELL * 1.5)
            months.append(f'<text x="{r2(mx)}" y="{r2(my)}">{MONTHS[d.month - 1]}</text>')

    leg = "".join(
        f'<rect x="{1004 + i * 26}" y="384" width="22" height="9" fill="{shade(PALETTE[i], 1.0)}"/>'
        for i in range(5))

    active = sum(1 for _, l in days if l)
    css = """
.cl .tp{animation:pop 1s cubic-bezier(.2,.8,.25,1) backwards;animation-delay:inherit}
.cl .fc{animation:grow 1s cubic-bezier(.2,.8,.25,1) backwards;animation-delay:inherit;
transform-box:fill-box;transform-origin:bottom}
@keyframes pop{from{transform:translateY(var(--h))}to{transform:translateY(0)}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="A 3D isometric calendar of the last year of contributions: {total} in total across {active} active days.">
<title>{user} — the last year in contributions</title>
<defs><linearGradient id="cbg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#070B14"/><stop offset="60%" stop-color="#0A1122"/><stop offset="100%" stop-color="#0D0A1C"/>
</linearGradient><style>{css}</style></defs>
<rect width="{W}" height="{H}" rx="14" fill="url(#cbg)"/>
<text x="60" y="52" font-size="25" fill="#F2F6FF" font-family="{SERIF}">The last year, one column per day</text>
<g font-family="{MONO}" font-size="11.5" fill="#7B8DA8">
<text x="60" y="76">{total} contributions across {active} active days</text></g>
<g font-family="{MONO}" font-size="10" fill="#6C7E9C">{"".join(months)}</g>
{"".join(cells)}
{leg}
<g font-family="{MONO}" font-size="10" fill="#6C7E9C">
<text x="1004" y="376">quiet</text><text x="1134" y="376" text-anchor="end">busy</text></g>
</svg>'''


if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "B-Soumya"
    out = sys.argv[2] if len(sys.argv) > 2 else "assets/contrib.svg"
    days, total = fetch(user)
    svg = build(user, days, total)
    open(out, "w", encoding="utf-8").write(svg)
    print(f"{out}: {len(svg.encode())} bytes, {len(days)} days, {total} contributions")
