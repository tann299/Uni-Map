# -*- coding: utf-8 -*-
"""
Quản trị lịch sử gợi ý (SRS UC-05, UC-06, UC-08) — giám sát engine AI.

Snapshot chỉ đọc: admin xem lại lần gợi ý, phiên bản mô hình, tầng và xác suất
đỗ để đối soát chất lượng; không sửa (con số là ảnh chụp lúc gợi ý).
"""
from django.contrib import admin

from .models import KetQuaGoiY, LanGoiY


class KetQuaGoiYInline(admin.TabularInline):
    model = KetQuaGoiY
    extra = 0
    can_delete = False
    fields = ("thu_hang", "ma_truong", "nganh", "ma_to_hop", "phuong_thuc",
              "diem_hoc_sinh", "margin", "xac_suat_do", "tang")
    readonly_fields = fields
    ordering = ("thu_hang",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LanGoiY)
class LanGoiYAdmin(admin.ModelAdmin):
    list_display = ("id", "ho_so", "thoi_diem", "dung_ai",
                    "phien_ban_mo_hinh", "so_ket_qua")
    list_filter = ("dung_ai", "phien_ban_mo_hinh", "thoi_diem")
    search_fields = ("ho_so__ten_ho_so", "ho_so__user__username")
    date_hierarchy = "thoi_diem"
    inlines = [KetQuaGoiYInline]
    readonly_fields = ("thoi_diem", "so_ket_qua")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(KetQuaGoiY)
class KetQuaGoiYAdmin(admin.ModelAdmin):
    list_display = ("lan_goi_y", "thu_hang", "ma_truong", "nganh", "tang",
                    "diem_hoc_sinh", "margin", "xac_suat_do", "phuong_thuc")
    list_filter = ("tang", "phuong_thuc")
    search_fields = ("ma_truong__ten_truong", "nganh__ten_nganh")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
