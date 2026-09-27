# -*- coding: utf-8 -*-
"""
Quản trị hồ sơ năng lực học sinh (SRS UC-04). Dữ liệu người dùng — admin xem để
hỗ trợ, không tạo hộ. Điểm môn + nhóm ngành quan tâm nhúng inline.
"""
from django.contrib import admin

from .models import DiemMon, HoSoNangLuc, NhomNganhQuanTam


class DiemMonInline(admin.TabularInline):
    model = DiemMon
    extra = 0
    fields = ("ma_mon", "diem")


class NhomNganhQuanTamInline(admin.TabularInline):
    model = NhomNganhQuanTam
    extra = 0
    fields = ("nhom_nganh",)


@admin.register(HoSoNangLuc)
class HoSoNangLucAdmin(admin.ModelAdmin):
    list_display = ("ten_ho_so", "user", "phuong_thuc", "diem_uu_tien",
                    "vung_mien_uu_tien", "ngay_tao", "ngay_sua")
    list_filter = ("phuong_thuc", "vung_mien_uu_tien", "ngay_tao")
    search_fields = ("ten_ho_so", "user__username")
    date_hierarchy = "ngay_tao"
    readonly_fields = ("ngay_tao", "ngay_sua")
    inlines = [DiemMonInline, NhomNganhQuanTamInline]
