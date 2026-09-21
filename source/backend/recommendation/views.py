# -*- coding: utf-8 -*-
"""
View app `recommendation` — engine gợi ý nguyện vọng (SRS UC-05, UC-06, UC-07, UC-08).

Luồng chính (UC-05):
  1. Đọc hồ sơ năng lực (UC-04, app `admissions`) -> CN-01 tính mọi tổ hợp đủ môn
  2. Lọc cứng bằng SQL (index có sẵn, không quét toàn bảng) — PC-01 < 3s
  3. Tính `margin = điểm tổ hợp (+ ưu tiên) − diem_moi_nhat`
  4. Chấm xác suất đỗ — HIỆN Ở CHẾ ĐỘ DỰ PHÒNG (UC-05/5b): chưa có mô hình
     huấn luyện nên xếp hạng bằng `margin` thuần, ghi `dung_ai=False`
  5. Phân tầng An toàn / Vừa sức / Thử sức (CN-03)
  6. Sinh lời giải thích từ đặc trưng thật (CN-04)
  7. Lưu snapshot vào `lan_goi_y` + `ket_qua_goi_y` (UC-08)

Khi UC-10 (huấn luyện RandomForest) xong, chỉ cần thay bước 4 — lược đồ và
snapshot giữ nguyên.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from urllib.parse import quote

from admissions.models import HoSoNangLuc
from university.services import tinh_to_hop_tu_db
from university.models import VUNG_MIEN, CuaSoNam, DacTrungDiemChuan

from .models import KetQuaGoiY, LanGoiY
from .services import chon_can_ban, giai_thich, phan_tang, style_tang

# UC-05 bước 7: hiển thị tối đa 30 gi ý.
MAX_GOI_Y = 30
# UC-05/5c: dưới ngưỡng này thì nới điều kiện lọc và báo cho học sinh.
NGUONG_IT = 5
# UC-07: so sánh tối đa 3 nguyện vọng cạnh nhau (mockup cũng ghi "thứ 3").
MAX_SO_SANH = 3


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


def _thanh_dong(r, diem_hs, uu_tien_ap_dung):
    """1 ứng viên -> dict hiển thị (giữ `kq` là dòng đặc trưng để lấy chuỗi 5 năm)."""
    margin = round(diem_hs - float(r.diem_moi_nhat), 2)
    tang = phan_tang(margin)
    return {
        "kq": r,
        "diem_hoc_sinh": diem_hs,
        "margin": margin,
        "tang": tang,
        "style": style_tang(tang),
        "uu_tien_ap_dung": uu_tien_ap_dung,
    }


def _xep_hang(hs, to_hop_diem, qs):
    """Bước 4–6: margin -> phân tầng -> chọn danh sách CÂN BẰNG rủi ro.

    CN-03 yêu cầu mỗi tầng đều có gợi ý (nếu dữ liệu cho phép) để học sinh xếp
    được thứ tự nguyện vọng. Nếu chỉ lấy top `MAX_GOI_Y` theo margin thì danh sách
    toàn tầng "An toàn" — mất hẳn nhóm "Thử sức". Nên chia quota đều cho 3 tầng,
    tầng nào thiếu thì nhường suất cho tầng khác.
    """
    uu_tien = float(hs.diem_uu_tien or 0)
    theo_tang = {"An toàn": [], "Vừa sức": [], "Thử sức": []}
    for r in qs:
        diem_hs = round(to_hop_diem[r.ma_to_hop_id] + uu_tien, 2)
        row = _thanh_dong(r, diem_hs, uu_tien)
        theo_tang[row["tang"]].append(row)
    for rows in theo_tang.values():
        rows.sort(key=lambda x: (-x["margin"], x["kq"].ma_truong_id, x["kq"].nganh_id))
    return chon_can_ban(theo_tang, MAX_GOI_Y)


@login_required
def xem_goi_y(request, pk):
    hs = _chi_cua_user(request.user, pk)
    to_hop = tinh_to_hop_tu_db(hs.diem_theo_mon())
    to_hop_diem = {t["ma"]: t["tong"] for t in to_hop}

    if not to_hop_diem:
        messages.warning(request, "Hồ sơ chưa có điểm môn nào — hãy nhập điểm trước.")
        return redirect("admissions:sua_ho_so", pk=hs.pk)

    # Nới điều kiện dần khi quá ít kết quả (UC-05/5a và 5c).
    qs = _loc_cung(hs, to_hop_diem)
    da_noi = None
    if qs.count() < NGUONG_IT and hs.vung_mien_uu_tien in dict(VUNG_MIEN):
        qs = _loc_cung(hs, to_hop_diem, dung_vung=False)
        da_noi = "khu vực"
    if qs.count() < NGUONG_IT and hs.nhomnganhquantam_set.exists():
        qs = _loc_cung(hs, to_hop_diem, dung_nhom=False, dung_vung=False)
        da_noi = "nhóm ngành và khu vực"

    rows = _xep_hang(hs, to_hop_diem, qs)

    with transaction.atomic():
        lan = LanGoiY.objects.create(
            ho_so=hs, phien_ban_mo_hinh="", dung_ai=False, so_ket_qua=len(rows))
        KetQuaGoiY.objects.bulk_create([
            KetQuaGoiY(
                lan_goi_y=lan, ma_truong_id=r["kq"].ma_truong_id,
                nganh_id=r["kq"].nganh_id, ma_to_hop_id=r["kq"].ma_to_hop_id,
                phuong_thuc=r["kq"].phuong_thuc, diem_hoc_sinh=r["diem_hoc_sinh"],
                margin=r["margin"], xac_suat_do=0,   # 0 = chưa dùng AI (dự phòng)
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
        "dung_ai": False,
    })


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
    """So sánh 2–3 nguyện vọng cạnh nhau: chuỗi 5 năm, margin, xu hướng."""
    hs = _chi_cua_user(request.user, pk)
    to_hop_diem = {t["ma"]: t["tong"] for t in tinh_to_hop_tu_db(hs.diem_theo_mon())}
    uu_tien = float(hs.diem_uu_tien or 0)
    nam_that = list(CuaSoNam.objects.values_list("nam", flat=True))

    ds = []
    for dt in _doc_danh_sach_so_sanh(request):
        tong = to_hop_diem.get(dt.ma_to_hop_id)
        # Ứng viên thuộc tổ hợp học sinh không đủ môn -> vẫn hiện, ghi rõ "thiếu môn".
        diem_hs = round(tong + uu_tien, 2) if tong is not None else None
        margin = (round(diem_hs - float(dt.diem_moi_nhat), 2)
                  if diem_hs is not None else None)
        tang = phan_tang(margin) if margin is not None else None
        ds.append({
            "kq": dt,
            "diem_hoc_sinh": diem_hs,
            "du_mon": tong is not None,
            "margin": margin,
            "tang": tang or "—",
            "style": style_tang(tang) if tang else None,
            "theo_nam": [{"nam": n, "diem": d}
                         for n, d in zip(nam_that, dt.chuoi_diem())],
        })

    return render(request, "recommendation/so_sanh.html", {
        "nav_active": "so_sanh", "ho_so": hs, "ds": ds,
        "to_hop": sorted(to_hop_diem.items(), key=lambda x: -x[1]),
        "toi_da": MAX_SO_SANH,
    })