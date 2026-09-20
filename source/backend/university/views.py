# -*- coding: utf-8 -*-
"""
View app `university` — tra cứu điểm chuẩn (UC-01) + chi tiết trường (UC-02).

Gồm hai tầng:
  * Trang HTML (`trang_chu`, `tra_cuu`, `danh_sach_truong`, `chi_tiet_truong`)
    pivot 5 năm theo `dac_trung_diemchuan` — đã có sẵn cột `diem_nam_1..5`.
  * API JSON dưới `/api/` (`api_tra_cuu`) trả fact phẳng từng năm.

Toàn bộ dữ liệu ở đây do crawler + import_mysql.py nạp vào; view chỉ đọc.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import (PHUONG_THUC, VUNG_MIEN, CuaSoNam, DacTrungDiemChuan,
                     DiemChuan, LanCapNhat, Nganh, ToHop, Truong)

PAGE_SIZE = 20
TRUONG_PAGE_SIZE = 12
MAX_LIMIT = 100
MAX_OFFSET = 100_000

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
        "vung_mien": [(ma, ten, Truong.objects.filter(vung_mien=ten).count())
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
    return render(request, "university/trang_chu.html", {
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
    return render(request, "university/tra_cuu.html", {
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


# ===========================================================================
# Danh sách trường + chi tiết trường (UC-02). Chỉ đọc, dữ liệu thật.
# ===========================================================================

def _truong_thanh_dong(t: Truong, so_nganh: int, diem_tb) -> dict:
    """1 thẻ trường: số ngành, điểm chuẩn TB, vùng miền."""
    return {
        "ma_truong": t.ma_truong,
        "ten_truong": t.ten_truong,
        "viet_tat": t.viet_tat,
        "tinh_thanh": t.tinh_thanh,
        "vung_mien": t.vung_mien,
        "so_nganh": so_nganh,
        "diem_tb": round(float(diem_tb), 2) if diem_tb is not None else None,
    }


def danh_sach_truong(request):
    """Lưới thẻ 288 trường + lọc theo vùng/tỉnh/nhóm ngành/tên."""
    g = request.GET
    q = (g.get("q") or "").strip()
    vung_mien = (g.get("vung_mien") or "").strip()
    tinh_thanh = (g.get("tinh_thanh") or "").strip()
    nhom_nganh = (g.get("nhom_nganh") or "").strip()
    sap_xep = (g.get("sap_xep") or "ten").strip()

    if vung_mien not in dict(VUNG_MIEN):
        vung_mien = ""
    if sap_xep not in {"ten", "nganh_desc", "diem_desc"}:
        sap_xep = "ten"

    qs = Truong.objects.all()
    if q:
        qs = qs.filter(Q(ten_truong__icontains=q) | Q(viet_tat__icontains=q)
                       | Q(ma_truong__icontains=q))
    if vung_mien:
        qs = qs.filter(vung_mien=vung_mien)
    if tinh_thanh:
        qs = qs.filter(tinh_thanh=tinh_thanh)
    if nhom_nganh:
        qs = qs.filter(nganh__nhom_nganh=nhom_nganh).distinct()

    # Số ngành + điểm chuẩn TB của mỗi trường, tính bằng 1 truy vấn gộp.
    thong_ke = {
        r["ma_truong_id"]: r
        for r in DacTrungDiemChuan.objects.values("ma_truong_id")
        .annotate(so_nganh=Count("nganh_id", distinct=True),
                  diem_tb=Avg("diem_moi_nhat"))
    }
    ds = [_truong_thanh_dong(t, thong_ke.get(t.ma_truong, {}).get("so_nganh", 0),
                             thong_ke.get(t.ma_truong, {}).get("diem_tb"))
          for t in qs]
    if sap_xep == "nganh_desc":
        ds.sort(key=lambda x: (-x["so_nganh"], x["ten_truong"]))
    elif sap_xep == "diem_desc":
        ds.sort(key=lambda x: (-(x["diem_tb"] or 0), x["ten_truong"]))
    else:
        ds.sort(key=lambda x: x["ten_truong"])

    paginator = Paginator(ds, TRUONG_PAGE_SIZE)
    page = paginator.get_page(g.get("trang") or 1)

    return render(request, "university/danh_sach_truong.html", {
        "nav_active": "truong",
        "params": {"q": q, "vung_mien": vung_mien, "tinh_thanh": tinh_thanh,
                   "nhom_nganh": nhom_nganh, "sap_xep": sap_xep},
        "bo_loc": {
            "tinh_thanh": (Truong.objects.values("tinh_thanh")
                           .annotate(so_truong=Count("ma_truong"))
                           .order_by("-so_truong", "tinh_thanh")),
            "vung_mien": [(ma, ten, Truong.objects.filter(vung_mien=ten).count())
                          for ma, ten in VUNG_MIEN],
            "nhom_nganh": (Nganh.objects.values("nhom_nganh")
                           .annotate(so_nganh=Count("nganh_id"))
                           .order_by("-so_nganh")),
        },
        "page": page,
        "page_range": paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1),
        "tong": paginator.count,
        "ds": page.object_list,
        "tong_truong": Truong.objects.count(),
    })


def chi_tiet_truong(request, ma_truong):
    """UC-02 — chi tiết 1 trường: KPI + bảng điểm chuẩn 5 năm theo ngành."""
    t = get_object_or_404(Truong, pk=ma_truong)
    cua_so = cua_so_nam()

    g = request.GET
    ma_to_hop = (g.get("ma_to_hop") or "").strip()
    phuong_thuc = (g.get("phuong_thuc") or "").strip()
    nhom_nganh = (g.get("nhom_nganh") or "").strip()
    sap_xep = (g.get("sap_xep") or "diem_desc").strip()
    if phuong_thuc not in dict(PHUONG_THUC):
        phuong_thuc = ""
    if sap_xep not in SAP_XEP:
        sap_xep = "diem_desc"

    qs = (DacTrungDiemChuan.objects
          .select_related("nganh", "ma_to_hop")
          .filter(ma_truong=t))
    if ma_to_hop:
        qs = qs.filter(ma_to_hop_id=ma_to_hop)
    if phuong_thuc:
        qs = qs.filter(phuong_thuc=phuong_thuc)
    if nhom_nganh:
        qs = qs.filter(nganh__nhom_nganh=nhom_nganh)
    qs = qs.order_by(SAP_XEP[sap_xep], "nganh__ten_nganh")

    ds = [_thanh_dong(r, cua_so) for r in qs]
    diem_tb = (sum(float(r["diem_moi_nhat"]) for r in ds) / len(ds)) if ds else None

    # KPI: số ngành, số nhóm ngành, số tổ hợp, điểm TB.
    return render(request, "university/chi_tiet_truong.html", {
        "nav_active": "truong",
        "truong": t,
        "cua_so": cua_so,
        "params": {"ma_to_hop": ma_to_hop, "phuong_thuc": phuong_thuc,
                   "nhom_nganh": nhom_nganh, "sap_xep": sap_xep},
        "bo_loc": {
            "to_hop": (ToHop.objects.filter(dactrungdiemchuan__ma_truong=t)
                       .distinct().order_by("ma_to_hop")
                       .values_list("ma_to_hop", "ten_to_hop")),
            "phuong_thuc": PHUONG_THUC,
            "nhom_nganh": (Nganh.objects.filter(dactrungdiemchuan__ma_truong=t)
                           .values("nhom_nganh")
                           .annotate(so_nganh=Count("nganh_id"))
                           .order_by("-so_nganh")),
        },
        "ds": ds,
        "kpi": {
            "so_nganh": len({r["nganh_slug"] for r in ds}),
            "so_nhom_nganh": len({r["nhom_nganh"] for r in ds}),
            "so_to_hop": len({r["ma_to_hop"] for r in ds}),
            "diem_tb": round(diem_tb, 2) if diem_tb is not None else None,
        },
    })

# ===========================================================================
# API JSON  (/api/tra-cuu/)  — fact phẳng từng năm
# ===========================================================================

PHUONG_THUC_HOP_LE = {ma for ma, _ in PHUONG_THUC}
VUNG_MIEN_HOP_LE = {ma for ma, _ in VUNG_MIEN}


@dataclass(frozen=True)
class SearchParams:
    q: str = ""
    nganh: str = ""
    truong: str = ""
    tinh_thanh: str = ""
    vung_mien: str = ""
    ma_to_hop: str = ""
    phuong_thuc: str = ""
    nam: int | None = None
    limit: int = 20
    offset: int = 0


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status, json_dumps_params={"ensure_ascii": False})


def _positive_int(value: str, name: str, *, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} phải là số nguyên") from None
    if number < 0 or number > maximum:
        raise ValueError(f"{name} phải trong khoảng 0–{maximum}")
    return number


def _parse_params(query) -> SearchParams:
    allowed = {
        "q", "nganh", "truong", "tinh_thanh", "vung_mien", "ma_to_hop",
        "phuong_thuc", "nam", "limit", "offset",
    }
    unknown = set(query) - allowed
    if unknown:
        raise ValueError(f"tham số không được hỗ trợ: {sorted(unknown)[0]}")

    phuong_thuc = query.get("phuong_thuc", "").strip()
    if phuong_thuc and phuong_thuc not in PHUONG_THUC_HOP_LE:
        raise ValueError("phuong_thuc không hợp lệ")
    vung_mien = query.get("vung_mien", "").strip()
    if vung_mien and vung_mien not in VUNG_MIEN_HOP_LE:
        raise ValueError("vung_mien không hợp lệ")

    nam_text = query.get("nam", "").strip()
    nam = None
    if nam_text:
        nam = _positive_int(nam_text, "nam", maximum=2100)
        if nam < 2000:
            raise ValueError("nam phải trong khoảng 2000–2100")

    limit = _positive_int(query.get("limit", "20"), "limit", maximum=MAX_LIMIT)
    if limit == 0:
        raise ValueError("limit phải lớn hơn 0")
    offset = _positive_int(query.get("offset", "0"), "offset", maximum=MAX_OFFSET)

    return SearchParams(
        q=query.get("q", "").strip(),
        nganh=query.get("nganh", "").strip(),
        truong=query.get("truong", "").strip(),
        tinh_thanh=query.get("tinh_thanh", "").strip(),
        vung_mien=vung_mien,
        ma_to_hop=query.get("ma_to_hop", "").strip().upper(),
        phuong_thuc=phuong_thuc,
        nam=nam,
        limit=limit,
        offset=offset,
    )


def _metadata() -> dict[str, str | None]:
    latest = LanCapNhat.objects.order_by("-thoi_diem").values("nguon", "thoi_diem").first()
    if not latest:
        return {"source": None, "updated_at": None}
    updated = latest["thoi_diem"]
    return {
        "source": latest["nguon"],
        "updated_at": updated.isoformat() if updated else None,
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _row(item: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in item.items()}


@require_GET
def api_tra_cuu(request):
    try:
        params = _parse_params(request.GET)
    except ValueError as exc:
        return _error(str(exc))

    filters = Q()
    if params.q:
        filters &= Q(nganh__ten_nganh__icontains=params.q) | Q(
            ma_truong__ten_truong__icontains=params.q
        )
    if params.nganh:
        filters &= Q(nganh__nganh_slug=params.nganh)
    if params.truong:
        filters &= Q(ma_truong_id=params.truong)
    if params.tinh_thanh:
        filters &= Q(ma_truong__tinh_thanh=params.tinh_thanh)
    if params.vung_mien:
        filters &= Q(ma_truong__vung_mien=params.vung_mien)
    if params.ma_to_hop:
        filters &= Q(ma_to_hop_id=params.ma_to_hop)
    if params.phuong_thuc:
        filters &= Q(phuong_thuc=params.phuong_thuc)
    if params.nam is not None:
        filters &= Q(nam=params.nam)

    query = DiemChuan.objects.select_related("ma_truong", "nganh", "ma_to_hop").filter(filters)
    total = query.count()
    rows = query.order_by("nganh__ten_nganh", "ma_truong__ten_truong", "nam").values(
        "nam", "diem_chuan", "phuong_thuc", "ten_nganh_goc",
        "ma_truong_id", "ma_truong__ten_truong", "ma_truong__tinh_thanh",
        "ma_truong__vung_mien", "nganh_id", "nganh__nganh_slug", "nganh__ten_nganh",
        "nganh__nhom_nganh", "ma_to_hop_id", "ma_to_hop__ten_to_hop",
        "ma_to_hop__cac_mon",
    )[params.offset:params.offset + params.limit]

    try:
        metadata = _metadata()
    except Exception:
        metadata = {"source": None, "updated_at": None}

    return JsonResponse(
        {
            "data": [_row(item) for item in rows],
            "pagination": {
                "total": total,
                "limit": params.limit,
                "offset": params.offset,
                "has_next": params.offset + params.limit < total,
            },
            "years": sorted({item["nam"] for item in rows}),
            **metadata,
        },
        json_dumps_params={"ensure_ascii": False},
    )
