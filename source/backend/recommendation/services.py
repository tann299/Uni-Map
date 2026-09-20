# -*- coding: utf-8 -*-
"""
Chức năng đặc thù của app `recommendation` — CN-03 (phân tầng) và CN-04 (giải thích).

CN-01 (ghép tổ hợp từ điểm môn) nằm ở `university.services` vì đó là dữ liệu tham
chiếu tổ hợp; ở đây chỉ dùng lại.

Mọi hàm đều THUẦN Python, không chạm ORM — test được mà không cần DB (xem tests.py).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# CN-03 — phân tầng nguyện vọng An toàn / Vừa sức / Thử sức (SRS mục CN-03)
# ---------------------------------------------------------------------------

# SRS CN-03 định ngưỡng theo XÁC SUẤT: p ≥ 0,8 An toàn · 0,4–0,8 Vừa sức · < 0,4
# Thử sức. Khi chưa có mô hình (chế độ dự phòng UC-05/5b) ta chỉ có `margin`, nên
# quy đổi ngưỡng xác suất sang margin trên cùng thang điểm của hồ sơ:
#   p = 0,8 ↔ margin ≈ +2,0   ·   p = 0,4 ↔ margin ≈ 0,0
# Ngưỡng chọn theo thang 30 điểm — học bạ/THPT dùng chung vì `diem_moi_nhat` của
# dòng đặc trưng đã cùng thang với `diem_hoc_sinh` của hồ sơ.
MARGIN_AN_TOAN = 2.0
MARGIN_VUA_SUC = 0.0

# Tailwind class theo base.html. KHÔNG dùng màu làm dấu hiệu duy nhất (PC-08):
# mỗi tầng luôn kèm icon + nhãn chữ ở template.
TANG_STYLE = {
    "An toàn": {"cls": "bg-[#DCFCE7] text-[#16A34A] border-[#16A34A]/30",
                "icon": "verified", "mo_ta": "Đặt cuối danh sách làm chốt an toàn"},
    "Vừa sức": {"cls": "bg-[#FEF3C7] text-[#D97706] border-[#D97706]/30",
                "icon": "trending_flat", "mo_ta": "Nhóm chính, nên đặt giữa"},
    "Thử sức": {"cls": "bg-[#FEE2E2] text-[#DC2626] border-[#DC2626]/30",
                "icon": "local_fire_department", "mo_ta": "Đặt đầu danh sách, được thì tốt"},
}


def phan_tang(margin: float) -> str:
    """margin (điểm học sinh − điểm chuẩn mới nhất) -> tên tầng."""
    if margin >= MARGIN_AN_TOAN:
        return "An toàn"
    if margin >= MARGIN_VUA_SUC:
        return "Vừa sức"
    return "Thử sức"


def style_tang(tang: str) -> dict:
    return TANG_STYLE[tang]


def chon_can_ban(theo_tang: dict[str, list], gioi_han: int) -> list:
    """CN-03 — chia quota đều cho 3 tầng, tầng thiếu nhường suất cho tầng khác.

    `theo_tang`: {'An toàn': [...], 'Vừa sức': [...], 'Thử sức': [...]} mỗi list đã
    sắp theo độ phù hợp giảm dần. Trả list đã chọn, sắp theo thứ tự tầng (An toàn
    trước). Tách thuần để test được không cần DB (xem tests.py).
    """
    thu_tu = list(theo_tang)
    quota, du = divmod(gioi_han, len(thu_tu))
    chon, con_lai = [], gioi_han
    for i, tang in enumerate(thu_tu):
        lay = min(len(theo_tang[tang]), quota + (1 if i < du else 0), con_lai)
        chon.extend(theo_tang[tang][:lay])
        con_lai -= lay
    if con_lai:
        for i, tang in enumerate(thu_tu):
            them = theo_tang[tang][quota + (1 if i < du else 0):]
            lay = min(len(them), con_lai)
            chon.extend(them[:lay])
            con_lai -= lay
            if not con_lai:
                break
    chon.sort(key=lambda x: thu_tu.index(x["tang"]))
    return chon


# ---------------------------------------------------------------------------
# CN-04 — giải thích gợi ý bằng ngôn ngữ tự nhiên (SRS mục CN-04)
# ---------------------------------------------------------------------------

def _so_vn(x: float, don_vi: str = "") -> str:
    """1.3 -> '1,3' — dấu phẩy thập phân tiếng Việt, kèm đơn vị."""
    return f"{x:,.2f}".rstrip("0").rstrip(".").replace(".", ",") + don_vi


def giai_thich(dac_trung: dict) -> list[dict]:
    """4 câu giải thích từ đặc trưng THẬT (SRS CN-04). Không bịa số.

    `dac_trung`: {margin, xu_huong, bien_dong, so_nam_co_dl, nam_moi_nhat}
    Trả list {loai, chu, canh_bao} để template tô màu câu cảnh báo.
    """
    margin = float(dac_trung["margin"] or 0)
    xu_huong = float(dac_trung.get("xu_huong") or 0)
    bien_dong = float(dac_trung.get("bien_dong") or 0)
    so_nam = int(dac_trung.get("so_nam_co_dl") or 0)
    nam = dac_trung.get("nam_moi_nhat") or "gần nhất"

    cau = []

    # 1. Khoảng cách điểm — đặc trưng mạnh nhất.
    if margin >= 0:
        cau.append({"loai": "margin", "canh_bao": False,
                    "chu": f"Bạn hơn {_so_vn(margin)} điểm so với điểm chuẩn {nam}"})
    else:
        cau.append({"loai": "margin", "canh_bao": True,
                    "chu": f"Bạn thiếu {_so_vn(abs(margin))} điểm so với điểm chuẩn {nam}"})

    # 2. Xu hướng — chỉ cảnh báo khi tăng nhanh (US-15).
    if xu_huong > 0:
        cau.append({"loai": "xu_huong", "canh_bao": xu_huong >= 0.5,
                    "chu": f"Điểm chuẩn đang tăng ~{_so_vn(xu_huong)} điểm/năm — cân nhắc rủi ro"})
    elif xu_huong < 0:
        cau.append({"loai": "xu_huong", "canh_bao": False,
                    "chu": f"Điểm chuẩn đang giảm ~{_so_vn(abs(xu_huong))} điểm/năm"})
    else:
        cau.append({"loai": "xu_huong", "canh_bao": False,
                    "chu": "Điểm chuẩn nhiều năm gần như không đổi"})

    # 3. Độ dao động.
    if bien_dong >= 2.0:
        cau.append({"loai": "bien_dong", "canh_bao": True,
                    "chu": f"Dao động 5 năm: {_so_vn(bien_dong)} điểm — khó đoán"})
    else:
        cau.append({"loai": "bien_dong", "canh_bao": False,
                    "chu": f"Dao động 5 năm: {_so_vn(bien_dong)} điểm — tương đối ổn định"})

    # 4. Độ tin cậy dữ liệu — cảnh báo khi mỏng (UC-05/7a).
    if so_nam < 3:
        chu = f"Dựa trên {so_nam}/5 năm dữ liệu — độ tin cậy thấp"
    elif so_nam == 5:
        chu = "Dựa trên 5/5 năm dữ liệu — độ tin cậy cao"
    else:
        chu = f"Dựa trên {so_nam}/5 năm dữ liệu"
    cau.append({"loai": "do_tin_cay", "canh_bao": so_nam < 3, "chu": chu})

    return cau