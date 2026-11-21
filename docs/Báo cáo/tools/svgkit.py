# -*- coding: utf-8 -*-
"""Bộ công cụ nhỏ sinh hình vector SVG cho báo cáo.

Mọi hình trong báo cáo được sinh từ đây dưới dạng SVG thuần (không dùng
thư viện ngoài), sau đó tools/svg2pdf.py đổi sang PDF để LaTeX chèn vào.
Nhờ vậy hình là vector thật: phóng to không vỡ, chữ chọn/copy được.
"""
from xml.sax.saxutils import escape

# ---- Bảng màu đồng bộ với styles/dau.sty -----------------------------
NAVY = "#0E2841"
MAROON = "#990000"
GOLD = "#FBAE40"
GREEN = "#196B24"
GRAY = "#6B7280"
GRAY7 = "#384152"
GRAY3 = "#DADEE2"
LIGHT = "#F3F4F6"
WARM = "#FCEFD9"
LIGHTNAVY = "#E7EBF0"
LIGHTFOREST = "#E8F0EA"
WHITE = "#FFFFFF"
INK = "#1F2937"

FONT = "'Times New Roman', 'Liberation Serif', serif"
MONO = "'Courier New', 'Liberation Mono', monospace"

# Ước lượng độ rộng ký tự theo em (Times New Roman) để ngắt dòng.
_CHAR_W = 0.50
_MONO_W = 0.60


def wrap(text, width_pt, size_pt, mono=False):
    """Ngắt dòng thô theo ước lượng độ rộng ký tự."""
    per_char = size_pt * (_MONO_W if mono else _CHAR_W)
    limit = max(1, int(width_pt / per_char))
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= limit:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class Svg:
    def __init__(self, width, height, background=WHITE):
        self.w, self.h = float(width), float(height)
        self.parts = []
        self.defs = []
        if background:
            self.parts.append(
                f'<rect x="0" y="0" width="{self.w:g}" height="{self.h:g}" fill="{background}"/>'
            )
        self._markers = set()

    # ---------------- nguyên thuỷ ----------------
    def rect(self, x, y, w, h, fill=WHITE, stroke=NAVY, sw=1.0, rx=0, dash=None, opacity=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' opacity="{opacity}"' if opacity is not None else ""
        s = f' stroke="{stroke}" stroke-width="{sw:g}"' if stroke else ' stroke="none"'
        r = f' rx="{rx:g}"' if rx else ""
        self.parts.append(
            f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}"{r} fill="{fill}"{s}{d}{o}/>'
        )

    def ellipse(self, cx, cy, rx, ry, fill=WHITE, stroke=NAVY, sw=1.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s = f' stroke="{stroke}" stroke-width="{sw:g}"' if stroke else ' stroke="none"'
        self.parts.append(
            f'<ellipse cx="{cx:g}" cy="{cy:g}" rx="{rx:g}" ry="{ry:g}" fill="{fill}"{s}{d}/>'
        )

    def circle(self, cx, cy, r, fill=MAROON, stroke=None, sw=1.0):
        s = f' stroke="{stroke}" stroke-width="{sw:g}"' if stroke else ' stroke="none"'
        self.parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{fill}"{s}/>')

    def polygon(self, pts, fill=WHITE, stroke=NAVY, sw=1.0):
        p = " ".join(f"{x:g},{y:g}" for x, y in pts)
        s = f' stroke="{stroke}" stroke-width="{sw:g}"' if stroke else ' stroke="none"'
        self.parts.append(f'<polygon points="{p}" fill="{fill}"{s}/>')

    def path(self, d, fill="none", stroke=NAVY, sw=1.0, dash=None, marker_end=None,
             marker_start=None, opacity=None):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        me = f' marker-end="url(#{self._marker(marker_end)})"' if marker_end else ""
        ms = f' marker-start="url(#{self._marker(marker_start)})"' if marker_start else ""
        o = f' opacity="{opacity}"' if opacity is not None else ""
        s = f' stroke="{stroke}" stroke-width="{sw:g}"' if stroke else ' stroke="none"'
        self.parts.append(f'<path d="{d}" fill="{fill}"{s}{da}{me}{ms}{o}/>')

    def line(self, x1, y1, x2, y2, stroke=NAVY, sw=1.0, dash=None, marker_end=None, marker_start=None):
        self.path(f"M{x1:g},{y1:g} L{x2:g},{y2:g}", stroke=stroke, sw=sw, dash=dash,
                  marker_end=marker_end, marker_start=marker_start)

    def _marker(self, color):
        key = color.replace("#", "")
        mid = f"ar{key}"
        if mid not in self._markers:
            self._markers.add(mid)
            self.defs.append(
                f'<marker id="{mid}" markerWidth="9" markerHeight="9" refX="7.5" refY="3" '
                f'orient="auto" markerUnits="strokeWidth">'
                f'<path d="M0,0 L7,3 L0,6 z" fill="{color}"/></marker>'
            )
        return mid

    def text(self, x, y, s, size=10, fill=INK, anchor="start", bold=False,
             italic=False, font=FONT, baseline="middle", spacing=None):
        fw = ' font-weight="bold"' if bold else ""
        fi = ' font-style="italic"' if italic else ""
        sp = f' letter-spacing="{spacing}"' if spacing else ""
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-family="{font}" font-size="{size:g}" '
            f'fill="{fill}" text-anchor="{anchor}" dominant-baseline="{baseline}"'
            f'{fw}{fi}{sp}>{escape(s)}</text>'
        )

    def multiline(self, x, y, lines, size=10, fill=INK, anchor="start", bold=False,
                  italic=False, lh=1.35, font=FONT):
        """lines: chuỗi (tự tách \n) hoặc list dòng. Trả về y sau khối chữ."""
        if isinstance(lines, str):
            lines = lines.split("\n")
        y0 = y
        for ln in lines:
            self.text(x, y0, ln, size=size, fill=fill, anchor=anchor,
                      bold=bold, italic=italic, font=font)
            y0 += size * lh
        return y0

    def wrapped(self, x, y, text, width, size=10, fill=INK, anchor="start",
                bold=False, italic=False, lh=1.35, font=FONT):
        lines = wrap(text, width, size, mono=(font == MONO))
        return self.multiline(x, y, lines, size=size, fill=fill, anchor=anchor,
                              bold=bold, italic=italic, lh=lh, font=font)

    # ---------------- khối dựng sẵn ----------------
    def box(self, x, y, w, h, text, fill=WHITE, stroke=NAVY, sw=1.0, size=10,
            color=INK, bold=False, rx=5, dash=None, pad=6, lh=1.35, anchor="middle",
            font=FONT):
        """Hộp bo góc có chữ tự căn giữa (tự ngắt dòng theo bề ngang)."""
        self.rect(x, y, w, h, fill=fill, stroke=stroke, sw=sw, rx=rx, dash=dash)
        lines = wrap(text, w - 2 * pad, size, mono=(font == MONO))
        total = len(lines) * size * lh
        cy = y + h / 2 - total / 2 + size * lh / 2
        tx = x + w / 2 if anchor == "middle" else x + pad
        for ln in lines:
            self.text(tx, cy, ln, size=size, fill=color, anchor=anchor,
                      bold=bold, font=font)
            cy += size * lh
        return len(lines)

    def label(self, x, y, text, size=9, color=GRAY7, anchor="middle",
              bg=WHITE, bold=False, italic=False):
        """Nhãn nền trắng đè lên đường nối."""
        tw = len(text) * size * _CHAR_W + 6
        self.rect(x - tw / 2, y - size * 0.75, tw, size * 1.5, fill=bg, stroke=None)
        self.text(x, y, text, size=size, fill=color, anchor=anchor,
                  bold=bold, italic=italic)

    def badge(self, x, y, text, size=8.5, fill=MAROON, color=WHITE, padx=7, h=None):
        """Nhãn nhỏ dạng viên thuốc."""
        h = h or size * 1.9
        w = len(text) * size * 0.55 + 2 * padx
        self.rect(x, y, w, h, fill=fill, stroke=None, rx=h / 2)
        self.text(x + w / 2, y + h / 2, text, size=size, fill=color, anchor="middle",
                  bold=True)
        return w

    # ---------------- xuất ----------------
    def render(self):
        defs = "<defs>" + "".join(self.defs) + "</defs>" if self.defs else ""
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w:g}pt" height="{self.h:g}pt" '
            f'viewBox="0 0 {self.w:g} {self.h:g}">\n'
            f'{defs}\n' + "\n".join(self.parts) + "\n</svg>\n"
        )

    def save(self, path):
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(self.render())
        return path
