# -*- coding: utf-8 -*-
"""Bước 4–5 (UC-10 + PC-01) — kiểm tra trang admin huấn luyện và hiệu năng.

Bước 4: admin vào /quan-tri/ai/ thấy mô hình đang chạy, bấm huấn luyện lại thì
Django khởi động thread nền (không giữ request), chạy xong model.pkl đổi.
Bước 5: đo thời gian phản hồi thật của UC-05 trên dữ liệu thật (PC-01 < 3s).

Chạy:  python -m recommendation.check_admin
       python -m recommendation.check_admin --khong-train   # bỏ qua train nền
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402

from admissions.models import DiemMon, HoSoNangLuc  # noqa: E402
from quantri import views as qv  # noqa: E402
from recommendation.ml.predict import ML_DIR  # noqa: E402
from university.models import Mon  # noqa: E402

U = get_user_model()
LOI = []
NONG_PKL = os.path.join(ML_DIR, "model.pkl")


def kt(ten, dieu_kien, chi_tiet=""):
    print(f"   [{'OK' if dieu_kien else 'SAI'}]  {ten}"
          f"{'' if dieu_kien else ' — ' + str(chi_tiet)}")
    if not dieu_kien:
        LOI.append(ten)


def _so_dong(ten_file: str) -> int:
    """Đếm dòng dữ liệu của CSV trong ML_DIR (-1 nếu không đọc được)."""
    try:
        with open(os.path.join(ML_DIR, ten_file), encoding="utf-8") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except OSError:
        return -1


def train_rows_mong_doi() -> int:
    """Số dòng train mong đợi theo `dataset_meta.json` (nguồn: bước 1)."""
    try:
        import json

        with open(os.path.join(ML_DIR, "dataset_meta.json"), encoding="utf-8") as f:
            return int(json.load(f)["train_rows"])
    except (OSError, ValueError, KeyError):
        return -1


def _ho_so_mau():
    u, _ = U.objects.get_or_create(username="e2e_b45",
                                   defaults={"email": "e45@x.local"})
    u.set_password("x")
    u.save()
    hs, _ = HoSoNangLuc.objects.get_or_create(
        user=u, ten_ho_so="E2E bước 4-5",
        defaults={"phuong_thuc": "Điểm thi THPT"})
    if not DiemMon.objects.filter(ho_so=hs).exists():
        for ma, d in (("TOAN", 8.0), ("LI", 7.5), ("HOA", 8.0), ("ANH", 7.0)):
            if Mon.objects.filter(ma_mon=ma).exists():
                DiemMon.objects.create(ho_so=hs, ma_mon_id=ma, diem=d)
    return u, hs


def phan_4(dem_train: bool):
    print("\n-- Bước 4: trang quản trị AI + huấn luyện lại (UC-10) --")
    staff = U.objects.filter(is_staff=True).order_by("pk").first()
    if staff is None:
        kt("có tài khoản staff", False, "chưa có user nào is_staff=True")
        return
    c = Client()
    c.force_login(staff)

    r = c.get("/quan-tri/ai/")
    kt("/quan-tri/ai/ trả 200", r.status_code == 200, r.status_code)
    html = r.content.decode()
    kt("trang hiện kết quả đánh giá mô hình", "Kết quả đánh giá" in html)
    kt("trang hiện feature importance", "Mức đóng góp đặc trưng" in html)
    kt("có nút huấn luyện", "Huấn luyện lại" in html)

    # RB-3 — kích thước mô hình trên đĩa.
    if os.path.exists(NONG_PKL):
        mb = os.path.getsize(NONG_PKL) / 1e6
        kt("RB-3: model.pkl < 100 MB", mb < 100, f"{mb:.1f} MB")

    # Không phải staff -> bị chặn (accounts:dang_nhap).
    u_thuong, _ = _ho_so_mau()
    c2 = Client()
    c2.force_login(u_thuong)
    r2 = c2.get("/quan-tri/ai/")
    kt("user thường KHÔNG vào được /quan-tri/ai/", r2.status_code == 302, r2.status_code)

    if not dem_train:
        return

    # UC-10 bước 1–6 — bấm huấn luyện: phải trả về NGAY, không chờ train xong.
    # KHÔNG POST thật: `_chay_huan_luyen` gọi `gen_dataset.main(ML_DIR, sample)`
    # và GHI ĐÈ train_dataset.csv/test_dataset.csv. Dù sample > 0 hay 0 thì chỉ
    # cần 1 lần bấm là mất dataset đầy đủ + báo cáo. Ở đây thay thread nền bằng
    # hàm rỗng nên luồng vào/ra của view (POST -> 302 -> cờ chạy -> kết thúc)
    # vẫn được kiểm đúng như thật mà đĩa không đổi.
    from recommendation.ml import gen_dataset as G

    goc_main = G.main
    truoc = os.path.getmtime(NONG_PKL) if os.path.exists(NONG_PKL) else 0
    G.main = lambda *a, **k: None          # chặn ghi CSV
    try:
        t0 = time.perf_counter()
        r = c.post("/quan-tri/ai/huan-luyen/", {"sample": "40"})
        giay = time.perf_counter() - t0
        kt("POST huấn luyện trả về ngay (< 3s)",
           giay < 3.0 and r.status_code == 302, f"{giay:.2f}s / {r.status_code}")
        kt("cờ đang_chạy được bật", qv._trang_thai["dang_chay"] is True)
        kt("POST trùng bị chặn khi đang chạy",
           c.post("/quan-tri/ai/huan-luyen/", {}).status_code == 302)
        kt("GET /ai/huan-luyen/ không train (chỉ POST mới chạy)",
           c.get("/quan-tri/ai/huan-luyen/").status_code == 302)

        het = time.time() + 180
        while qv._trang_thai["dang_chay"] and time.time() < het:
            time.sleep(1)
        kt("huấn luyện kết thúc trong 180s", not qv._trang_thai["dang_chay"])
        kt("không có lỗi khi huấn luyện", not qv._trang_thai["loi"],
           qv._trang_thai["loi"])

        kq = qv._trang_thai.get("ket_qua") or {}
        rf = [k for k in kq.get("ket_qua") or []
              if k["ten"].startswith("RandomForest")]
        kt("báo cáo có kết quả RandomForest", bool(rf))
        # Model train trên dataset đầy đủ = y hệt bản đang chạy -> KHÔNG thay thế
        # (UC-10/5 so `>=` nên bằng nhau vẫn thay; ở đây acc_cu lấy từ báo cáo nên
        # nhiều khả năng thay_the=True). Điều bắt buộc là KHÔNG lỗi và có báo cáo.
        if rf:
            print(f"        acc={rf[0]['accuracy']} auc={rf[0]['roc_auc']}"
                  f" thay_the={kq.get('thay_the')}")
    finally:
        G.main = goc_main

    kt("CSV tập huấn luyện giữ nguyên (không bị lấy mẫu)",
       _so_dong("train_dataset.csv") == train_rows_mong_doi(),
       _so_dong("train_dataset.csv"))
    kt("model.pkl vẫn là bản 43 MB của dữ liệu đầy đủ",
       os.path.getsize(NONG_PKL) > 10e6 and os.path.getmtime(NONG_PKL) >= truoc,
       f"{os.path.getsize(NONG_PKL) / 1e6:.1f} MB")

    # UC-10 bước 5 — model kém hơn thì KHÔNG được ghi đè.
    truoc2 = os.path.getmtime(NONG_PKL)
    bao_cu = qv._doc_bao_cao()
    acc_cu = (max(k["accuracy"] for k in bao_cu["ket_qua"]
                  if k["ten"].startswith("RandomForest")) if bao_cu else None)
    from recommendation.ml import train as T

    kem = T.huan_luyen(ML_DIR, acc_cu=1.1)  # 1.1 = không mô hình nào đạt
    kt("UC-10/5: acc thấp hơn -> không thay thế", kem["thay_the"] is False,
       kem["thay_the"])
    kt("UC-10/5: model.pkl giữ nguyên", os.path.getmtime(NONG_PKL) == truoc2)
    # Báo cáo của lần bị từ chối ghi ra file riêng — báo cáo đang chạy không đổi.
    cu = qv._doc_bao_cao()
    kt("UC-10/5: báo cáo mô hình đang chạy không bị đè",
       cu and cu.get("thay_the") is True, cu and cu.get("thay_the"))
    kt("UC-10/5: báo cáo bị từ chối ghi ra file riêng",
       os.path.exists(os.path.join(ML_DIR, T.NONG_BAO_CAO_MOI)))


def phan_5():
    print("\n-- Bước 5: hiệu năng PC-01 (< 3s) + chế độ dự phòng --")
    u, hs = _ho_so_mau()
    c = Client()
    c.force_login(u)

    # Đo 3 lần: lần 1 gồm nạp model từ đĩa, các lần sau dùng bản trong RAM.
    for i in range(3):
        t0 = time.perf_counter()
        r = c.get(f"/goi-y/{hs.pk}/")
        giay = time.perf_counter() - t0
        kt(f"UC-05 lần {i + 1} trả 200 và < 3s",
           r.status_code == 200 and giay < 3.0, f"{giay:.2f}s / {r.status_code}")

    # Chế độ dự phòng UC-05/5b: giả lập mô hình hỏng -> vẫn phải ra gợi ý.
    from recommendation.ml import predict

    goc = predict.NONG_PKL
    try:
        predict.nap_lai()
        predict.NONG_PKL = os.path.join(ML_DIR, "khong_ton_tai.pkl")
        predict.nap_lai()
        kt("thiếu model.pkl -> nap_mo_hinh trả None",
           predict.nap_mo_hinh() is None)

        r = c.get(f"/goi-y/{hs.pk}/")
        html = r.content.decode()
        kt("UC-05/5b: vẫn trả 200 khi mô hình lỗi", r.status_code == 200,
           r.status_code)
        kt("UC-05/5b: có ghi chú 'chưa dùng mô hình AI'",
           "chưa dùng mô hình AI" in html)

        from recommendation.models import LanGoiY

        lan = LanGoiY.objects.filter(ho_so=hs).order_by("-pk").first()
        kt("UC-05/5b: ghi dung_ai=False", lan is not None and lan.dung_ai is False,
           None if lan is None else lan.dung_ai)
    finally:
        predict.NONG_PKL = goc
        predict.nap_lai()

    # Nạp lại bình thường.
    r = c.get(f"/goi-y/{hs.pk}/")
    from recommendation.models import LanGoiY

    lan = LanGoiY.objects.filter(ho_so=hs).order_by("-pk").first()
    kt("khôi phục: dùng AI trở lại", lan is not None and lan.dung_ai is True,
       None if lan is None else lan.dung_ai)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--khong-train", action="store_true",
                    help="bỏ qua phần huấn luyện nền (chỉ kiểm tra trang + hiệu năng)")
    a = ap.parse_args()
    phan_4(not a.khong_train)
    phan_5()
    print()
    if LOI:
        print(f"THẤT BẠI: {len(LOI)} mục -> {LOI}")
        sys.exit(1)
    print("Bước 4–5: tất cả đạt.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    main()
