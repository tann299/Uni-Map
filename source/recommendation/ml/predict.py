# -*- coding: utf-8 -*-
"""Nạp mô hình + chấm xác suất đỗ (SRS 6.5 bước 4, UC-05 bước 4).

Mô hình nạp MỘT LẦN cho cả tiến trình (`_kho` + `_khoa`), không đọc lại `.pkl`
43 MB mỗi request — PC-01 yêu cầu phản hồi < 3s.

Mọi lỗi (thiếu file, sklearn lệch bản, vector sai kích thước) đều trả `None`
thay vì raise — view rơi về chế độ dự phòng UC-05/5b (xếp hạng bằng `margin`,
ghi `dung_ai=False`). Gợi ý suy giảm chất lượng còn hơn 500.
"""
from __future__ import annotations

import json
import os
import threading

from .constants import (FEATURES_SO, NHOM_NGANH, PHUONG_THUC, VUNG_MIEN,
                        ten_cot_dac_trung)

ML_DIR = os.path.dirname(os.path.abspath(__file__))
NONG_PKL = os.path.join(ML_DIR, "model.pkl")
NONG_SCALER = os.path.join(ML_DIR, "scaler.pkl")
NONG_QUAN_TRONG = os.path.join(ML_DIR, "feature_importance.json")

_khoa = threading.Lock()
_kho: dict | None = None
_da_thu = False


def phien_ban() -> str:
    """Tên phiên bản mô hình để ghi vào `LanGoiY.phien_ban_mo_hinh`."""
    try:
        mtime = int(os.path.getmtime(NONG_PKL))
    except OSError:
        return ""
    try:
        with open(NONG_QUAN_TRONG, encoding="utf-8") as f:
            dong = json.load(f)
        n = len(dong)
    except (OSError, ValueError):
        n = 0
    return f"rf-n{n}-{mtime}"


def nap_mo_hinh() -> dict | None:
    """Nạp 1 lần: {'model', 'scaler', 'cot'}. None nếu không dùng được."""
    global _kho, _da_thu
    if _kho is not None:
        return _kho
    with _khoa:
        if _kho is not None:
            return _kho
        if _da_thu and _kho is None:
            return None
        _da_thu = True
        try:
            import joblib

            cot = ten_cot_dac_trung()
            scaler = joblib.load(NONG_SCALER)
            # Lúc suy luận ta đưa vào numpy array (nhanh hơn DataFrame), còn
            # scaler lưu tên cột từ lúc fit -> sklearn cảnh báo "X does not have
            # valid feature names" mỗi request. Gắn lại tên cột KHÔNG làm hết
            # cảnh báo (đã thử); phải xoá hẳn attribute để sklearn coi scaler
            # là không có tên cột. Thứ tự cột do `ten_cot_dac_trung()` bảo đảm.
            if hasattr(scaler, "feature_names_in_"):
                del scaler.feature_names_in_
            _kho = {"model": joblib.load(NONG_PKL), "scaler": scaler, "cot": cot}
        except Exception:  # noqa: BLE001 — mọi lỗi đều rơi về dự phòng
            _kho = None
    return _kho


def nap_lai() -> None:
    """Quên mô hình đang giữ trong RAM — gọi sau khi huấn luyện ghi `model.pkl`
    mới (UC-10 bước 6). Request kế tiếp sẽ nạp bản vừa train."""
    global _kho, _da_thu
    with _khoa:
        _kho, _da_thu = None, False


def _vector(dong_dac_trung, cot: list[str]) -> np.ndarray:
    """1 dòng `DacTrungDiemChuan` + điểm học sinh -> vector 27 chiều.

    Cột one-hot dựng theo danh mục CỐ ĐỊNH trong `gen_dataset`, không theo giá
    trị có trong DB — nhóm ngành mới chưa từng thấy thành vector toàn 0 (CN-08).
    """
    import numpy as np  # lazy: numpy chỉ cần khi thực sự chấm điểm

    pt = dong_dac_trung.phuong_thuc
    nn = dong_dac_trung.nganh.nhom_nganh
    vm = dong_dac_trung.ma_truong.vung_mien
    return np.array([[
        # FEATURES_SO theo đúng thứ tự; 3 ô đầu do hàm gọi điền sau.
        0.0, 0.0, float(dong_dac_trung.diem_moi_nhat),
        float(dong_dac_trung.diem_tb), float(dong_dac_trung.xu_huong),
        float(dong_dac_trung.bien_dong), int(dong_dac_trung.so_nam_co_dl),
        *[1 if nn == g else 0 for g in NHOM_NGANH],
        *[1 if vm == g else 0 for g in VUNG_MIEN],
        *[1 if pt == g else 0 for g in PHUONG_THUC],
    ]], dtype="float64")


def cham_xac_suat(ds_dong, cot: list[str] | None = None) -> np.ndarray | None:
    """Nhiều ứng viên -> mảng xác suất đỗ. None nếu mô hình không dùng được.

    `ds_dong`: list (dòng `DacTrungDiemChuan`, điểm học sinh đã cộng ưu tiên).
    Chấm theo lô — 1 lần `predict_proba` cho cả danh sách, không gọi từng dòng.
    """
    kho = nap_mo_hinh()
    if kho is None or not ds_dong:
        return None
    cot = cot or kho["cot"]
    try:
        import numpy as np  # lazy: numpy chỉ cần khi thực sự chấm điểm

        X = np.vstack([_vector(d, cot) for d, _ in ds_dong])
        # Điền 3 ô đầu của FEATURES_SO: diem_thi, margin, diem_moi_nhat.
        diem = np.array([diem_hs for _, diem_hs in ds_dong], dtype="float64")
        X[:, FEATURES_SO.index("diem_thi")] = diem
        X[:, FEATURES_SO.index("diem_moi_nhat")] = [
            float(d.diem_moi_nhat) for d, _ in ds_dong]
        X[:, FEATURES_SO.index("margin")] = (
            diem - X[:, FEATURES_SO.index("diem_moi_nhat")])
        Z = kho["scaler"].transform(X)
        return kho["model"].predict_proba(Z)[:, 1]
    except Exception:  # noqa: BLE001 — mọi lỗi đều rơi về dự phòng
        return None
