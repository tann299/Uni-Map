from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import DiemChuan, LanCapNhat

MAX_LIMIT = 100
MAX_OFFSET = 100_000
PHUONG_THUC_HOP_LE = {"Điểm thi THPT", "Điểm học bạ"}
VUNG_MIEN_HOP_LE = {"Miền Bắc", "Miền Trung", "Miền Nam"}


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
def tra_cuu(request):
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
