# -*- coding: utf-8 -*-
"""Chuyển file SVG -> PDF để chèn vào LaTeX (\\includegraphics).

LaTeX (kể cả XeLaTeX) không đọc trực tiếp SVG. Pipeline:
    SVG --(Chrome headless, HTML bọc @page đúng kích thước)--> PDF vector.

Dùng:  python tools/svg2pdf.py figs/svg/*.svg
"""
import glob
import os
import re
import subprocess
import sys
import tempfile

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 1 px = 0.75 pt ở 96 dpi
PX_PER_PT = 96.0 / 72.0


def read_size(svg_text):
    """Đọc width/height hoặc viewBox của thẻ <svg> đầu tiên (đơn vị pt/px)."""
    m = re.search(r"<svg[^>]*>", svg_text, re.S)
    if not m:
        raise ValueError("không tìm thấy thẻ <svg>")
    tag = m.group(0)

    def grab(attr):
        mm = re.search(attr + r'=["\']([\d.]+)\s*(pt|px|mm|cm)?["\']', tag)
        return (float(mm.group(1)), mm.group(2) or "px") if mm else (None, None)

    w, wu = grab("width")
    h, hu = grab("height")
    if w is None or h is None:
        vb = re.search(r'viewBox=["\']([-\d.\s]+)["\']', tag)
        if not vb:
            raise ValueError("SVG không có width/height lẫn viewBox")
        nums = [float(x) for x in vb.group(1).split()]
        w, h, wu, hu = nums[2], nums[3], "px", "px"

    def to_pt(v, unit):
        return {"pt": v, "px": v * 0.75, "mm": v * 72 / 25.4, "cm": v * 72 / 2.54}[unit]

    return to_pt(w, wu), to_pt(h, hu)


def svg_to_pdf(svg_path, pdf_path):
    svg_path = os.path.abspath(svg_path)
    pdf_path = os.path.abspath(pdf_path)
    with open(svg_path, encoding="utf-8") as fh:
        text = fh.read()
    w_pt, h_pt = read_size(text)

    # Chrome in ra page lớn hơn nội dung ~0.08pt do làm tròn px→pt, khiến
    # một số hình bị đẩy sang trang 2. Cộng biên 1pt mỗi chiều rồi cắt lại
    # đúng khung bằng pdfcrop để trang PDF trùng khít nội dung.
    w_px, h_px = (w_pt + 1) * PX_PER_PT, (h_pt + 1) * PX_PER_PT
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>\n"
        f"@page {{ size: {w_px:.2f}px {h_px:.2f}px; margin: 0; }}\n"
        "html,body{margin:0;padding:0;background:transparent;}\n"
        "svg{display:block;width:100%;height:auto;}\n"
        "</style></head><body>\n" + text + "\n</body></html>"
    )

    fd, html_path = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    cmd = [
        CHROME, "--headless", "--disable-gpu", "--no-sandbox",
        f"--print-to-pdf={pdf_path}", "--no-pdf-header-footer",
        "file:///" + html_path.replace("\\", "/").replace(" ", "%20"),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    os.unlink(html_path)
    if not os.path.exists(pdf_path):
        raise RuntimeError(f"Chrome không tạo được PDF cho {svg_path}\n{r.stderr[-800:]}")

    # cắt sát khung nội dung: bỏ phần biên thừa và trang trắng (nếu có)
    cropped = pdf_path + ".crop.pdf"
    subprocess.run(["pdfcrop", "--margins", "0", pdf_path, cropped],
                   capture_output=True, timeout=120)
    if os.path.exists(cropped):
        os.replace(cropped, pdf_path)
    return w_pt, h_pt


def main(patterns):
    paths = []
    for p in patterns:
        paths.extend(glob.glob(p))
    if not paths:
        print("không có file SVG nào")
        return 1
    for svg in sorted(paths):
        pdf = os.path.splitext(svg)[0] + ".pdf"
        w, h = svg_to_pdf(svg, pdf)
        print(f"{os.path.basename(svg):32s} -> {os.path.basename(pdf):32s} ({w:.0f}x{h:.0f} pt)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:] or ["figs/svg/*.svg"]))
