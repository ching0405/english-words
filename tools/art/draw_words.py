#!/usr/bin/env python3
"""Draw the built-in word illustrations as SVG files (style: STYLE_GUIDE.md).

Each drawing is a function that returns SVG elements built with the helpers
below, so every picture shares the same outline, shading and highlight rules.

Usage:  python3 tools/art/draw_words.py            # write all
        python3 tools/art/draw_words.py cat dog    # write some
Output: images/words/<id>.svg
"""
import math, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "images" / "words"

INK = "#2b3a55"      # outline colour
LINE = 10            # main outline width
DETAIL = 7           # inner detail line width
P = {                # shared palette (keep in sync with STYLE_GUIDE.md)
    "red": "#ff5a5f", "orange": "#ff9f43", "yellow": "#ffd43b", "green": "#5ccf6a",
    "blue": "#4fb0ff", "purple": "#9b6bff", "pink": "#ff8fc0", "brown": "#c8875a",
    "dark_brown": "#8d5a3b", "tan": "#f2c27b", "cream": "#fff3dc", "white": "#ffffff",
    "sky": "#c4e8ff", "blush": "#ff8fab", "gray": "#d9dde8", "tyre": "#3a3f58",
}

_n = 0


def _uid():
    global _n
    _n += 1
    return f"s{_n}"


def _el(tag, **a):
    attrs = " ".join(f'{k.rstrip("_").replace("_", "-")}="{v}"' for k, v in a.items())
    return f"<{tag} {attrs}/>"


def _shade(hex_color, amount=0.22):
    """Mix a colour toward the ink colour for the lower-right shade."""
    c = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    k = [int(INK[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(a + (b - a) * amount):02x}" for a, b in zip(c, k))


def shape(tag, color, shade=True, line=LINE, off=(-12, -14), **a):
    """Filled shape with a crescent shade on the lower right and an outline."""
    out = []
    if shade:
        cid = _uid()
        out.append(f'<clipPath id="{cid}">{_el(tag, **a)}</clipPath>')
        moved = dict(a)
        moved["transform"] = f"translate({off[0]} {off[1]})" + (" " + a["transform"] if "transform" in a else "")
        out.append(f'<g clip-path="url(#{cid})">{_el(tag, fill=_shade(color), **a)}{_el(tag, fill=color, **moved)}</g>')
    else:
        out.append(_el(tag, fill=color, **a))
    if line:
        out.append(_el(tag, fill="none", stroke=INK, stroke_width=line, stroke_linejoin="round", **a))
    return "".join(out)


def clipped(clip_tag, clip_attrs, *inner):
    cid = _uid()
    return f'<clipPath id="{cid}">{_el(clip_tag, **clip_attrs)}</clipPath><g clip-path="url(#{cid})">{"".join(inner)}</g>'


def fill(tag, color, **a):
    return _el(tag, fill=color, **a)


def line(d, w=DETAIL, color=INK, **a):
    return _el("path", d=d, fill="none", stroke=color, stroke_width=w, stroke_linecap="round", stroke_linejoin="round", **a)


def tube(d, color, w=12):
    """A thick coloured line with an ink outline (stems, strings)."""
    return line(d, w + 2 * LINE - 4, INK) + line(d, w, color)


def hl(cx, cy, rx, ry, rot=0, op=0.7):
    """White highlight on the upper left."""
    return _el("ellipse", cx=cx, cy=cy, rx=rx, ry=ry, fill="#fff", opacity=op, transform=f"rotate({rot} {cx} {cy})")


def ground(cx=256, cy=456, rx=150):
    return _el("ellipse", cx=cx, cy=cy, rx=rx, ry=16, fill=INK, opacity=0.12)


def eye(cx, cy, r=15):
    return fill("ellipse", INK, cx=cx, cy=cy, rx=r, ry=r * 1.3) + fill("circle", "#fff", cx=cx + r * 0.35, cy=cy - r * 0.5, r=r * 0.38)


def cheek(cx, cy):
    return fill("ellipse", P["blush"], cx=cx, cy=cy, rx=20, ry=12, opacity=0.65)


def mirror(x):
    return 512 - x


# ---------------------------------------------------------------- shared
def blob_path(cx=256, cy=262, r=150, lobes=6, amp=26, wobble=10, squash=0.92):
    """Smooth wavy closed blob (lion mane, monster fur)."""
    pts = []
    n = 72
    for i in range(n):
        t = 2 * math.pi * i / n
        rr = r + amp * math.sin(lobes * t + 0.4) + wobble * math.sin(11 * t + 1.3)
        pts.append((cx + rr * math.cos(t), cy + rr * squash * math.sin(t)))
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(n):  # Catmull-Rom to cubic Bezier for a smooth closed blob
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d + " Z"




def sit_body(color, belly, paw, cx=256, cy=376, rx=106, ry=82):
    """Sitting body with belly patch and two front paws (front-facing animals)."""
    o = shape("ellipse", color, cx=cx, cy=cy, rx=rx, ry=ry)
    if belly:
        o += fill("ellipse", belly, cx=cx, cy=cy + 18, rx=rx * 0.54, ry=ry * 0.6)
    for x in (cx - 50, cx + 50):
        o += shape("ellipse", paw, shade=False, cx=x, cy=448, rx=36, ry=20)
    return o


def face(y=212, dx=56, cx=256, r=15, cheeks=True):
    o = eye(cx - dx, y, r) + eye(cx + dx, y, r)
    if cheeks:
        o += cheek(cx - dx - 26, y + 44) + cheek(cx + dx + 26, y + 44)
    return o


def smile(cx, cy, w=24, depth=18):
    return line(f"M{cx - w} {cy} Q{cx} {cy + depth} {cx + w} {cy}", 7)


# ---------------------------------------------------------------- animals
def goat():
    fur, horn = "#f6f1e7", "#c9a77c"
    o = ground()
    o += sit_body(fur, None, "#8a93a6")
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("path", horn, d=f"M{X(206)} 126 Q{X(190)} 52 {X(122)} 62 Q{X(176)} 82 {X(176)} 140 Z")
        o += shape("ellipse", fur, cx=X(132), cy=196, rx=58, ry=24, transform=f"rotate({20 * s} {X(132)} 196)")
        o += fill("ellipse", P["pink"], cx=X(126), cy=198, rx=34, ry=10, transform=f"rotate({20 * s} {X(126)} 198)")
    o += shape("ellipse", fur, cx=256, cy=212, rx=110, ry=118)
    o += shape("ellipse", "#ffe1d9", shade=False, line=0, cx=256, cy=286, rx=66, ry=42)
    o += shape("path", "#e6dccb", line=7, d="M230 322 Q256 400 282 322 Z")
    o += hl(196, 138, 24, 12, -35)
    o += face(206, 52)
    o += fill("ellipse", INK, cx=240, cy=276, rx=6, ry=8) + fill("ellipse", INK, cx=272, cy=276, rx=6, ry=8)
    o += smile(256, 298, 20, 14)
    return o


def cow():
    W, spot, pink = P["white"], "#3a3f58", "#ffc4d0"
    o = ground()
    o += sit_body(W, None, spot)
    o += clipped("ellipse", dict(cx=256, cy=376, rx=106, ry=82), fill("ellipse", spot, cx=330, cy=350, rx=44, ry=34), fill("ellipse", spot, cx=180, cy=400, rx=30, ry=24))
    o += _el("ellipse", cx=256, cy=376, rx=106, ry=82, fill="none", stroke=INK, stroke_width=LINE)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("path", P["cream"], d=f"M{X(176)} 122 Q{X(150)} 72 {X(172)} 52 Q{X(190)} 92 {X(214)} 108 Z")
        o += shape("ellipse", W, cx=X(118), cy=186, rx=50, ry=24, transform=f"rotate({-20 * s} {X(118)} 186)")
        o += fill("ellipse", pink, cx=X(112), cy=186, rx=30, ry=11, transform=f"rotate({-20 * s} {X(112)} 186)")
    o += shape("ellipse", W, cx=256, cy=206, rx=132, ry=110)
    o += clipped("ellipse", dict(cx=256, cy=206, rx=132, ry=110), fill("ellipse", spot, cx=336, cy=150, rx=52, ry=40))
    o += _el("ellipse", cx=256, cy=206, rx=132, ry=110, fill="none", stroke=INK, stroke_width=LINE)
    o += shape("ellipse", pink, shade=False, cx=256, cy=270, rx=92, ry=52)
    o += fill("ellipse", "#e98aa0", cx=226, cy=264, rx=10, ry=14) + fill("ellipse", "#e98aa0", cx=286, cy=264, rx=10, ry=14)
    o += smile(256, 292, 24, 12)
    o += face(196, 58, cheeks=False)
    o += shape("circle", P["yellow"], line=7, cx=256, cy=340, r=20) + fill("circle", INK, cx=256, cy=348, r=5)
    o += hl(178, 150, 24, 12, -35)
    return o


def koala():
    g, lt = "#a9b3c4", "#eef1f6"
    o = ground()
    o += sit_body(g, lt, lt)
    for x in (134, 378):
        o += shape("circle", g, cx=x, cy=150, r=64)
        o += fill("circle", "#f6dbe3", cx=x, cy=154, r=34)
    o += shape("ellipse", g, cx=256, cy=222, rx=132, ry=110)
    o += hl(184, 154, 24, 12, -35)
    o += face(214, 70)
    o += fill("ellipse", INK, cx=256, cy=238, rx=30, ry=40) + hl(246, 220, 8, 12, 0, .6)
    o += smile(256, 292, 16, 10)
    return o


def lion():
    mane, fur = "#e8873a", "#ffcf6b"
    o = ground()
    o += line("M330 410 Q420 420 420 340", 12)
    o += line("M330 410 Q420 420 420 340", 4, fur)
    o += shape("path", mane, d=blob_path(420, 330, 26, 5, 6, 2, 1))
    o += sit_body(fur, P["cream"], fur, ry=80)
    o += shape("path", mane, d=blob_path(256, 214, 148, 11, 18, 0, 0.98))
    for x in (178, 334):
        o += shape("circle", fur, cx=x, cy=134, r=30) + fill("circle", "#f5a35a", cx=x, cy=136, r=14)
    o += shape("circle", fur, cx=256, cy=222, r=104)
    o += hl(196, 168, 22, 11, -35)
    o += face(208, 44, r=14)
    o += shape("ellipse", P["cream"], shade=False, line=0, cx=256, cy=268, rx=56, ry=36)
    o += shape("path", P["dark_brown"], line=5, d="M238 246 L274 246 Q268 264 256 266 Q244 264 238 246 Z")
    o += line("M256 266 Q256 282 238 284 M256 266 Q256 282 274 284", 6)
    return o


def zebra():
    W, mz = P["white"], "#8a93a6"
    stripe = lambda d: line(d, 14)
    o = ground()
    body = dict(cx=256, cy=380, rx=100, ry=78)
    o += shape("ellipse", W, **body)
    o += clipped("ellipse", body, stripe("M140 340 Q188 350 206 334"), stripe("M146 392 Q194 404 214 386"), stripe("M372 340 Q324 350 306 334"), stripe("M366 392 Q318 404 298 386"), stripe("M226 316 Q256 336 286 316"))
    o += _el("ellipse", **body, fill="none", stroke=INK, stroke_width=LINE)
    for x in (206, 306):
        o += shape("ellipse", INK, shade=False, cx=x, cy=448, rx=36, ry=20)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("path", W, d=f"M{X(204)} 112 Q{X(160)} 70 {X(168)} 30 Q{X(214)} 52 {X(232)} 102 Z")
        o += fill("path", P["pink"], d=f"M{X(204)} 100 Q{X(178)} 76 {X(178)} 50 Q{X(206)} 66 {X(218)} 96 Z")
    o += shape("path", INK, line=0, d="M220 96 L232 52 L246 86 L258 46 L270 86 L284 54 L294 96 Z")
    head = dict(cx=256, cy=196, rx=96, ry=126)
    o += shape("ellipse", W, **head)
    o += clipped("ellipse", head,
                 stripe("M206 92 Q256 128 306 92"), stripe("M216 128 Q256 150 296 128"),
                 stripe("M160 150 Q190 160 200 152"), stripe("M352 150 Q322 160 312 152"),
                 stripe("M160 236 Q186 244 196 234"), stripe("M352 236 Q326 244 316 234"),
                 fill("ellipse", mz, cx=256, cy=292, rx=82, ry=56))
    o += _el("ellipse", **head, fill="none", stroke=INK, stroke_width=LINE)
    o += hl(206, 164, 18, 9, -35)
    o += face(196, 50, cheeks=False) + cheek(190, 244) + cheek(322, 244)
    o += fill("ellipse", INK, cx=232, cy=286, rx=8, ry=10) + fill("ellipse", INK, cx=280, cy=286, rx=8, ry=10)
    o += smile(256, 302, 22, 12)
    return o


def wolf():
    g, lt = "#9aa7bd", "#eef1f6"
    o = ground()
    o += shape("circle", P["yellow"], cx=420, cy=90, r=40) + hl(406, 76, 10, 6, -30, .6)
    o += shape("path", g, d="M340 420 Q450 410 440 300 Q470 360 440 420 Q410 450 340 440 Z")
    o += fill("path", lt, d="M440 300 Q470 360 452 400 Q440 360 440 300 Z")
    o += sit_body(g, lt, lt)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("path", g, d=f"M{X(150)} 170 L{X(156)} 56 Q{X(160)} 46 {X(170)} 52 L{X(240)} 120 Z")
        o += fill("path", "#f6dbe3", d=f"M{X(166)} 150 L{X(168)} 82 L{X(214)} 126 Z")
    o += shape("path", g, d="M256 96 C356 96 392 160 392 210 L420 250 L386 262 C374 300 320 326 256 326 C192 326 138 300 126 262 L92 250 L120 210 C120 160 156 96 256 96 Z")
    o += hl(184, 150, 24, 12, -35)
    o += shape("path", lt, shade=False, line=0, d="M256 196 C300 196 330 240 330 270 C330 306 290 318 256 318 C222 318 182 306 182 270 C182 240 212 196 256 196 Z")
    o += face(200, 56)
    o += fill("ellipse", INK, cx=256, cy=252, rx=24, ry=16) + hl(248, 247, 8, 4)
    o += line("M256 266 v12 M256 278 Q240 294 226 282 M256 278 Q272 294 286 282", 6)
    return o


def turtle():
    skin, shell, lt = "#9be07a", "#4fae54", "#8fd77a"
    o = ground(256, 452, 170)
    o += shape("path", skin, d="M88 330 L54 314 L80 300 Z")
    for x in (130, 330):
        o += shape("ellipse", skin, cx=x, cy=380, rx=36, ry=40)
    o += shape("path", skin, d="M350 300 Q380 250 420 236 L440 300 Q400 330 360 336 Z")
    o += shape("ellipse", skin, cx=420, cy=236, rx=56, ry=50)
    o += hl(402, 210, 14, 8, -30)
    o += eye(436, 226, 12) + cheek(432, 264)
    o += line("M440 252 Q452 262 464 250", 6)
    dome = "M80 340 Q86 140 236 136 Q386 140 392 340 Z"
    o += shape("path", shell, d=dome)
    o += clipped("path", dict(d=dome),
                 shape("path", lt, shade=False, line=6, d="M190 210 L282 210 L310 270 L282 330 L190 330 L162 270 Z"),
                 shape("path", lt, shade=False, line=6, d="M110 250 L150 250 L162 270 L150 330 L96 330 Z"),
                 shape("path", lt, shade=False, line=6, d="M322 250 L362 250 L378 330 L322 330 L310 270 Z"),
                 shape("path", lt, shade=False, line=6, d="M190 160 L282 160 L282 196 L190 196 Z"))
    o += _el("path", d=dome, fill="none", stroke=INK, stroke_width=LINE, stroke_linejoin="round")
    o += hl(150, 200, 14, 34, 35)
    o += shape("rect", "#e9c46a", x=66, y=328, width=340, height=34, rx=17)
    return o


# ---------------------------------------------------------------- halloween
def pumpkin():
    c = P["orange"]
    o = ground(256, 456, 170)
    o += line("M262 168 Q300 120 330 136 Q350 150 334 166", 7, P["green"])
    o += shape("path", P["green"], d="M276 150 Q330 104 380 130 Q336 176 276 150 Z")
    o += tube("M250 176 Q246 130 266 100", "#5d8a3a", 18)
    for cx, rx in ((160, 100), (352, 100)):
        o += shape("ellipse", c, cx=cx, cy=306, rx=rx, ry=138)
    o += shape("ellipse", c, cx=256, cy=304, rx=112, ry=146)
    o += hl(196, 220, 16, 36, 15)
    dark = "#6b3a12"
    o += shape("path", dark, shade=False, line=5, d="M188 270 L214 226 L240 270 Z")
    o += shape("path", dark, shade=False, line=5, d="M272 270 L298 226 L324 270 Z")
    o += fill("circle", "#fff", cx=212, cy=252, r=6) + fill("circle", "#fff", cx=296, cy=252, r=6)
    o += shape("path", dark, shade=False, line=5, d="M184 306 Q256 330 328 306 Q316 376 256 378 Q196 376 184 306 Z")
    o += shape("rect", c, shade=False, line=5, x=242, y=308, width=28, height=26, rx=4)
    o += cheek(160, 308) + cheek(352, 308)
    return o


def vampire():
    skin, hair, cape, lining = "#ede6ff", "#3b3355", "#7c4ddb", P["red"]
    o = ground()
    o += shape("path", cape, d="M160 296 Q120 390 96 450 L416 450 Q392 390 352 296 Z")
    o += shape("path", lining, d="M196 306 L88 176 Q104 286 150 336 Z")
    o += shape("path", lining, d="M316 306 L424 176 Q408 286 362 336 Z")
    o += shape("path", P["white"], shade=False, d="M206 300 L256 444 L306 300 Z")
    o += shape("path", lining, line=6, d="M256 330 L226 314 L226 346 Z M256 330 L286 314 L286 346 Z")
    o += shape("circle", lining, shade=False, line=6, cx=256, cy=330, r=10)
    o += shape("ellipse", skin, cx=256, cy=208, rx=122, ry=112)
    o += shape("path", hair, d="M134 210 Q124 96 256 92 Q388 96 378 210 Q350 150 256 176 Q162 150 134 210 Z")
    o += hl(196, 128, 22, 10, -25, .35)
    o += face(222, 54)
    o += fill("path", "#c0404a", d="M224 262 Q256 296 288 262 Z") + line("M224 262 Q256 296 288 262 Z", 6)
    o += shape("path", "#fff", shade=False, line=4, d="M236 264 L242 280 L248 264 Z")
    o += shape("path", "#fff", shade=False, line=4, d="M264 264 L270 280 L276 264 Z")
    return o


def zombie():
    skin, shirt, pants = "#a8e6a1", P["blue"], "#9b6bff"
    o = ground(256, 456, 140)
    for x in (206, 290):
        o += shape("ellipse", INK, shade=False, cx=x, cy=446, rx=36, ry=16)
    o += shape("path", pants, d="M178 380 L334 380 L330 440 L264 440 L256 404 L248 440 L182 440 Z")
    o += shape("rect", shirt, x=272, y=332, width=140, height=36, rx=18)
    o += shape("circle", skin, cx=416, cy=350, r=24)
    o += shape("path", shirt, d="M176 286 L336 286 L342 396 L318 384 L298 400 L278 384 L256 400 L234 384 L214 400 L194 384 L170 396 Z")
    o += shape("rect", shirt, x=288, y=288, width=150, height=36, rx=18)
    o += shape("circle", skin, cx=442, cy=306, r=24)
    o += shape("path", "#8d5a3b", d="M168 132 L176 84 L200 118 L218 70 L238 112 L262 66 L278 112 L304 78 L310 132 Z")
    o += shape("ellipse", skin, cx=242, cy=196, rx=118, ry=104)
    o += hl(178, 134, 22, 11, -35)
    o += shape("rect", "#ffd8a8", shade=False, line=5, x=262, y=114, width=70, height=26, rx=10, transform="rotate(-20 297 127)")
    o += fill("circle", "#e0b07c", cx=290, cy=128, r=3) + fill("circle", "#e0b07c", cx=304, cy=124, r=3)
    o += eye(192, 200, 17) + eye(290, 204, 12)
    o += line("M170 166 L210 174 M274 176 L306 170", 6)
    o += cheek(162, 240) + cheek(318, 240)
    o += line("M206 252 Q242 276 280 252", 7)
    o += shape("rect", "#fff", shade=False, line=4, x=232, y=258, width=16, height=14, rx=3)
    o += line("M146 196 l14 0 M153 189 l0 14", 4)
    return o


def witch():
    skin, hat, hair = "#ffe0c7", "#7c4ddb", "#ff9f43"
    o = ground()
    o += tube("M110 452 L410 300", "#a9744f", 12)
    o += shape("path", P["yellow"], d="M78 452 L120 404 L150 452 Z")
    o += shape("path", hat, d="M176 316 L336 316 L376 446 L136 446 Z")
    o += shape("path", P["white"], shade=False, line=6, d="M210 316 L256 352 L302 316 Z")
    for x in (156, 356):
        o += shape("ellipse", hair, cx=x, cy=262, rx=40, ry=64)
    o += shape("ellipse", skin, cx=256, cy=248, rx=106, ry=96)
    o += shape("path", hair, d="M150 220 Q160 160 256 158 Q352 160 362 220 Q330 196 300 210 Q280 186 256 206 Q232 186 212 210 Q182 196 150 220 Z")
    o += face(250, 46, r=14)
    o += smile(256, 288, 22, 16)
    o += shape("path", hat, d="M176 176 L242 58 Q258 28 302 42 Q264 56 266 86 L336 176 Z")
    o += shape("ellipse", hat, cx=256, cy=180, rx=152, ry=30)
    o += shape("path", P["orange"], shade=False, line=6, d="M188 160 L324 160 L330 178 L182 178 Z")
    o += hl(220, 120, 8, 26, 30, .5)
    for cx, cy, r in ((400, 120, 18), (100, 140, 13), (420, 230, 11)):
        pts = " L".join(f"{cx + (r if k % 2 == 0 else r * .45) * math.cos(-math.pi / 2 + k * math.pi / 5):.1f} {cy + (r if k % 2 == 0 else r * .45) * math.sin(-math.pi / 2 + k * math.pi / 5):.1f}" for k in range(10))
        o += shape("path", P["yellow"], shade=False, line=5, d="M" + pts + " Z")
    return o


def monster():
    fur = "#5fd3c6"
    o = ground()
    for x in (196, 316):
        o += shape("ellipse", fur, cx=x, cy=440, rx=40, ry=22)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("path", P["yellow"], d=f"M{X(178)} 130 Q{X(150)} 70 {X(176)} 50 Q{X(196)} 90 {X(214)} 118 Z")
        o += shape("ellipse", fur, cx=X(96), cy=300, rx=26, ry=50, transform=f"rotate({30 * s} {X(96)} 300)")
    o += shape("path", fur, d=blob_path(256, 270, 160, 14, 8, 3, 1.02))
    o += clipped("path", dict(d=blob_path(256, 270, 160, 14, 8, 3, 1.02)), fill("ellipse", "#c8f3ee", cx=256, cy=360, rx=90, ry=64))
    o += hl(176, 168, 24, 12, -35)
    o += shape("circle", P["white"], shade=False, cx=256, cy=220, r=58)
    o += fill("circle", INK, cx=266, cy=228, r=30) + fill("circle", "#fff", cx=278, cy=214, r=10)
    o += cheek(176, 296) + cheek(336, 296)
    o += shape("path", "#c0404a", shade=False, line=7, d="M196 300 Q256 360 316 300 Z")
    o += shape("path", "#fff", shade=False, line=4, d="M224 304 L234 322 L244 304 Z")
    o += shape("path", "#fff", shade=False, line=4, d="M268 304 L278 322 L288 304 Z")
    return o


def rabbit():
    W = P["white"]
    o = ground()
    o += shape("circle", W, cx=352, cy=400, r=28)
    for cx, rot in ((204, -10), (308, 10)):
        o += shape("ellipse", W, cx=cx, cy=128, rx=38, ry=84, transform=f"rotate({rot} {cx} 128)")
        o += fill("ellipse", P["pink"], cx=cx, cy=136, rx=17, ry=60, transform=f"rotate({rot} {cx} 136)")
    o += shape("ellipse", W, cx=256, cy=388, rx=100, ry=76)
    for x in (204, 308):
        o += shape("ellipse", W, shade=False, cx=x, cy=450, rx=40, ry=18)
    o += shape("ellipse", W, cx=256, cy=248, rx=130, ry=106)
    o += eye(208, 240) + eye(304, 240) + cheek(182, 282) + cheek(330, 282)
    o += shape("path", P["pink"], shade=False, line=5, d="M244 270 Q256 262 268 270 Q262 282 256 282 Q250 282 244 270 Z")
    o += shape("rect", W, shade=False, line=5, x=246, y=292, width=20, height=18, rx=4)
    o += line("M256 282 Q256 294 238 296 M256 282 Q256 294 274 296", 6)
    return o



def monkey():
    fur, lt = "#b07a4f", "#f6d7b0"
    o = ground()
    o += tube("M344 418 Q446 418 438 330 Q432 272 386 284 Q356 296 378 322", fur, 16)
    o += sit_body(fur, lt, lt)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("circle", fur, cx=X(132), cy=226, r=46)
        o += fill("circle", lt, cx=X(134), cy=228, r=26)
    o += shape("ellipse", fur, cx=256, cy=214, rx=118, ry=112)
    o += shape("path", fur, line=0, shade=False, d="M228 106 Q240 78 262 92 Q270 72 290 84 Q276 96 274 112 Z")
    o += line("M232 108 Q242 84 262 96 Q270 78 288 86", 6)
    o += hl(182, 150, 22, 11, -35)
    mask = ("M256 176 C238 138 162 146 166 212 C168 240 180 254 188 266 C184 318 220 334 256 334 "
            "C292 334 328 318 324 266 C332 254 344 240 346 212 C350 146 274 138 256 176 Z")
    o += shape("path", lt, shade=False, line=6, d=mask)
    o += face(214, 34, r=14, cheeks=False) + cheek(188, 280) + cheek(324, 280)
    o += fill("ellipse", INK, cx=246, cy=262, rx=6, ry=8) + fill("ellipse", INK, cx=266, cy=262, rx=6, ry=8)
    o += smile(256, 288, 30, 22)
    return o


def cat():
    fur, lt, stripe = "#ffb054", "#fff0d9", "#e07b24"
    o = ground()
    o += tube("M340 424 Q440 430 436 340 Q432 300 400 304", fur, 22)
    o += sit_body(fur, lt, lt)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("path", fur, d=f"M{X(150)} 190 L{X(160)} 70 Q{X(166)} 58 {X(178)} 66 L{X(250)} 128 Z")
        o += fill("path", P["pink"], d=f"M{X(168)} 160 L{X(172)} 92 L{X(222)} 134 Z")
    head = dict(cx=256, cy=222, rx=128, ry=108)
    o += shape("ellipse", fur, **head)
    o += clipped("ellipse", head, line("M232 118 L236 150 M256 114 L256 152 M280 118 L276 150", 9, stripe))
    o += _el("ellipse", **head, fill="none", stroke=INK, stroke_width=LINE)
    o += hl(180, 168, 22, 11, -35)
    o += shape("ellipse", lt, shade=False, line=0, cx=256, cy=270, rx=62, ry=40)
    o += face(214, 56)
    o += shape("path", P["pink"], shade=False, line=5, d="M242 254 L270 254 Q264 268 256 270 Q248 268 242 254 Z")
    o += line("M256 270 Q256 284 238 286 M256 270 Q256 284 274 286", 6)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += line(f"M{X(200)} 266 L{X(130)} 256 M{X(200)} 280 L{X(132)} 284", 5)
    return o


def dog():
    fur, lt, ear = "#e9b77a", "#fff3dc", "#8d5a3b"
    o = ground()
    o += tube("M342 410 Q420 400 420 320", fur, 22)
    o += sit_body(fur, lt, lt)
    o += shape("circle", P["red"], line=7, cx=256, cy=318, r=18) + fill("circle", P["yellow"], cx=256, cy=318, r=7)
    head = dict(cx=256, cy=206, rx=118, ry=108)
    o += shape("ellipse", fur, **head)
    o += clipped("ellipse", head, fill("ellipse", ear, cx=316, cy=184, rx=46, ry=40))
    o += _el("ellipse", **head, fill="none", stroke=INK, stroke_width=LINE)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("path", ear, d=f"M{X(170)} 128 Q{X(110)} 120 {X(100)} 200 Q{X(94)} 270 {X(132)} 284 Q{X(162)} 290 {X(170)} 240 Z")
    o += hl(196, 140, 22, 11, -35)
    o += shape("ellipse", lt, shade=False, line=0, cx=256, cy=262, rx=66, ry=44)
    o += face(196, 50, cheeks=False) + cheek(184, 256) + cheek(328, 256)
    o += fill("ellipse", INK, cx=256, cy=244, rx=26, ry=18) + hl(248, 238, 8, 4)
    o += line("M256 262 v10 M256 272 Q240 288 226 276 M256 272 Q272 288 286 276", 6)
    o += shape("path", P["pink"], shade=False, line=5, d="M244 282 L268 282 L268 300 Q256 316 244 300 Z")
    return o


def elephant():
    g, lt = "#a6b4cf", "#f6c7d4"
    o = ground()
    o += sit_body(g, None, "#c8d1e3", rx=112)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("ellipse", g, cx=X(122), cy=206, rx=84, ry=100, transform=f"rotate({-12 * s} {X(122)} 206)")
        o += fill("ellipse", lt, cx=X(128), cy=210, rx=52, ry=70, transform=f"rotate({-12 * s} {X(128)} 210)")
    o += shape("ellipse", g, cx=256, cy=204, rx=110, ry=104)
    o += hl(204, 140, 22, 11, -35)
    o += face(184, 52, r=14, cheeks=False) + cheek(192, 226) + cheek(320, 226)
    # Smile on both sides of the trunk, then the trunk curling up at the tip.
    o += line("M190 254 Q208 276 230 266", 7) + line("M282 266 Q304 276 322 254", 7)
    o += tube("M256 222 Q254 300 266 330 Q282 362 314 352 Q336 344 328 320", g, 32)
    o += line("M244 276 h22 M247 302 h22", 5)
    return o


def penguin():
    body, belly, beak = "#3a4668", P["white"], P["orange"]
    o = ground()
    for x in (206, 306):
        o += shape("ellipse", beak, cx=x, cy=446, rx=40, ry=18)
    for s in (1, -1):
        X = (lambda x: x) if s == 1 else mirror
        o += shape("ellipse", body, cx=X(136), cy=318, rx=30, ry=78, transform=f"rotate({24 * s} {X(136)} 318)")
    outer = dict(cx=256, cy=270, rx=130, ry=180)
    o += shape("ellipse", body, **outer)
    o += clipped("ellipse", outer, fill("path", belly, d="M256 160 C330 120 376 190 360 250 C380 330 340 440 256 440 C172 440 132 330 152 250 C136 190 182 120 256 160 Z"))
    o += _el("ellipse", **outer, fill="none", stroke=INK, stroke_width=LINE)
    o += hl(190, 140, 22, 11, -35, .4)
    o += face(208, 48, r=15)
    o += smile(256, 290, 22, 12)
    o += shape("path", beak, shade=False, line=6, d="M228 236 L284 236 L256 270 Z")
    return o


def duck():
    y, bill = P["yellow"], P["orange"]
    o = _el("ellipse", cx=256, cy=430, rx=200, ry=36, fill=P["sky"])
    o += line("M90 432 Q120 420 150 432 M362 432 Q392 420 422 432", 6, P["blue"])
    o += shape("path", y, d="M96 330 Q110 250 220 270 L330 270 Q400 270 420 230 Q440 300 416 360 Q380 430 256 430 Q120 430 96 330 Z")
    o += shape("path", "#ffc21a", line=7, d="M180 320 Q250 290 320 330 Q270 380 200 360 Z")
    o += shape("circle", y, cx=196, cy=190, r=100)
    o += hl(150, 130, 22, 11, -35)
    o += line("M196 90 Q190 60 214 54 M200 92 Q214 66 236 72", 7)
    o += shape("path", bill, d="M110 196 Q60 196 42 224 Q72 258 134 240 Q148 214 110 196 Z")
    o += line("M50 226 Q90 244 132 226", 6)
    o += eye(168, 170, 16) + cheek(196, 224)
    return o


def fish():
    c, fin = P["orange"], P["yellow"]
    o = ""
    for cx, cy, r in ((420, 120, 18), (448, 70, 11), (400, 60, 8)):
        o += _el("circle", cx=cx, cy=cy, r=r, fill="#e8f6ff", stroke=INK, stroke_width=5)
    o += shape("path", fin, d="M118 256 L40 176 Q30 256 40 336 Z")
    o += shape("path", fin, d="M210 176 Q240 96 330 132 L320 180 Z")
    o += shape("path", fin, d="M230 330 Q250 400 310 380 L300 330 Z")
    body = dict(cx=262, cy=256, rx=168, ry=112)
    o += shape("ellipse", c, **body)
    o += clipped("ellipse", body, line("M220 150 Q190 256 220 362", 26, P["white"]), line("M220 150 Q190 256 220 362", 6, INK, transform="translate(-14 0)"),
                 line("M220 150 Q190 256 220 362", 6, INK, transform="translate(14 0)"))
    o += _el("ellipse", **body, fill="none", stroke=INK, stroke_width=LINE)
    o += hl(300, 186, 26, 12, -20)
    o += eye(350, 232, 18) + cheek(340, 286)
    o += smile(388, 290, 24, 16)
    return o


def shark():
    g, belly = "#6f8fb8", "#f2f6fb"
    o = _el("ellipse", cx=256, cy=452, rx=210, ry=26, fill=P["sky"])
    o += shape("path", g, d="M232 170 Q250 60 330 66 Q300 120 300 176 Z")
    o += shape("path", g, d="M92 250 L28 160 Q60 260 36 350 Z")
    o += shape("path", g, d="M240 330 Q236 400 290 410 Q300 370 300 330 Z")
    body = "M80 256 C120 160 260 150 360 168 C430 180 480 220 488 262 C480 310 420 350 330 356 C220 364 120 340 80 256 Z"
    o += shape("path", g, d=body)
    o += clipped("path", dict(d=body), fill("path", belly, d="M100 280 C200 300 330 300 500 262 L500 400 L80 400 Z"))
    o += _el("path", d=body, fill="none", stroke=INK, stroke_width=LINE, stroke_linejoin="round")
    o += hl(250, 196, 40, 10, -6)
    o += line("M300 226 v40 M318 222 v40 M336 222 v38", 5)
    o += eye(398, 222, 15) + cheek(420, 262)
    o += smile(408, 296, 30, 16)
    return o



# ---------------------------------------------------------------- numbers
# The numeral on top (drawn as thick strokes, no font) and that many apples to
# count below it. Digit strokes live in a 100 x 160 box.
DIGITS = {
    "0": "M50 0 C112 0 112 160 50 160 C-12 160 -12 0 50 0 Z",
    "1": "M22 34 L58 0 L58 160",
    "2": "M8 40 C8 -12 94 -12 94 42 C94 86 34 112 6 160 L96 160",
    "3": "M10 22 C40 -10 94 0 90 40 C88 70 62 78 44 78 C72 78 98 92 96 120 C92 166 30 172 4 140",
    "4": "M72 160 L72 0 L4 108 L100 108",
    "5": "M90 2 L22 2 L14 72 C42 56 96 62 96 110 C96 166 30 170 4 140",
    "6": "M86 12 C40 -16 6 40 8 102 C10 166 96 166 96 112 C96 60 24 60 10 104",
    "7": "M4 2 L96 2 L40 160",
    "8": "M50 78 C8 78 8 0 50 0 C92 0 92 78 50 78 C-2 78 -2 160 50 160 C102 160 102 78 50 78 Z",
    "9": "M90 56 C88 102 10 102 10 56 C10 4 90 4 90 56 C92 112 72 162 18 154",
}
NUMBER_COLORS = [P["red"], P["orange"], P["yellow"], P["green"], P["blue"], P["purple"], P["pink"], "#5fd3c6", "#ff7b54", "#4f7dff"]


def numeral(text, color, cy=112, h=118):
    k = h / 160
    w = 100 * k * len(text) + 30 * (len(text) - 1)
    o = ""
    for i, ch in enumerate(text):
        x = 256 - w / 2 + i * (100 * k + 30)
        g = f'<g transform="translate({x:.1f} {cy - h / 2:.1f}) scale({k:.3f})">'
        o += g + line(DIGITS[ch], (22 + 2 * LINE) / k, INK) + line(DIGITS[ch], 22 / k, color) + "</g>"
        o += g + line(DIGITS[ch], 6 / k, "#fff", opacity=0.4, transform="translate(-6 -6)") + "</g>"
    return o


def apple(cx, cy, r):
    o = tube(f"M{cx} {cy - r * 0.8} Q{cx + r * 0.05} {cy - r * 1.15} {cx + r * 0.2} {cy - r * 1.3}", P["dark_brown"], max(5, r * 0.16))
    o += shape("path", P["green"], line=6, d=f"M{cx + r * 0.1} {cy - r * 0.95} Q{cx + r * 0.6} {cy - r * 1.45} {cx + r * 1.0} {cy - r * 1.05} Q{cx + r * 0.55} {cy - r * 0.7} {cx + r * 0.1} {cy - r * 0.95} Z", off=(-4, -4))
    d = (f"M{cx} {cy - r * 0.72} C{cx + r * 0.6} {cy - r * 1.05} {cx + r * 1.08} {cy - r * 0.55} {cx + r} {cy + r * 0.1} "
         f"C{cx + r * 0.92} {cy + r * 0.75} {cx + r * 0.45} {cy + r * 1.0} {cx} {cy + r * 0.88} "
         f"C{cx - r * 0.45} {cy + r * 1.0} {cx - r * 0.92} {cy + r * 0.75} {cx - r} {cy + r * 0.1} "
         f"C{cx - r * 1.08} {cy - r * 0.55} {cx - r * 0.6} {cy - r * 1.05} {cx} {cy - r * 0.72} Z")
    o += shape("path", P["red"], line=7, off=(-r * 0.25, -r * 0.3), d=d)
    o += hl(cx - r * 0.45, cy - r * 0.25, r * 0.16, r * 0.3, 25, 0.75)
    return o


def counted(n):
    """n apples under the numeral, in one row up to four, else two rows (the
    longer one on top), sized to stay inside 48-464 and below the numeral."""
    rows = [n] if n <= 4 else [(n + 1) // 2, n // 2]
    top, bottom, gap = 196, 452, 14
    k = rows[0]
    r = min(80, (416 - gap * (k - 1)) / (2 * k), (bottom - top - 20) / (2.6 * len(rows)))
    h = 2.6 * r                                   # stem tip to the bottom of an apple, with air
    y = (top + bottom) / 2 - (len(rows) * h + 20 * (len(rows) - 1)) / 2 + 1.55 * r
    o = ""
    for row in rows:
        x0 = 256 - (row - 1) * (2 * r + gap) / 2
        for i in range(row):
            o += apple(x0 + i * (2 * r + gap), y, r)
        y += h + 20
    return o


def _number(n):
    def draw():
        o = ground(256, 456, 190)
        o += numeral(str(n), NUMBER_COLORS[n - 1])
        o += counted(n)
        return o
    draw.__name__ = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"][n - 1]
    return draw


NUMBERS = [_number(n) for n in range(1, 11)]


# ---------------------------------------------------------------- colors
# One smiling blob of paint in that colour on the same pale disc every time,
# so white and black show up on the white card too. Nothing else in the
# picture: a red apple would make "red" sound like a question about apples.
COLOR_WORDS = {
    "red": "#f2393f", "orange": "#ff8c1a", "yellow": "#ffd43b", "green": "#3cbf4f", "blue": "#2f7fe8",
    "purple": "#8e55e8", "pink": "#ff8fc0", "black": "#2a2a30", "white": "#ffffff", "brown": "#9a5f35",
}
DARK_COLORS = {"black", "brown", "purple", "blue"}   # highlight drawn softer


def paint_blob(name):
    c = COLOR_WORDS[name]
    soft = 0.4 if name in DARK_COLORS else 0.7
    o = _el("circle", cx=256, cy=256, r=212, fill="#e3e7ef")
    o += ground(256, 432, 130)
    body = blob_path(256, 262, 146, 7, 20, 7, 0.9)
    o += shape("path", c, d=body)
    for cx, cy, r in ((116, 132, 22), (402, 112, 16), (420, 380, 20), (96, 352, 12)):
        o += shape("circle", c, off=(-r * 0.3, -r * 0.35), cx=cx, cy=cy, r=r) + hl(cx - r * 0.3, cy - r * 0.3, r * 0.22, r * 0.14, -35, soft)
    o += hl(178, 178, 30, 14, -35, soft)
    for x in (206, 306):           # white eyes with a dark pupil: they show on every colour
        o += _el("ellipse", cx=x, cy=238, rx=26, ry=32, fill="#fff", stroke=INK, stroke_width=6)
        o += eye(x + 4, 244, 13)
    if name not in ("pink", "red"):
        o += cheek(170, 290) + cheek(342, 290)
    o += shape("path", "#c0404a", shade=False, line=7, d="M214 296 Q256 344 298 296 Z")
    return o


def _color(name):
    def draw():
        return paint_blob(name)
    draw.__name__ = name
    return draw


COLORS = [_color(n) for n in COLOR_WORDS]

DRAWINGS = {f.__name__: f for f in (goat, cow, koala, lion, zebra, wolf, rabbit, turtle, monkey,
                                     cat, penguin, elephant, dog, duck, fish, shark,
                                     pumpkin, vampire, zombie, witch, monster, *NUMBERS, *COLORS)}


def svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">\n'
            f'{body}\n</svg>\n')


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names or DRAWINGS:
        global _n
        _n = 0
        (OUT / f"{name}.svg").write_text(svg(DRAWINGS[name]()))
        print("wrote", f"images/words/{name}.svg")


if __name__ == "__main__":
    main(sys.argv[1:])
