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

    # `nhom_nganh` của model là CharField nên Django render <input type="text">.
    # Gán `widget.choices` KHÔNG đổi được kiểu widget — phải khai báo hẳn
    # ChoiceField thì mới ra <select>. Đây là lý do form trước đây hiện ô gõ tay
    # thay vì danh sách chọn.
    nhom_nganh = forms.ChoiceField(
        required=False, label="Nhóm ngành",
        widget=forms.Select(attrs={"class": "w-full px-3 py-2 rounded-lg border "
                                          "border-outline-variant bg-surface-container-lowest"}),
    )

    class Meta:
        model = NhomNganhQuanTam
        fields = ["nhom_nganh"]

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        # Lấy từ dữ liệu thật (15 nhóm), không hardcode theo mockup.
        nhom = (Nganh.objects.values_list("nhom_nganh", flat=True)
                .distinct().order_by("nhom_nganh"))
        self.fields["nhom_nganh"].choices = [("", "— Không chọn —")] + [
            (n, n) for n in nhom]


# `DiemMon`/`NhomNganhQuanTam` dùng CompositePrimaryKey. Django render hidden `pk`
# thành tuple Python `(19, 'TOAN')` trong khi `CompositePrimaryKey.to_python`
# chỉ đọc được JSON -> mọi lần bấm Lưu ở trang SỬA đều nổ JSONDecodeError (500).
# Vá điểm render về đúng dạng JSON `["19", "TOAN"]` để bound form hoạt động.
import json as _json

from django.forms.widgets import HiddenInput as _HiddenInput


class _PkJson(_HiddenInput):
    def format_value(self, value):
        if isinstance(value, (tuple, list)):
            return _json.dumps([str(v) for v in value], ensure_ascii=False)
        return super().format_value(value)

    def value_from_datadict(self, data, files, name):
        # Ô ẩn của form rỗng (extra) gửi lên "[\"None\", \"None\"]" — coi như
        # không có khóa, nếu không formset tưởng đây là bản ghi cũ.
        raw = data.get(name)
        if raw and "None" in raw:
            return ""
        return raw


class _KhongCoPk:
    """Vá ô khóa composite của formset con (Django 5.2 + CompositePrimaryKey).

    Hai lỗi liên tiếp khi formset con có `CompositePrimaryKey`:
      1. Django render ô ẩn `pk` dạng tuple Python `(19, 'TOAN')` trong khi
         `CompositePrimaryKey.to_python` chỉ đọc JSON -> trang SỬA nổ
         `JSONDecodeError` (500).
      2. Sau khi đổi sang JSON, `_existing_object` lại tra `_object_dict` bằng
         `list` -> `TypeError: unhashable type: 'list'`. Khóa của `_object_dict`
         là tuple.

    Xử lý cả hai: ghi ra JSON (đúng thứ `to_python` đọc) và khi đọc vào thì
    chuyển list -> tuple trước lúc tra cứu.

    Lỗi thứ ba: `pk` là `ModelChoiceField` với choices sinh từ `to_python`, nên
    giá trị JSON không khớp choices -> "Hãy chọn một lựa chọn hợp lệ" và cả
    formset invalid. Thay field `pk` bằng `CharField` (không validate gì) —
    `_construct_form` đã tự gán `instance` đúng theo pk rồi.
    """

    def add_fields(self, form, index):
        super().add_fields(form, index)
        for ten in list(form.fields):
            if ten == "pk" or ten.endswith("-pk"):
                form.fields[ten] = forms.CharField(required=False, widget=_PkJson())
        # Django không đưa pk composite vào `initial` -> ô ẩn rỗng, lần lưu sau
        # mất luôn khóa. Tự nạp từ instance (form extra có pk None -> bỏ qua).
        try:
            khoa = form.instance.pk
        except (AttributeError, ValueError):
            khoa = None
        if khoa and not any(v is None for v in khoa):
            form.initial["pk"] = khoa

    def _construct_form(self, i, **kwargs):
        # Trước khi cha tra `_object_dict`: đổi value JSON thành tuple.
        if self.is_bound and i < self.initial_form_count():
            key = "%s-%s" % (self.add_prefix(i), self.model._meta.pk.name)
            raw = self.data.get(key)
            if raw:
                data = self.data.copy()
                try:
                    data[key] = tuple(_json.loads(raw))
                except (ValueError, TypeError):
                    pass
                self.data = data
        form = super()._construct_form(i, **kwargs)
        # Cha ép `pk` required=True cho form cũ; giá trị đã JSON hoá nên không
        # cần validate lại — để required sẽ chặn cả form thêm mới.
        if "pk" in form.fields:
            form.fields["pk"].required = False
        return form

    def _existing_object(self, pk):
        # `_object_dict` khoá bằng tuple; Django truyền vào list -> unhashable.
        if isinstance(pk, list):
            pk = tuple(pk)
        return super()._existing_object(pk)


class DiemMonFormSet(_KhongCoPk, inlineformset_factory(
        HoSoNangLuc, DiemMon, form=DiemMonForm,
        fields=["ma_mon", "diem"], extra=6, can_delete=True)):
    pass


class NhomNganhFormSet(_KhongCoPk, inlineformset_factory(
        HoSoNangLuc, NhomNganhQuanTam, form=NhomNganhForm,
        fields=["nhom_nganh"], extra=3, can_delete=True)):
    pass


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