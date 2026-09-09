# -*- coding: utf-8 -*-
"""
Model Django cho Uni Map — sinh từ `manage.py inspectdb` rồi dọn tay.

QUY ƯỚC QUAN TRỌNG: `db/schema.sql` là NGUỒN SỰ THẬT của lược đồ.
Mọi model ở đây đặt `managed = False` nên Django KHÔNG tạo/sửa/xoá bảng.
Đổi cấu trúc bảng = sửa `schema.sql` rồi chạy lại, sau đó cập nhật file này.
Lý do: cửa sổ trượt, CHECK constraint, ENUM tiếng Việt và các FK RESTRICT
đã đặc tả trong SQL; để Django migrate quản lý sẽ làm mất chúng.

auth_user KHÔNG khai lại ở đây — dùng `django.contrib.auth.models.User`
(Django tự quản lý bảng đó qua migrate).
"""

from django.conf import settings
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
TANG = [
    ("An toàn", "An toàn"),
    ("Vừa sức", "Vừa sức"),
    ("Thử sức", "Thử sức"),
]

# ===========================================================================
# A. DỮ LIỆU THAM CHIẾU  (chỉ đọc — crawler + import_mysql.py ghi)
# ===========================================================================


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


# ===========================================================================
# B. DỮ LIỆU SỰ KIỆN  (chỉ đọc — import_mysql.py ghi)
# ===========================================================================


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

    def chuoi_diem(self) -> list[float | None]:
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


# ===========================================================================
# C. DỮ LIỆU NGƯỜI DÙNG  (Django ghi)
# ===========================================================================


class HoSoNangLuc(models.Model):
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


class LanGoiY(models.Model):
    ho_so = models.ForeignKey(HoSoNangLuc, models.CASCADE, db_column="ho_so_id")
    thoi_diem = models.DateTimeField(auto_now_add=True)
    phien_ban_mo_hinh = models.CharField(max_length=50, blank=True, default="")
    dung_ai = models.BooleanField(default=True)
    so_ket_qua = models.PositiveSmallIntegerField(default=0)

    class Meta:
        managed = False
        db_table = "lan_goi_y"
        ordering = ["-thoi_diem"]


class KetQuaGoiY(models.Model):
    """Snapshot lúc gợi ý — KHÔNG tính lại khi xem lịch sử (điểm chuẩn có thể đã đổi)."""

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



