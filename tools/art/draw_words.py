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


DRAWINGS = {f.__name__: f for f in (goat, cow, koala, lion, zebra, wolf, rabbit, turtle, monkey,
                                     pumpkin, vampire, zombie, witch, monster)}


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
