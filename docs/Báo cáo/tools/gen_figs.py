# -*- coding: utf-8 -*-
"""Sinh toàn bộ hình vector SVG cho báo cáo đồ án Uni Connect.

Chạy:  python tools/gen_figs.py
Sau đó: python tools/svg2pdf.py "figs/svg/*.svg"

Mỗi hàm vẽ một hình, dùng svgkit để dựng. Toạ độ tính bằng point (pt),
bề ngang chuẩn 460pt ≈ bề ngang vùng chữ của trang A4 (16cm).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import (Svg, NAVY, MAROON, GOLD, GREEN, GRAY, GRAY7, GRAY3,
                    LIGHT, WARM, LIGHTNAVY, LIGHTFOREST, WHITE, INK, MONO)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figs", "svg")
W = 460.0


def save(svg, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".svg")
    svg.save(path)
    print("  ", name + ".svg", f"({svg.w:.0f}x{svg.h:.0f})")


# =====================================================================
#  H1 — Kiến trúc tổng thể 4 tầng
# =====================================================================
def fig_kientruc():
    s = Svg(W, 205)
    stages = [
        ("1. THU THẬP", "crawler + CSV", "Tải, làm sạch dữ liệu\ntừ cổng tuyển sinh", LIGHTNAVY, NAVY),
        ("2. CSDL MySQL", "15 bảng quan hệ", "240.483 dòng điểm chuẩn\nCửa sổ trượt 10 năm", LIGHT, NAVY),
        ("3. MÔ HÌNH AI", "Random Forest", "27 đặc trưng\nmodel.pkl ~52 MB", WARM, MAROON),
        ("4. WEB DJANGO", "tra cứu + gợi ý", "6 ứng dụng\nTailwind CSS", LIGHTFOREST, GREEN),
    ]
    bw, gap, x0, y0, bh = 100.0, 20.0, 4.0, 40.0, 92.0
    for i, (t, sub, desc, fill, accent) in enumerate(stages):
        x = x0 + i * (bw + gap)
        s.rect(x, y0, bw, bh, fill=fill, stroke=accent, sw=1.4, rx=6)
        s.rect(x, y0, bw, 22, fill=accent, stroke=None, rx=6)
        s.rect(x, y0 + 16, bw, 6, fill=accent, stroke=None)
        s.text(x + bw / 2, y0 + 11, t, size=9.5, fill=WHITE, anchor="middle", bold=True)
        s.text(x + bw / 2, y0 + 35, sub, size=9, fill=accent, anchor="middle", bold=True)
        s.multiline(x + bw / 2, y0 + 52, desc, size=7.6, fill=GRAY7, anchor="middle", lh=1.5)
        if i < 3:
            s.line(x + bw + 3, y0 + bh / 2, x + bw + gap - 3, y0 + bh / 2,
                   stroke=MAROON, sw=1.6, marker_end=MAROON)

    # vòng phản hồi người dùng
    s.path(f"M{x0 + 3 * (bw + gap) + bw / 2},{y0 + bh} L{x0 + 3 * (bw + gap) + bw / 2},178 "
           f"L{x0 + bw / 2},178 L{x0 + bw / 2},{y0 + bh + 4}",
           stroke=GOLD, sw=1.5, dash="5,3", marker_end=GOLD)
    s.label(x0 + 2 * (bw + gap), 178,
            "phản hồi & nhật ký sử dụng → cải thiện dữ liệu", size=7.6, color=MAROON, bg=WHITE)

    s.text(W / 2, 16, "KIẾN TRÚC TỔNG THỂ HỆ THỐNG UNI CONNECT", size=10, fill=NAVY,
           anchor="middle", bold=True, spacing="1.5")
    s.text(W / 2, 30, "Luồng dữ liệu khép kín, chạy ngoại tuyến trước rồi phục vụ trực tuyến",
           size=7.8, fill=GRAY, anchor="middle", italic=True)
    save(s, "h-kien-truc")


# =====================================================================
#  H2 — ERD rút gọn (nhóm bảng + quan hệ)
# =====================================================================
def fig_erd():
    s = Svg(W, 330)

    def table(x, y, w, title, rows, accent=NAVY, fill=WHITE):
        hh, rh = 15.0, 10.5
        h = hh + rh * len(rows)
        s.rect(x, y, w, h, fill=fill, stroke=accent, sw=1.1, rx=3)
        s.rect(x, y, w, hh, fill=accent, stroke=None, rx=3)
        s.rect(x, y + hh - 4, w, 4, fill=accent, stroke=None)
        s.text(x + w / 2, y + hh / 2, title, size=7.8, fill=WHITE, anchor="middle", bold=True)
        yy = y + hh + rh / 2
        for col, kind in rows:
            bold = kind in ("PK", "PK FK")
            if kind:
                kc = MAROON if "PK" in kind else GREEN
                s.text(x + 4, yy, kind, size=5.8, fill=kc, bold=True)
            # cột tên rộng 16pt không đủ cho "PK FK" + tên cột dài -> đẩy sang 22
            s.text(x + (23 if kind else 4), yy, col, size=6.8, fill=INK, bold=bold,
                   font=MONO if kind else "'Times New Roman', serif")
            yy += rh
        return (x, y, w, h)

    t_truong = table(4, 26, 78, "truong  (295)", [
        ("ma_truong", "PK"), ("ten_truong", ""), ("viet_tat", ""),
        ("tinh_thanh", ""), ("vung_mien", "")], accent="#1F4E78")
    t_nganh = table(88, 26, 74, "nganh  (3.037)", [
        ("nganh_id", "PK"), ("nganh_slug", "U"), ("ten_nganh", ""),
        ("nhom_nganh", "")], accent="#1F4E78")
    t_tohop = table(168, 26, 74, "to_hop  (340)", [
        ("ma_to_hop", "PK"), ("ten_to_hop", ""), ("cac_mon", "")], accent="#1F4E78")
    t_mon = table(248, 26, 62, "mon  (27)", [
        ("ma_mon", "PK"), ("ten_mon", ""), ("la_nang_khieu", "")], accent="#1F4E78")
    t_thm = table(316, 26, 66, "to_hop_mon", [
        ("ma_to_hop", "PK FK"), ("ma_mon", "PK FK"), ("vi_tri", "PK")], accent="#1F4E78")

    t_dc = table(4, 108, 108, "diem_chuan  (240.483)  FACT", [
        ("id", "PK"), ("ma_truong", "FK"), ("nganh_id", "FK"), ("ma_to_hop", "FK"),
        ("phuong_thuc", ""), ("nam", ""), ("diem_chuan", "")], accent="#C0504D", fill="#FBEEEE")
    t_dt = table(122, 108, 110, "dac_trung_diemchuan  (100.363)", [
        ("(4 khoá)", "FK"), ("diem_nam_1..10", ""), ("diem_tb/min/max", ""),
        ("diem_moi_nhat", ""), ("bien_dong / xu_huong", ""), ("so_nam_co_dl", "")],
        accent="#4F6228", fill="#EEF3E7")
    t_csn = table(242, 108, 68, "cua_so_nam  (10)", [
        ("vi_tri", "PK"), ("nam", "U")], accent="#595959", fill="#F2F2F2")
    t_lcn = table(320, 108, 62, "lan_cap_nhat", [
        ("id", "PK"), ("thoi_diem", ""), ("selfcheck_dat", "")], accent="#595959", fill="#F2F2F2")

    t_user = table(4, 200, 80, "auth_user", [
        ("id", "PK"), ("username", "U"), ("password", "")], accent="#5F3E7A", fill="#F2EDF7")
    t_hs = table(94, 200, 76, "ho_so_nang_luc", [
        ("id", "PK"), ("user_id", "FK"), ("ten_ho_so", ""),
        ("diem_uu_tien", "")], accent="#5F3E7A", fill="#F2EDF7")
    t_lgy = table(178, 200, 86, "lan_goi_y", [
        ("id", "PK"), ("ho_so_id", "FK"), ("dung_ai", ""),
        ("phien_ban_mo_hinh", "")], accent="#5F3E7A", fill="#F2EDF7")
    t_kq = table(272, 200, 110, "ket_qua_goi_y", [
        ("id", "PK"), ("lan_goi_y_id", "FK"), ("(trường, ngành)", "FK"),
        ("margin / xac_suat_do", ""), ("tang / thu_hang", "")], accent="#5F3E7A", fill="#F2EDF7")
    t_dm = table(4, 258, 62, "diem_mon", [
        ("ho_so_id", "PK FK"), ("ma_mon", "PK FK"), ("diem", "")], accent="#5F3E7A", fill="#F2EDF7")
    t_nn = table(74, 258, 84, "nhom_nganh_quan_tam", [
        ("ho_so_id", "PK FK"), ("nhom_nganh", "PK")], accent="#5F3E7A", fill="#F2EDF7")

    def edge(a, b, label=None, color=NAVY, dash=None):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        # nối cạnh gần nhau nhất
        if ay + ah < by:  # a trên b
            s.line(ax + aw / 2, ay + ah, bx + bw / 2, by - 2, stroke=color, sw=0.8,
                   dash=dash, marker_end=color)
        elif by + bh < ay:
            s.line(ax + aw / 2, ay, bx + bw / 2, by + bh + 2, stroke=color, sw=0.8,
                   dash=dash, marker_end=color)
        else:
            if ax < bx:
                s.line(ax + aw, ay + ah / 2, bx - 2, by + bh / 2, stroke=color, sw=0.8,
                       dash=dash, marker_end=color)
            else:
                s.line(ax, ay + ah / 2, bx + bw + 2, by + bh / 2, stroke=color, sw=0.8,
                       dash=dash, marker_end=color)

    edge(t_dc, t_truong, color="#C0504D")
    edge(t_dc, t_nganh, color="#C0504D")
    edge(t_dc, t_tohop, color="#C0504D")
    edge(t_thm, t_tohop, color="#1F4E78")
    edge(t_thm, t_mon, color="#1F4E78")
    edge(t_dt, t_dc, color="#4F6228", dash="4,2")
    edge(t_hs, t_user, color="#5F3E7A")
    edge(t_dm, t_hs, color="#5F3E7A")
    edge(t_nn, t_hs, color="#5F3E7A")
    edge(t_lgy, t_hs, color="#5F3E7A")
    edge(t_kq, t_lgy, color="#5F3E7A")
    s.line(t_kq[0] + 10, t_kq[1], t_dc[0] + 90, t_dc[1] + t_dc[3] + 2,
           stroke=GREEN, sw=0.8, dash="4,2", marker_end=GREEN)

    # chú giải
    s.text(W / 2, 14, "LƯỢC ĐỒ QUAN HỆ RÚT GỌN — 15 BẢNG, 4 NHÓM CHỨC NĂNG",
           size=9.5, fill=NAVY, anchor="middle", bold=True, spacing="1")
    ly = 320
    s.text(6, ly, "Chú giải:", size=7, fill=GRAY7, bold=True)
    s.text(40, ly, "PK = khoá chính", size=7, fill=MAROON)
    s.text(110, ly, "FK = khoá ngoại", size=7, fill=GREEN)
    s.text(178, ly, "U = duy nhất", size=7, fill=GRAY)
    s.text(238, ly, "nét liền = quan hệ 1:N", size=7, fill=NAVY)
    s.text(340, ly, "nét đứt = bảng dẫn xuất", size=7, fill=GREEN)
    save(s, "h-erd")


# =====================================================================
#  H3 — Use Case
# =====================================================================
def fig_usecase():
    # Bố cục: tác nhân | cột UC trái | cột UC phải | tác nhân
    # Khung hệ thống đủ rộng để không đè lên tiêu đề và các nút.
    s = Svg(W, 320)
    bx, by, bw, bh = 84.0, 40.0, 292.0, 252.0
    s.rect(bx, by, bw, bh, fill="#FAFBFC", stroke=NAVY, sw=1.3, rx=8)
    s.text(bx + bw / 2, by + 16, "Hệ thống Uni Connect", size=9, fill=NAVY,
           anchor="middle", bold=True)

    def actor(x, y, name):
        s.circle(x, y, 8, fill=WARM, stroke=MAROON, sw=1.1)
        s.path(f"M{x},{y + 8} L{x},{y + 26} M{x - 11},{y + 15} L{x + 11},{y + 15} "
               f"M{x},{y + 26} L{x - 9},{y + 40} M{x},{y + 26} L{x + 9},{y + 40}",
               stroke=MAROON, sw=1.1)
        s.text(x, y + 54, name, size=7.6, fill=MAROON, anchor="middle", bold=True)

    def uc(x, y, w, text, ai=False):
        fill = WARM if ai else WHITE
        stroke = MAROON if ai else NAVY
        s.rect(x, y, w, 22, fill=fill, stroke=stroke, sw=1.0 if not ai else 1.3, rx=11)
        s.text(x + w / 2, y + 11, text, size=6.6, fill=stroke, anchor="middle",
               bold=ai)
        return (x, y, w, 22)

    lx, rx, uw = 104.0, 254.0, 108.0
    left = [
        uc(lx, 64, uw, "UC-01 Tra cứu điểm chuẩn"),
        uc(lx, 92, uw, "UC-02 Xem chi tiết trường"),
        uc(lx, 120, uw, "UC-03 Đăng ký / Đăng nhập"),
        uc(lx, 168, uw, "UC-09 Cập nhật dữ liệu"),
        uc(lx, 196, uw, "UC-10 Huấn luyện lại ★", ai=True),
        uc(lx, 224, uw, "UC-11 Xem thống kê"),
    ]
    right = [
        uc(rx, 64, uw, "UC-04 Nhập hồ sơ năng lực"),
        uc(rx, 92, uw, "UC-05 Nhận gợi ý AI ★", ai=True),
        uc(rx, 120, uw, "UC-06 Xem lời giải thích ★", ai=True),
        uc(rx, 148, uw, "UC-07 So sánh nguyện vọng"),
        uc(rx, 176, uw, "UC-08 Lưu / xem lại hồ sơ"),
    ]

    actor(40, 90, "Khách")
    actor(40, 212, "Quản trị viên")
    actor(420, 118, "Học sinh")

    def left_assoc(actor_y, uses):
        # Actor → trunk → từng use case. Không dùng đường chéo xuyên actor/khối.
        trunk_x = 76
        centers = [u[1] + u[3] / 2 for u in uses]
        s.line(52, actor_y, trunk_x, actor_y, stroke=GRAY, sw=0.8)
        s.line(trunk_x, min(centers), trunk_x, max(centers), stroke=GRAY, sw=0.8)
        for cy, u in zip(centers, uses):
            s.line(trunk_x, cy, u[0] - 2, cy, stroke=GRAY, sw=0.8)

    def right_assoc(uses):
        # Use case → trunk → Actor. Đường nối đi ra mép phải hệ thống.
        trunk_x, actor_x, actor_y = 386, 408, 132
        centers = [u[1] + u[3] / 2 for u in uses]
        s.line(trunk_x, min(centers), trunk_x, max(centers), stroke=GRAY, sw=0.8)
        for cy, u in zip(centers, uses):
            s.line(u[0] + u[2] + 2, cy, trunk_x, cy, stroke=GRAY, sw=0.8)
        s.line(trunk_x, actor_y, actor_x, actor_y, stroke=GRAY, sw=0.8)

    left_assoc(104, left[:3])
    left_assoc(226, left[3:])
    right_assoc(right)

    # nối hai actor trái tới trục chung bằng đường ngang; không chéo xuyên hệ thống
    s.line(52, 104, 76, 104, stroke=GRAY, sw=0.8)
    s.line(52, 226, 76, 226, stroke=GRAY, sw=0.8)

    # include: UC-05 → UC-06 (hai nút cùng cột, nối dọc bên phải)
    s.path(f"M{rx + uw},{92 + 22} L{rx + uw + 10},{92 + 22} "
           f"L{rx + uw + 10},{120 + 11} L{rx + uw + 2},{120 + 11}",
           stroke=MAROON, sw=1.0, dash="4,2", marker_end=MAROON)
    s.text(rx + uw + 14, 108, "«include»", size=6.0, fill=MAROON, anchor="start")
    # follows: UC-09 → UC-10
    s.path(f"M{lx},{168 + 22} L{lx - 8},{168 + 22} L{lx - 8},{196 + 11} L{lx - 2},{196 + 11}",
           stroke=MAROON, sw=1.0, dash="4,2", marker_end=MAROON)
    s.text(lx - 12, 193, "«follows»", size=6.0, fill=MAROON, anchor="end")

    s.text(W / 2, 18, "SƠ ĐỒ CA SỬ DỤNG TỔNG THỂ", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    s.text(bx + bw / 2, 306, "★ = ca sử dụng có mô hình AI (Random Forest) tham gia",
           size=7, fill=MAROON, anchor="middle", italic=True)
    save(s, "h-usecase")


# =====================================================================
#  H4 — BFD (phân rã chức năng)
# =====================================================================
def fig_bfd():
    s = Svg(W, 250)
    root_w, root_h = 210.0, 26.0
    s.rect((W - root_w) / 2, 26, root_w, root_h, fill=WARM, stroke=MAROON, sw=1.4, rx=6)
    s.text(W / 2, 39, "Hệ thống gợi ý nguyện vọng Uni Connect", size=9, fill=MAROON,
           anchor="middle", bold=True)

    groups = [
        ("Tra cứu", "UC-01, 02", ["Tìm theo tên trường,\nngành, tổ hợp, tỉnh",
                                  "Lọc theo vùng miền,\nphương thức, năm",
                                  "Xem chuỗi điểm\nchuẩn 10 năm"]),
        ("Tài khoản", "UC-03", ["Đăng ký, đăng nhập\nnội bộ",
                                "Đăng nhập\nGoogle OAuth2",
                                "Đăng nhập\nFacebook OAuth2"]),
        ("Hồ sơ", "UC-04, 08", ["Nhập điểm từng môn\nvà điểm ưu tiên",
                                "Chọn nhóm ngành,\nvùng miền quan tâm",
                                "Sửa, xoá, xem lại\nhồ sơ"]),
        ("Gợi ý AI", "UC-05, 06, 07", ["Suy luận xác suất\ntheo lô",
                                       "Phân tầng An toàn,\nVừa sức, Thử sức",
                                       "Sinh lời giải thích\ntừ đặc trưng",
                                       "So sánh và lưu\nnguyện vọng"]),
        ("Quản trị", "UC-09, 10, 11", ["Cập nhật dữ liệu\nnăm mới",
                                       "Huấn luyện lại\nmô hình",
                                       "Quản lý người dùng",
                                       "Xem thống kê\nhệ thống"]),
    ]
    gw, gap = 82.0, 12.0
    total = len(groups) * gw + (len(groups) - 1) * gap
    x0 = (W - total) / 2
    for i, (name, ucs, fns) in enumerate(groups):
        gx = x0 + i * (gw + gap)
        s.path(f"M{W / 2},{26 + root_h} L{W / 2},{64} L{gx + gw / 2},{64} L{gx + gw / 2},{74}",
               stroke=MAROON, sw=0.8)
        s.rect(gx, 74, gw, 30, fill=WARM, stroke=MAROON, sw=1.0, rx=4)
        s.text(gx + gw / 2, 84, name, size=8, fill=MAROON, anchor="middle", bold=True)
        s.text(gx + gw / 2, 96, f"({ucs})", size=6.2, fill=MAROON, anchor="middle")
        fy = 112
        for fn in fns:
            lines = fn.split("\n")
            h = 8 + len(lines) * 9
            s.rect(gx, fy, gw, h, fill=WHITE, stroke=NAVY, sw=0.7, rx=3)
            s.line(gx + gw / 2, fy - 8, gx + gw / 2, fy, stroke=NAVY, sw=0.7)
            s.multiline(gx + gw / 2, fy + 8 + (len(lines) - 1) * 4.5, lines,
                        size=6.4, fill=NAVY, anchor="middle", lh=1.4)
            fy += h + 8

    s.text(W / 2, 14, "SƠ ĐỒ PHÂN RÃ CHỨC NĂNG (BFD)", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    save(s, "h-bfd")


# =====================================================================
#  H5 — API routing
# =====================================================================
def fig_api():
    s = Svg(W, 300)
    rows = [
        ("/", "GET /"),
        ("university/", "GET /tra-cuu/   GET /truong/\nGET /truong/<ma_truong>/"),
        ("api/", "GET /api/tra-cuu/"),
        ("accounts/", "GET,POST /dang-ky/   GET,POST /dang-nhap/\nGET /dang-xuat/   GET /tai-khoan/\nGoogle & Facebook OAuth2"),
        ("admissions/", "GET /ho-so/   GET,POST /ho-so/tao/\nGET /ho-so/chi-tiet/<pk>/\nGET,POST /ho-so/sua/<pk>/   POST /ho-so/xoa/<pk>/"),
        ("recommendation/", "GET /goi-y/<pk>/   GET /goi-y/chi-tiet/<kq_id>/\nGET,POST /goi-y/so-sanh/   GET,POST /goi-y/so-sanh/<pk>/\nGET /goi-y/lich-su/<pk>/   POST /goi-y/lich-su/<pk>/xoa/"),
        ("quantri/", "GET /quan-tri/dashboard/   GET /quan-tri/du-lieu/\nGET,POST /quan-tri/cap-nhat/   POST /quan-tri/cap-nhat/chay/\nGET /quan-tri/ai/   POST /quan-tri/ai/huan-luyen/\nCRUD /quan-tri/nguoi-dung/"),
    ]
    y = 34
    layer_x = 336
    s.rect(layer_x, 34, 118, 34, fill=LIGHTNAVY, stroke=NAVY, sw=1.0, rx=4)
    s.text(layer_x + 59, 44, "View tầng web (Django)", size=7.4, fill=NAVY,
           anchor="middle", bold=True)
    s.text(layer_x + 59, 57, "urls.py → views.py", size=6.4, fill=GRAY7, anchor="middle")

    for i, (grp, eps) in enumerate(rows):
        lines = eps.split("\n")
        h = max(20, 9 + len(lines) * 9.5)
        s.rect(4, y, 74, h, fill=WARM, stroke=MAROON, sw=0.9, rx=4)
        s.text(41, y + h / 2, grp, size=7.4, fill=MAROON, anchor="middle",
               bold=True, font=MONO)
        s.rect(84, y, 244, h, fill=WHITE, stroke=NAVY, sw=0.7, rx=3)
        s.multiline(88, y + 8, lines, size=6.2, fill=GRAY7, font=MONO, lh=1.45)
        s.line(84 + 244 + 2, y + h / 2, layer_x - 2, y + h / 2, stroke=GRAY, sw=0.7)
        y += h + 6

    # các tầng phía sau
    ly = y + 4
    layers = [
        ("services.py — lọc cứng + xếp hạng", LIGHTFOREST, GREEN),
        ("ml/predict.py — Random Forest (RAM)", WARM, MAROON),
        ("Django ORM — models.py (managed=False)", LIGHTNAVY, NAVY),
        ("MySQL 8.0 — CSDL uni_map", LIGHT, GRAY7),
    ]
    for i, (t, fill, accent) in enumerate(layers):
        s.rect(layer_x, ly, 118, 22, fill=fill, stroke=accent, sw=0.9, rx=4)
        s.text(layer_x + 59, ly + 11, t, size=6.4, fill=accent, anchor="middle", bold=True)
        if i < len(layers) - 1:
            s.line(layer_x + 59, ly + 22, layer_x + 59, ly + 27, stroke=GRAY7, sw=0.9,
                   marker_end=GRAY7)
        ly += 27

    s.text(W / 2, 14, "SƠ ĐỒ ĐỊNH TUYẾN URL → TẦNG XỬ LÝ", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    save(s, "h-api")


# =====================================================================
#  H6 — IFD (luồng giao diện)
# =====================================================================
def fig_ifd():
    s = Svg(W, 292)

    def scr(x, y, w, title, url, accent=NAVY, fill=WHITE):
        h = 30.0
        s.rect(x, y, w, h, fill=fill, stroke=accent, sw=1.0, rx=4)
        s.text(x + w / 2, y + 11, title, size=6.8, fill=accent, anchor="middle", bold=True)
        s.text(x + w / 2, y + 22, url, size=5.8, fill=GRAY, anchor="middle", font=MONO)
        return (x, y, w, h)

    sw_, sh_ = 100.0, 30.0
    # các hàng được dời nhẹ để đường nối gấp khúc chạy ở hành lang trống,
    # không cắt xuyên qua khối
    row1 = [scr(8, 34, sw_, "Trang chủ", "/", MAROON, WARM),
            scr(120, 34, sw_, "Tra cứu điểm chuẩn", "/tra-cuu/"),
            scr(232, 34, sw_, "Danh sách trường", "/truong/"),
            scr(344, 34, sw_, "Chi tiết trường", "/truong/<ma>/")]
    row2 = [scr(8, 96, sw_, "Đăng nhập", "/dang-nhap/"),
            scr(120, 96, sw_, "Đăng ký", "/dang-ky/"),
            scr(232, 96, sw_, "Trang tài khoản", "/tai-khoan/"),
            scr(344, 96, sw_, "Quản lý hồ sơ", "/ho-so/")]
    row3 = [scr(8, 158, sw_, "Nhập / sửa hồ sơ", "/ho-so/tao/"),
            scr(120, 158, sw_, "Chi tiết hồ sơ", "/ho-so/chi-tiet/"),
            scr(232, 158, sw_, "Kết quả gợi ý AI", "/goi-y/<pk>/", MAROON, WARM),
            scr(344, 158, sw_, "Lời giải thích", "/goi-y/chi-tiet/", MAROON, WARM)]
    row4 = [scr(8, 222, sw_, "Dashboard", "/quan-tri/dashboard/"),
            scr(120, 222, sw_, "Quản lý dữ liệu", "/quan-tri/du-lieu/"),
            scr(232, 222, sw_, "Trang AI", "/quan-tri/ai/"),
            scr(344, 222, sw_, "Quản lý người dùng", "/quan-tri/nguoi-dung/")]

    def ar(a, b, dash=None, color=MAROON, label=None):
        pass  # luồng phụ được vẽ thủ công bên dưới để không cắt qua khối

    for r in (row1, row2, row3, row4):
        for i in range(len(r) - 1):
            s.line(r[i][0] + r[i][2], r[i][1] + sh_ / 2, r[i + 1][0] - 2,
                   r[i + 1][1] + sh_ / 2, stroke=MAROON, sw=1.0, marker_end=MAROON)

    # luồng phụ: dùng đường gấp khúc chạy trong hành lang trống giữa các hàng
    # row1[1] -> row2[0]: xuống từ đáy khối "Tra cứu" sang trái, vào đỉnh "Đăng nhập"
    s.line(170, 64, 170, 80, stroke=MAROON, sw=1.0, dash="4,2")
    s.line(170, 80, 58, 80, stroke=MAROON, sw=1.0, dash="4,2")
    s.line(58, 80, 58, 94, stroke=MAROON, sw=1.0, dash="4,2", marker_end=MAROON)
    s.label(114, 80, "cần đăng nhập", size=6, color=MAROON, bg=WHITE)
    # row2[0] -> row2[1]: ngang nét đứt
    s.line(108, 111, 118, 111, stroke=MAROON, sw=1.0, dash="4,2", marker_end=MAROON)
    # row2[2] -> row3[0]: xuống từ đáy "Trang tài khoản", sang trái, vào đỉnh "Nhập hồ sơ"
    s.line(282, 126, 282, 142, stroke=MAROON, sw=1.0, dash="4,2")
    s.line(282, 142, 58, 142, stroke=MAROON, sw=1.0, dash="4,2")
    s.line(58, 142, 58, 156, stroke=MAROON, sw=1.0, dash="4,2", marker_end=MAROON)
    # row3[1] -> row3[2]: ngang nét liền có nhãn
    s.line(220, 173, 230, 173, stroke=MAROON, sw=1.0, marker_end=MAROON)
    s.label(225, 162, "chạy gợi ý", size=6, color=MAROON, bg=WHITE)
    # row3[2] -> row3[3]: ngang nét liền
    s.line(332, 173, 342, 173, stroke=MAROON, sw=1.0, marker_end=MAROON)
    # row4[2] -> row3[3]: lên từ đỉnh "Trang AI" sang phải, vào đáy "Lời giải thích"
    s.line(282, 220, 282, 206, stroke=GOLD, sw=1.0, dash="4,2")
    s.line(282, 206, 394, 206, stroke=GOLD, sw=1.0, dash="4,2")
    s.line(394, 206, 394, 190, stroke=GOLD, sw=1.0, dash="4,2", marker_end=GOLD)
    s.label(338, 206, "huấn luyện lại", size=6, color=GOLD, bg=WHITE)

    s.text(W / 2, 14, "SƠ ĐỒ LUỒNG GIAO DIỆN (IFD)", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    s.text(W / 2, 286, "nét liền: luồng chính    nét đứt: luồng phụ / quay về / phụ thuộc quyền",
           size=6.8, fill=GRAY, anchor="middle", italic=True)
    save(s, "h-ifd")


# =====================================================================
#  H7 — Sequence: đăng nhập
# =====================================================================
def fig_seq_login():
    parts = [("Học sinh", 40), ("Trình duyệt", 130), ("accounts.views", 230),
             ("Cache\n(rate limit)", 325), ("CSDL\nauth_user", 418)]
    s = Svg(W, 250)
    for name, x in parts:
        s.rect(x - 34, 30, 68, 24, fill=LIGHTNAVY, stroke=NAVY, sw=0.9, rx=4)
        s.multiline(x, 38 if "\n" in name else 42, name.split("\n"), size=6.6,
                    fill=NAVY, anchor="middle", bold=True, lh=1.3)
        s.line(x, 54, x, 232, stroke=GRAY, sw=0.7, dash="4,3")

    def msg(y, a, b, text, ret=False):
        color = NAVY if ret else MAROON
        s.line(a, y, b, y, stroke=color, sw=0.9, dash="4,2" if ret else None,
               marker_end=color)
        s.label((a + b) / 2, y - 6, text, size=6.1, color=color, bg=WHITE)

    msg(68, 40, 130, "1. nhập username, password")
    msg(82, 130, 230, "2. POST /dang-nhap/")
    msg(96, 230, 325, "3. _bi_khoa(IP, user)")
    msg(110, 325, 230, "4. trạng thái khoá", ret=True)
    s.rect(122, 118, 350, 20, fill=LIGHT, stroke=MAROON, sw=0.7, rx=3, dash="3,2")
    s.text(126, 128, "[số lần sai ≥ 5]", size=6.0, fill=MAROON, bold=True)
    msg(134, 230, 130, "5a. báo lỗi tạm khoá 5 phút", ret=True)
    s.rect(122, 148, 350, 74, fill="#FCFCFC", stroke=MAROON, sw=0.7, rx=3, dash="3,2")
    s.text(126, 158, "[hợp lệ / chưa bị khoá]", size=6.0, fill=MAROON, bold=True)
    msg(170, 230, 418, "5b. authenticate(user, password)")
    msg(184, 230, 325, "6a. [sai] _ghi_nhan_sai() +1")
    msg(196, 230, 130, "6b. báo lỗi đăng nhập không đúng", ret=True)
    msg(210, 230, 325, "7a. [đúng] _xoa_bo_dem()")
    msg(222, 230, 418, "7b. login() tạo session")
    msg(234, 230, 130, "7c. 302 → /ho-so/", ret=True)

    s.text(W / 2, 14, "SƠ ĐỒ TRÌNH TỰ — UC-03 ĐĂNG NHẬP (CÓ RATE LIMIT)", size=9.5,
           fill=NAVY, anchor="middle", bold=True, spacing="1")
    save(s, "h-seq-dangnhap")


# =====================================================================
#  H8 — Sequence: gợi ý AI
# =====================================================================
def fig_seq_recommend():
    s = Svg(W, 400)
    parts = [("Học sinh", 40), ("views.py", 125), ("services.py", 215),
             ("ml/predict.py", 305), ("CSDL uni_map", 420)]
    for name, x in parts:
        s.rect(x - 34, 30, 68, 22, fill=LIGHTNAVY, stroke=NAVY, sw=0.9, rx=4)
        s.text(x, 41, name, size=6.4, fill=NAVY, anchor="middle", bold=True)
        s.line(x, 52, x, 386, stroke=GRAY, sw=0.7, dash="4,3")

    def msg(y, a, b, text, ret=False):
        color = NAVY if ret else MAROON
        s.line(a, y, b, y, stroke=color, sw=0.9, dash="4,2" if ret else None,
               marker_end=color)
        s.label((a + b) / 2, y - 6, text, size=5.8, color=color, bg=WHITE)

    msg(68, 40, 125, "1. bấm nhận gợi ý (GET /goi-y/<pk>/)")
    msg(84, 125, 215, "2. goi_y_nguyen_vong(ho_so)")
    msg(100, 215, 420, "3. lọc cứng tổ hợp, vùng miền")
    msg(116, 420, 215, "4. N nguyện vọng ứng viên", ret=True)
    msg(132, 215, 305, "5. cham_xac_suat(ds, điểm)")

    # nhánh A — mô hình sẵn sàng trong RAM
    s.rect(56, 146, 396, 52, fill=LIGHTFOREST, stroke=GREEN, sw=0.7, rx=3, dash="3,2")
    s.text(60, 158, "[mô hình sẵn sàng trong RAM]", size=5.8, fill=GREEN, bold=True)
    s.text(60, 174, "vector hoá 27 chiều → predict_proba() → mảng xác suất p",
           size=5.6, fill=GREEN)
    s.text(60, 188, "thời gian suy luận cho 30 nguyện vọng dưới 50 ms", size=5.6, fill=GREEN)
    msg(214, 305, 215, "trả về p (AI_RANDOM_FOREST)", ret=True)

    # nhánh B — lỗi nạp mô hình
    s.rect(56, 228, 396, 44, fill=WARM, stroke=MAROON, sw=0.7, rx=3, dash="3,2")
    s.text(60, 240, "[lỗi nạp mô hình / thiếu model.pkl]", size=5.8, fill=MAROON, bold=True)
    s.text(60, 256, "xếp hạng theo margin thuần, đánh dấu FALLBACK_MARGIN, HTTP 200",
           size=5.6, fill=MAROON)
    msg(288, 305, 215, "danh sách margin (FALLBACK_MARGIN)", ret=True)

    s.text(56, 306, "phân tầng 3 mức + sinh lời giải thích", size=5.8, fill=NAVY)
    msg(320, 215, 420, "6. lưu lan_goi_y, ket_qua_goi_y")
    msg(338, 215, 125, "7. top 30 nguyện vọng đã phân tầng", ret=True)
    msg(356, 125, 40, "8. render giao diện phân tầng", ret=True)

    s.text(W / 2, 14, "SƠ ĐỒ TRÌNH TỰ — UC-05 NHẬN GỢI Ý (AI + DỰ PHÒNG)", size=9.5,
           fill=NAVY, anchor="middle", bold=True, spacing="1")
    save(s, "h-seq-goiy")


# =====================================================================
#  H9 — Sequence: cập nhật dữ liệu + huấn luyện
# =====================================================================
def fig_seq_update():
    s = Svg(W, 268)
    parts = [("Quản trị viên", 40), ("quantri.views", 130), ("CSDL uni_map", 220),
             ("gen_dataset.py", 310), ("train.py / RAM", 420)]
    for name, x in parts:
        s.rect(x - 34, 30, 68, 22, fill=LIGHTNAVY, stroke=NAVY, sw=0.9, rx=4)
        s.text(x, 41, name, size=6.2, fill=NAVY, anchor="middle", bold=True)
        s.line(x, 52, x, 250, stroke=GRAY, sw=0.7, dash="4,3")

    def msg(y, a, b, text, ret=False):
        color = NAVY if ret else MAROON
        s.line(a, y, b, y, stroke=color, sw=0.9, dash="4,2" if ret else None,
               marker_end=color)
        s.label((a + b) / 2, y - 6, text, size=5.8, color=color, bg=WHITE)

    msg(68, 40, 130, "1. POST /quan-tri/cap-nhat/chay/")
    msg(84, 130, 220, "2. nạp CSV mới vào diem_chuan")
    msg(100, 130, 220, "3. cập nhật cua_so_nam (trượt 10 năm)")
    msg(116, 220, 130, "4. xác nhận + ghi lan_cap_nhat", ret=True)
    msg(132, 130, 40, "5. thông báo nạp dữ liệu thành công", ret=True)

    msg(152, 40, 130, "6. POST /quan-tri/ai/huan-luyen/")
    msg(168, 130, 310, "7. build_split(target_year, lookback=6)")
    msg(184, 310, 220, "8. đọc chuỗi lịch sử điểm chuẩn")
    s.text(314, 200, "sinh 11 DELTAS + trích 27 đặc trưng", size=5.8, fill=NAVY)
    msg(212, 310, 130, "9. tập dữ liệu phẳng huấn luyện", ret=True)

    msg(232, 130, 420, "10. train_and_export(X, y)")
    s.text(424, 244, "RF fit → dump pkl → xoá _CACHE", size=5.6, fill=NAVY, anchor="end")
    msg(258, 420, 130, "11. chỉ số kiểm định (Accuracy, ROC-AUC)", ret=True)

    s.text(W / 2, 14, "SƠ ĐỒ TRÌNH TỰ — UC-09 + UC-10 CẬP NHẬT & HUẤN LUYỆN LẠI",
           size=9.5, fill=NAVY, anchor="middle", bold=True, spacing="1")
    save(s, "h-seq-capnhat")


# =====================================================================
#  H10 — Quy trình sinh nhãn (pipeline dữ liệu)
# =====================================================================
def fig_pipeline():
    s = Svg(W, 175)
    steps = [
        ("Dữ liệu thô", "crawl_diemchuan.py\nCSV theo năm", LIGHTNAVY, NAVY),
        ("Làm sạch", "chuẩn hoá tên ngành\nánh xạ nhóm ngành", LIGHT, NAVY),
        ("Nạp CSDL", "import_mysql.py\ndiem_chuan", LIGHT, NAVY),
        ("Trích đặc trưng", "gen_dataset.py\ncửa sổ 6 năm", WARM, MAROON),
        ("Sinh nhãn", "11 mức DELTAS\n±0,2 … ±3,0", WARM, MAROON),
        ("Huấn luyện", "train.py\nRandom Forest", LIGHTFOREST, GREEN),
    ]
    bw, gap, x0, y0, bh = 66.0, 10.0, 4.0, 44.0, 74.0
    for i, (t, d, fill, accent) in enumerate(steps):
        x = x0 + i * (bw + gap)
        s.rect(x, y0, bw, bh, fill=fill, stroke=accent, sw=1.1, rx=5)
        s.text(x + bw / 2, y0 + 14, t, size=7.6, fill=accent, anchor="middle", bold=True)
        s.multiline(x + bw / 2, y0 + 32, d.split("\n"), size=6.0, fill=GRAY7,
                    anchor="middle", lh=1.5)
        if i < len(steps) - 1:
            s.line(x + bw + 1, y0 + bh / 2, x + bw + gap - 1, y0 + bh / 2,
                   stroke=MAROON, sw=1.2, marker_end=MAROON)

    # nhánh rẽ: chia tập
    s.path(f"M{x0 + 4 * (bw + gap) + bw / 2},{y0 + bh} L{x0 + 4 * (bw + gap) + bw / 2},140 "
           f"L{x0 + 5 * (bw + gap) + bw / 2},140 L{x0 + 5 * (bw + gap) + bw / 2},{y0 + bh + 2}",
           stroke=GREEN, sw=1.0, dash="4,2", marker_end=GREEN)
    s.text(W / 2, 150, "chia cứng theo thời gian:  train 2021–2024  |  test 2025 (đo một lần)",
           size=6.8, fill=GREEN, anchor="middle", bold=True)

    s.text(W / 2, 16, "PIPELINE DỮ LIỆU NGOẠI TUYẾN", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    s.text(W / 2, 30, "6 bước, chạy trước khi web khởi động — tách hoàn toàn khỏi luồng phục vụ",
           size=7, fill=GRAY, anchor="middle", italic=True)
    save(s, "h-pipeline")


# =====================================================================
#  H11 — Biểu đồ cột so sánh mô hình (vector)
# =====================================================================
def fig_model_bars():
    s = Svg(W, 205)
    metrics = [("Accuracy", 0.7214, 0.7456), ("ROC-AUC", 0.7535, 0.8354),
               ("F1 (lớp Đỗ)", 0.7183, 0.7493)]
    x0, y0, plot_h, bw = 60.0, 40.0, 110.0, 26.0
    group_gap = 42.0
    for i, (name, dt, rf) in enumerate(metrics):
        gx = x0 + 34 + i * (2 * bw + group_gap)
        for j, (val, color, lab) in enumerate([(dt, GRAY, "DT"), (rf, MAROON, "RF")]):
            h = val * plot_h
            s.rect(gx + j * (bw + 4), y0 + plot_h - h, bw, h, fill=color, stroke=None, rx=2)
            s.text(gx + j * (bw + 4) + bw / 2, y0 + plot_h - h - 8,
                   f"{val:.4f}".replace(".", ","), size=6.6, fill=color, anchor="middle", bold=True)
            s.text(gx + j * (bw + 4) + bw / 2, y0 + plot_h + 10, lab, size=6.4,
                   fill=color, anchor="middle", bold=True)
        s.text(gx + bw + 2, y0 + plot_h + 24, name, size=7.2, fill=NAVY, anchor="middle", bold=True)

    # trục
    s.line(x0 + 20, y0 + plot_h, x0 + 20, y0, stroke=NAVY, sw=1.0)
    s.line(x0 + 20, y0 + plot_h, W - 10, y0 + plot_h, stroke=NAVY, sw=1.0)
    for tick in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        yy = y0 + plot_h - tick * plot_h
        s.line(x0 + 16, yy, x0 + 20, yy, stroke=NAVY, sw=0.8)
        s.text(x0 + 13, yy, f"{tick:.1f}".replace(".", ","), size=6.0, fill=GRAY7, anchor="end")
    s.text(x0 - 6, y0 + plot_h / 2, "giá trị", size=6.4, fill=GRAY7, anchor="middle")

    s.text(W / 2, 14, "SO SÁNH TRỰC QUAN HAI MÔ HÌNH TRÊN TẬP KIỂM THỬ 2025",
           size=9.5, fill=NAVY, anchor="middle", bold=True, spacing="1")
    s.text(W / 2, 191, "Cột xám: Decision Tree (đối chứng) — Cột đỏ: Random Forest (mô hình chính)",
           size=6.8, fill=GRAY, anchor="middle", italic=True)
    save(s, "h-model-bars")


# =====================================================================
#  H12 — Tầm quan trọng đặc trưng (thanh ngang)
# =====================================================================
def fig_feature_importance():
    feats = [("margin", 0.6060), ("diem_thi", 0.2181), ("diem_moi_nhat", 0.0509),
             ("diem_tb", 0.0425), ("bien_dong", 0.0164), ("xu_huong", 0.0164),
             ("so_nam_co_dl", 0.0120), ("nhóm ngành (15 cột)", 0.0180),
             ("vùng miền (3 cột)", 0.0090), ("phương thức (2 cột)", 0.0080)]
    s = Svg(W, 235)
    x0, y, bar_max, row_h = 118.0, 40.0, 300.0, 17.0
    mx = max(v for _, v in feats)
    for i, (name, val) in enumerate(feats):
        yy = y + i * row_h
        w = val / mx * bar_max
        color = MAROON if i < 2 else (GOLD if i < 6 else GRAY)
        s.rect(x0, yy, w, row_h - 5, fill=color, stroke=None, rx=2)
        s.text(x0 - 4, yy + (row_h - 5) / 2, name, size=6.8, fill=NAVY,
               anchor="end", bold=(i < 2), font=MONO if i < 6 else FONT_SAFE)
        s.text(x0 + w + 4, yy + (row_h - 5) / 2, f"{val:.4f}".replace(".", ","),
               size=6.4, fill=GRAY7)
    s.line(x0, y + len(feats) * row_h, x0, y - 4, stroke=NAVY, sw=0.9)
    s.text(W / 2, 14, "TẦM QUAN TRỌNG CỦA CÁC ĐẶC TRƯNG (feature_importances_)",
           size=9.5, fill=NAVY, anchor="middle", bold=True, spacing="1")
    s.text(W / 2, 222, "Hai đặc trưng đầu chiếm 82,4% tổng đóng góp; nhóm lịch sử đóng vai trò hiệu chỉnh rủi ro",
           size=6.8, fill=GRAY, anchor="middle", italic=True)
    save(s, "h-feature-importance")


FONT_SAFE = "'Times New Roman', serif"


# =====================================================================
#  H13 — Biểu đồ phân tầng nguyện vọng
# =====================================================================
def fig_tiers():
    s = Svg(W, 150)
    bands = [
        ("THỬ SỨC", "p < 0,40", 0.0, 0.40, "#FDF0E4", "#C05621"),
        ("VỪA SỨC", "0,40 ≤ p < 0,80", 0.40, 0.80, "#E8F0FA", "#1F4E78"),
        ("AN TOÀN", "p ≥ 0,80", 0.80, 1.00, "#E9F5EA", GREEN),
    ]
    x0, y0, w, h = 50.0, 52.0, 380.0, 46.0
    for name, rng, a, b, fill, accent in bands:
        x = x0 + a * w
        bw = (b - a) * w
        s.rect(x, y0, bw, h, fill=fill, stroke=accent, sw=1.2)
        s.text(x + bw / 2, y0 + 18, name, size=9, fill=accent, anchor="middle", bold=True)
        s.text(x + bw / 2, y0 + 32, rng, size=7, fill=accent, anchor="middle")

    # trục x
    s.line(x0, y0 + h + 8, x0 + w, y0 + h + 8, stroke=NAVY, sw=1.0)
    for v in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        xx = x0 + v * w
        s.line(xx, y0 + h + 8, xx, y0 + h + 13, stroke=NAVY, sw=0.9)
        s.text(xx, y0 + h + 22, f"{v:.1f}".replace(".", ","), size=6.6, fill=GRAY7, anchor="middle")
    s.text(x0 + w / 2, y0 + h + 36, "xác suất trúng tuyển dự đoán p", size=7, fill=NAVY,
           anchor="middle", bold=True)

    s.text(W / 2, 16, "BA TẦNG PHÂN LOẠI NGUYỆN VỌNG", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    s.text(W / 2, 32, "Ngưỡng cố định, công khai trên giao diện — người dùng không phải tự ước đoán",
           size=7, fill=GRAY, anchor="middle", italic=True)
    save(s, "h-tiers")


# =====================================================================
#  H14 — Kiến trúc triển khai (deployment)
# =====================================================================
def fig_deploy():
    s = Svg(W, 200)
    # khối ngoài
    s.rect(4, 40, 300, 130, fill="#FAFBFC", stroke=NAVY, sw=1.2, rx=6, dash="5,3")
    s.text(10, 52, "Máy chủ ứng dụng (VPS / hosting)", size=7.4, fill=NAVY, bold=True)

    s.rect(20, 66, 110, 44, fill=LIGHTNAVY, stroke=NAVY, sw=1.0, rx=4)
    s.text(75, 78, "Nginx / Apache", size=7.4, fill=NAVY, anchor="middle", bold=True)
    s.text(75, 92, "phục vụ /static/ và /media/", size=6.2, fill=GRAY7, anchor="middle")
    s.text(75, 102, "proxy → Gunicorn", size=6.2, fill=GRAY7, anchor="middle")

    s.rect(146, 66, 140, 44, fill=LIGHTFOREST, stroke=GREEN, sw=1.0, rx=4)
    s.text(216, 78, "Django 5.2 + Gunicorn", size=7.4, fill=GREEN, anchor="middle", bold=True)
    s.text(216, 92, "6 ứng dụng · ORM", size=6.2, fill=GRAY7, anchor="middle")
    s.text(216, 102, "model.pkl nạp sẵn trong RAM", size=6.2, fill=GRAY7, anchor="middle")

    s.rect(20, 122, 110, 38, fill=WARM, stroke=MAROON, sw=1.0, rx=4)
    s.text(75, 134, "MySQL 8.0", size=7.4, fill=MAROON, anchor="middle", bold=True)
    s.text(75, 148, "CSDL uni_map · utf8mb4", size=6.2, fill=GRAY7, anchor="middle")

    s.rect(146, 122, 140, 38, fill=WHITE, stroke=NAVY, sw=1.0, rx=4)
    s.text(216, 134, "Tệp tĩnh & media", size=7.4, fill=NAVY, anchor="middle", bold=True)
    s.text(216, 148, "Tailwind CDN · logo trường · avatar", size=6.2, fill=GRAY7, anchor="middle")

    s.line(130, 88, 144, 88, stroke=GRAY7, sw=1.0, marker_end=GRAY7)
    s.line(216, 110, 216, 120, stroke=GRAY7, sw=1.0, marker_end=GRAY7)

    # client
    s.rect(330, 66, 126, 90, fill=WHITE, stroke=NAVY, sw=1.1, rx=6)
    s.text(393, 80, "Người dùng", size=7.6, fill=NAVY, anchor="middle", bold=True)
    s.text(393, 96, "Trình duyệt", size=6.6, fill=GRAY7, anchor="middle")
    s.text(393, 108, "máy tính / di động", size=6.6, fill=GRAY7, anchor="middle")
    s.text(393, 126, "HTTPS · responsive", size=6.2, fill=GRAY, anchor="middle", italic=True)
    s.text(393, 140, "Tailwind CSS", size=6.2, fill=GRAY, anchor="middle", italic=True)
    s.line(328, 110, 306, 110, stroke=MAROON, sw=1.2, marker_end=MAROON)
    s.label(317, 104, "HTTPS", size=6.2, color=MAROON, bg=WHITE)

    s.text(W / 2, 16, "SƠ ĐỒ TRIỂN KHAI", size=9.5, fill=NAVY, anchor="middle",
           bold=True, spacing="1")
    s.text(W / 2, 32, "Cấu hình tham chiếu: 1 VPS 2 vCPU / 2 GB RAM chạy được toàn bộ hệ thống",
           size=7, fill=GRAY, anchor="middle", italic=True)
    save(s, "h-deploy")


# =====================================================================
#  H15 — Vòng đời cập nhật dữ liệu hằng năm (cửa sổ trượt)
# =====================================================================
def fig_sliding_window():
    s = Svg(W, 175)
    s.text(W / 2, 16, "CƠ CHẾ CỬA SỔ TRƯỢT 10 NĂM", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    s.text(W / 2, 30, "Cập nhật năm mới chỉ cần đổi ánh xạ cột — không ALTER TABLE, không sửa mã nguồn",
           size=7, fill=GRAY, anchor="middle", italic=True)

    cw, gap, x0 = 40.0, 3.0, 26.0

    def row(y, start_year, label, accent):
        s.text(x0 - 4, y + 14, label, size=7, fill=accent, anchor="end", bold=True)
        for i in range(10):
            x = x0 + i * (cw + gap)
            year = start_year + i
            fill = WARM if year >= 2025 else LIGHT
            s.rect(x, y, cw, 28, fill=fill, stroke=accent, sw=0.9, rx=3)
            s.text(x + cw / 2, y + 10, f"cột {i + 1}", size=6.0, fill=GRAY7, anchor="middle")
            s.text(x + cw / 2, y + 21, str(year), size=7.4, fill=accent, anchor="middle", bold=True)

    row(52, 2016, "Trước\n(2025)", NAVY)
    row(104, 2017, "Sau\n(2026)", MAROON)

    s.text(W / 2, 152, "Quản trị viên chỉ thay đổi bảng cua_so_nam qua giao diện: vị trí 1 → năm 2017, … vị trí 10 → năm 2026.",
           size=6.8, fill=GRAY7, anchor="middle")
    s.text(W / 2, 165, "Hệ thống hiển thị tự trượt; AI dùng 6 năm gần nhất trong cửa sổ.",
           size=6.8, fill=GRAY7, anchor="middle")
    save(s, "h-sliding-window")


# =====================================================================
#  H16 — Sơ đồ khối thuật toán Random Forest
# =====================================================================
def fig_rf_diagram():
    s = Svg(W, 215)
    s.text(W / 2, 14, "NGUYÊN LÝ RANDOM FOREST", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")

    s.rect(6, 60, 92, 60, fill=LIGHT, stroke=NAVY, sw=1.0, rx=5)
    s.text(52, 74, "Tập huấn luyện", size=7.4, fill=NAVY, anchor="middle", bold=True)
    s.text(52, 88, "913.924 mẫu", size=6.8, fill=GRAY7, anchor="middle")
    s.text(52, 100, "27 đặc trưng", size=6.8, fill=GRAY7, anchor="middle")
    s.text(52, 112, "nhãn đỗ/trượt", size=6.8, fill=GRAY7, anchor="middle")

    tree_y = [36, 76, 116]
    for i, ty in enumerate(tree_y):
        s.path(f"M98,90 L128,{ty + 20}", stroke=MAROON, sw=1.0, marker_end=MAROON)
        s.rect(130, ty, 74, 40, fill=WARM, stroke=MAROON, sw=0.9, rx=4)
        s.text(167, ty + 11, f"Cây {i + 1}", size=7, fill=MAROON, anchor="middle", bold=True)
        s.multiline(167, ty + 21, ["bootstrap mẫu", "ngẫu nhiên √27 đặc trưng"],
                    size=5.4, fill=GRAY7, anchor="middle", lh=1.4)
        s.path(f"M204,{ty + 20} L236,90", stroke=MAROON, sw=1.0, marker_end=MAROON)

    s.rect(238, 60, 96, 60, fill=LIGHTFOREST, stroke=GREEN, sw=1.1, rx=5)
    s.text(286, 74, "Tổng hợp", size=7.4, fill=GREEN, anchor="middle", bold=True)
    s.text(286, 88, "trung bình 100 cây", size=6.6, fill=GRAY7, anchor="middle")
    s.text(286, 100, "P(y=1|x) = 1/T · Σ Pₜ", size=6.4, fill=GRAY7, anchor="middle")
    s.text(286, 112, "→ xác suất trúng tuyển", size=6.2, fill=GREEN, anchor="middle")

    s.line(336, 90, 366, 90, stroke=GREEN, sw=1.3, marker_end=GREEN)
    s.rect(368, 60, 86, 60, fill=WARM, stroke=MAROON, sw=1.1, rx=5)
    s.text(411, 74, "Phân tầng", size=7.4, fill=MAROON, anchor="middle", bold=True)
    s.text(411, 88, "p ≥ 0,80 → An toàn", size=6.2, fill=GRAY7, anchor="middle")
    s.text(411, 99, "0,40–0,80 → Vừa sức", size=6.2, fill=GRAY7, anchor="middle")
    s.text(411, 110, "p < 0,40 → Thử sức", size=6.2, fill=GRAY7, anchor="middle")

    s.text(W / 2, 162, "Mỗi cây học trên một mẫu bootstrap khác nhau và chỉ xét √27 ≈ 5 đặc trưng tại mỗi lần chia nút,",
           size=6.8, fill=GRAY7, anchor="middle")
    s.text(W / 2, 176, "nhờ đó giảm phương sai và hạn chế quá khớp so với một cây đơn lẻ.",
           size=6.8, fill=GRAY7, anchor="middle")
    save(s, "h-rf")


# =====================================================================
#  H17 — Sơ đồ cây quyết định đơn giản (minh hoạ Gini)
# =====================================================================
def fig_decision_tree():
    s = Svg(W, 190)
    s.text(W / 2, 14, "MINH HOẠ MỘT CÂY QUYẾT ĐỊNH", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")

    def node(x, y, w, text, fill=WHITE, stroke=NAVY, bold=False, size=6.8):
        s.rect(x - w / 2, y - 12, w, 24, fill=fill, stroke=stroke, sw=0.9, rx=3)
        s.text(x, y, text, size=size, fill=stroke if bold else INK, anchor="middle", bold=bold)

    node(W / 2, 44, 140, "margin ≥ 0 ?", WARM, MAROON, True)
    node(W / 2 - 105, 92, 120, "diem_thi ≥ 24 ?", WHITE, NAVY)
    node(W / 2 + 105, 92, 120, "xu_huong ≥ 0 ?", WHITE, NAVY)
    node(W / 2 - 150, 142, 84, "TRƯỢT", "#FBEEEE", MAROON, True, 7.4)
    node(W / 2 - 60, 142, 84, "ĐỖ (cao)", LIGHTFOREST, GREEN, True, 7.4)
    node(W / 2 + 60, 142, 84, "ĐỖ", LIGHTFOREST, GREEN, True, 7.4)
    node(W / 2 + 150, 142, 84, "TRƯỢT (nguy cơ)", "#FBEEEE", MAROON, True, 6.6)

    s.line(W / 2 - 60, 56, W / 2 - 105, 80, stroke=GRAY7, sw=0.9, marker_end=GRAY7)
    s.line(W / 2 + 60, 56, W / 2 + 105, 80, stroke=GRAY7, sw=0.9, marker_end=GRAY7)
    s.label(W / 2 - 92, 66, "không", size=6, color=GRAY7)
    s.label(W / 2 + 92, 66, "có", size=6, color=GRAY7)

    s.line(W / 2 - 145, 104, W / 2 - 150, 130, stroke=GRAY7, sw=0.9, marker_end=GRAY7)
    s.line(W / 2 - 65, 104, W / 2 - 60, 130, stroke=GRAY7, sw=0.9, marker_end=GRAY7)
    s.label(W / 2 - 160, 116, "không", size=6, color=GRAY7)
    s.label(W / 2 - 45, 116, "có", size=6, color=GRAY7)

    s.line(W / 2 + 65, 104, W / 2 + 60, 130, stroke=GRAY7, sw=0.9, marker_end=GRAY7)
    s.line(W / 2 + 145, 104, W / 2 + 150, 130, stroke=GRAY7, sw=0.9, marker_end=GRAY7)
    s.label(W / 2 + 45, 116, "có", size=6, color=GRAY7)
    s.label(W / 2 + 160, 116, "không", size=6, color=GRAY7)

    s.text(W / 2, 176, "Mỗi nút chọn ngưỡng làm giảm bất thuần Gini nhiều nhất: Gini(S) = 1 − Σ pₖ²",
           size=6.8, fill=GRAY7, anchor="middle", italic=True)
    save(s, "h-decision-tree")


# =====================================================================
#  H18 — Giao diện mockup: nhập hồ sơ
# =====================================================================
def fig_ui_profile():
    s = Svg(W, 200)
    s.rect(4, 26, 452, 160, fill=WHITE, stroke=NAVY, sw=1.2, rx=6)
    s.rect(4, 26, 452, 22, fill=NAVY, stroke=None, rx=6)
    s.rect(4, 40, 452, 8, fill=NAVY, stroke=None)
    s.text(W / 2, 37, "UNI CONNECT — NHẬP HỒ SƠ ĐIỂM NĂNG LỰC THÍ SINH",
           size=8, fill=WHITE, anchor="middle", bold=True, spacing="0.8")

    # form
    s.rect(16, 58, 428, 44, fill=LIGHT, stroke=GRAY3, sw=0.8, rx=4)
    s.text(24, 70, "Tên hồ sơ:", size=6.6, fill=NAVY, bold=True)
    s.rect(70, 62, 130, 16, fill=WHITE, stroke=GRAY3, sw=0.7, rx=2)
    s.text(75, 70, "Hồ sơ xét tuyển 2026", size=6.0, fill=GRAY7)
    s.text(212, 70, "Phương thức:", size=6.6, fill=NAVY, bold=True)
    s.rect(266, 62, 110, 16, fill=WHITE, stroke=GRAY3, sw=0.7, rx=2)
    s.text(271, 70, "Xét điểm thi THPT", size=6.0, fill=GRAY7)
    s.text(24, 90, "Điểm ưu tiên:", size=6.6, fill=NAVY, bold=True)
    s.rect(78, 82, 90, 16, fill=WHITE, stroke=GRAY3, sw=0.7, rx=2)
    s.text(83, 90, "0,50 (KV2 nông thôn)", size=6.0, fill=GRAY7)

    # bảng điểm môn
    s.rect(16, 110, 428, 36, fill="#F7FAFD", stroke=NAVY, sw=0.8, rx=4)
    s.text(24, 120, "BẢNG ĐIỂM TỪNG MÔN (thang 10):", size=6.6, fill=NAVY, bold=True)
    subs = [("Toán", "8,5"), ("Lý", "8,0"), ("Hóa", "8,5"), ("Sinh", "6,5"),
            ("Văn", "7,0"), ("Sử", "6,0"), ("Địa", "6,5")]
    for i, (name, val) in enumerate(subs):
        x = 24 + i * 59
        s.rect(x, 128, 50, 14, fill=WHITE, stroke=GRAY3, sw=0.6, rx=2)
        s.text(x + 6, 135, name, size=5.6, fill=GRAY7)
        s.text(x + 44, 135, val, size=6.2, fill=MAROON, anchor="end", bold=True)

    # tổng điểm
    s.rect(16, 152, 428, 26, fill=WARM, stroke=GOLD, sw=0.9, rx=4)
    s.text(24, 160, "TỔNG ĐIỂM TỔ HỢP TỰ ĐỘNG (đã gồm điểm ưu tiên):",
           size=6.6, fill=MAROON, bold=True)
    combos = [("A00 (Toán, Lý, Hóa)", "25,50"), ("A01 (Toán, Lý, Anh)", "25,00"),
              ("D01 (Toán, Văn, Anh)", "24,00")]
    for i, (name, val) in enumerate(combos):
        x = 24 + i * 140
        s.rect(x, 165, 128, 11, fill=WHITE, stroke=MAROON if i == 0 else GRAY3, sw=0.7, rx=2)
        s.text(x + 4, 170.5, f"{name}: {val}", size=5.8,
               fill=MAROON if i == 0 else NAVY, bold=(i == 0))

    s.text(W / 2, 14, "MÔ PHỎNG GIAO DIỆN NHẬP HỒ SƠ ĐIỂM", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    save(s, "h-ui-profile")


# =====================================================================
#  H19 — Giao diện mockup: kết quả phân tầng
# =====================================================================
def fig_ui_result():
    s = Svg(W, 215)
    s.rect(4, 26, 452, 178, fill=WHITE, stroke=NAVY, sw=1.2, rx=6)
    s.rect(4, 26, 452, 22, fill=NAVY, stroke=None, rx=6)
    s.rect(4, 40, 452, 8, fill=NAVY, stroke=None)
    s.text(W / 2, 37, "UNI CONNECT — KẾT QUẢ GỢI Ý NGUYỆN VỌNG", size=8, fill=WHITE,
           anchor="middle", bold=True, spacing="0.8")

    s.text(16, 60, "Hồ sơ: Khối A00 — Toán 8,5 · Lý 8,0 · Hóa 8,5 → 25,0 | Miền Trung",
           size=6.4, fill=NAVY)
    s.text(16, 72, "30 nguyện vọng phù hợp — 0,038 giây (AI Random Forest)", size=6.2, fill=GRAY)

    tiers = [
        ("AN TOÀN (p ≥ 80%) — 8 nguyện vọng", "#E9F5EA", GREEN, 82, [
            "ĐH Bách Khoa ĐN — CN Thông tin · A00 · 2025: 23,5 · 91,4% · +1,50",
            "ĐH Sư phạm ĐN — Sư phạm Tin học · A00 · 2025: 22,0 · 95,8% · +3,00"]),
        ("VỪA SỨC (40–80%) — 14 nguyện vọng", "#E8F0FA", "#1F4E78", 122, [
            "ĐH Bách Khoa ĐN — Kỹ thuật Phần mềm · A00 · 2025: 25,1 · 63,2% · −0,10",
            "ĐH Kinh tế ĐN — Thương mại Điện tử · A00 · 2025: 24,8 · 68,5% · +0,20"]),
        ("THỬ SỨC (p < 40%) — 8 nguyện vọng", "#FDF0E4", "#C05621", 162, [
            "ĐH Bách Khoa ĐN — CN Thông tin · A00 · 2025: 26,25 · 24,6% · −1,25",
            "ĐH SP Kỹ thuật TP.HCM — Robot & AI · A00 · 2025: 26,5 · 18,2% · −1,50"]),
    ]
    for title, fill, accent, y, rows in tiers:
        s.rect(14, y, 432, 36, fill=fill, stroke=accent, sw=1.0, rx=4)
        s.text(20, y + 9, title, size=6.6, fill=accent, bold=True)
        for i, r in enumerate(rows):
            s.text(20, y + 20 + i * 9, r, size=5.8, fill=GRAY7)

    s.text(W / 2, 14, "MÔ PHỎNG GIAO DIỆN PHÂN TẦNG KẾT QUẢ", size=9.5, fill=NAVY,
           anchor="middle", bold=True, spacing="1")
    save(s, "h-ui-result")


# =====================================================================
#  H20 — Kiểm thử: sơ đồ quy trình
# =====================================================================
def fig_testing():
    s = Svg(W, 155)
    s.text(W / 2, 14, "BA CẤP ĐỘ KIỂM THỬ", size=9.5, fill=NAVY, anchor="middle",
           bold=True, spacing="1")
    levels = [
        ("ĐƠN VỊ", "unit test", "Kiểm tra từng hàm:\ntính điểm tổ hợp, thứ tự\n27 đặc trưng, phân tầng", LIGHTNAVY, NAVY),
        ("TÍCH HỢP", "integration test", "Kiểm tra luồng đầy đủ:\nđăng nhập → hồ sơ →\ngợi ý → lưu kết quả", LIGHTFOREST, GREEN),
        ("CHỊU LỖI", "fault tolerance", "Xoá model.pkl, ngắt CSDL:\nhệ thống phải trả HTTP 200\nvà xếp hạng dự phòng", WARM, MAROON),
    ]
    bw, gap, x0, y0, bh = 132.0, 18.0, 14.0, 34.0, 96.0
    for i, (t, sub, d, fill, accent) in enumerate(levels):
        x = x0 + i * (bw + gap)
        s.rect(x, y0, bw, bh, fill=fill, stroke=accent, sw=1.1, rx=5)
        s.rect(x, y0, bw, 22, fill=accent, stroke=None, rx=5)
        s.rect(x, y0 + 16, bw, 6, fill=accent, stroke=None)
        s.text(x + bw / 2, y0 + 11, t, size=8, fill=WHITE, anchor="middle", bold=True)
        s.text(x + bw / 2, y0 + 32, sub, size=6.4, fill=accent, anchor="middle", italic=True)
        s.multiline(x + bw / 2, y0 + 48, d.split("\n"), size=6.2, fill=GRAY7,
                    anchor="middle", lh=1.55)
        if i < 2:
            s.line(x + bw + 2, y0 + bh / 2, x + bw + gap - 2, y0 + bh / 2,
                   stroke=MAROON, sw=1.3, marker_end=MAROON)

    s.text(W / 2, 144, "6 ca kiểm thử chức năng (TC-01 … TC-06) — tất cả đạt, chi tiết ở Bảng 4.2",
           size=6.8, fill=GRAY, anchor="middle", italic=True)
    save(s, "h-testing")


# =====================================================================
#  MAIN
# =====================================================================
def main():
    print("Sinh hình SVG cho báo cáo:")
    fig_kientruc()
    fig_pipeline()
    fig_erd()
    fig_usecase()
    fig_bfd()
    fig_api()
    fig_ifd()
    fig_seq_login()
    fig_seq_recommend()
    fig_seq_update()
    fig_rf_diagram()
    fig_decision_tree()
    fig_model_bars()
    fig_feature_importance()
    fig_tiers()
    fig_sliding_window()
    fig_deploy()
    fig_ui_profile()
    fig_ui_result()
    fig_testing()
    print(f"\nXong. {len(os.listdir(OUT))} tệp trong {OUT}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
