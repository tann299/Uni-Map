# -*- coding: utf-8 -*-
"""
App `university` — dữ liệu tham chiếu + sự kiện điểm chuẩn (SRS mục 8).

Sinh từ `manage.py inspectdb` rồi dọn tay. QUY ƯỚC: `db/schema.sql` là NGUỒN SỰ
THẬT của lược đồ. Mọi model đặt `managed = False` nên Django KHÔNG tạo/sửa/xoá
bảng — đổi cấu trúc = sửa schema.sql rồi cập nhật file này.

App này giữ toàn bộ dữ liệu "trường/ngành/tổ hợp/điểm chuẩn" (chỉ đọc từ phía
web; crawler + import_mysql.py ghi). Dữ liệu người dùng nằm ở app `admissions`,
kết quả gợi ý ở app `recommendation`.
"""

from django.db import models

PHUONG_THUC = [
    ("Điểm thi THPT", "Điểm thi THPT"),
    ("Điểm học bạ", "Điểm học bạ"),
]
VUNG_MIEN = [
    ("Miền Bắc", "Miền Bắc"),
    ("Miền Trung", "Miền Trung"),
    ("Miền Nam", "Miền Nam"),
]


class Truong(models.Model):
    ma_truong = models.CharField(primary_key=True, max_length=10)
    ten_truong = models.CharField(max_length=150)
    viet_tat = models.CharField(max_length=20)
    tinh_thanh = models.CharField(max_length=30)
    vung_mien = models.CharField(max_length=10, choices=VUNG_MIEN)

    class Meta:
        managed = False
        db_table = "truong"

    def __str__(self):
        return f"{self.ma_truong} — {self.ten_truong}"


class Nganh(models.Model):
    nganh_id = models.AutoField(primary_key=True)
    nganh_slug = models.CharField(unique=True, max_length=120)
    ten_nganh = models.CharField(max_length=320)
    nhom_nganh = models.CharField(max_length=40)

    class Meta:
        managed = False
        db_table = "nganh"

    def __str__(self):
        return self.ten_nganh


class Mon(models.Model):
    ma_mon = models.CharField(primary_key=True, max_length=15)
    ten_mon = models.CharField(max_length=60)
    la_nang_khieu = models.BooleanField()
    thu_tu = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = "mon"
        ordering = ["thu_tu"]

    def __str__(self):
        return self.ten_mon


class ToHop(models.Model):
    ma_to_hop = models.CharField(primary_key=True, max_length=5)
    ten_to_hop = models.CharField(max_length=80)
    cac_mon = models.CharField(max_length=60, help_text="TOAN,LI,HOA")
    so_mon = models.PositiveIntegerField()
    nguon = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = "to_hop"

    def __str__(self):
        return f"{self.ma_to_hop} ({self.ten_to_hop})"

    def danh_sach_mon(self) -> list[str]:
        """Mã môn dạng list. Rỗng nếu chưa map được tổ hợp -> CN-01 bỏ qua."""
        return self.cac_mon.split(",") if self.cac_mon else []


class ToHopMon(models.Model):
    pk = models.CompositePrimaryKey("ma_to_hop", "ma_mon", "vi_tri")
    ma_to_hop = models.ForeignKey(ToHop, models.DO_NOTHING, db_column="ma_to_hop")
    ma_mon = models.ForeignKey(Mon, models.DO_NOTHING, db_column="ma_mon")
    vi_tri = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = "to_hop_mon"


class DiemChuan(models.Model):
    """Bảng fact: 1 dòng = (trường, ngành, tổ hợp, phương thức, năm)."""

    ma_truong = models.ForeignKey(Truong, models.DO_NOTHING, db_column="ma_truong")
    nganh = models.ForeignKey(Nganh, models.DO_NOTHING, db_column="nganh_id")
    ma_to_hop = models.ForeignKey(ToHop, models.DO_NOTHING, db_column="ma_to_hop")
    phuong_thuc = models.CharField(max_length=13, choices=PHUONG_THUC)
    nam = models.PositiveSmallIntegerField()
    diem_chuan = models.DecimalField(max_digits=4, decimal_places=2)
    ten_nganh_goc = models.CharField(max_length=512)

    class Meta:
        managed = False
        db_table = "diem_chuan"
        unique_together = (("ma_truong", "nganh", "ma_to_hop", "phuong_thuc", "nam"),)


class DacTrungDiemChuan(models.Model):
    """Đặc trưng cho mô hình (SRS 6.4). diem_nam_1..5 map qua CuaSoNam."""

    ma_truong = models.ForeignKey(Truong, models.DO_NOTHING, db_column="ma_truong")
    nganh = models.ForeignKey(Nganh, models.DO_NOTHING, db_column="nganh_id")
    ma_to_hop = models.ForeignKey(ToHop, models.DO_NOTHING, db_column="ma_to_hop")
    phuong_thuc = models.CharField(max_length=13, choices=PHUONG_THUC)

    diem_nam_1 = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    diem_nam_2 = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    diem_nam_3 = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    diem_nam_4 = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    diem_nam_5 = models.DecimalField(max_digits=4, decimal_places=2, null=True)

    diem_tb = models.DecimalField(max_digits=4, decimal_places=2)
    diem_min = models.DecimalField(max_digits=4, decimal_places=2)
    diem_max = models.DecimalField(max_digits=4, decimal_places=2)
    diem_moi_nhat = models.DecimalField(max_digits=4, decimal_places=2)
    bien_dong = models.DecimalField(max_digits=5, decimal_places=2)
    xu_huong = models.DecimalField(max_digits=6, decimal_places=3)
    so_nam_co_dl = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = "dac_trung_diemchuan"
        unique_together = (("ma_truong", "nganh", "ma_to_hop", "phuong_thuc"),)

    def chuoi_diem(self) -> list:
        """Chuỗi 5 năm theo thứ tự cũ -> mới, None = năm không tuyển."""
        return [getattr(self, f"diem_nam_{i}") for i in range(1, 6)]


class CuaSoNam(models.Model):
    """vi_tri 1..5 -> năm thật. Đổi cửa sổ không cần ALTER TABLE (CN-05)."""

    vi_tri = models.PositiveIntegerField(primary_key=True)
    nam = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        managed = False
        db_table = "cua_so_nam"
        ordering = ["vi_tri"]


class LanCapNhat(models.Model):
    thoi_diem = models.DateTimeField()
    nguon = models.CharField(max_length=100)
    nam_bat_dau = models.PositiveSmallIntegerField()
    nam_ket_thuc = models.PositiveSmallIntegerField()
    so_truong = models.PositiveSmallIntegerField()
    so_nganh = models.PositiveSmallIntegerField()
    so_dong_diem = models.PositiveIntegerField()
    selfcheck_dat = models.BooleanField()
    ghi_chu = models.CharField(max_length=500)

    class Meta:
        managed = False
        db_table = "lan_cap_nhat"
        ordering = ["-thoi_diem"]