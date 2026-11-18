"""Render the animated profile header in light and dark themes.

The header is a self-contained SVG: no external fonts, images or scripts, so it
animates when GitHub serves it through an <img> tag. Run this after changing
the text or the palette:

    python .github/scripts/render_header.py
"""

import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIDTH, HEIGHT = 1200, 200

THEMES = {
    "dark": {"bg": "#0b1220", "border": "#26324a", "text": "#eef1f5", "soft": "#b9c2d0", "muted": "#94a0b5",
             "point": "#dfe7f5", "warm": "#ff8a50", "accent": "#ff6a2b", "core": "#ffffff", "glow": 0.24, "star": 0.55},
    "light": {"bg": "#eef1f5", "border": "#c9d0db", "text": "#0b1220", "soft": "#2c3546", "muted": "#4d5768",
              "point": "#0b1220", "warm": "#d9480f", "accent": "#ff6a2b", "core": "#0b1220", "glow": 0.2, "star": 0.3},
}

LABEL = "SENIOR SOFTWARE ENGINEER · MICROSOFT · MELBOURNE"
NAME = "Robbie Cronin"

# The ring is drawn as stacked ellipses. Each one is split into a far (top) arc and a
# near (bottom) arc whose dashes slide along the path, which reads as the ring turning.
RX, RY, BAND = 236, 92, 37
ROWS = 7
SPEED = 11.0  # path-length units per second; each half arc is 500 units long


def dashes(rng, period, dots):
    """A dash pattern of round dots whose gaps sum with the dots to exactly `period`."""
    cuts = sorted(rng.uniform(0, period) for _ in range(dots))
    gaps = [b - a for a, b in zip(cuts, cuts[1:] + [cuts[0] + period])]
    return " ".join(f"0.1 {max(gap - 0.1, 0.4):.2f}" for gap in gaps), sum(0.1 + max(gap - 0.1, 0.4) for gap in gaps)


def arc(cy, top):
    if top:
        return f"M{-RX} {cy:.1f}A{RX} {RY} 0 0 1 {RX} {cy:.1f}"
    return f"M{RX} {cy:.1f}A{RX} {RY} 0 0 1 {-RX} {cy:.1f}"


def ring(rng):
    parts, rules = [], []
    for row in range(ROWS):
        cy = -BAND + row * (2 * BAND / (ROWS - 1))
        for kind, dots, width in (("cool", rng.randint(34, 52), 2.1), ("warm", rng.randint(5, 9), 2.6)):
            period = rng.choice([100, 125, 250])
            pattern, total = dashes(rng, period, max(3, dots * period // 250))
            name = f"{kind[0]}{row}"
            rules.append(f".{name}{{stroke-dasharray:{pattern};animation:turn-{name} {total / SPEED:.2f}s linear infinite}}"
                         f"@keyframes turn-{name}{{to{{stroke-dashoffset:{-total:.2f}}}}}")
            for top in (True, False):
                parts.append(f'<path class="{name}" d="{arc(cy, top)}" pathLength="500" fill="none" stroke="url(#{kind})" '
                             f'stroke-width="{width}" stroke-linecap="round" opacity="{0.34 if top else 1}"/>')
    for cy in (-BAND, BAND):
        parts.append(f'<path d="{arc(cy, True)}" fill="none" stroke="url(#cool)" stroke-width="1" opacity="0.28"/>')
        parts.append(f'<path d="{arc(cy, False)}" fill="none" stroke="url(#cool)" stroke-width="1" opacity="0.7"/>')
    return "\n".join(parts), "".join(rules)


def ships(theme):
    orbits = [(318, 150, 14, 34, theme["warm"], False), (392, 118, -9, 52, theme["point"], True), (132, 44, 31, 21, theme["point"], False)]
    parts = []
    for index, (rx, ry, tilt, seconds, color, reverse) in enumerate(orbits):
        path = f"M{-rx} 0A{rx} {ry} 0 0 1 {rx} 0A{rx} {ry} 0 0 1 {-rx} 0"
        parts.append(f'<g transform="rotate({tilt})">')
        parts.append(f'<path d="{path}" fill="none" stroke="{theme["border"]}" stroke-width="1" stroke-dasharray="2 7"/>')
        for length, width, opacity in ((95, 1.1, 0.3), (48, 1.6, 0.55), (0.1, 4.4, 1)):
            parts.append(f'<path class="ship" d="{path}" pathLength="1000" fill="none" stroke="{color}" stroke-width="{width}" '
                         f'stroke-linecap="round" opacity="{opacity}" stroke-dasharray="{length} {1000 - length}" '
                         f'style="--from:{length + index * 310};--to:{length + index * 310 - 1000};animation-duration:{seconds}s'
                         f'{";animation-direction:reverse" if reverse else ""}"/>')
        parts.append("</g>")
    return "\n".join(parts)


def stars(rng, theme):
    parts = []
    for index in range(44):
        x, y, size = rng.uniform(12, WIDTH - 12), rng.uniform(12, HEIGHT - 12), rng.choice([0.7, 0.9, 1.1, 1.5])
        twinkle = f' class="twinkle" style="animation-delay:{rng.uniform(0, 6):.1f}s"' if index % 6 == 0 else ""
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{size}" fill="{theme["point"]}" opacity="{rng.uniform(0.25, 1) * theme["star"]:.2f}"{twinkle}/>')
    return "\n".join(parts)


def render(name):
    theme = THEMES[name]
    rng = random.Random(7)
    ring_paths, ring_rules = ring(rng)
    sans = "'Helvetica Neue', 'Segoe UI', Helvetica, Arial, sans-serif"
    mono = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">{NAME}, software engineer</title>
<desc id="desc">{NAME}. Beside the name, a ring habitat turns slowly around a star while three ships orbit it.</desc>
<defs>
<clipPath id="frame"><rect width="{WIDTH}" height="{HEIGHT}" rx="24"/></clipPath>
<linearGradient id="cool" gradientUnits="userSpaceOnUse" x1="{-RX}" y1="0" x2="{RX}" y2="0"><stop offset="0" stop-color="{theme["point"]}" stop-opacity="0.16"/><stop offset="0.55" stop-color="{theme["point"]}" stop-opacity="0.8"/><stop offset="1" stop-color="{theme["point"]}"/></linearGradient>
<linearGradient id="warm" gradientUnits="userSpaceOnUse" x1="{-RX}" y1="0" x2="{RX}" y2="0"><stop offset="0" stop-color="{theme["warm"]}"/><stop offset="0.5" stop-color="{theme["warm"]}" stop-opacity="0.25"/><stop offset="0.7" stop-color="{theme["warm"]}" stop-opacity="0"/></linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#ffa06e" stop-opacity="{theme["glow"]}"/><stop offset="1" stop-color="#ffa06e" stop-opacity="0"/></radialGradient>
</defs>
<style>
.scene{{animation:arrive 2.4s cubic-bezier(.16,1,.3,1) both;transform-box:fill-box;transform-origin:center}}
.copy>*{{animation:rise 1.1s cubic-bezier(.16,1,.3,1) both}}
.copy>:nth-child(2){{animation-delay:.12s}}
.ship{{stroke-dashoffset:var(--from);animation:fly linear infinite}}
.twinkle{{animation:twinkle 5s ease-in-out infinite}}
@keyframes arrive{{from{{opacity:0;transform:scale(.9)}}}}
@keyframes rise{{from{{opacity:0;transform:translateY(14px)}}}}
@keyframes fly{{to{{stroke-dashoffset:var(--to)}}}}
@keyframes twinkle{{50%{{opacity:.15}}}}
{ring_rules}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<g clip-path="url(#frame)">
<rect width="{WIDTH}" height="{HEIGHT}" fill="{theme["bg"]}"/>
{stars(rng, theme)}
<g transform="translate(992 102) scale(0.58)">
<g class="scene">
<g transform="rotate(-17)">
<circle r="150" fill="url(#glow)"/>
{ships(theme)}
{ring_paths}
<circle r="3.2" fill="{theme["core"]}"/>
</g>
</g>
</g>
<g class="copy">
<text x="50" y="80" fill="{theme["muted"]}" font-family="{mono}" font-size="13" font-weight="500" letter-spacing="2.4">{LABEL}</text>
<text x="47" y="142" fill="{theme["text"]}" font-family="{sans}" font-size="60" font-weight="300" letter-spacing="-2.4">{NAME}</text>
</g>
</g>
<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="23.5" fill="none" stroke="{theme["border"]}"/>
</svg>
'''


if __name__ == "__main__":
    for theme_name in THEMES:
        (ROOT / "assets" / f"header-{theme_name}.svg").write_text(render(theme_name), encoding="utf-8")
    print("Rendered header-dark.svg and header-light.svg.")
