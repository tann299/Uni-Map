# -*- coding: utf-8 -*-
"""
================================================================================
 VẼ SƠ ĐỒ CSDL (ERD)  ->  db/so_do_csdl.png
================================================================================
Sinh sơ đồ quan hệ của lược đồ trong db/schema.sql bằng matplotlib
(không cần Graphviz — chỉ cần matplotlib đã có sẵn).

Muốn sửa sơ đồ: chỉnh danh sách TABLES / ARROWS ở dưới rồi chạy lại.

    python db/ve_so_do.py
================================================================================
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")                       # không cần cửa sổ hiển thị
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "so_do_csdl.png")

# Font có dấu tiếng Việt (Windows). Thiếu thì matplotlib dùng font mặc định.
FONT = None
for p in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
    if os.path.exists(p):
        FONT = p
        break
f_title = FontProperties(fname=FONT, size=26, weight="bold") if FONT else FontProperties(size=26, weight="bold")
f_head  = FontProperties(fname=FONT, size=12, weight="bold") if FONT else FontProperties(size=12, weight="bold")
f_row   = FontProperties(fname=FONT, size=9.5) if FONT else FontProperties(size=9.5)
f_note  = FontProperties(fname=FONT, size=10) if FONT else FontProperties(size=10)
f_zone  = FontProperties(fname=FONT, size=13, weight="bold") if FONT else FontProperties(size=13, weight="bold")

# Màu theo nhóm bảng
C = {
    "ref":  "#1F4E78",   # dữ liệu tham chiếu
    "fact": "#C0504D",   # bảng fact
    "ai":   "#4F6228",   # đặc trưng cho AI
    "user": "#5F3E7A",   # dữ liệu người dùng
    "ops":  "#595959",   # vận hành
}
ZONE_BG = {"ref": "#EAF1F8", "fact": "#FBEEEE", "ai": "#EEF3E7",
           "user": "#F2EDF7", "ops": "#F2F2F2"}

H_HEAD, H_ROW, PAD = 5.0, 2.75, 1.4      # chiều cao header / mỗi dòng / lề trong

# ============================================================================
#  ĐỊNH NGHĨA BẢNG:  key -> (x, y, nhóm, tiêu đề, [(cột, loại_khoá)])
#  loại_khoá: PK | FK | U (unique) | NK (khoá tự nhiên) | '' (thường)
#  Toạ độ tính theo hệ đơn vị tuỳ ý, gốc ở góc trên-trái, y tăng xuống dưới.
# ============================================================================
TABLES = {
    # --- A. Tham chiếu: 1 hàng ngang trên cùng ---
    "truong": (4, 14, "ref", "truong  (289)", [
        ("ma_truong", "PK"), ("ten_truong", ""), ("viet_tat", ""),
        ("tinh_thanh", ""), ("vung_mien", "")]),
    "nganh": (34, 14, "ref", "nganh  (2.312)", [
        ("nganh_id", "PK"), ("nganh_slug", "U"), ("ten_nganh", ""),
        ("nhom_nganh", "")]),
    "to_hop": (64, 14, "ref", "to_hop  (330)", [
        ("ma_to_hop", "PK"), ("ten_to_hop", ""), ("cac_mon", ""), ("so_mon", "")]),
    "to_hop_mon": (94, 14, "ref", "to_hop_mon  (848)", [
        ("ma_to_hop", "FK"), ("ma_mon", "FK"), ("vi_tri", "")]),
    "mon": (120, 14, "ref", "mon  (27)", [
        ("ma_mon", "PK"), ("ten_mon", ""), ("la_nang_khieu", ""), ("thu_tu", "")]),

    # --- B. Sự kiện: xếp dọc, căn giữa dưới nhóm A ---
    "diem_chuan": (36, 58, "fact", "diem_chuan  (178.821)   FACT", [
        ("id", "PK"), ("ma_truong", "FK"), ("nganh_id", "FK"), ("ma_to_hop", "FK"),
        ("phuong_thuc", ""), ("nam", ""), ("diem_chuan", ""),
        ("UNIQUE(4 khoá + nam)", "NK")]),
    "dac_trung": (36, 94, "ai", "dac_trung_diemchuan  (91.782)   AI", [
        ("ma_truong / nganh_id / ma_to_hop", "FK"), ("phuong_thuc", ""),
        ("diem_nam_1 … diem_nam_5", ""), ("diem_tb / min / max", ""),
        ("diem_moi_nhat", ""), ("bien_dong / xu_huong", ""),
        ("so_nam_co_dl", "")]),

    # --- Vận hành: cột riêng bên phải ---
    "cua_so_nam": (100, 58, "ops", "cua_so_nam  (5)", [
        ("vi_tri", "PK"), ("nam", "U")]),
    "lan_cap_nhat": (100, 76, "ops", "lan_cap_nhat", [
        ("id", "PK"), ("thoi_diem", ""), ("nam_bat_dau / ket_thuc", ""),
        ("selfcheck_dat", "")]),

    # --- C. Người dùng ---
    "auth_user": (4, 140, "user", "auth_user  (Django)", [
        ("id", "PK"), ("username", "U"), ("password", ""), ("email", "")]),
    "ho_so": (34, 140, "user", "ho_so_nang_luc", [
        ("id", "PK"), ("user_id", "FK"), ("ten_ho_so", ""),
        ("phuong_thuc", ""), ("diem_uu_tien", "")]),
    "lan_goi_y": (68, 140, "user", "lan_goi_y", [
        ("id", "PK"), ("ho_so_id", "FK"), ("thoi_diem", ""),
        ("dung_ai", ""), ("phien_ban_mo_hinh", "")]),
    "diem_mon": (4, 170, "user", "diem_mon", [
        ("ho_so_id", "PK FK"), ("ma_mon", "PK FK"), ("diem", "")]),
    "nhom_qt": (34, 170, "user", "nhom_nganh_quan_tam", [
        ("ho_so_id", "PK FK"), ("nhom_nganh", "PK")]),
    "ket_qua": (68, 170, "user", "ket_qua_goi_y", [
        ("id", "PK"), ("lan_goi_y_id", "FK"),
        ("ma_truong / nganh_id / ma_to_hop", "FK"),
        ("diem_hoc_sinh", ""), ("margin", ""), ("xac_suat_do", ""),
        ("tang  (An toàn/Vừa/Thử)", ""), ("thu_hang", "")]),
}

# Chiều rộng riêng cho bảng có nội dung dài
WIDTHS = {"dac_trung": 44, "ket_qua": 42, "diem_chuan": 34, "ho_so": 28,
          "lan_goi_y": 28, "lan_cap_nhat": 32, "to_hop_mon": 22, "mon": 24,
          "nhom_qt": 28, "diem_mon": 26}
W_DEFAULT = 26

# ============================================================================
#  QUAN HỆ:  (bảng_nguồn, bảng_đích, nhãn, kiểu_nét)
#  Hướng mũi tên: từ bảng CON (chứa FK) -> bảng CHA (chứa PK)
# ============================================================================
ARROWS = [
    ("diem_chuan", "truong",     "N:1", "solid"),
    ("diem_chuan", "nganh",      "N:1", "solid"),
    ("diem_chuan", "to_hop",     "N:1", "solid"),
    ("to_hop_mon", "to_hop",     "N:1", "solid"),
    ("to_hop_mon", "mon",        "N:1", "solid"),
    ("dac_trung",  "diem_chuan", "tổng hợp lại sau mỗi lần cập nhật", "dashed"),
    ("ho_so",      "auth_user",  "N:1", "solid"),
    ("diem_mon",   "ho_so",      "N:1", "solid"),
    ("nhom_qt",    "ho_so",      "N:1", "solid"),
    ("lan_goi_y",  "ho_so",      "N:1", "solid"),
    ("ket_qua",    "lan_goi_y",  "N:1", "solid"),
]

# Khung nhóm:  (nhãn, x, y, rộng, cao, nhóm)
ZONES = [
    ("A. DỮ LIỆU THAM CHIẾU  —  crawl 1 lần/năm", 1, 6, 146, 40, "ref"),
    ("B. DỮ LIỆU SỰ KIỆN  —  bảng fact + đặc trưng cho AI", 1, 50, 88, 78, "fact"),
    ("VẬN HÀNH  —  cửa sổ trượt & nhật ký", 95, 50, 52, 48, "ops"),
    ("C. DỮ LIỆU NGƯỜI DÙNG", 1, 132, 114, 70, "user"),
]


# ============================================================================
#  VẼ
# ============================================================================
def table_box(key):
    """Trả (x, y, w, h) của một bảng."""
    x, y, *_ , rows = (*TABLES[key][:4], TABLES[key][4])
    w = WIDTHS.get(key, W_DEFAULT)
    h = H_HEAD + len(rows) * H_ROW + PAD
    return x, y, w, h


def anchor(key, toward):
    """Điểm neo trên viền bảng `key`, hướng về tâm bảng `toward`."""
    x, y, w, h = table_box(key)
    cx, cy = x + w / 2, y + h / 2
    tx, ty, tw, th = table_box(toward)
    ox, oy = tx + tw / 2, ty + th / 2

    dx, dy = ox - cx, oy - cy
    # chọn cạnh theo hướng trội
    if abs(dx) * h > abs(dy) * w:
        return (x + w if dx > 0 else x), cy
    return cx, (y + h if dy > 0 else y)


def main():
    fig, ax = plt.subplots(figsize=(20, 14), dpi=150)

    # --- khung nhóm (vẽ trước để nằm dưới) ---
    for label, zx, zy, zw, zh, grp in ZONES:
        ax.add_patch(FancyBboxPatch(
            (zx, zy), zw, zh, boxstyle="round,pad=0.6,rounding_size=1.2",
            facecolor=ZONE_BG[grp], edgecolor=C[grp], linewidth=1.4,
            linestyle=(0, (6, 4)), alpha=0.55, zorder=0))
        ax.text(zx + 1.4, zy + 2.6, label, fontproperties=f_zone,
                color=C[grp], zorder=1)

    # --- quan hệ ---
    for src, dst, label, style in ARROWS:
        x1, y1 = anchor(src, dst)
        x2, y2 = anchor(dst, src)
        dashed = style == "dashed"
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="-|>", mutation_scale=16,
            connectionstyle="arc3,rad=0.08",
            linewidth=1.5 if not dashed else 1.2,
            linestyle="--" if dashed else "-",
            color="#8C8C8C" if dashed else "#4A4A4A", zorder=2))
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 - 0.7, label,
                fontproperties=f_row, color="#666666", ha="center",
                bbox=dict(facecolor="white", edgecolor="none", pad=1.2), zorder=3)

    # --- bảng ---
    for key, (x, y, grp, title, rows) in TABLES.items():
        w = WIDTHS.get(key, W_DEFAULT)
        h = H_HEAD + len(rows) * H_ROW + PAD

        # thân
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8",
            facecolor="white", edgecolor=C[grp], linewidth=1.8, zorder=4))
        # header
        ax.add_patch(Rectangle((x, y), w, H_HEAD, facecolor=C[grp],
                               edgecolor="none", zorder=5))
        ax.text(x + w / 2, y + H_HEAD / 2, title, fontproperties=f_head,
                color="white", ha="center", va="center", zorder=6)

        for i, (col, kind) in enumerate(rows):
            ty = y + H_HEAD + PAD * 0.5 + i * H_ROW + H_ROW / 2
            if i:                                     # kẻ vạch giữa các dòng
                ax.plot([x + 0.5, x + w - 0.5],
                        [y + H_HEAD + PAD * 0.5 + i * H_ROW] * 2,
                        color="#E8E8E8", linewidth=0.6, zorder=5)
            bold = "PK" in kind
            fp = (FontProperties(fname=FONT, size=9.5, weight="bold") if (bold and FONT)
                  else f_row)
            ax.text(x + 1.2, ty, col, fontproperties=fp, va="center",
                    color="#1A1A1A", zorder=6)
            if kind:
                tag_color = {"PK": "#B8860B", "U": "#2E7D32",
                             "NK": "#C0504D"}.get(kind.split()[0], "#1565C0")
                ax.text(x + w - 1.2, ty, kind, fontproperties=f_row,
                        va="center", ha="right", color=tag_color, zorder=6)

    # --- tiêu đề + chú giải ---
    ax.text(1, 3.2, "UNI MAP — Sơ đồ cơ sở dữ liệu", fontproperties=f_title,
            color="#1F4E78")
    legend = ("PK = khoá chính   ·   FK = khoá ngoại   ·   U = duy nhất   ·   "
              "NK = khoá tự nhiên (nền tảng upsert hằng năm)   ·   "
              "nét liền = ràng buộc FK   ·   nét đứt = luồng dữ liệu")
    ax.text(1, 208, legend, fontproperties=f_note, color="#555555")
    ax.text(1, 211.5,
            "Không vẽ để sơ đồ khỏi rối (vẫn có trong schema.sql): "
            "diem_mon.ma_mon → mon   ·   "
            "ket_qua_goi_y.{ma_truong, nganh_id, ma_to_hop} → truong / nganh / to_hop",
            fontproperties=f_note, color="#A0522D")
    ax.text(1, 215, "15 bảng · MySQL 8.0 · utf8mb4 · InnoDB      "
                    "Nguồn: db/schema.sql", fontproperties=f_note, color="#888888")

    ax.set_xlim(0, 150)
    ax.set_ylim(218, 0)              # đảo trục y: gốc ở trên
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    print(f">> {OUT}  ({os.path.getsize(OUT) // 1024} KB)")


if __name__ == "__main__":
    main()


