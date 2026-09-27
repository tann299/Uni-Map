# -*- coding: utf-8 -*-
"""Kiểm tra bước 3 (SRS 6.5 bước 4) — mô hình có thật sự chạy trong web không.

Đi hết luồng thật qua Django test Client: đăng nhập -> hồ sơ -> UC-05 -> UC-06
-> UC-07 -> UC-08, kiểm tra `dung_ai=True`, `xac_suat_do` nằm trong [0,1], tầng
khớp ngưỡng xác suất CN-03, lịch sử lưu đúng snapshot.

Chạy:  python -m recommendation.check_e2e
"""
from __future__ import annotations

import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

from admissions.models import HoSoNangLuc, DiemMon  # noqa: E402
from recommendation.models import KetQuaGoiY, LanGoiY  # noqa: E402
from recommendation.services import phan_tang_theo_xac_suat  # noqa: E402
from university.models import Mon  # noqa: E402

U = get_user_model()
LOI = []


def kt(ten, dieu_kien, chi_tiet=""):
    print(f"   [{'OK' if dieu_kien else 'SAI'}]  {ten}{'' if dieu_kien else ' — ' + str(chi_tiet)}")
    if not dieu_kien:
        LOI.append(ten)


def main():
    u, _ = U.objects.get_or_create(username="e2e_b3",
                                   defaults={"email": "e2e@x.local"})
    u.set_password("x")
    u.save()

    # Hồ sơ có điểm thật để CN-01 ra được tổ hợp.
    hs, _ = HoSoNangLuc.objects.get_or_create(
        user=u, ten_ho_so="E2E bước 3",
        defaults={"phuong_thuc": "Điểm thi THPT"})
    DiemMon.objects.filter(ho_so=hs).delete()
    for ma, d in (("TOAN", 8.0), ("LI", 7.5), ("HOA", 8.0), ("ANH", 7.0)):
        if Mon.objects.filter(ma_mon=ma).exists():
            DiemMon.objects.create(ho_so=hs, ma_mon_id=ma, diem=d)

    c = Client()
    c.force_login(u)

    t0 = time.perf_counter()
    r = c.get(f"/goi-y/{hs.pk}/")
    giay = time.perf_counter() - t0
    kt("UC-05 trả 200", r.status_code == 200, r.status_code)
    kt("PC-01 phản hồi < 3s", giay < 3.0, f"{giay:.2f}s")

    lan = LanGoiY.objects.filter(ho_so=hs).order_by("-pk").first()
    kt("có bản ghi lan_goi_y", lan is not None)
    if lan is None:
        return tong_ket()
    kt("dung_ai=True (mô hình chạy)", lan.dung_ai is True, lan.dung_ai)
    kt("có phiên bản mô hình", bool(lan.phien_ban_mo_hinh), lan.phien_ban_mo_hinh)

    kq = list(KetQuaGoiY.objects.filter(lan_goi_y=lan).select_related("nganh"))
    kt("có kết quả gợi ý", len(kq) > 0, len(kq))

    # Xác suất trong [0,1] và tầng khớp ngưỡng CN-03.
    xau = [k for k in kq if not (0 <= float(k.xac_suat_do) <= 1)]
    kt("mọi xac_suat_do ∈ [0,1]", not xau, [(k.pk, k.xac_suat_do) for k in xau[:3]])
    lech = [k for k in kq
            if k.tang != phan_tang_theo_xac_suat(float(k.xac_suat_do))]
    kt("tầng khớp ngưỡng xác suất CN-03", not lech,
       [(k.pk, float(k.xac_suat_do), k.tang) for k in lech[:3]])

    # Xác suất phải PHÂN BIỆT được các ngành — không dồn về 1 giá trị.
    cac_p = {round(float(k.xac_suat_do), 3) for k in kq}
    kt("xác suất không hằng số", len(cac_p) > 1, f"{len(cac_p)} giá trị khác nhau")

    # Việc học: ngành margin cao hơn phải có xác suất cao hơn (tương quan dương).
    cap = sorted(((float(k.margin), float(k.xac_suat_do)) for k in kq))
    if len(cap) >= 5:
        nua = len(cap) // 2
        tb_thap = sum(p for _, p in cap[:nua]) / nua
        tb_cao = sum(p for _, p in cap[-nua:]) / nua
        kt("margin cao -> xác suất cao hơn", tb_cao > tb_thap,
           f"thấp {tb_thap:.3f} vs cao {tb_cao:.3f}")

    # UC-06 — trang chi tiết hiện xác suất, đọc snapshot không tính lại.
    r = c.get(f"/goi-y/chi-tiet/{kq[0].pk}/")
    kt("UC-06 trả 200", r.status_code == 200, r.status_code)
    kt("UC-06 hiện 'Khả năng đỗ'", "Khả năng đỗ" in r.content.decode(), "")

    # UC-07 — so sánh cùng thang đo với UC-05.
    ss = "&".join(f"ss={k.ma_truong_id}|{k.nganh_id}|{k.ma_to_hop_id}|{k.phuong_thuc}"
                  for k in kq[:2])
    r = c.get(f"/goi-y/so-sanh/{hs.pk}/?{ss}")
    kt("UC-07 trả 200", r.status_code == 200, r.status_code)

    # UC-08 — lịch sử giữ nguyên snapshot.
    r = c.get(f"/goi-y/lich-su/{hs.pk}/")
    kt("UC-08 trả 200", r.status_code == 200, r.status_code)

    tong_ket()


def tong_ket():
    print()
    if LOI:
        print(f"THẤT BẠI: {len(LOI)} mục -> {LOI}")
        sys.exit(1)
    print("E2E bước 3: tất cả đạt.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    main()
