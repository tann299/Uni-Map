# -*- coding: utf-8 -*-
"""
View app `admissions` — hồ sơ năng lực học sinh (SRS UC-04).

Yêu cầu đăng nhập. Một học sinh có thể có nhiều hồ sơ nên danh sách liệt kê tất
cả hồ sơ của user; tạo mới / sửa / xóa / xem từng cái.

  * Điểm từng môn -> `diem_mon`, formset (US-07). CN-01 tự suy ra mọi tổ hợp đủ
    môn — hàm nằm ở `university.services` vì đó là dữ liệu tham chiếu tổ hợp.
  * Nhóm ngành quan tâm -> `nhom_nganh_quan_tam`, formset (US-09).
  * Khu vực muốn học -> `vung_mien_uu_tien` (US-10).

Phần gợi ý nguyện vọng (UC-05/06/07/08) nằm ở app `recommendation`.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import inlineformset_factory, ModelForm
from django.shortcuts import get_object_or_404, redirect, render

from university.models import VUNG_MIEN, Mon, Nganh
from university.services import tinh_to_hop_tu_db

from .models import DiemMon, HoSoNangLuc, NhomNganhQuanTam


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
    """UC-04 — xem hồ sơ + CN-01 tự tính mọi t hợp học sinh đủ môn."""
    hs = _chi_cua_user(request.user, pk)
    diem_mon = hs.diem_theo_mon()
    to_hop = tinh_to_hop_tu_db(diem_mon)
    nhom = list(hs.nhomnganhquantam_set.values_list("nhom_nganh", flat=True))
    return render(request, "admissions/ho_so_detail.html", {
        "nav_active": "ho_so", "ho_so": hs, "diem_mon": diem_mon,
        "to_hop": to_hop, "nhom_nganh": nhom,
        "so_lan_goi_y": hs.langoiy_set.count(),
    })