# -*- coding: utf-8 -*-
"""
CN-01 — tự tính điểm mọi tổ hợp từ điểm từng môn (SRS mục CN-01, US-08).

Hàm `tinh_to_hop` thuần Python, KHÔNG chạm ORM: nhận điểm từng môn + danh mục
tổ hợp (mã -> danh sách mã môn), trả về những tổ hợp học sinh đủ môn kèm tổng
điểm. Tách thuần để test được mà không cần DB. Wrapper `tinh_to_hop_tu_db` bơm
dữ liệu từ bảng `to_hop` vào hàm thuần.

Đặt ở app `university` vì tổ hợp môn + bảng `mon` là dữ liệu tham chiếu của
trường/ngành; cả `admissions` (nhập điểm) lẫn `recommendation` (gợi ý) đều dùng.
"""
from __future__ import annotations


def tinh_to_hop(diem_mon: dict[str, float],
                to_hop_mon: dict[str, list[str]],
                mon_nang_khieu: set[str] | None = None) -> list[dict]:
    """Trả list tổ hợp đủ môn, mỗi phần tử {ma, tong, mon, can_nang_khieu}.

    - `diem_mon`:   {'TOAN': 8.5, 'LI': 7.75, ...}
    - `to_hop_mon`: {'A00': ['TOAN','LI','HOA'], ...}
    - Thiếu 1 môn -> bỏ qua IM LẶNG (không báo lỗi), theo tiêu chí US-08.
    - Tổ hợp rỗng (chưa map được môn) -> bỏ qua.
    Kết quả sắp theo tổng điểm giảm dần rồi mã tổ hợp.
    """
    nang_khieu = mon_nang_khieu or set()
    ket_qua = []
    for ma, mon in to_hop_mon.items():
        if not mon:
            continue
        if all(m in diem_mon for m in mon):
            ket_qua.append({
                "ma": ma,
                "mon": mon,
                "tong": round(sum(diem_mon[m] for m in mon), 2),
                "can_nang_khieu": any(m in nang_khieu for m in mon),
            })
    ket_qua.sort(key=lambda x: (-x["tong"], x["ma"]))
    return ket_qua


def tinh_to_hop_tu_db(diem_mon: dict[str, float]) -> list[dict]:
    """Bơm danh mục tổ hợp thật từ bảng `to_hop` vào hàm thuần ở trên."""
    from .models import Mon, ToHop

    to_hop_mon = {
        th.ma_to_hop: th.danh_sach_mon()
        for th in ToHop.objects.exclude(cac_mon="")
    }
    nang_khieu = set(
        Mon.objects.filter(la_nang_khieu=True).values_list("ma_mon", flat=True)
    )
    return tinh_to_hop(diem_mon, to_hop_mon, nang_khieu)