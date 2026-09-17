# -*- coding: utf-8 -*-
"""Render web/tra_cuu.html + web/trang_chu.html voi context gia de bat loi template
khi MySQL chua chay. Xoa file sau khi Laragon len (hoac giu lai lam self-check).
    PYTHONIOENCODING=utf-8 python _render_check.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import AnonymousUser  # noqa: E402
from django.core.paginator import Paginator  # noqa: E402
from django.template.loader import render_to_string  # noqa: E402
from django.test import RequestFactory  # noqa: E402

YEARS = [2021, 2022, 2023, 2024, 2025]
CUA_SO = [type("C", (), {"nam": y, "vi_tri": i + 1})() for i, y in enumerate(YEARS)]


def dong(tt, nganh, slug, tinh, vung, to_hop, diem, bien_dong, so_nam, chip=None):
    return {
        "theo_nam": [{"nam": y, "diem": d} for y, d in zip(YEARS, diem)],
        "chip": chip or {"cls": "bg-[#FEE2E2] text-[#DC2626] border-[#DC2626]/30",
                         "icon": "trending_up"},
        "ma_truong": tt, "truong": "Trường Đại học " + tt, "viet_tat": tt,
        "tinh_thanh": tinh, "vung_mien": vung,
        "nganh": "Ngành " + nganh, "nganh_slug": slug, "nhom_nganh": "CNTT",
        "ma_to_hop": to_hop, "ten_to_hop": "Toán, Lý, Hóa", "phuong_thuc": "thpt",
        "diem": diem, "diem_moi_nhat": diem[-1], "diem_tb": 28.0,
        "bien_dong": bien_dong, "xu_huong": "up", "so_nam_co_dl": so_nam,
    }


DS = [
    dong("HUST", "Khoa học máy tính", "khoa-hoc-may-tinh", "Hà Nội", "bac",
         "A00", [28.43, 28.29, 29.42, 28.53, 28.85], 0.10, 5),
    dong("NEU", "Hệ thống TTQL", "he-thong-ttql", "Hà Nội", "bac",
         "A01", [27.65, 27.40, 27.50, 27.55, None], -0.05, 4),
]

BO_LOC = {
    "tinh_thanh": [{"tinh_thanh": "Hà Nội", "so_truong": 70}],
    "vung_mien": [("bac", "Miền Bắc", 139)],
    "phuong_thuc": [("thpt", "THPT Quốc gia")],
    "to_hop": [("A00", "Toán, Lý, Hóa")],
    "nhom_nganh": [{"nhom_nganh": "CNTT", "so_nganh": 40}],
}

PARAMS = {"q": "abc", "truong": "", "nganh": "", "tinh_thanh": "Hà Nội",
          "vung_mien": "", "ma_to_hop": "", "phuong_thuc": "", "nhom_nganh": "",
          "nam": "", "sap_xep": "diem_desc"}


def kiem(ten, ctx, phai_co):
    r = RequestFactory().get("/tra-cuu/?q=abc&trang=3&tinh_thanh=H%C3%A0%20N%E1%BB%99i")
    r.user = AnonymousUser()
    try:
        html = render_to_string(ten, ctx, request=r)
    except Exception as e:
        print("FAIL", ten, type(e).__name__, e)
        return False
    thieu = [k for k in phai_co if k not in html]
    print(("OK   " if not thieu else "THIEU"), ten, len(html), thieu or "")
    return not thieu


p = Paginator(list(range(2)), 20).get_page(1)
ok = kiem("web/tra_cuu.html", {
    "nav_active": "tra_cuu", "params": PARAMS, "bo_loc": BO_LOC, "cua_so": CUA_SO,
    "page": p, "page_range": list(p.paginator.get_elided_page_range(1, on_each_side=2, on_ends=1)),
    "tong": 2, "ds": DS,
}, ["28.85", "28.43", "Hà Nội", "Miền Bắc", "khoa-hoc-may-tinh", "2021", "2025",
    "Chính thức", "Đăng nhập để lưu", "trang=2", "tinh_thanh=H%C3%A0+N%E1%BB%99i",
    "So sánh", "visibility", "Đặt lại bộ lọc", "142" if False else "Tìm thấy"])

ok &= kiem("web/trang_chu.html", {
    "nav_active": "trang_chu",
    "kpi": {"so_truong": 288, "so_nganh": 1200, "so_dong_diem": 91581, "so_to_hop": 328},
    "cua_so": CUA_SO, "tieu_bieu": DS,
    "nhom_nganh": [{"nhom_nganh": "CNTT", "so_nganh": 40}],
}, ["2025", "HUST", "28.85", "Trang chủ"])

# Truong hop rong: bo loc khong khop gi -> nhanh {% empty %}
ok &= kiem("web/tra_cuu.html", {
    "nav_active": "tra_cuu", "params": PARAMS, "bo_loc": BO_LOC, "cua_so": CUA_SO,
    "page": p, "page_range": [1], "tong": 0, "ds": [],
}, ["Không tìm thấy ngành nào khớp bộ lọc"])

print("KET QUA:", "PASS" if ok else "FAIL")