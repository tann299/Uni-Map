# -*- coding: utf-8 -*-
"""
App `recommendation` — kết quả mỗi lần chạy engine gi ý (SRS UC-05, UC-06, UC-08).

`lan_goi_y` giữ 1 dòng cho mỗi lần bấm "Xem gợi ý"; `ket_qua_goi_y` giữ từng
nguyện vọng trong lần đó. Con số trong `ket_qua_goi_y` là ẢNH CHỤP lúc gợi ý —
không tính lại khi xem lịch sử, vì điểm chuẩn trong DB có thể đã cập nhật.

`managed = False`: `db/schema.sql` là nguồn sự thật, Django không tạo/sửa bảng.
"""

from django.db import models

from university.models import Nganh, ToHop, Truong

PHUONG_THUC = [
    ("Điểm thi THPT", "Điểm thi THPT"),
    ("Điểm học bạ", "Điểm học bạ"),
]
TANG = [
    ("An toàn", "An toàn"),
    ("Vừa sức", "Vừa sức"),
    ("Thử sức", "Thử sức"),
]


class LanGoiY(models.Model):
    """Mỗi lần chạy engine gợi ý. Lưu phiên bản mô hình để truy vết."""

    ho_so = models.ForeignKey("admissions.HoSoNangLuc", models.CASCADE,
                              db_column="ho_so_id")
    thoi_diem = models.DateTimeField(auto_now_add=True)
    phien_ban_mo_hinh = models.CharField(max_length=50, blank=True, default="")
    dung_ai = models.BooleanField(default=True)
    so_ket_qua = models.PositiveSmallIntegerField(default=0)

    class Meta:
        managed = False
        db_table = "lan_goi_y"
        ordering = ["-thoi_diem"]

    def __str__(self):
        return f"Gợi ý #{self.pk} ({self.thoi_diem:%d/%m/%Y %H:%M})"


class KetQuaGoiY(models.Model):
    """Snapshot lúc gợi  — KHÔNG tính lại khi xem lịch sử."""

    lan_goi_y = models.ForeignKey(LanGoiY, models.CASCADE, db_column="lan_goi_y_id")
    ma_truong = models.ForeignKey(Truong, models.DO_NOTHING, db_column="ma_truong")
    nganh = models.ForeignKey(Nganh, models.DO_NOTHING, db_column="nganh_id")
    ma_to_hop = models.ForeignKey(ToHop, models.DO_NOTHING, db_column="ma_to_hop")
    phuong_thuc = models.CharField(max_length=13, choices=PHUONG_THUC)

    diem_hoc_sinh = models.DecimalField(max_digits=4, decimal_places=2)
    margin = models.DecimalField(max_digits=5, decimal_places=2)
    xac_suat_do = models.DecimalField(max_digits=5, decimal_places=4)
    tang = models.CharField(max_length=7, choices=TANG)
    thu_hang = models.PositiveSmallIntegerField()
    da_luu = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "ket_qua_goi_y"
        unique_together = (("lan_goi_y", "ma_truong", "nganh",
                            "ma_to_hop", "phuong_thuc"),)
        ordering = ["thu_hang"]