# -*- coding: utf-8 -*-
"""
Test CN-01 — hàm tính tổ hợp thuần (SRS mục CN-01, tiêu chí US-08).

Assert-based, KHÔNG cần DB (mọi model managed=False nên `manage.py test` không
dựng được bảng). Chạy thẳng:

    python -m admissions.tests
"""
from recommendation.services import chon_can_ban, giai_thich, phan_tang
from university.services import tinh_to_hop

TO_HOP = {
    "A00": ["TOAN", "LI", "HOA"],
    "A01": ["TOAN", "LI", "ANH"],
    "C00": ["VAN", "SU", "DIA"],
    "H00": ["VAN", "NK", "NK"],
    "CN01": [],                       # chưa map được môn -> bỏ qua
}
NANG_KHIEU = {"NK"}


def test_du_mon_thi_cong():
    diem = {"TOAN": 8.5, "LI": 7.75, "HOA": 8.0, "ANH": 9.0}
    kq = {r["ma"]: r["tong"] for r in tinh_to_hop(diem, TO_HOP, NANG_KHIEU)}
    assert kq["A00"] == 24.25, f"A00 = {kq.get('A00')}, cần 24.25"
    assert kq["A01"] == 25.25, f"A01 = {kq.get('A01')}, cần 25.25"


def test_thieu_mon_thi_bo_qua_im_lang():
    diem = {"TOAN": 8.5, "LI": 7.75, "HOA": 8.0, "ANH": 9.0}
    ma = {r["ma"] for r in tinh_to_hop(diem, TO_HOP, NANG_KHIEU)}
    assert "C00" not in ma, "C00 cần VAN,SU,DIA — thiếu môn, không được tính"
    assert "H00" not in ma, "H00 cần NK — thiếu môn, không được tính"


def test_to_hop_rong_bi_bo():
    diem = {"TOAN": 8.5, "LI": 7.75, "HOA": 8.0, "ANH": 9.0}
    ma = {r["ma"] for r in tinh_to_hop(diem, TO_HOP, NANG_KHIEU)}
    assert "CN01" not in ma, "tổ hợp rỗng phải bị bỏ qua"


def test_danh_dau_nang_khieu():
    diem = {"VAN": 7.0, "NK": 8.0}   # đủ môn cho H00 (VAN, NK, NK)
    kq = {r["ma"]: r for r in tinh_to_hop(diem, TO_HOP, NANG_KHIEU)}
    assert "H00" in kq, "H00 đủ môn (VAN, NK) phải được tính"
    assert kq["H00"]["can_nang_khieu"] is True, "H00 phải bị đánh dấu cần năng khiếu"
    assert kq["H00"]["tong"] == 23.0, f"H00 = {kq['H00']['tong']}, cần 23.0 (7+8+8)"


def test_sap_xep_giam_dan():
    diem = {"TOAN": 8.5, "LI": 7.75, "HOA": 8.0, "ANH": 9.0}
    tong = [r["tong"] for r in tinh_to_hop(diem, TO_HOP, NANG_KHIEU)]
    assert tong == sorted(tong, reverse=True), "kết quả phải sắp theo tổng điểm giảm dần"


def test_phan_tang():
    """CN-03: ngưỡng An toàn ≥+2đ · Vừa sức 0..+2đ · Thử sức <0."""
    assert phan_tang(2.0) == "An toàn", "margin +2.0 phải An toàn"
    assert phan_tang(3.5) == "An toàn"
    assert phan_tang(1.5) == "Vừa sức", "margin +1.5 phải Vừa sức"
    assert phan_tang(0.0) == "Vừa sức"
    assert phan_tang(-0.5) == "Thử sức", "margin âm phải Thử sức"

def test_giai_thich_co_cau():
    """CN-04: đúng 4 câu, margin âm -> câu đầu là cảnh báo."""
    dt = {"margin": -0.5, "xu_huong": 0.6, "bien_dong": 2.1,
          "so_nam_co_dl": 2, "nam_moi_nhat": 2025}
    cau = giai_thich(dt)
    assert len(cau) == 4, f"cần 4 câu, got {len(cau)}"
    assert cau[0]["canh_bao"] is True, "margin âm phải là cảnh báo"
    assert cau[1]["canh_bao"] is True, "xu_huong +0.6 phải cảnh báo"
    assert cau[3]["canh_bao"] is True, "2/5 năm phải cảnh báo độ tin cậy"

def _tang(t, n):
    return [{"tang": t, "margin": n - i} for i in range(n)]

def test_chon_can_ban_chia_deu():
    """CN-03: mỗi tầng đủ dữ liệu -> chia đều 10/10/10."""
    theo = {"An toàn": _tang("An toàn", 20),
            "Vừa sức": _tang("Vừa sức", 20),
            "Thử sức": _tang("Thử sức", 20)}
    chon = chon_can_ban(theo, 30)
    dem = {t: sum(1 for x in chon if x["tang"] == t) for t in theo}
    assert dem == {"An toàn": 10, "Vừa sức": 10, "Thử sức": 10}, dem
    hang = [list(theo).index(x["tang"]) for x in chon]
    assert hang == sorted(hang), "phải sắp theo tầng An toàn trước"

def test_chon_can_ban_tang_thieu_nhuong_suat():
    """Tầng thiếu thì tầng khác lấp cho đủ giới hạn."""
    theo = {"An toàn": _tang("An toàn", 2),
            "Vừa sức": _tang("Vừa sức", 50),
            "Thử sức": _tang("Thử sức", 0)}
    chon = chon_can_ban(theo, 30)
    assert len(chon) == 30, f"cần đủ 30, got {len(chon)}"
    dem = {t: sum(1 for x in chon if x["tang"] == t) for t in theo}
    assert dem["An toàn"] == 2 and dem["Thử sức"] == 0, dem
    assert dem["Vừa sức"] == 28, dem

def test_giai_thich_khong_bia_so():
    """CN-04: câu phải chứa đúng con số trong đặc trưng."""
    dt = {"margin": 1.3, "xu_huong": 0.4, "bien_dong": 1.0,
          "so_nam_co_dl": 5, "nam_moi_nhat": 2025}
    chu = " ".join(c["chu"] for c in giai_thich(dt))
    assert "1,3" in chu, "margin phải dùng dấu phẩy tiếng Việt"
    assert "2025" in chu
    assert "5/5 năm" in chu

def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    loi = 0
    for fn in tests:
        try:
            fn()
            print(f"   [OK]   {fn.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"   [SAI]  {fn.__name__}: {e}")
    if loi:
        raise SystemExit(f"{loi}/{len(tests)} test CN-01 thất bại")
    print(f"[OK] {len(tests)}/{len(tests)} test CN-01 đạt.")


if __name__ == "__main__":
    main()
