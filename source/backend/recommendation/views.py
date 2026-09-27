# -*- coding: utf-8 -*-
"""
View app `recommendation` — engine gợi ý nguyện vọng (SRS UC-05, UC-06, UC-07, UC-08).

Luồng chính (UC-05):
  1. Đọc hồ sơ năng lực (UC-04, app `admissions`) -> CN-01 tính mọi tổ hợp đủ môn
  2. Lọc cứng bằng SQL (index có sẵn, không quét toàn bảng) — PC-01 < 3s
  3. Tính `margin = điểm tổ hợp (+ ưu tiên) − diem_moi_nhat`
  4. Chấm xác suất đỗ bằng RandomForest (SRS 6.5 bước 4). Mô hình lỗi/thiếu file
     -> chế độ dự phòng UC-05/5b: xếp hạng bằng `margin`, ghi `dung_ai=False`
  5. Phân tầng An toàn / Vừa sức / Thử sức (CN-03)
  6. Sinh lời giải thích từ đặc trưng thật (CN-04)
  7. Lưu snapshot vào `lan_goi_y` + `ket_qua_goi_y` (UC-08)
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
import json as _json
from urllib.parse import quote

from admissions.models import HoSoNangLuc
from university.services import tinh_to_hop_tu_db
from university.models import VUNG_MIEN, CuaSoNam, DacTrungDiemChuan

from .ml.predict import cham_xac_suat, nap_mo_hinh, phien_ban
from .models import KetQuaGoiY, LanGoiY
from .services import (chon_can_ban, giai_thich, phan_tang,
                       phan_tang_theo_xac_suat, style_tang)

# UC-05 bước 7: hiển thị tối đa 30 gi ý.
MAX_GOI_Y = 30
# UC-05/5c: dưới ngưỡng này thì nới điều kiện lọc và báo cho học sinh.
NGUONG_IT = 5
# UC-07: so sánh tối đa 3 nguyện vọng cạnh nhau (mockup cũng ghi "thứ 3").
MAX_SO_SANH = 3
# UC-07: số ứng viên bày ra để chọn khi vào trang so sánh mà chưa chọn gì.
SO_UNG_VIEN_CHON = 12


def _chi_cua_user(user, pk):
    return get_object_or_404(HoSoNangLuc, pk=pk, user=user)


# ===========================================================================
# UC-05 — Nhận gợi  trường/ngành
# ===========================================================================

def _loc_cung(hs, to_hop_diem, *, dung_nhom=True, dung_vung=True):
    """UC-05 bước 3 — lọc cứng bằng SQL (có index), không quét toàn bảng.

    Loại: t hợp học sinh không đủ môn (đã lo ở CN-01), không thuộc nhóm ngành /
    khu vực học sinh chọn, và `so_nam_co_dl = 0` (không có lịch sử).
    """
    qs = (DacTrungDiemChuan.objects
          .select_related("ma_truong", "nganh", "ma_to_hop")
          .filter(ma_to_hop_id__in=list(to_hop_diem),
                  phuong_thuc=hs.phuong_thuc,
                  so_nam_co_dl__gt=0))
    nhom = list(hs.nhomnganhquantam_set.values_list("nhom_nganh", flat=True))
    if dung_nhom and nhom:
        qs = qs.filter(nganh__nhom_nganh__in=nhom)
    if dung_vung and hs.vung_mien_uu_tien in dict(VUNG_MIEN):
        qs = qs.filter(ma_truong__vung_mien=hs.vung_mien_uu_tien)
    return qs


def _thanh_dong(r, diem_hs, uu_tien_ap_dung, p=None):
    """1 ứng viên -> dict hiển thị (giữ `kq` là dòng đặc trưng để lấy chuỗi 5 năm).

    `p` là xác suất đỗ của mô hình; None = chưa chấm được -> phân tầng bằng
    `margin` (chế độ dự phòng UC-05/5b).

    `p` được LÀM TRÒN về 4 chữ số thập phân TRƯỚC khi phân tầng, khớp
    `xac_suat_do DECIMAL(5,4)` của lược đồ. Nếu không, p=0,80001 lưu thành
    0,8000 nhưng tầng tính theo 0,80001 -> xem lại lịch sử thấy tầng không khớp
    con số hiển thị.
    """
    p = None if p is None else round(float(p), 4)
    margin = round(diem_hs - float(r.diem_moi_nhat), 2)
    tang = phan_tang_theo_xac_suat(p) if p is not None else phan_tang(margin)
    return {
        "kq": r,
        "diem_hoc_sinh": diem_hs,
        "margin": margin,
        "xac_suat": None if p is None else round(p * 100, 2),
        "tang": tang,
        "style": style_tang(tang),
        "uu_tien_ap_dung": uu_tien_ap_dung,
    }


def _xep_hang(hs, to_hop_diem, qs):
    """Bước 4–6: chấm xác suất -> phân tầng -> chọn danh sách CÂN BẰNG rủi ro.

    CN-03 yêu cầu mỗi tầng đều có gợi ý (nếu dữ liệu cho phép) để học sinh xếp
    được thứ tự nguyện vọng. Nếu chỉ lấy top `MAX_GOI_Y` theo điểm thì danh sách
    toàn tầng "An toàn" — mất hẳn nhóm "Thử sức". Nên chia quota đều cho 3 tầng,
    tầng nào thiếu thì nhường suất cho tầng khác.
    """
    uu_tien = float(hs.diem_uu_tien or 0)
    ds = list(qs)

    # Bước 4 (SRS 6.5) — chấm cả lô trong 1 lần predict_proba (PC-01 < 3s).
    p_theo_ung_vien = {}
    if nap_mo_hinh() is not None:
        diem_theo_ung_vien = [
            (r, round(to_hop_diem[r.ma_to_hop_id] + uu_tien, 2)) for r in ds]
        kq = cham_xac_suat(diem_theo_ung_vien)
        if kq is not None:
            p_theo_ung_vien = dict(zip((r.pk for r in ds), (float(v) for v in kq)))

    theo_tang = {"An toàn": [], "Vừa sức": [], "Thử sức": []}
    for r in ds:
        diem_hs = round(to_hop_diem[r.ma_to_hop_id] + uu_tien, 2)
        row = _thanh_dong(r, diem_hs, uu_tien, p_theo_ung_vien.get(r.pk))
        theo_tang[row["tang"]].append(row)
    # Xếp trong tầng: có xác suất thì theo xác suất giảm dần (khớp ngưỡng phân
    # tầng), chưa có thì theo margin như cũ.
    for rows in theo_tang.values():
        rows.sort(key=lambda x: (-(x["xac_suat"] if x["xac_suat"] is not None
                                   else x["margin"] * 10),
                                 x["kq"].ma_truong_id, x["kq"].nganh_id))
    return chon_can_ban(theo_tang, MAX_GOI_Y), bool(p_theo_ung_vien)


@login_required
def xem_goi_y(request, pk):
    hs = _chi_cua_user(request.user, pk)
    to_hop = tinh_to_hop_tu_db(hs.diem_theo_mon())
    to_hop_diem = {t["ma"]: t["tong"] for t in to_hop}

    if not to_hop_diem:
        messages.warning(request, "Hồ sơ chưa có điểm môn nào — hãy nhập điểm trước.")
        return redirect("admissions:sua_ho_so", pk=hs.pk)

    _, _, rows, da_noi, dung_ai = _goi_y_uc05(hs, to_hop_diem)

    with transaction.atomic():
        lan = LanGoiY.objects.create(
            ho_so=hs, phien_ban_mo_hinh=phien_ban() if dung_ai else "",
            dung_ai=dung_ai, so_ket_qua=len(rows))
        KetQuaGoiY.objects.bulk_create([
            KetQuaGoiY(
                lan_goi_y=lan, ma_truong_id=r["kq"].ma_truong_id,
                nganh_id=r["kq"].nganh_id, ma_to_hop_id=r["kq"].ma_to_hop_id,
                phuong_thuc=r["kq"].phuong_thuc, diem_hoc_sinh=r["diem_hoc_sinh"],
                margin=r["margin"],
                # Chưa dùng AI -> 0, ghi rõ ở UI (UC-05/5b). Dùng `xac_suat` đã
                # tròn 4 chữ số — cùng con số đã dùng để phân tầng.
                xac_suat_do=(r["xac_suat"] or 0) / 100 if dung_ai else 0,
                tang=r["tang"], thu_hang=i + 1,
            ) for i, r in enumerate(rows)
        ])
    # bulk_create không trả pk trên MySQL -> đọc lại theo thu_hang để link chi tiết.
    pk_theo_hang = dict(KetQuaGoiY.objects.filter(lan_goi_y=lan)
                        .values_list("thu_hang", "pk"))
    for i, r in enumerate(rows):
        r["kq_id"] = pk_theo_hang.get(i + 1)

    return render(request, "recommendation/goi_y_ket_qua.html", {
        "nav_active": "goi_y", "ho_so": hs, "lan": lan, "ds": rows,
        "to_hop": to_hop, "da_noi": da_noi, "nguong_it": NGUONG_IT,
        "dung_ai": dung_ai, "toi_da_so_sanh": MAX_SO_SANH,
    })


def _goi_y_uc05(hs, to_hop_diem):
    """Bước 3–6 của UC-05, tách ra để trang so sánh dùng lại đúng danh sách đó.

    Trả `(to_hop_diem, to_hop_diem, rows, da_noi, dung_ai)`. Không ghi DB — chỉ
    `xem_goi_y` mới lưu snapshot (UC-08).
    """
    # Nới điều kiện dần khi quá ít kết quả (UC-05/5a và 5c).
    qs = _loc_cung(hs, to_hop_diem)
    da_noi = None
    if qs.count() < NGUONG_IT and hs.vung_mien_uu_tien in dict(VUNG_MIEN):
        qs = _loc_cung(hs, to_hop_diem, dung_vung=False)
        da_noi = "khu vực"
    if qs.count() < NGUONG_IT and hs.nhomnganhquantam_set.exists():
        qs = _loc_cung(hs, to_hop_diem, dung_nhom=False, dung_vung=False)
        da_noi = "nhóm ngành và khu vực"
    rows, dung_ai = _xep_hang(hs, to_hop_diem, qs)
    # Ứng viên xếp hạng chưa có `khoa` — trang so sánh cần để dựng lại URL `ss`.
    for r in rows:
        r["khoa"] = _khoa_ss(r["kq"])
    return to_hop_diem, to_hop_diem, rows, da_noi, dung_ai


@login_required
def lich_su_goi_y(request, pk):
    hs = _chi_cua_user(request.user, pk)
    ds = (LanGoiY.objects.filter(ho_so=hs)
          .prefetch_related("ketquagoiy_set__ma_truong", "ketquagoiy_set__nganh"))
    return render(request, "recommendation/lich_su_goi_y.html", {
        "nav_active": "goi_y", "ho_so": hs, "danh_sach": ds,
    })


@login_required
def xoa_lich_su(request, pk):
    """Xóa toàn bộ lần gợi ý của hồ sơ (CASCADE xóa ket_qua_goi_y)."""
    hs = _chi_cua_user(request.user, pk)
    if request.method == "POST":
        LanGoiY.objects.filter(ho_so=hs).delete()
        messages.success(request, "Đã xóa toàn bộ lịch sử gợi ý.")
    return redirect("recommendation:lich_su_goi_y", pk=hs.pk)


@login_required
def chi_tiet_goi_y(request, kq_id):
    """UC-06 — xem lời giải thích. Đọc SNAPSHOT, không tính lại (SRS UC-05)."""
    kq = get_object_or_404(
        KetQuaGoiY.objects.select_related(
            "lan_goi_y__ho_so", "ma_truong", "nganh", "ma_to_hop"),
        pk=kq_id, lan_goi_y__ho_so__user=request.user)

    # Đặc trưng để giải thích — đọc bảng đặc trưng hiện tại (CN-04).
    dt = DacTrungDiemChuan.objects.filter(
        ma_truong_id=kq.ma_truong_id, nganh_id=kq.nganh_id,
        ma_to_hop_id=kq.ma_to_hop_id, phuong_thuc=kq.phuong_thuc).first()

    nam_that = list(CuaSoNam.objects.values_list("nam", flat=True))
    bieu_do = [{"nam": n, "diem": d}
               for n, d in zip(nam_that, dt.chuoi_diem() if dt else [])]

    cau = giai_thich({
        "margin": kq.margin,
        "xu_huong": dt.xu_huong if dt else 0,
        "bien_dong": dt.bien_dong if dt else 0,
        "so_nam_co_dl": dt.so_nam_co_dl if dt else 0,
        "nam_moi_nhat": nam_that[-1] if nam_that else "gần nhất",
    })
    return render(request, "recommendation/goi_y_chi_tiet.html", {
        "nav_active": "goi_y", "kq": kq, "ho_so": kq.lan_goi_y.ho_so,
        "dt": dt, "bieu_do": bieu_do, "giai_thich": cau,
        "style": style_tang(kq.tang), "dung_ai": kq.lan_goi_y.dung_ai,
        "xac_suat_phan_tram": round(float(kq.xac_suat_do) * 100, 1),
    })


# ===========================================================================
# UC-07 — So sánh nguyện vọng (US-17)
# ===========================================================================

def _ung_vien(truong, nganh, to_hop, phuong_thuc):
    """Đọc 1 ứng viên từ bảng đặc trưng. None nếu không tồn tại."""
    return (DacTrungDiemChuan.objects
            .select_related("ma_truong", "nganh", "ma_to_hop")
            .filter(ma_truong_id=truong, nganh_id=nganh,
                    ma_to_hop_id=to_hop, phuong_thuc=phuong_thuc)
            .first())


def _doc_danh_sach_so_sanh(request):
    """Query `ss` dạng 'MA_TRUONG|nganh_id|ma_to_hop|phuong_thuc', lặp lại.

    Tối đa MAX_SO_SANH mục; bỏ mục không tra được để trang không vỡ.
    """
    ra = []
    for raw in request.GET.getlist("ss")[:MAX_SO_SANH]:
        phan = raw.split("|")
        if len(phan) != 4:
            continue
        ma_truong, nganh_id, ma_to_hop, phuong_thuc = phan
        try:
            nganh_id = int(nganh_id)
        except ValueError:
            continue
        dt = _ung_vien(ma_truong, nganh_id, ma_to_hop, phuong_thuc)
        if dt is not None:
            ra.append(dt)
    return ra


@login_required
def so_sanh_moi(request):
    """UC-07 — vào từ trang tra cứu: chọn hồ sơ đầu của user rồi so sánh.

    Trang tra cứu là công khai nên không biết hồ sơ nào; dùng hồ sơ mới nhất
    của user làm đích. Nếu chưa có hồ sơ, đẩy sang tạo hồ sơ trước.
    """
    hs = (HoSoNangLuc.objects.filter(user=request.user)
          .order_by("-ngay_sua").first())
    if not hs:
        messages.info(request, "Tạo hồ sơ năng lực để so sánh nguyện vọng.")
        return redirect("admissions:danh_sach_ho_so")
    # Chỉ chuyển tiếp `ss`, bỏ query của trang tra cứu (q, trang, ...).
    query = "&".join(f"ss={quote(s, safe='|')}"
                     for s in request.GET.getlist("ss")[:MAX_SO_SANH])
    url = reverse("recommendation:so_sanh", args=[hs.pk])
    return redirect(f"{url}?{query}" if query else url)


@login_required
def so_sanh(request, pk):
    """UC-07 — chọn và so sánh 2–3 nguyện vọng cạnh nhau.

    Vào từ header (không có `ss`) thì trang tự nạp danh sách gợi ý UC-05 để
    chọn ngay tại đây, không phải quay lại trang gợi ý. Vào từ nút "So sánh"
    thì `ss` đã có sẵn -> hiện luôn bảng so sánh.

    Cùng thang đo với UC-05: có mô hình thì phân tầng theo xác suất, không thì
    theo `margin` — hai trang không được nói hai chuyện khác nhau (SRS UC-07).
    """
    hs = _chi_cua_user(request.user, pk)
    to_hop_diem = {t["ma"]: t["tong"] for t in tinh_to_hop_tu_db(hs.diem_theo_mon())}
    uu_tien = float(hs.diem_uu_tien or 0)
    nam_that = list(CuaSoNam.objects.values_list("nam", flat=True))

    dong_dac_trung = _doc_danh_sach_so_sanh(request)
    row_theo_dt = _chi_tiet_dong(dong_dac_trung, to_hop_diem, uu_tien, nam_that)
    ds = list(row_theo_dt.values())
    da_chon = set(row_theo_dt)

    # Danh sách ứng viên để chọn NGAY TẠI ĐÂY (chính là gợi ý UC-05) — vào từ
    # header không có `ss` vẫn dùng được, không phải quay lại trang gợi ý.
    ung_vien = []
    if len(ds) < MAX_SO_SANH:
        _r = _goi_y_uc05(hs, to_hop_diem)[2]
        ung_vien = [r for r in _r if r["khoa"] not in da_chon][:SO_UNG_VIEN_CHON]

    return render(request, "recommendation/so_sanh.html", {
        "nav_active": "so_sanh", "ho_so": hs, "ds": ds, "ung_vien": ung_vien,
        # JSON để nhúng thẳng vào JS — `|safe` trong template, không phải list
        # Python (quote đơn vỡ cú pháp JS khi mã có dấu nháy).
        "da_chon": _json.dumps(sorted(da_chon), ensure_ascii=False),
        "to_hop": sorted(to_hop_diem.items(), key=lambda x: -x[1]),
        "toi_da": MAX_SO_SANH, "dung_ai": bool(any(r["xac_suat"] is not None for r in ds)),
    })


def _khoa_ss(kq):
    """Khóa định danh 1 ứng viên trên URL — khớp `_doc_danh_sach_so_sanh`."""
    return f"{kq.ma_truong_id}|{kq.nganh_id}|{kq.ma_to_hop_id}|{kq.phuong_thuc}"


def _chi_tiet_dong(dong_dac_trung, to_hop_diem, uu_tien, nam_that):
    """Ứng viên -> dict hiển thị bảng so sánh. Khóa dict là `_khoa_ss`."""
    co_diem = [(dt, round(to_hop_diem[dt.ma_to_hop_id] + uu_tien, 2))
               for dt in dong_dac_trung if dt.ma_to_hop_id in to_hop_diem]
    kq_p = cham_xac_suat(co_diem) if co_diem and nap_mo_hinh() is not None else None
    # Tròn 4 chữ số như `_thanh_dong` — cùng ngưỡng thì cùng tầng ở cả hai trang.
    p_theo_key = ({dt.pk: round(float(v), 4) for (dt, _), v in zip(co_diem, kq_p)}
                  if kq_p is not None else {})

    ra = {}
    for dt in dong_dac_trung:
        tong = to_hop_diem.get(dt.ma_to_hop_id)
        # Ứng viên thuộc tổ hợp học sinh không đủ môn -> vẫn hiện, ghi "thiếu môn".
        diem_hs = round(tong + uu_tien, 2) if tong is not None else None
        margin = (round(diem_hs - float(dt.diem_moi_nhat), 2)
                  if diem_hs is not None else None)
        p = p_theo_key.get(dt.pk)
        if margin is None:
            tang = None
        elif p is not None:
            tang = phan_tang_theo_xac_suat(p)
        else:
            tang = phan_tang(margin)
        ra[_khoa_ss(dt)] = {
            "kq": dt,
            "khoa": _khoa_ss(dt),
            "diem_hoc_sinh": diem_hs,
            "du_mon": tong is not None,
            "margin": margin,
            "xac_suat": None if p is None else round(p * 100, 1),
            "tang": tang or "—",
            "style": style_tang(tang) if tang else None,
            "theo_nam": [{"nam": n, "diem": d}
                         for n, d in zip(nam_that, dt.chuoi_diem())],
        }
    return ra
