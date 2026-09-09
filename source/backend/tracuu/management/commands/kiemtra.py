# -*- coding: utf-8 -*-
"""
Kiểm tra model Django khớp lược đồ MySQL và dữ liệu đã import.

Không dùng `manage.py test`: mọi model đều `managed = False` nên Django không
tạo được bảng trong test DB. Lệnh này chạy thẳng trên DB thật, CHỈ ĐỌC.

    python manage.py kiemtra
"""

import csv

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from tracuu.models import (CuaSoNam, DacTrungDiemChuan, DiemChuan, Mon, Nganh,
                           ToHop, Truong)

VUNG_MIEN_HOP_LE = {"Miền Bắc", "Miền Trung", "Miền Nam"}
DATA_DIR = settings.DATA_DIR      # gốc dự án/data, dùng chung với crawler

# model -> file CSV nguồn. Không hardcode số dòng: dữ liệu đổi hằng năm, mà
# một con số cứng trong test thì mỗi lần cập nhật lại phải sửa test.
NGUON = [
    (Truong, "truong.csv"),
    (Nganh, "nganh.csv"),
    (ToHop, "to_hop.csv"),
    (DiemChuan, "diem_chuan.csv"),
    (DacTrungDiemChuan, "dac_trung_diemchuan.csv"),
]


def dem_dong_csv(name: str) -> int:
    with open(DATA_DIR / name, encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1      # trừ dòng tiêu đề


def so_dong():
    """DB khớp CSV — bắt cả dòng thiếu (import lỗi) và dòng rác (chưa dọn)."""
    for model, name in NGUON:
        db, csv_n = model.objects.count(), dem_dong_csv(name)
        assert db == csv_n, f"{name}: DB {db:,} != CSV {csv_n:,}"
    assert Mon.objects.count() == 27, "bảng mon phải có 27 môn (seed schema.sql)"


def cua_so_nam():
    """CN-05: đúng N năm liên tục, khớp số năm thực có trong bảng fact."""
    nam = list(CuaSoNam.objects.values_list("nam", flat=True))
    assert nam == list(range(nam[0], nam[0] + len(nam))), f"năm không liên tục: {nam}"
    thuc = DiemChuan.objects.values_list("nam", flat=True).distinct().count()
    assert len(nam) == thuc, f"cua_so_nam {len(nam)} năm != fact {thuc} năm"


def vi_tri_truong():
    """CN-06: 100% trường có vị trí — rỗng thì lọc theo khu vực mất trường."""
    la = set(Truong.objects.values_list("vung_mien", flat=True).distinct()) - VUNG_MIEN_HOP_LE
    assert not la, f"vung_mien lạ: {la}"
    assert not Truong.objects.filter(tinh_thanh="").exists(), "có trường thiếu tinh_thanh"


def khong_co_font_loi():
    """Nguồn ngẫu nhiên trả byte hỏng -> U+FFFD. Crawler vá, đây là chốt chặn."""
    for model, field in ((Truong, "ten_truong"), (Nganh, "ten_nganh"),
                         (ToHop, "ten_to_hop"), (DiemChuan, "ten_nganh_goc")):
        n = model.objects.filter(**{f"{field}__contains": "�"}).count()
        assert n == 0, f"{model.__name__}.{field}: {n:,} dòng còn ký tự hỏng"


def khong_co_mo_coi():
    """Bảng chiều không được chứa dòng mà không dòng fact nào trỏ tới."""
    for model, field in ((Truong, "ma_truong"), (Nganh, "nganh"), (ToHop, "ma_to_hop")):
        n = model.objects.filter(**{f"diemchuan__{field}": None}).count()
        assert n == 0, f"{model.__name__}: {n:,} dòng mồ côi (không có điểm chuẩn)"


def join_foreign_key():
    """select_related nổ nếu db_column trong model sai."""
    dc = DiemChuan.objects.select_related("ma_truong", "nganh", "ma_to_hop").first()
    assert dc.ma_truong.ten_truong and dc.nganh.ten_nganh and dc.ma_to_hop.ma_to_hop


def so_nam_co_dl():
    """Bất biến bảng đặc trưng: so_nam_co_dl == số ô điểm không rỗng."""
    for dt in DacTrungDiemChuan.objects.all()[:500]:
        co = sum(1 for d in dt.chuoi_diem() if d is not None)
        assert co == dt.so_nam_co_dl, f"lệch tại {dt.pk}: {co} != {dt.so_nam_co_dl}"


def ghep_to_hop():
    """CN-01: đủ môn thì cộng, thiếu môn thì bỏ qua im lặng."""
    diem_hs = {"TOAN": 8.5, "LI": 7.75, "HOA": 8.0, "ANH": 9.0}
    duoc = {}
    for th in ToHop.objects.exclude(cac_mon=""):
        mon = th.danh_sach_mon()
        if all(m in diem_hs for m in mon):
            duoc[th.ma_to_hop] = round(sum(diem_hs[m] for m in mon), 2)

    assert duoc.get("A00") == 24.25, f"A00 = {duoc.get('A00')}, cần 24.25"
    assert duoc.get("A01") == 25.25, f"A01 = {duoc.get('A01')}, cần 25.25"
    assert "C00" not in duoc, "C00 cần VAN,SU,DIA — không được tính"


KIEM_TRA = [
    ("DB khớp CSV", so_dong),
    ("cửa sổ năm liên tục", cua_so_nam),
    ("vị trí trường 100%", vi_tri_truong),
    ("không còn font lỗi", khong_co_font_loi),
    ("không có dòng mồ côi", khong_co_mo_coi),
    ("join qua foreign key", join_foreign_key),
    ("so_nam_co_dl nhất quán", so_nam_co_dl),
    ("CN-01 ghép tổ hợp", ghep_to_hop),
]


class Command(BaseCommand):
    help = "Kiểm tra model khớp lược đồ MySQL và dữ liệu đã import (chỉ đọc)"

    def handle(self, *args, **opts):
        loi = 0
        for ten, fn in KIEM_TRA:
            try:
                fn()
                self.stdout.write(f"   [OK]   {ten}")
            except AssertionError as e:
                loi += 1
                self.stdout.write(self.style.ERROR(f"   [SAI]  {ten}: {e}"))

        if loi:
            raise CommandError(f"{loi}/{len(KIEM_TRA)} kiểm tra thất bại")
        self.stdout.write(self.style.SUCCESS(
            f"[OK] {len(KIEM_TRA)}/{len(KIEM_TRA)} kiểm tra đạt."))
