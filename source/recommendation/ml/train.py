# -*- coding: utf-8 -*-
"""Huấn luyện + đánh giá mô hình gợi ý (SRS 6.5, UC-10 bước 4).

Đọc `train_dataset.csv` / `test_dataset.csv` do `gen_dataset.py` sinh ra, fit
`RandomForestClassifier(n_estimators=300, min_samples_leaf=5)` (SRS 6.5) và
`DecisionTreeClassifier` làm baseline đối chiếu, chuẩn hoá đặc trưng số bằng
`StandardScaler`, đánh giá bằng `accuracy_score` + `classification_report`.

Chia tập đã làm ở bước 1 (theo NĂM, không ngẫu nhiên) — ở đây chỉ đọc lại.

Chạy:  python -m recommendation.ml.train            # train + lưu pkl
        python -m recommendation.ml.train --selfcheck  # kiểm tra logic
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, brier_score_loss,
                             classification_report, roc_auc_score)
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .gen_dataset import ten_cot_dac_trung

# SRS 6.5 — siêu tham số chốt sẵn, không dò tự động.
# n_estimators=100 thay 300 của SRS: 300 cây cho model.pkl 130MB, vượt RB-3
# (<100MB). 100 cây giữ nguyên accuracy, dưới hạn.
# max_depth=14: chặn cây mọc hết cỡ, model.pkl < 100MB (RB-3).
RF_KW = dict(n_estimators=100, min_samples_leaf=5, max_depth=14, n_jobs=-1,
             random_state=42)
DT_KW = dict(min_samples_leaf=5, random_state=42)
NONG_PKL = "model.pkl"
NONG_SCALER = "scaler.pkl"
NONG_BAO_CAO = "bao_cao_danh_gia.json"
NONG_QUAN_TRONG = "feature_importance.json"
# Báo cáo của lần train bị từ chối (UC-10 bước 5) — ghi riêng, KHÔNG đè báo cáo
# của mô hình đang chạy. Trước đây ghi đè làm trang admin hiện chỉ số sai.
NONG_BAO_CAO_MOI = "bao_cao_danh_gia_moi.json"

# Ngưỡng dưới mức này thì feature phải làm lại — chốt chặn trước khi sang bước 3.
ACC_TOI_THIEU = 0.70


def doc_tap(ml_dir: str) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """Đọc 2 CSV, trả (X_train, X_test, y_train, y_test) đúng thứ tự cột."""
    cot = ten_cot_dac_trung()
    tr = pd.read_csv(os.path.join(ml_dir, "train_dataset.csv"))
    te = pd.read_csv(os.path.join(ml_dir, "test_dataset.csv"))
    thieu = [c for c in cot if c not in tr.columns or c not in te.columns]
    if thieu:
        raise SystemExit(f"CSV thiếu {len(thieu)} cột đặc trưng: {thieu[:5]}")
    return (tr[cot], te[cot],
            tr["nhan"].to_numpy(), te["nhan"].to_numpy())


def danh_gia(ten: str, y: np.ndarray, p1: np.ndarray) -> dict:
    """accuracy / AUC / Brier / precision-recall theo lớp đỗ (nhãn 1)."""
    yhat = (p1 >= 0.5).astype("int8")
    bao = classification_report(y, yhat, output_dict=True, zero_division=0)
    return {
        "ten": ten,
        "accuracy": round(float(accuracy_score(y, yhat)), 4),
        "roc_auc": round(float(roc_auc_score(y, p1)), 4),
        "brier": round(float(brier_score_loss(y, p1)), 4),
        "precision_do": round(float(bao["1"]["precision"]), 4),
        "recall_do": round(float(bao["1"]["recall"]), 4),
        "f1_do": round(float(bao["1"]["f1-score"]), 4),
        "precision_truot": round(float(bao["0"]["precision"]), 4),
        "recall_truot": round(float(bao["0"]["recall"]), 4),
    }


def huan_luyen(ml_dir: str, acc_cu: float | None = None) -> dict:
    """Fit scaler + baseline + RF, đánh giá trên test, ghi pkl + báo cáo."""
    Xtr, Xte, ytr, yte = doc_tap(ml_dir)
    print(f"train {Xtr.shape} · test {Xte.shape} · đỗ {ytr.mean():.1%}/{yte.mean():.1%}")

    # SRS 6.5 — StandardScaler cho đặc trưng số. Cây quyết định không cần chuẩn
    # hoá (ngưỡng chia bất biến theo tỉ lệ đơn điệu) nhưng SRS yêu cầu và nó làm
    # các mô hình tuyến tính thêm sau này dùng chung được pipeline.
    scaler = StandardScaler().fit(Xtr)
    Ztr, Zte = scaler.transform(Xtr), scaler.transform(Xte)

    ket_qua = []
    t0 = time.perf_counter()
    dt = DecisionTreeClassifier(**DT_KW).fit(Ztr, ytr)
    ket_qua.append(danh_gia("DecisionTree (baseline)", yte, dt.predict_proba(Zte)[:, 1]))
    print(f"  {ket_qua[-1]['ten']:26} acc={ket_qua[-1]['accuracy']:.4f} "
          f"auc={ket_qua[-1]['roc_auc']:.4f} ({time.perf_counter() - t0:.1f}s)")

    t0 = time.perf_counter()
    rf = RandomForestClassifier(**RF_KW).fit(Ztr, ytr)
    ket_qua.append(danh_gia("RandomForest (chính)", yte, rf.predict_proba(Zte)[:, 1]))
    print(f"  {ket_qua[-1]['ten']:26} acc={ket_qua[-1]['accuracy']:.4f} "
          f"auc={ket_qua[-1]['roc_auc']:.4f} ({time.perf_counter() - t0:.1f}s)")

    chinh, base = ket_qua[1], ket_qua[0]
    for c in ("accuracy", "roc_auc", "f1_do"):
        if chinh[c] < base[c]:
            print(f"  ! RandomForest kém hơn baseline ở {c} "
                  f"({chinh[c]:.4f} < {base[c]:.4f})")

    # feature_importances_ -> UC-06 hiển thị mức đóng góp (SRS 6.5)
    cot = ten_cot_dac_trung()
    quan_trong = sorted(zip(cot, (float(v) for v in rf.feature_importances_)),
                        key=lambda x: -x[1])

    # UC-10 bước 5 — chỉ thay thế nếu độ chính xác không giảm.
    thay = acc_cu is None or chinh["accuracy"] >= acc_cu
    bao_cao = {
        "thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"),
        "siêu_tham_so": {"RandomForest": RF_KW, "DecisionTree": DT_KW},
        "so_dac_trung": len(cot),
        "cot_dac_trung": cot,
        "ket_qua": ket_qua,
        "feature_importance": [{"dac_trung": k, "muc_dong_gop": round(v, 5)}
                               for k, v in quan_trong],
        "acc_cu": acc_cu,
        "thay_the": bool(thay),
    }
    if not thay:
        print(f"  ! acc {chinh['accuracy']:.4f} < bản đang chạy {acc_cu:.4f} "
              f"— KHÔNG ghi đè model.pkl (UC-10 bước 5)")
        with open(os.path.join(ml_dir, NONG_BAO_CAO_MOI), "w", encoding="utf-8") as f:
            json.dump(bao_cao, f, ensure_ascii=False, indent=2)
        return bao_cao

    joblib.dump(rf, os.path.join(ml_dir, NONG_PKL))
    joblib.dump(scaler, os.path.join(ml_dir, NONG_SCALER))
    with open(os.path.join(ml_dir, NONG_BAO_CAO), "w", encoding="utf-8") as f:
        json.dump(bao_cao, f, ensure_ascii=False, indent=2)
    with open(os.path.join(ml_dir, NONG_QUAN_TRONG), "w", encoding="utf-8") as f:
        json.dump(bao_cao["feature_importance"], f, ensure_ascii=False, indent=2)

    co = os.path.getsize(os.path.join(ml_dir, NONG_PKL))
    print(f"  model.pkl {co / 1e6:.1f} MB (RB-3: < 100 MB) · "
          f"thay_thế={bao_cao['thay_the']} · acc cũ={acc_cu}")
    if co > 100e6:
        print("  ! model.pkl vượt 100 MB — RB-3 yêu cầu giảm n_estimators")
    if chinh["accuracy"] < ACC_TOI_THIEU:
        print(f"  ! acc {chinh['accuracy']:.4f} < {ACC_TOI_THIEU} — cần xem lại "
              f"đặc trưng ở bước 1 trước khi sang bước 3")
    return bao_cao


def _selfcheck() -> None:
    """Kiểm tra hàm đánh giá trên dữ liệu giả — không cần CSV."""
    y = np.array([1, 1, 0, 0])
    # dự đoán hoàn hảo
    k = danh_gia("hoan_hao", y, np.array([0.9, 0.8, 0.2, 0.1]))
    assert k["accuracy"] == 1.0 and k["roc_auc"] == 1.0, k
    assert k["precision_do"] == 1.0 and k["recall_do"] == 1.0
    # dự đoán ngược hoàn toàn
    k = danh_gia("nguoc", y, np.array([0.1, 0.2, 0.8, 0.9]))
    assert k["accuracy"] == 0.0 and k["roc_auc"] == 0.0, k
    assert k["recall_do"] == 0.0 and k["recall_truot"] == 0.0
    # toàn 0.5 -> ngưỡng >=0.5 => đoán hết là đỗ
    k = danh_gia("giua", y, np.full(4, 0.5))
    assert k["accuracy"] == 0.5, k
    assert k["recall_truot"] == 0.0 and k["recall_do"] == 1.0
    # Brier: dự đoán hoàn hảo = 0
    assert danh_gia("b", y, np.array([1.0, 1.0, 0.0, 0.0]))["brier"] == 0.0

    # Fit thật trên dữ liệu tổng hợp để chắc pipeline chạy được end-to-end.
    rng = np.random.default_rng(0)
    n = 400
    X = pd.DataFrame(rng.normal(size=(n, len(ten_cot_dac_trung()))),
                     columns=ten_cot_dac_trung())
    yg = (X["margin"] + rng.normal(scale=0.3, size=n) > 0).astype("int8")
    sc = StandardScaler().fit(X)
    m = RandomForestClassifier(n_estimators=20, min_samples_leaf=5,
                               random_state=42).fit(sc.transform(X), yg)
    p = m.predict_proba(sc.transform(X))[:, 1]
    assert accuracy_score(yg, (p >= 0.5).astype("int8")) > 0.8
    assert len(m.feature_importances_) == len(ten_cot_dac_trung())

    print(f"selfcheck OK ({len(ten_cot_dac_trung())} đặc trưng, "
          f"pipeline fit được, acc trên dữ liệu tổng hợp "
          f"{accuracy_score(yg, (p >= 0.5).astype('int8')):.3f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--acc-cu", type=float, default=None,
                    help="accuracy của model.pkl đang chạy (UC-10 bước 5)")
    a = ap.parse_args()
    if a.selfcheck:
        _selfcheck()
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
        r = huan_luyen(a.dir, a.acc_cu)
        print("báo cáo: " + NONG_BAO_CAO)
