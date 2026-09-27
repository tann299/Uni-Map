# -*- coding: utf-8 -*-
"""
Quản trị tài khoản người dùng (tầng auth mặc định của Django).

User là model mặc định (không AUTH_USER_MODEL tuỳ biến) nên dùng
django.contrib.auth.models.User. Hiển thị kèm số hồ sơ đã tạo để admin nắm nhanh.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from admissions.models import HoSoNangLuc


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


class UniMapUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name",
                    "is_staff", "is_active", "date_joined")
    inlines = [HoSoInline]


admin.site.unregister(User)
admin.site.register(User, UniMapUserAdmin)
