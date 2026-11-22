# SPDX-License-Identifier: MIT
"""news-image-20261122 v1 — "THE WORLD IN SEVEN FRAMES".

Pure Python stdlib program. Draws a 1024x1024 PNG summing up the world news
of Sunday 22 November 2026 and writes it to /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png). Hand-written PNG encoder (zlib) + 5x7 bitmap
font + pictogram rasterizer. No third-party dependencies, no network.
Deterministic: two runs write byte-identical files.
"""
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# --- palette: dark newsroom video wall -------------------------------------
BG = (11, 22, 38)          # deep ink navy
PANEL = (19, 35, 58)       # panel navy
PANEL_BORDER = (42, 63, 92)
TICKER_BG = (15, 30, 51)
WHITE = (255, 255, 255)
MUTED = (140, 163, 191)
RED = (220, 38, 38)        # breaking red
RED_DARK = (239, 68, 68)
CYAN = (56, 189, 248)
AMBER = (245, 158, 11)
GREEN = (34, 197, 94)
VIOLET = (167, 139, 250)
ORANGE = (251, 146, 60)
GOLD = (234, 179, 8)

# --- 5x7 bitmap font ('#' = ink, '.' = blank) ------------------------------
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    # middle dot (used as separator)
    "·": (".....", ".....", ".##..", ".##..", ".....", ".....", "....."),
}

# --- raster helpers ---------------------------------------------------------
def new_image(w, h, color):
    return [[color] * w for _ in range(h)]


def set_px(img, x, y, color):
    if 0 <= x < len(img[0]) and 0 <= y < len(img):
        img[y][x] = color


def fill_rect(img, x, y, w, h, color):
    for yy in range(max(0, y), min(len(img), y + h)):
        row = img[yy]
        for xx in range(max(0, x), min(len(row), x + w)):
            row[xx] = color


def rect_border(img, x, y, w, h, color, t=2):
    fill_rect(img, x, y, w, t, color)
    fill_rect(img, x, y + h - t, w, t, color)
    fill_rect(img, x, y, t, h, color)
    fill_rect(img, x + w - t, y, t, h, color)


def line(img, x0, y0, x1, y1, color, t=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for a in range(t):
            for b in range(t):
                set_px(img, x0 + a, y0 + b, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def circle_outline(img, cx, cy, r, color, t=1):
    import math
    steps = max(24, r * 6)
    for i in range(steps):
        a = 2 * math.pi * i / steps
        x = int(round(cx + r * math.cos(a)))
        y = int(round(cy + r * math.sin(a)))
        for a2 in range(t):
            for b2 in range(t):
                set_px(img, x + a2, y + b2, color)


def fill_circle(img, cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                set_px(img, xx, yy, color)


def ellipse_outline(img, cx, cy, rx, ry, color):
    import math
    steps = max(24, (rx + ry) * 4)
    for i in range(steps):
        a = 2 * math.pi * i / steps
        set_px(img, int(round(cx + rx * math.cos(a))),
               int(round(cy + ry * math.sin(a))), color)


def fill_triangle(img, p0, p1, p2, color):
    xs = [p0[0], p1[0], p2[0]]
    ys = [p0[1], p1[1], p2[1]]
    for yy in range(min(ys), max(ys) + 1):
        nodes = []
        for (ax, ay), (bx, by) in ((p0, p1), (p1, p2), (p2, p0)):
            if ay == by:
                continue
            if (yy >= min(ay, by)) and (yy < max(ay, by)):
                nodes.append(ax + (yy - ay) * (bx - ax) / (by - ay))
        if len(nodes) >= 2:
            x0, x1 = int(min(nodes)), int(max(nodes))
            for xx in range(x0, x1 + 1):
                set_px(img, xx, yy, color)


def polyline(img, pts, color, t=1):
    for a, b in zip(pts, pts[1:]):
        line(img, a[0], a[1], b[0], b[1], color, t)


# --- text -------------------------------------------------------------------
def text_width(text, scale, bold=False):
    w = len(text) * 6 * scale
    if bold:
        w += max(1, scale // 3)
    return w


def text_height(scale):
    return 7 * scale


def draw_glyph(img, x, y, ch, scale, color, bold=False):
    glyph = FONT[ch]
    off = max(1, scale // 3) if bold else 0
    for shift in ([0, off] if bold else [0]):
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "#":
                    fill_rect(img, x + shift + gx * scale, y + gy * scale,
                              scale, scale, color)


def draw_text(img, x, y, text, scale, color, bold=False):
    cx = x
    for ch in text:
        draw_glyph(img, cx, y, ch, scale, color, bold)
        cx += 6 * scale
    return cx


def draw_text_right(img, right_x, y, text, scale, color, bold=False):
    draw_text(img, right_x - text_width(text, scale, bold), y, text, scale, color, bold)


def wrap_text(text, scale, max_w, bold=False):
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        cand = w if not cur else cur + " " + w
        if text_width(cand, scale, bold) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_block(img, block):
    lines = wrap_text(block["text"], block["scale"], block["max_w"],
                      block.get("bold", False))
    y = block["y"]
    for ln in lines:
        draw_text(img, block["x"], y, ln, block["scale"], block["color"],
                  block.get("bold", False))
        y += text_height(block["scale"]) + 4


# --- pictograms (img, cx, cy, size, color) ----------------------------------
def draw_globe(img, cx, cy, s, color):
    r = s // 2
    circle_outline(img, cx, cy, r, color, 2)
    ellipse_outline(img, cx, cy, max(2, r // 3), r, color)
    line(img, cx - r, cy, cx + r, cy, color, 1)
    line(img, cx - r + 4, cy - r // 2, cx + r - 4, cy - r // 2, color, 1)
    line(img, cx - r + 4, cy + r // 2, cx + r - 4, cy + r // 2, color, 1)


def draw_flags(img, cx, cy, s, color):
    # two small flags on poles: US (stripes + canton) and Ukraine (blue/yellow)
    fw, fh = s // 2 - 4, s // 3
    x0 = cx - s // 2
    y0 = cy - s // 2
    # poles
    line(img, x0 + 2, y0, x0 + 2, y0 + s, WHITE, 2)
    line(img, x0 + fw + 6, y0, x0 + fw + 6, y0 + s, WHITE, 2)
    # US flag: red/white stripes + blue canton
    for i in range(4):
        fill_rect(img, x0 + 4, y0 + i * (fh // 4), fw - 2, fh // 4,
                  RED_DARK if i % 2 == 0 else WHITE)
    fill_rect(img, x0 + 4, y0, (fw - 2) // 2, fh // 2, (30, 64, 175))
    # Ukraine flag: blue over yellow
    fill_rect(img, x0 + fw + 8, y0, fw - 2, fh // 2, (0, 91, 187))
    fill_rect(img, x0 + fw + 8, y0 + fh // 2, fw - 2, fh - fh // 2, (255, 213, 0))


def draw_chart(img, cx, cy, s, color):
    r = s // 2
    x0, y0 = cx - r, cy - r
    x1, y1 = cx + r, cy + r
    # axes
    line(img, x0, y1, x1, y1, MUTED, 2)
    line(img, x0, y0, x0, y1, MUTED, 2)
    pts = [(x0 + 4, y0 + 8), (x0 + 18, y0 + 14), (x0 + 30, y0 + 10),
           (x0 + 44, y0 + 26), (x0 + 56, y0 + 34), (x1 - 4, y1 - 8)]
    polyline(img, pts, color, 3)
    # arrowhead at the end
    ex, ey = pts[-1]
    fill_triangle(img, (ex, ey), (ex - 10, ey - 2), (ex - 2, ey - 12), color)


def draw_barrier(img, cx, cy, s, color):
    r = s // 2
    x0, y0 = cx - r, cy - r
    # posts
    fill_rect(img, x0, y0 + 6, 5, s - 6, color)
    fill_rect(img, x0 + s - 5, y0 + 6, 5, s - 6, color)
    # two horizontal bars
    fill_rect(img, x0, y0 + 8, s, 6, color)
    fill_rect(img, x0, y0 + s // 2, s, 6, color)
    # no-entry circle + slash
    circle_outline(img, cx, cy - 2, s // 4, RED_DARK, 3)
    line(img, cx - s // 6, cy - 2 + s // 6, cx + s // 6, cy - 2 - s // 6,
         RED_DARK, 3)


def draw_seismic(img, cx, cy, s, color):
    r = s // 2
    x0, y0 = cx - r, cy - r
    line(img, x0, cy + r // 2, x0 + s, cy + r // 2, MUTED, 2)
    pts = [(x0, cy), (x0 + 10, cy), (x0 + 14, cy - r // 2),
           (x0 + 20, cy + r // 3), (x0 + 26, cy - r // 3),
           (x0 + 32, cy + r // 4), (x0 + 38, cy - r // 2),
           (x0 + 46, cy), (x0 + s, cy)]
    polyline(img, pts, color, 3)
    # ground crack
    line(img, cx - 6, cy + r // 2, cx - 2, cy + r, color, 2)
    line(img, cx - 2, cy + r, cx + 6, cy + r // 2 + 4, color, 2)


def draw_rocket(img, cx, cy, s, color):
    r = s // 2
    x0, y0 = cx - r, cy - r
    # body + nose + fins, pointing up-right
    fill_rect(img, cx - 5, y0 + 12, 10, s - 26, color)
    fill_triangle(img, (cx - 5, y0 + 12), (cx + 5, y0 + 12), (cx, y0), color)
    fill_triangle(img, (cx - 5, y0 + s - 14), (cx - 13, y0 + s - 2),
                  (cx - 5, y0 + s - 6), color)
    fill_triangle(img, (cx + 5, y0 + s - 14), (cx + 13, y0 + s - 2),
                  (cx + 5, y0 + s - 6), color)
    # flame
    fill_triangle(img, (cx - 4, y0 + s - 14), (cx + 4, y0 + s - 14),
                  (cx, y0 + s), ORANGE)
    # motion lines
    for dy in (0, 10, 20):
        line(img, x0, y0 + 16 + dy, x0 + 12, y0 + 16 + dy, MUTED, 2)


def draw_padlock(img, cx, cy, s, color):
    r = s // 2
    # shackle
    circle_outline(img, cx, cy - r // 4, s // 4, color, 3)
    # body
    fill_rect(img, cx - s // 3, cy - 2, 2 * s // 3, s // 2, color)
    # keyhole
    fill_circle(img, cx, cy + s // 6, 3, BG)
    fill_rect(img, cx - 1, cy + s // 6, 3, s // 6, BG)


PICTOGRAMS = {
    "globe": draw_globe,
    "flags": draw_flags,
    "chart": draw_chart,
    "barrier": draw_barrier,
    "seismic": draw_seismic,
    "rocket": draw_rocket,
    "padlock": draw_padlock,
}

# --- layout -----------------------------------------------------------------
MASTHEAD = [
    {"text": "THE WORLD IN SEVEN FRAMES", "scale": 4, "max_w": 640,
     "max_lines": 1, "max_h": 30, "x": 104, "y": 18, "color": WHITE, "bold": True},
    {"text": "SUNDAY 22 NOVEMBER 2026", "scale": 2, "max_w": 400,
     "max_lines": 1, "max_h": 16, "x": 104, "y": 58, "color": WHITE, "bold": True},
    {"text": "7 STORIES - ONE DAY", "scale": 2, "max_w": 240,
     "max_lines": 1, "max_h": 16, "x": 780, "y": 36, "color": WHITE, "bold": True},
]

PANELS = [
    {"id": "cop31", "rect": (16, 104, 992, 192), "accent": CYAN,
     "picto": ("globe", 920, 200, 64, CYAN),
     "blocks": [
         {"text": "CLIMATE - COP31 - ANTALYA", "scale": 2, "max_w": 800,
          "max_lines": 1, "max_h": 16, "x": 40, "y": 122, "color": CYAN, "bold": True},
         {"text": "COP31 NEARS A DEAL", "scale": 5, "max_w": 800,
          "max_lines": 1, "max_h": 40, "x": 40, "y": 146, "color": WHITE, "bold": True},
         {"text": "NEW PACKAGE AGREED - APPROVAL VOTE 06:00 GMT SUNDAY",
          "scale": 2, "max_w": 800, "max_lines": 1, "max_h": 16,
          "x": 40, "y": 198, "color": AMBER, "bold": True},
         {"text": "FOSSIL-FUEL WORDING SETTLED AFTER TWO DAYS OF OVERTIME TALKS",
          "scale": 2, "max_w": 800, "max_lines": 1, "max_h": 16,
          "x": 40, "y": 224, "color": WHITE},
         {"text": "NEARLY 200 NATIONS - DEAL TEXT CIRCULATED OVERNIGHT",
          "scale": 2, "max_w": 800, "max_lines": 1, "max_h": 16,
          "x": 40, "y": 246, "color": MUTED},
     ]},
    {"id": "trump", "rect": (16, 308, 484, 188), "accent": AMBER,
     "picto": ("flags", 446, 356, 40, AMBER),
     "blocks": [
         {"text": "DIPLOMACY", "scale": 1, "max_w": 340, "max_lines": 1,
          "max_h": 10, "x": 34, "y": 324, "color": AMBER, "bold": True},
         {"text": "TRUMP MEETS ZELENSKY", "scale": 3, "max_w": 380,
          "max_lines": 1, "max_h": 24, "x": 34, "y": 342, "color": WHITE, "bold": True},
         {"text": "20-POINT PEACE PLAN IN FLORIDA - TERRITORY AND ZAPORIZHZHIA UNRESOLVED",
          "scale": 2, "max_w": 448, "max_lines": 3, "max_h": 50,
          "x": 34, "y": 398, "color": WHITE},
         {"text": "20 POINTS", "scale": 3, "max_w": 448, "max_lines": 1,
          "max_h": 24, "x": 34, "y": 456, "color": AMBER, "bold": True},
     ]},
    {"id": "anthropic", "rect": (524, 308, 484, 188), "accent": RED_DARK,
     "picto": ("chart", 954, 356, 40, RED_DARK),
     "blocks": [
         {"text": "MARKETS - AI", "scale": 1, "max_w": 340, "max_lines": 1,
          "max_h": 10, "x": 542, "y": 324, "color": RED_DARK, "bold": True},
         {"text": "ANTHROPIC SLIDES", "scale": 3, "max_w": 380,
          "max_lines": 1, "max_h": 24, "x": 542, "y": 342, "color": WHITE, "bold": True},
         {"text": "NEAR ITS $83 IPO PRICE - NASDAQ -5.6% FRIDAY AS AI RALLY HALTS",
          "scale": 2, "max_w": 448, "max_lines": 3, "max_h": 50,
          "x": 542, "y": 398, "color": WHITE},
         {"text": "-8.5%", "scale": 3, "max_w": 448, "max_lines": 1,
          "max_h": 24, "x": 542, "y": 456, "color": RED_DARK, "bold": True},
     ]},
    {"id": "estonia", "rect": (16, 508, 484, 188), "accent": VIOLET,
     "picto": ("barrier", 446, 556, 40, VIOLET),
     "blocks": [
         {"text": "EUROPE", "scale": 1, "max_w": 340, "max_lines": 1,
          "max_h": 10, "x": 34, "y": 524, "color": VIOLET, "bold": True},
         {"text": "ESTONIA SHUTS BORDER", "scale": 3, "max_w": 380,
          "max_lines": 1, "max_h": 24, "x": 34, "y": 542, "color": WHITE, "bold": True},
         {"text": "ROAD CROSSINGS CLOSE 1 DEC - FOR 6 MONTHS - MOSCOW: 'NEW IRON CURTAIN'",
          "scale": 2, "max_w": 448, "max_lines": 3, "max_h": 50,
          "x": 34, "y": 598, "color": WHITE},
         {"text": "1 DEC", "scale": 3, "max_w": 448, "max_lines": 1,
          "max_h": 24, "x": 34, "y": 656, "color": VIOLET, "bold": True},
     ]},
    {"id": "peru", "rect": (524, 508, 484, 188), "accent": ORANGE,
     "picto": ("seismic", 954, 556, 40, ORANGE),
     "blocks": [
         {"text": "DISASTER", "scale": 1, "max_w": 340, "max_lines": 1,
          "max_h": 10, "x": 542, "y": 524, "color": ORANGE, "bold": True},
         {"text": "PERU SHAKEN", "scale": 3, "max_w": 380,
          "max_lines": 1, "max_h": 24, "x": 542, "y": 542, "color": WHITE, "bold": True},
         {"text": "MAGNITUDE 6.9 IN THE ANDES - NO CASUALTIES REPORTED",
          "scale": 2, "max_w": 448, "max_lines": 3, "max_h": 50,
          "x": 542, "y": 598, "color": WHITE},
         {"text": "6.9", "scale": 3, "max_w": 448, "max_lines": 1,
          "max_h": 24, "x": 542, "y": 656, "color": ORANGE, "bold": True},
     ]},
    {"id": "houthi", "rect": (16, 708, 484, 188), "accent": GREEN,
     "picto": ("rocket", 446, 756, 40, GREEN),
     "blocks": [
         {"text": "MIDDLE EAST", "scale": 1, "max_w": 340, "max_lines": 1,
          "max_h": 10, "x": 34, "y": 724, "color": GREEN, "bold": True},
         {"text": "MISSILES OVER RIYADH", "scale": 3, "max_w": 380,
          "max_lines": 1, "max_h": 24, "x": 34, "y": 742, "color": WHITE, "bold": True},
         {"text": "SAUDI INTERCEPTS 3 MISSILES - 2ND STRIKE ON RIYADH IN DAYS",
          "scale": 2, "max_w": 448, "max_lines": 3, "max_h": 50,
          "x": 34, "y": 798, "color": WHITE},
         {"text": "3 SHOT DOWN", "scale": 3, "max_w": 448, "max_lines": 1,
          "max_h": 24, "x": 34, "y": 856, "color": GREEN, "bold": True},
     ]},
    {"id": "fbi", "rect": (524, 708, 484, 188), "accent": GOLD,
     "picto": ("padlock", 954, 756, 40, GOLD),
     "blocks": [
         {"text": "CYBER", "scale": 1, "max_w": 340, "max_lines": 1,
          "max_h": 10, "x": 542, "y": 724, "color": GOLD, "bold": True},
         {"text": "FBI DATABASE HACKED", "scale": 3, "max_w": 380,
          "max_lines": 1, "max_h": 24, "x": 542, "y": 742, "color": WHITE, "bold": True},
         {"text": "CRIME DATABASE PROBED - 2ND INTRUSION IN MONTHS",
          "scale": 2, "max_w": 448, "max_lines": 3, "max_h": 50,
          "x": 542, "y": 798, "color": WHITE},
         {"text": "2ND TIME", "scale": 3, "max_w": 448, "max_lines": 1,
          "max_h": 24, "x": 542, "y": 856, "color": GOLD, "bold": True},
     ]},
]

TICKER = [
    {"text": "ALSO TODAY: SOUTH AFRICA VOTES - AUSTRALIA ENDS ENGLAND'S T20 STREAK",
     "scale": 2, "max_w": 992, "max_lines": 1, "max_h": 16,
     "x": 16, "y": 916, "color": WHITE},
    {"text": "MODI OPENS NITISH SETU - CYCLONE AKVAN - 128 NATIONS DRAFT ROBOT-WEAPON RULES",
     "scale": 2, "max_w": 992, "max_lines": 1, "max_h": 16,
     "x": 16, "y": 938, "color": MUTED},
]

FOOTER = [
    {"text": "SOURCES: REUTERS - AP - BBC - CNN - AFP - UN NEWS - ICJ",
     "scale": 1, "max_w": 992, "max_lines": 1, "max_h": 10,
     "x": 16, "y": 972, "color": MUTED},
    {"text": "ALL STORIES REPORTED 20-22 NOV 2026 - IMAGE DRAWN BY A PROGRAM, NO PHOTOS",
     "scale": 1, "max_w": 992, "max_lines": 1, "max_h": 10,
     "x": 16, "y": 990, "color": MUTED},
]

ALL_TEXT = ([b["text"] for b in MASTHEAD]
            + [b["text"] for p in PANELS for b in p["blocks"]]
            + [b["text"] for b in TICKER]
            + [b["text"] for b in FOOTER])


# --- render ---------------------------------------------------------------
def render():
    img = new_image(W, H, BG)
    # masthead: red breaking band
    fill_rect(img, 0, 0, W, 92, RED)
    draw_globe(img, 52, 46, 56, WHITE)
    for block in MASTHEAD:
        draw_block(img, block)
    # lead + panels
    for panel in PANELS:
        x, y, w, h = panel["rect"]
        fill_rect(img, x, y, w, h, PANEL)
        rect_border(img, x, y, w, h, PANEL_BORDER, 2)
        if panel["id"] == "cop31":
            fill_rect(img, x, y, 8, h, panel["accent"])
        else:
            fill_rect(img, x, y, w, 4, panel["accent"])
        name, cx, cy, size, color = panel["picto"]
        PICTOGRAMS[name](img, cx, cy, size, color)
        for block in panel["blocks"]:
            draw_block(img, block)
    # ticker strip
    fill_rect(img, 0, 908, W, 48, TICKER_BG)
    rect_border(img, 0, 908, W, 48, PANEL_BORDER, 1)
    for block in TICKER:
        draw_block(img, block)
    # footer
    for block in FOOTER:
        draw_block(img, block)
    return img


# --- PNG encoding -----------------------------------------------------------
def _chunk(ctype, payload):
    return (struct.pack(">I", len(payload)) + ctype + payload
            + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF))


def encode_png(img):
    raw = bytearray()
    for row in img:
        raw.append(0)  # filter: none
        for (r, g, b) in row:
            raw.extend((r, g, b))
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(render())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
