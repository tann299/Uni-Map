# -*- coding: utf-8 -*-
"""
View HTML cho Uni Map (namespace `web:`).

Tách khỏi app `tracuu` vì `tracuu` chỉ phục vụ JSON API dưới `/api/`.
Trang HTML cần pivot 5 năm theo `dac_trung_diemchuan` (đã có sẵn cột
`diem_nam_1..5`), trong khi API trả fact phẳng từng năm.
"""

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from tracuu.models import (
    PHUONG_THUC,
    VUNG_MIEN,
    CuaSoNam,
    DacTrungDiemChuan,
    DiemChuan,
    Nganh,
    ToHop,
    Truong,
)

PAGE_SIZE = 20

# Chỉ cho phép sắp xếp theo danh sách trắng — không nhận thẳng tên cột từ query.
SAP_XEP = {
    "diem_desc": "-diem_moi_nhat",
    "diem_asc": "diem_moi_nhat",
    "bien_dong_desc": "-bien_dong",
    "bien_dong_asc": "bien_dong",
    "ten": "ma_truong__ten_truong",
}


def cua_so_nam() -> list[CuaSoNam]:
    """vi_tri 1..5 -> năm thật, dùng làm tiêu đề cột."""
    return list(CuaSoNam.objects.all())


def _chip(bien_dong) -> dict:
    """Mockup to mau theo huong: tang = do, giam = xanh, on dinh = ho phach."""
    b = float(bien_dong or 0)
    if b > 0.05:
        return {"cls": "bg-[#FEE2E2] text-[#DC2626] border-[#DC2626]/30", "icon": "trending_up"}
    if b < -0.05:
        return {"cls": "bg-[#DCFCE7] text-[#16A34A] border-[#16A34A]/30", "icon": "trending_down"}
    return {"cls": "bg-[#FEF3C7] text-[#D97706] border-[#D97706]/30", "icon": "horizontal_rule"}


def _thanh_dong(row, cua_so) -> dict:
    """1 dòng bảng: gộp (trường, ngành, tổ hợp) + chuỗi 5 năm.

    `theo_nam` ghép sẵn (năm, điểm) vì template Django không zip được 2 list.
    """
    return {
        "theo_nam": [
            {"nam": c.nam, "diem": d} for c, d in zip(cua_so, row.chuoi_diem())
        ],
        "chip": _chip(row.bien_dong),
        "ma_truong": row.ma_truong_id,
        "truong": row.ma_truong.ten_truong,
        "viet_tat": row.ma_truong.viet_tat,
        "tinh_thanh": row.ma_truong.tinh_thanh,
        "vung_mien": row.ma_truong.vung_mien,
        "nganh": row.nganh.ten_nganh,
        "nganh_slug": row.nganh.nganh_slug,
        "nhom_nganh": row.nganh.nhom_nganh,
        "ma_to_hop": row.ma_to_hop_id,
        "ten_to_hop": row.ma_to_hop.ten_to_hop,
        "phuong_thuc": row.phuong_thuc,
        "diem": row.chuoi_diem(),
        "diem_moi_nhat": row.diem_moi_nhat,
        "diem_tb": row.diem_tb,
        "bien_dong": row.bien_dong,
        "xu_huong": row.xu_huong,
        "so_nam_co_dl": row.so_nam_co_dl,
    }


def _loc(request):
    """Đọc query string -> (params đã chuẩn hoá, queryset đã lọc)."""
    g = request.GET
    q = (g.get("q") or "").strip()
    truong = (g.get("truong") or "").strip()
    nganh = (g.get("nganh") or "").strip()
    tinh_thanh = (g.get("tinh_thanh") or "").strip()
    vung_mien = (g.get("vung_mien") or "").strip()
    ma_to_hop = (g.get("ma_to_hop") or "").strip()
    phuong_thuc = (g.get("phuong_thuc") or "").strip()
    nhom_nganh = (g.get("nhom_nganh") or "").strip()
    nam = (g.get("nam") or "").strip()
    sap_xep = (g.get("sap_xep") or "diem_desc").strip()

    if sap_xep not in SAP_XEP:
        sap_xep = "diem_desc"
    if vung_mien not in dict(VUNG_MIEN):
        vung_mien = ""
    if phuong_thuc not in dict(PHUONG_THUC):
        phuong_thuc = ""

    qs = DacTrungDiemChuan.objects.select_related("ma_truong", "nganh", "ma_to_hop")

    if q:
        qs = qs.filter(
            Q(ma_truong__ten_truong__icontains=q)
            | Q(ma_truong__viet_tat__icontains=q)
            | Q(nganh__ten_nganh__icontains=q)
            | Q(nganh__nhom_nganh__icontains=q)
        )
    if truong:
        qs = qs.filter(ma_truong_id=truong)
    if nganh:
        qs = qs.filter(nganh__nganh_slug=nganh)
    if tinh_thanh:
        qs = qs.filter(ma_truong__tinh_thanh=tinh_thanh)
    if vung_mien:
        qs = qs.filter(ma_truong__vung_mien=vung_mien)
    if ma_to_hop:
        qs = qs.filter(ma_to_hop_id=ma_to_hop)
    if phuong_thuc:
        qs = qs.filter(phuong_thuc=phuong_thuc)
    if nhom_nganh:
        qs = qs.filter(nganh__nhom_nganh=nhom_nganh)
    if nam:
        # Lọc "có dữ liệu ở năm này" — map năm thật -> cột diem_nam_N.
        vi_tri = next((c.vi_tri for c in cua_so_nam() if str(c.nam) == nam), None)
        if vi_tri:
            qs = qs.filter(**{f"diem_nam_{vi_tri}__isnull": False})

    qs = qs.order_by(SAP_XEP[sap_xep], "ma_truong_id", "nganh_id")

    params = {
        "q": q, "truong": truong, "nganh": nganh, "tinh_thanh": tinh_thanh,
        "vung_mien": vung_mien, "ma_to_hop": ma_to_hop,
        "phuong_thuc": phuong_thuc, "nhom_nganh": nhom_nganh,
        "nam": nam, "sap_xep": sap_xep,
    }
    return params, qs


def _bo_loc():
    """Giá trị cho các select — lấy từ dữ liệu thật, không hardcode."""
    return {
        "tinh_thanh": (Truong.objects.values("tinh_thanh")
                       .annotate(so_truong=Count("ma_truong"))
                       .order_by("-so_truong", "tinh_thanh")),
        "vung_mien": [(ma, ten, Truong.objects.filter(vung_mien=ma).count())
                      for ma, ten in VUNG_MIEN],
        "phuong_thuc": PHUONG_THUC,
        "to_hop": ToHop.objects.order_by("ma_to_hop").values_list("ma_to_hop", "ten_to_hop"),
        "nhom_nganh": (Nganh.objects.values("nhom_nganh")
                       .annotate(so_nganh=Count("nganh_id"))
                       .order_by("-so_nganh")),
    }


def trang_chu(request):
    kpi = {
        "so_truong": Truong.objects.count(),
        "so_nganh": Nganh.objects.count(),
        "so_dong_diem": DiemChuan.objects.count(),
        "so_to_hop": ToHop.objects.count(),
    }
    # "Ngành tiêu biểu": điểm chuẩn năm mới nhất cao nhất, đủ 5 năm dữ liệu.
    tieu_bieu = DacTrungDiemChuan.objects.select_related(
        "ma_truong", "nganh", "ma_to_hop"
    ).filter(so_nam_co_dl=5).order_by("-diem_moi_nhat")[:5]

    # Khám phá theo nhóm ngành: lấy thẳng từ dữ liệu, không hardcode 6 nhóm
    # của mockup (mockup dùng tên nhóm không có trong CSDL).
    nhom_nganh = list(
        Nganh.objects.values("nhom_nganh")
        .annotate(so_nganh=Count("nganh_id"))
        .order_by("-so_nganh")[:6]
    )

    cua_so = cua_so_nam()
    return render(request, "web/trang_chu.html", {
        "nav_active": "trang_chu",
        "kpi": kpi,
        "cua_so": cua_so,
        "tieu_bieu": [_thanh_dong(r, cua_so) for r in tieu_bieu],
        "nhom_nganh": nhom_nganh,
    })


def tra_cuu(request):
    params, qs = _loc(request)
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("trang") or 1)

    cua_so = cua_so_nam()
    return render(request, "web/tra_cuu.html", {
        "nav_active": "tra_cuu",
        "params": params,
        "bo_loc": _bo_loc(),
        "cua_so": cua_so,
        # Giu query string khi doi trang: template dung {% querystring %} (Django 5.1+).
        "page": page,
        # Danh sach so trang da rut gon (91k dong -> ~4.5k trang).
        "page_range": paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1),
        "tong": paginator.count,
        "ds": [_thanh_dong(r, cua_so) for r in page.object_list],
    })