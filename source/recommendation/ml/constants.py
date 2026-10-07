# -*- coding: utf-8 -*-
"""Danh mục đặc trưng dùng chung giữa gen_dataset (train) và predict (suy luận).

File này THUẦN PYTHON — không import numpy/pandas/sklearn, để các view import
an toàn mà không kéo theo dependency nặng lúc server khởi động.
"""

FEATURES_SO = [
    "diem_thi", "margin", "diem_moi_nhat", "diem_tb",
    "xu_huong", "bien_dong", "so_nam_co_dl",
]

NHOM_NGANH = [
    "Báo chí - Truyền thông", "Công nghệ thông tin",
    "Du lịch - Khách sạn - Nhà hàng", "Khác",
    "Khoa học XH & Nhân văn", "Kiến trúc - Xây dựng",
    "Kinh tế - Kinh doanh - Tài chính", "Kỹ thuật - Công nghệ",
    "Luật", "Nghệ thuật - Thiết kế - TDTT", "Ngôn ngữ - Quốc tế học",
    "Nông - Lâm - Ngư - Thú y", "Quân đội - Công an",
    "Sư phạm - Giáo dục", "Y - Dược - Sức khỏe",
]

VUNG_MIEN = ["Miền Bắc", "Miền Trung", "Miền Nam"]
PHUONG_THUC = ["Điểm thi THPT", "Điểm học bạ"]


def ten_cot_dac_trung() -> list[str]:
    """Thứ tự cột vector đặc trưng — BẮT BUỘC khớp giữa train và suy luận."""
    return (
        FEATURES_SO
        + [f"nn_{g}" for g in dict.fromkeys(NHOM_NGANH)]
        + [f"vm_{g}" for g in dict.fromkeys(VUNG_MIEN)]
        + [f"pt_{g}" for g in dict.fromkeys(PHUONG_THUC)]
    )
