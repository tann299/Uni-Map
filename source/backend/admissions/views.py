# -*- coding: utf-8 -*-
"""
View app `admissions` — hồ sơ năng lực (SRS UC-04) + gợi ý nguyện vọng (UC-05/06/08).

Yêu cầu đăng nhập. Một học sinh có thể có nhiều hồ sơ nên danh sách liệt kê tất cả
hồ sơ của user, tạo mới / sửa / xóa từng cái. Điểm từng môn lưu trong `diem_mon`
(khóa chính (ho_so_id, ma_mon)) — formset; nhóm ngành quan tâm (US-09) trong
`nhom_nganh_quan_tam` — formset thứ hai.

Phần gợi ý chạy ở CHẾ ĐỘ DỰ PHÒNG (SRS UC-05/5b): chưa có mô hình huấn luyện nên
xếp hạng bằng `margin` thuần. Kết quả vẫn lưu vào `lan_goi_y` / `ket_qua_goi_y` với
`dung_ai=False` để sau này thay bằng mô hình thật mà không đổi lược đồ.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django import forms
from django.forms import inlineformset_factory, ModelForm
from django.shortcuts import get_object_or_404, redirect, render

from tracuu.models import (VUNG_MIEN, CuaSoNam, DacTrungDiemChuan, DiemMon,
                           HoSoNangLuc, KetQuaGoiY, LanGoiY, Mon, Nganh,
                           NhomNganhQuanTam)
from admissions.services import (chon_can_ban, giai_thich, phan_tang,
                                 style_tang, tinh_to_hop_tu_db)

# UC-05 bước 7: hiển thị tối đa 30 gợi ý.
MAX_GOI_Y = 30
# UC-05/5c: dưới ngưỡng này thì nới điều kiện lọc và báo cho học sinh.
NGUONG_IT = 5


class HoSoForm(ModelForm):
    # US-10: khu vực muốn học — chọn từ danh sách chuẩn thay vì gõ tay.
    vung_mien_uu_tien = forms.ChoiceField(
        required=False, label="Khu vực muốn học",
        choices=[("", "— Không giới hạn —"), *VUNG_MIEN],
        widget=forms.Select(attrs={"class": "w-full px-3 py-2 rounded-lg border "
                                          "border-outline-variant bg-surface-container-lowest"}))

    class Meta:
        model = HoSoNangLuc
        fields = ["ten_ho_so", "phuong_thuc", "diem_uu_tien", "vung_mien_uu_tien"]


class DiemMonForm(ModelForm):
    class Meta:
        model = DiemMon
        fields = ["ma_mon", "diem"]
        labels = {"ma_mon": "Môn", "diem": "Điểm"}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fields["ma_mon"].queryset = Mon.objects.filter(la_nang_khieu=False)
        self.fields["ma_mon"].label_from_instance = lambda m: f"{m.ma_mon} — {m.ten_mon}"


class NhomNganhForm(ModelForm):
    """US-09 — nhóm ngành quan tâm, dùng để lọc cứng ở UC-05 bước 3."""

    class Meta:
        model = NhomNganhQuanTam
        fields = ["nhom_nganh"]
        labels = {"nhom_nganh": "Nhóm ngành"}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        # Lấy từ dữ liệu thật (15 nhóm), không hardcode theo mockup.
        nhom = (Nganh.objects.values_list("nhom_nganh", flat=True)
                .distinct().order_by("nhom_nganh"))
        self.fields["nhom_nganh"].widget.choices = [("", "— Không chọn —")] + [
            (n, n) for n in nhom]


DiemMonFormSet = inlineformset_factory(
    HoSoNangLuc, DiemMon, form=DiemMonForm,
    fields=["ma_mon", "diem"], extra=6, can_delete=True,
)
NhomNganhFormSet = inlineformset_factory(
    HoSoNangLuc, NhomNganhQuanTam, form=NhomNganhForm,
    fields=["nhom_nganh"], extra=3, can_delete=True,
)


def _chi_cua_user(user, pk):
    return get_object_or_404(HoSoNangLuc, pk=pk, user=user)


def _luu_ho_so(request, hs=None):
    """Tạo/sửa hồ sơ + điểm môn + nhóm ngành trong 1 transaction."""
    la_sua = hs is not None
    if request.method == "POST":
        form = HoSoForm(request.POST, instance=hs)
        fs_diem = DiemMonFormSet(request.POST, instance=hs)
        fs_nhom = NhomNganhFormSet(request.POST, instance=hs)
        if form.is_valid() and fs_diem.is_valid() and fs_nhom.is_valid():
            with transaction.atomic():
                obj = form.save(commit=False)
                if not la_sua:
                    obj.user = request.user
                obj.save()
                for fs in (fs_diem, fs_nhom):
                    fs.instance = obj
                    fs.save()
            messages.success(request, "Đã lưu hồ sơ năng lực.")
            return redirect("admissions:chi_tiet_ho_so", pk=obj.pk)
    else:
        form = HoSoForm(instance=hs)
        fs_diem = DiemMonFormSet(instance=hs)
        fs_nhom = NhomNganhFormSet(instance=hs)
    return render(request, "admissions/ho_so_form.html", {
        "nav_active": "ho_so", "form": form, "formset": fs_diem, "formset_nhom": fs_nhom,
        "tieu_de": (f"Chỉnh sửa hồ sơ: {hs.ten_ho_so}" if la_sua
                    else "Tạo hồ sơ năng lực mới"),
        "la_sua": la_sua, "ho_so": hs,
    })


@login_required
def danh_sach_ho_so(request):
    hs = HoSoNangLuc.objects.filter(user=request.user)
    return render(request, "admissions/ho_so_list.html", {
        "nav_active": "ho_so", "danh_sach": hs,
    })


@login_required
def tao_ho_so(request):
    return _luu_ho_so(request)


@login_required
def sua_ho_so(request, pk):
    return _luu_ho_so(request, _chi_cua_user(request.user, pk))


@login_required
def xoa_ho_so(request, pk):
    hs = _chi_cua_user(request.user, pk)
    if request.method == "POST":
        hs.delete()
        messages.success(request, "Đã xóa hồ sơ.")
        return redirect("admissions:danh_sach_ho_so")
    return render(request, "admissions/ho_so_xoa.html", {
        "nav_active": "ho_so", "ho_so": hs,
    })


@login_required
def chi_tiet_ho_so(request, pk):
    hs = _chi_cua_user(request.user, pk)
    diem_mon = hs.diem_theo_mon()
    to_hop = tinh_to_hop_tu_db(diem_mon)
    nhom = list(hs.nhomnganhquantam_set.values_list("nhom_nganh", flat=True))
    return render(request, "admissions/ho_so_detail.html", {
        "nav_active": "ho_so", "ho_so": hs, "diem_mon": diem_mon,
        "to_hop": to_hop, "nhom_nganh": nhom,
        "so_lan_goi_y": hs.langoiy_set.count(),
    })


# ===========================================================================
# UC-05 — Nhận gợi ý trường/ngành
# ===========================================================================

def _loc_cung(hs, to_hop_diem, *, dung_nhom=True, dung_vung=True):
    """UC-05 bước 3 — lọc cứng bằng SQL (có index), không quét toàn bảng.

    Loại: tổ hợp học sinh không đủ môn (đã lo ở CN-01), không thuộc nhóm ngành /
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
        margin = round(diem_hs - float(r.diem_moi_nhat), 2)
        tang = phan_tang(margin)
        theo_tang[tang].append({
            "kq": r,                      # DacTrungDiemChuan — chuỗi 5 năm + đặc trưng
            "diem_hoc_sinh": diem_hs,
            "margin": margin,
            "tang": tang,
            "style": style_tang(tang),
        })
    for rows in theo_tang.values():
        rows.sort(key=lambda x: (-x["margin"], x["kq"].ma_truong_id, x["kq"].nganh_id))

    # Thứ tự HIỂN THỊ là gợi ý tham khảo — học sinh vẫn tự xếp nguyện vọng (CN-03).
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
    # bulk_create không trả pk trên MySQL -> đọc lại theo thu_hang để lấy pk link chi tiết.
    pk_theo_hang = dict(KetQuaGoiY.objects.filter(lan_goi_y=lan)
                        .values_list("thu_hang", "pk"))
    for i, r in enumerate(rows):
        r["kq_id"] = pk_theo_hang.get(i + 1)

    return render(request, "admissions/goi_y_ket_qua.html", {
        "nav_active": "goi_y", "ho_so": hs, "lan": lan, "ds": rows,
        "to_hop": to_hop, "da_noi": da_noi, "nguong_it": NGUONG_IT,
        "dung_ai": False,
    })


@login_required
def lich_su_goi_y(request, pk):
    hs = _chi_cua_user(request.user, pk)
    ds = (LanGoiY.objects.filter(ho_so=hs)
          .prefetch_related("ketquagoiy_set__ma_truong", "ketquagoiy_set__nganh"))
    return render(request, "admissions/lich_su_goi_y.html", {
        "nav_active": "goi_y", "ho_so": hs, "danh_sach": ds,
    })


@login_required
def xoa_lich_su(request, pk):
    """Xóa toàn bộ lần gợi ý của hồ sơ (CASCADE xóa ket_qua_goi_y)."""
    hs = _chi_cua_user(request.user, pk)
    if request.method == "POST":
        LanGoiY.objects.filter(ho_so=hs).delete()
        messages.success(request, "Đã xóa toàn bộ lịch sử gợi ý.")
    return redirect("admissions:lich_su_goi_y", pk=hs.pk)


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
    return render(request, "admissions/goi_y_chi_tiet.html", {
        "nav_active": "goi_y", "kq": kq, "ho_so": kq.lan_goi_y.ho_so,
        "dt": dt, "bieu_do": bieu_do, "giai_thich": cau,
        "style": style_tang(kq.tang), "dung_ai": kq.lan_goi_y.dung_ai,
    })