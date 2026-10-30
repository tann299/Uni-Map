# -*- coding: utf-8 -*-
"""
Quản trị tài khoản người dùng (tầng auth mặc định của Django).

User là model mặc định (không AUTH_USER_MODEL tuỳ biến) nên dùng
django.contrib.auth.models.User. Hiển thị kèm số hồ sơ đã tạo để admin nắm nhanh.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from accounts.gmail import chuan_hoa_email, truy_van_theo_email
from admissions.models import HoSoNangLuc


def _trung_email(email: str, bo_tru_pk=None) -> bool:
    """Email đã có user khác dùng chưa — dùng chung cho add/change form."""
    if not email:
        return False
    return truy_van_theo_email(email, exclude_pk=bo_tru_pk).exists()


class HoSoInline(admin.TabularInline):
    model = HoSoNangLuc
    extra = 0
    fields = ("ten_ho_so", "phuong_thuc", "vung_mien_uu_tien", "ngay_tao")
    readonly_fields = fields
    show_change_link = True
    ordering = ("-ngay_sua",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class UniMapUserCreationForm(AdminUserCreationForm):
    """Form thêm user trong admin: chuẩn hoá + chặn email trùng.

    Kế thừa AdminUserCreationForm (KHÔNG phải UserCreationForm) để giữ field
    `usable_password` mà add_fieldsets của Django 5.2 tham chiếu. `auth_user.email`
    là UNIQUE (uq_auth_user_email_chuan) — validate ở form để hiện lỗi thân thiện,
    không để IntegrityError nổ trang 500. Email vẫn để trống được (User.email blank):
    không hiện ô email mà chặn thì admin không tạo nổi tài khoản nào.
    """

    class Meta(AdminUserCreationForm.Meta):
        fields = ("username", "email")

    def clean_email(self):
        goc = (self.cleaned_data.get("email") or "").strip()
        email = chuan_hoa_email(goc)
        if email and _trung_email(goc):
            raise ValidationError("Email này đã được dùng bởi tài khoản khác.")
        return email


class UniMapUserChangeForm(UserChangeForm):
    """Form sửa user: chuẩn hoá + chặn email trùng người khác (bỏ qua chính mình).

    Email TRỐNG không được xoá email cũ của tài khoản OAuth: lần login sau
    sẽ không tìm thấy và tạo user mới, dữ liệu cũ bị bỏ rơi. Chỉ cho xoá khi
    email cũ cũng rỗng sẵn.
    """

    def clean_email(self):
        goc = (self.cleaned_data.get("email") or "").strip()
        email = chuan_hoa_email(goc)
        if not email and self.instance.email:
            return self.instance.email
        if email and _trung_email(goc, bo_tru_pk=self.instance.pk):
            raise ValidationError("Email này đã được dùng bởi tài khoản khác.")
        return email


class UniMapUserAdmin(UserAdmin):
    add_form = UniMapUserCreationForm
    form = UniMapUserChangeForm
    # add_fieldsets gốc của Django 5.2 không có email — thêm vào để hiện ô email
    # khi tạo tài khoản (nếu bỏ trống cũng được, chỉ chặn khi có mà trùng).
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "usable_password",
                           "password1", "password2"),
            },
        ),
    )
    list_display = ("username", "email", "first_name", "last_name",
                    "is_staff", "is_active", "date_joined")
    inlines = [HoSoInline]


admin.site.unregister(User)
admin.site.register(User, UniMapUserAdmin)
