# -*- coding: utf-8 -*-
"""
Quản trị dữ liệu tham chiếu trường/ngành/tổ hợp/điểm chuẩn (SRS mục 8).

Dữ liệu do crawler + import_mysql.py ghi, Django chỉ đọc để đối soát nên vô hiệu
hóa thêm/sửa trực tiếp (xóa vẫn mở cho admin dọn rác). Tất cả model managed=False.
"""
from django.contrib import admin

from .models import (CuaSoNam, DacTrungDiemChuan, DiemChuan, LanCapNhat, Mon,
                     Nganh, ToHop, Truong)


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """Chặn thêm/sửa trên admin — dữ liệu nguồn nằm ngoài Django."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Truong)
class TruongAdmin(ReadOnlyModelAdmin):
    list_display = ("ma_truong", "ten_truong", "viet_tat", "tinh_thanh", "vung_mien")
    search_fields = ("ma_truong", "ten_truong", "viet_tat", "tinh_thanh")
    list_filter = ("vung_mien", "tinh_thanh")


@admin.register(Nganh)
class NganhAdmin(ReadOnlyModelAdmin):
    list_display = ("nganh_id", "nganh_slug", "ten_nganh", "nhom_nganh")
    search_fields = ("ten_nganh", "nganh_slug")
    list_filter = ("nhom_nganh",)


@admin.register(Mon)
class MonAdmin(ReadOnlyModelAdmin):
    list_display = ("ma_mon", "ten_mon", "la_nang_khieu", "thu_tu")
    search_fields = ("ma_mon", "ten_mon")
    list_filter = ("la_nang_khieu",)


@admin.register(ToHop)
class ToHopAdmin(ReadOnlyModelAdmin):
    list_display = ("ma_to_hop", "ten_to_hop", "cac_mon", "so_mon", "nguon")
    search_fields = ("ma_to_hop", "ten_to_hop", "cac_mon")


# ToHopMon dùng CompositePrimaryKey — Django admin không hỗ trợ model không có
# pk đơn nên không đăng ký; xem quan hệ tổ hợp-môn qua bảng ToHop.


@admin.register(DiemChuan)
class DiemChuanAdmin(ReadOnlyModelAdmin):
    list_display = ("ma_truong", "nganh", "ma_to_hop", "phuong_thuc", "nam", "diem_chuan")
    search_fields = ("ma_truong__ten_truong", "nganh__ten_nganh", "ma_to_hop__ma_to_hop")
    list_filter = ("nam", "phuong_thuc", "ma_truong__vung_mien")


@admin.register(DacTrungDiemChuan)
class DacTrungDiemChuanAdmin(ReadOnlyModelAdmin):
    """Bảng đặc trưng đầu vào cho mô hình AI (UC-10) — theo dõi chất lượng."""
    list_display = ("ma_truong", "nganh", "ma_to_hop", "phuong_thuc",
                    "diem_moi_nhat", "xu_huong", "bien_dong", "so_nam_co_dl")
    search_fields = ("ma_truong__ten_truong", "nganh__ten_nganh", "ma_to_hop__ma_to_hop")
    list_filter = ("phuong_thuc", "so_nam_co_dl")


@admin.register(CuaSoNam)
class CuaSoNamAdmin(ReadOnlyModelAdmin):
    list_display = ("vi_tri", "nam")


@admin.register(LanCapNhat)
class LanCapNhatAdmin(ReadOnlyModelAdmin):
    list_display = ("thoi_diem", "nguon", "nam_bat_dau", "nam_ket_thuc",
                    "so_truong", "so_nganh", "so_dong_diem", "selfcheck_dat")
    list_filter = ("selfcheck_dat", "nguon")
