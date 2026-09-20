# -*- coding: utf-8 -*-
"""
App `admissions` — hồ sơ năng lực học sinh (SRS UC-04, US-06..US-11).

Ba bảng `ho_so_nang_luc`, `diem_mon`, `nhom_nganh_quan_tam` là DỮ LIỆU NGƯỜI
DÙNG do Django ghi (khác phần còn lại của lược đồ: chỉ crawler ghi).

`managed = False` vì `db/schema.sql` là nguồn sự thật của lược đồ — bảng đã tạo
kèm CHECK constraint và FK RESTRICT mà migrate của Django sẽ làm mất.
"""

from django.conf import settings
from django.db import models

from university.models import Mon

PHUONG_THUC = [
    ("Điểm thi THPT", "Điểm thi THPT"),
    ("Điểm học bạ", "Điểm học bạ"),
]


class HoSoNangLuc(models.Model):
    """Một học sinh có thể có nhiều hồ sơ (thi thử nhiều lần) -> không UNIQUE user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE,
                             db_column="user_id")
    ten_ho_so = models.CharField(max_length=100, default="Hồ sơ của tôi")
    phuong_thuc = models.CharField(max_length=13, choices=PHUONG_THUC,
                                   default="Điểm thi THPT")
    diem_uu_tien = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    vung_mien_uu_tien = models.CharField(max_length=60, blank=True, default="")
    ngay_tao = models.DateTimeField(auto_now_add=True)
    ngay_sua = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "ho_so_nang_luc"
        ordering = ["-ngay_sua"]

    def __str__(self):
        return f"{self.ten_ho_so} ({self.user_id})"

    def diem_theo_mon(self) -> dict[str, float]:
        """{'TOAN': 8.5, ...} — đầu vào cho CN-01."""
        return {d.ma_mon_id: float(d.diem) for d in self.diemmon_set.all()}


class DiemMon(models.Model):
    pk = models.CompositePrimaryKey("ho_so_id", "ma_mon")
    ho_so = models.ForeignKey(HoSoNangLuc, models.CASCADE, db_column="ho_so_id")
    ma_mon = models.ForeignKey(Mon, models.DO_NOTHING, db_column="ma_mon")
    diem = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        managed = False
        db_table = "diem_mon"


class NhomNganhQuanTam(models.Model):
    pk = models.CompositePrimaryKey("ho_so_id", "nhom_nganh")
    ho_so = models.ForeignKey(HoSoNangLuc, models.CASCADE, db_column="ho_so_id")
    nhom_nganh = models.CharField(max_length=40)

    class Meta:
        managed = False
        db_table = "nhom_nganh_quan_tam"