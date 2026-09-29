# -*- coding: utf-8 -*-
"""Sinh mẫu huấn luyện AI từ lịch sử điểm chuẩn (SRS 6.3, UC-10 bước 2).

Không có dữ liệu đỗ/trượt thật (GĐ-3) nên nhãn sinh từ fact `diem_chuan`:
mỗi dòng điểm chuẩn C của năm t là một "sự thật" — thí sinh giả lập điểm X
quanh C thì đỗ khi X >= C.

Chống data leakage (SRS 6.3, 6.6): đặc trưng của mẫu năm t CHỈ tính từ các
năm < t (công thức khớp `build_features` trong crawler). Chia tập theo năm,
không chia ngẫu nhiên: train 2021–2024, test 2025 (SRS 6.3, UC-10 bước 3).
Hiển thị 10 năm (2016–2025) nhưng AI chỉ nhìn 6 năm gần nhất (NAM_LOOKBACK):
phổ điểm kỳ thi cũ 2016–2019 gây nhiễu, đo thực tế lookback 6 cho acc cao
nhất (0.7456 vs 10 năm 0.7454, 7 năm 0.7451 — chênh lệch trong nhiễu).

Chạy:  python -m recommendation.ml.gen_dataset            # sinh CSV + meta
        python -m recommendation.ml.gen_dataset --selfcheck  # kiểm tra logic
        python -m recommendation.ml.gen_dataset --sample 200 # thử nhanh N key
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

NAM_TRAIN = [2021, 2022, 2023, 2024]
NAM_TEST = [2025]

# Số năm quá khứ AI được nhìn khi tính đặc trưng cho mẫu năm t. DB giữ 10 năm
# (2016–2025) để hiển thị, nhưng phổ điểm 2016–2019 khác biệt nên chỉ dùng 6
# năm gần nhất. Đổi số này là đổi cửa sổ AI, không đụng dữ liệu hiển thị.
NAM_LOOKBACK = 6

# Điểm thí sinh giả lập = C + delta. Đối xứng quanh 0 để nhãn cân bằng
# (delta = 0 -> đỗ, nên dương nhỉnh hơn âm 1 mẫu — kiểm tra ở meta).
DELTAS = [-3.0, -2.0, -1.0, -0.5, -0.2, 0.0, 0.2, 0.5, 1.0, 2.0, 3.0]

KEY = ["ma_truong", "nganh_id", "ma_to_hop", "phuong_thuc"]

# 6 đặc trưng số + 3 nhóm one-hot (SRS 6.4). `diem_thi` cũng vào vector: lúc
# chạy thật mô hình nhận điểm học sinh, không chỉ margin.
FEATURES_SO = ["diem_thi", "margin", "diem_moi_nhat", "diem_tb",
               "xu_huong", "bien_dong", "so_nam_co_dl"]
# Danh mục one-hot CỐ ĐỊNH — khớp `Nganh.nhom_nganh` trong DB (15 giá trị).
# Cố định thay vì suy từ tập train để lúc suy luận cột khớp thứ tự kể cả khi
# tập train thiếu một nhóm ngành nào đó.
NHOM_NGANH = ["Báo chí - Truyền thông", "Công nghệ thông tin",
              "Du lịch - Khách sạn - Nhà hàng", "Khác",
              "Khoa học XH & Nhân văn", "Kiến trúc - Xây dựng",
              "Kinh tế - Kinh doanh - Tài chính", "Kỹ thuật - Công nghệ",
              "Luật", "Nghệ thuật - Thiết kế - TDTT", "Ngôn ngữ - Quốc tế học",
              "Nông - Lâm - Ngư - Thú y", "Quân đội - Công an",
              "Sư phạm - Giáo dục", "Y - Dược - Sức khỏe"]
VUNG_MIEN = ["Miền Bắc", "Miền Trung", "Miền Nam"]
PHUONG_THUC = ["Điểm thi THPT", "Điểm học bạ"]


def encode(ds: pd.DataFrame) -> pd.DataFrame:
    """One-hot 3 cột phân loại thành cột 0/1 với danh mục cố định (SRS 6.4).

    Bỏ cột gốc dạng chuỗi — sklearn chỉ ăn số. Giá trị lạ (nguồn thêm nhóm mới)
    thành vector toàn 0 thay vì lỗi, đúng tinh thần chịu lỗi của CN-08.
    """
    ds = ds.copy()
    for cot, danh_muc, tien_to in (("nhom_nganh", dict.fromkeys(NHOM_NGANH), "nn_"),
                                   ("vung_mien", dict.fromkeys(VUNG_MIEN), "vm_"),
                                   ("phuong_thuc", dict.fromkeys(PHUONG_THUC), "pt_")):
        for gt in danh_muc:
            ds[f"{tien_to}{gt}"] = (ds[cot] == gt).astype("int8")
        ds = ds.drop(columns=[cot])
    return ds


def ten_cot_dac_trung() -> list[str]:
    """Thứ tự cột vector đặc trưng — BẮT BUỘC khớp lúc suy luận (bước 3.1)."""
    return (FEATURES_SO
            + [f"nn_{g}" for g in dict.fromkeys(NHOM_NGANH)]
            + [f"vm_{g}" for g in VUNG_MIEN]
            + [f"pt_{g}" for g in PHUONG_THUC])

# ponytail: CSV thay parquet vì chưa có pyarrow; chuyển khi dataset > 500MB.
# ponytail: DELTAS cố định thay vì lấy mẫu theo phân phối điểm thật; nâng cấp
# khi kiểm tra calibration thấy xác suất lệch ở biên.


def dac_trung_cutoff(past: pd.DataFrame, years_past: list[int]) -> pd.DataFrame:
    """Đặc trưng mỗi key CHỈ từ các năm < t (công thức = crawler build_features)."""
    piv = (past.pivot_table(index=KEY, columns="nam", values="diem_chuan",
                            aggfunc="max").reindex(columns=years_past))
    V = piv.to_numpy(dtype="float64")
    M = ~np.isnan(V)
    n = M.sum(axis=1)
    yrs = np.asarray(years_past, dtype="float64")

    with np.errstate(invalid="ignore", divide="ignore"):
        tb = np.nanmean(V, axis=1)
        mx = np.nanmax(V, axis=1)
        mn = np.nanmin(V, axis=1)
        last = (M * np.arange(len(years_past))).max(axis=1)
        moi_nhat = V[np.arange(len(V)), last]
        # hồi quy tuyến tính có mặt nạ -> độ dốc = xu hướng điểm/năm
        X, Y = np.where(M, yrs, 0.0), np.nan_to_num(V)
        sx, sy, sxy, sxx = X.sum(1), Y.sum(1), (X * Y).sum(1), (X * X).sum(1)
        den = n * sxx - sx ** 2
        slope = np.where(den != 0, (n * sxy - sx * sy) / np.where(den == 0, 1, den), 0.0)

    feat = piv.reset_index()[KEY].copy()
    feat["diem_tb"] = np.round(tb, 2)
    feat["diem_moi_nhat"] = moi_nhat
    feat["bien_dong"] = np.round(mx - mn, 2)
    feat["so_nam_co_dl"] = n.astype("int8")
    feat["xu_huong"] = np.round(np.where(n >= 2, slope, 0.0), 3)
    return feat


def sinh_mau(fact: pd.DataFrame) -> pd.DataFrame:
    """fact: [KEY + nam, diem_chuan, nhom_nganh, vung_mien] -> mẫu train/test."""
    khoi = []
    for t in NAM_TRAIN + NAM_TEST:
        past = fact[(fact["nam"] < t) & (fact["nam"] >= t - NAM_LOOKBACK)]
        muc_tieu = fact[fact["nam"] == t]
        if past.empty or muc_tieu.empty:
            continue
        feat = dac_trung_cutoff(past, sorted(past["nam"].unique()))
        m = muc_tieu.merge(feat, on=KEY, how="inner")  # key mới toanh ở t -> bỏ
        m = m.reset_index(drop=True)
        rep = m.loc[m.index.repeat(len(DELTAS))].reset_index(drop=True)
        d = np.tile(np.asarray(DELTAS), len(m))
        diem_thi = np.clip((rep["diem_chuan"].to_numpy() + d), 0, 40).round(2)
        rep["diem_thi"] = diem_thi
        rep["margin"] = (diem_thi - rep["diem_moi_nhat"].to_numpy()).round(2)
        rep["nhan"] = (diem_thi >= rep["diem_chuan"].to_numpy()).astype("int8")
        rep["nam_muc_tieu"] = t
        rep["split"] = "train" if t in NAM_TRAIN else "test"
        khoi.append(rep)
    out = pd.concat(khoi, ignore_index=True)
    return encode(out.drop(columns=["diem_chuan"]))


def load_fact(sample: int = 0) -> pd.DataFrame:
    """Đọc fact + chiều phân loại từ DB (giữ trong backend để khỏi lệ thuộc data/)."""
    import django  # noqa: E402

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from university.models import DiemChuan  # noqa: E402

    qs = (DiemChuan.objects
          .select_related("ma_truong", "nganh")
          .values("ma_truong_id", "nganh_id", "ma_to_hop_id", "phuong_thuc",
                  "nam", "diem_chuan",
                  "nganh__nhom_nganh", "ma_truong__vung_mien"))
    rows = list(qs)
    df = pd.DataFrame(rows).rename(columns={
        "ma_truong_id": "ma_truong", "ma_to_hop_id": "ma_to_hop",
        "nganh__nhom_nganh": "nhom_nganh", "ma_truong__vung_mien": "vung_mien"})
    df["diem_chuan"] = df["diem_chuan"].astype(float)
    if sample:
        keys = df[KEY].drop_duplicates().head(sample)
        df = df.merge(keys, on=KEY, how="inner")
    return df


def main(out_dir: str, sample: int = 0) -> None:
    fact = load_fact(sample)
    print(f"fact: {len(fact):,} dòng")
    ds = sinh_mau(fact)
    train = ds[ds["split"] == "train"].drop(columns=["split"])
    test = ds[ds["split"] == "test"].drop(columns=["split"])
    os.makedirs(out_dir, exist_ok=True)
    train.to_csv(os.path.join(out_dir, "train_dataset.csv"), index=False)
    test.to_csv(os.path.join(out_dir, "test_dataset.csv"), index=False)
    cot = ten_cot_dac_trung()
    meta = {
        "nam_train": NAM_TRAIN, "nam_test": NAM_TEST,
        "nam_lookback": NAM_LOOKBACK, "deltas": DELTAS,
        "train_rows": len(train), "test_rows": len(test),
        "train_pos_rate": round(float(train["nhan"].mean()), 4),
        "test_pos_rate": round(float(test["nhan"].mean()), 4),
        "so_key": int(fact[KEY].drop_duplicates().shape[0]),
        "cot_dac_trung": cot, "so_dac_trung": len(cot),
        "nhan_thieu": {c: int(train[c].isna().sum() + test[c].isna().sum())
                       for c in cot if train[c].isna().any() or test[c].isna().any()},
    }
    with open(os.path.join(out_dir, "dataset_meta.json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"train: {len(train):,} dòng (đỗ {meta['train_pos_rate']:.1%})")
    print(f"test : {len(test):,} dòng (đỗ {meta['test_pos_rate']:.1%})")


def _selfcheck() -> None:
    """Kiểm tra logic không cần DB: leakage, nhãn, margin, split."""
    fact = pd.DataFrame([
        # key A: 2021=20, 2022=22 -> mẫu năm 2023 phải thấy moi_nhat=22, tb=21
        {"ma_truong": "A", "nganh_id": 1, "ma_to_hop": "A00",
         "phuong_thuc": "Điểm thi THPT", "nam": 2021, "diem_chuan": 20.0,
         "nhom_nganh": "Kỹ thuật - Công nghệ", "vung_mien": "Miền Bắc"},
        {"ma_truong": "A", "nganh_id": 1, "ma_to_hop": "A00",
         "phuong_thuc": "Điểm thi THPT", "nam": 2022, "diem_chuan": 22.0,
         "nhom_nganh": "Kỹ thuật - Công nghệ", "vung_mien": "Miền Bắc"},
        {"ma_truong": "A", "nganh_id": 1, "ma_to_hop": "A00",
         "phuong_thuc": "Điểm thi THPT", "nam": 2023, "diem_chuan": 21.0,
         "nhom_nganh": "Kỹ thuật - Công nghệ", "vung_mien": "Miền Bắc"},
    ])
    ds = sinh_mau(fact)
    # chỉ năm 2022, 2023 có quá khứ -> train hết (không có 2025)
    assert set(ds["nam_muc_tieu"]) == {2022, 2023}, ds["nam_muc_tieu"].unique()
    assert (ds["split"] == "train").all()
    # chống leakage: mẫu năm 2023 không được thấy C=21 trong đặc trưng
    m23 = ds[ds["nam_muc_tieu"] == 2023]
    assert (m23["diem_moi_nhat"] == 22.0).all(), m23["diem_moi_nhat"].unique()
    assert (m23["diem_tb"] == 21.0).all()
    assert (m23["xu_huong"] == 2.0).all(), m23["xu_huong"].unique()
    assert (m23["so_nam_co_dl"] == 2).all()
    # nhãn: đỗ khi diem_thi >= C(2023)=21
    assert ((m23["diem_thi"] >= 21.0) == (m23["nhan"] == 1)).all()
    # margin = diem_thi - moi_nhat
    assert np.allclose(m23["margin"], m23["diem_thi"] - 22.0)
    # mẫu năm 2022 chỉ thấy 2021: n=1, slope=0, bien_dong=0
    m22 = ds[ds["nam_muc_tieu"] == 2022]
    assert (m22["so_nam_co_dl"] == 1).all()
    assert (m22["xu_huong"] == 0.0).all() and (m22["bien_dong"] == 0.0).all()
    # 1.3 — encode: cột chuỗi biến mất, one-hot đúng 1 giá trị mỗi nhóm
    assert not {"nhom_nganh", "vung_mien", "phuong_thuc"} & set(ds.columns)
    cot = ten_cot_dac_trung()
    assert all(c in ds.columns for c in cot), set(cot) - set(ds.columns)
    assert len(cot) == len(set(cot)), "cột đặc trưng trùng tên"
    assert (ds[[c for c in cot if c.startswith("nn_")]].sum(axis=1) == 1).all()
    assert (ds[[c for c in cot if c.startswith("vm_")]].sum(axis=1) == 1).all()
    assert (ds[[c for c in cot if c.startswith("pt_")]].sum(axis=1) == 1).all()
    # 1.4 — không null trong vector đặc trưng + nhãn nhị phân
    assert not ds[cot].isna().any().any()
    assert set(ds["nhan"].unique()) <= {0, 1}

    # Giá trị phân loại lạ (nguồn thêm nhóm mới) -> vector toàn 0, không lỗi.
    la = fact.copy()
    la.loc[la["nam"] == 2023, "nhom_nganh"] = "Nhóm Chưa Từng Có"
    ds_la = sinh_mau(la)
    m = ds_la[ds_la["nam_muc_tieu"] == 2023]
    assert (m[[c for c in cot if c.startswith("nn_")]].sum(axis=1) == 0).all()
    assert (ds_la[[c for c in ten_cot_dac_trung()]].isna().sum().sum() == 0)

    print(f"selfcheck OK ({len(ds)} mẫu, {len(DELTAS)}/năm-key, {len(cot)} cột đặc trưng)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__)))
    a = ap.parse_args()
    if a.selfcheck:
        _selfcheck()
    else:
        main(a.out, a.sample)
