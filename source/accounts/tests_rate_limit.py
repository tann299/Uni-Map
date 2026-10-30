# -*- coding: utf-8 -*-
"""Test rate limit dùng chung (accounts.rate_limit) và áp dụng ở các view.

Chạy: python manage.py test accounts
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.rate_limit import (ip_khach, khoa_theo_ip, khoa_theo_user,
                                 vuot_gioi_han)


def _req(ip="1.2.3.4", user=None):
    r = RequestFactory().get("/")
    r.META["REMOTE_ADDR"] = ip
    if user is not None:
        r.user = user
    else:
        from django.contrib.auth.models import AnonymousUser
        r.user = AnonymousUser()
    return r


class DemCoBanTest(TestCase):
    def setUp(self):
        cache.clear()   # cache chia sẻ giữa test — phải dọn

    def test_duoi_gioi_han_khong_chan(self):
        khoa = "test:duoi"
        for _ in range(3):
            self.assertFalse(vuot_gioi_han(khoa, 5, 60))

    def test_vuot_gioi_han_thi_chan(self):
        khoa = "test:tren"
        for _ in range(5):
            self.assertFalse(vuot_gioi_han(khoa, 5, 60))
        self.assertTrue(vuot_gioi_han(khoa, 5, 60))      # lần 6
        self.assertTrue(vuot_gioi_han(khoa, 5, 60))      # vẫn chặn

    def test_khoa_khac_nhau_dem_rieng(self):
        for _ in range(5):
            vuot_gioi_han("test:a", 5, 60)
        self.assertTrue(vuot_gioi_han("test:a", 5, 60))
        self.assertFalse(vuot_gioi_han("test:b", 5, 60))

    def test_ip_lay_tu_x_forwarded_for(self):
        r = RequestFactory().get("/")
        r.META["HTTP_X_FORWARDED_FOR"] = "8.8.8.8, 10.0.0.1"
        self.assertEqual(ip_khach(r), "8.8.8.8")

    def test_khoa_theo_user_uu_tien_user_pk(self):
        u = User.objects.create_user(username="u1", password="x")
        k1 = khoa_theo_user(_req(ip="1.1.1.1", user=u), "goi-y")
        k2 = khoa_theo_user(_req(ip="2.2.2.2", user=u), "goi-y")
        self.assertEqual(k1, k2)              # cùng user, khác IP -> cùng khoá
        self.assertIn(f"u:{u.pk}", k1)

    def test_khoa_theo_user_roi_ve_ip_khi_chua_dang_nhap(self):
        k = khoa_theo_user(_req(ip="3.3.3.3"), "goi-y")
        self.assertEqual(k, khoa_theo_ip(_req(ip="3.3.3.3"), "goi-y"))


class DangKyRateLimitTest(TestCase):
    def setUp(self):
        cache.clear()

    def _post(self, i):
        """Mỗi lần dùng Client MỚI: đăng ký thành công tự login, client cũ sẽ
        bị view đá về trang chủ ngay (is_authenticated) và không tới bộ đếm."""
        from django.test import Client
        return Client().post(reverse("accounts:dang_ky"), {
            "username": f"u{i}", "email": f"u{i}@x.local",
            "password1": "MatKhauKhaManh1!", "password2": "MatKhauKhaManh1!",
        })

    def test_dang_ky_qua_5_lan_bi_chan_429(self):
        from accounts.views import DANG_KY_CUA_SO, DANG_KY_TOI_DA
        for i in range(DANG_KY_TOI_DA):
            self._post(i)
        r = self._post("cuoi")
        self.assertEqual(r.status_code, 429)
        self.assertFalse(User.objects.filter(username="u_cuoi").exists())
        # các lần trước vẫn tạo được
        self.assertEqual(User.objects.count(), DANG_KY_TOI_DA)
        self.assertGreater(DANG_KY_CUA_SO, 0)


class GoiYRateLimitTest(TestCase):
    """Không gọi ML thật: chỉ kiểm bộ đếm chặn TRƯỚC khi vào view nặng.

    Không tạo HoSoNangLuc: bảng đó `managed = False` (schema.sql là nguồn sự
    thật) nên DB test sqlite không có. Đủ để chứng minh view chặn ở bộ đếm
    TRƯỚC mọi truy vấn hồ sơ — nếu lọt qua sẽ nổ DoesNotExist thay vì 302.
    """

    def setUp(self):
        cache.clear()

    def test_qua_gioi_han_thi_chan_truoc_khi_doc_ho_so(self):
        from recommendation.views import GOI_Y_CUA_SO, GOI_Y_TOI_DA
        from accounts.rate_limit import khoa_theo_user

        u = User.objects.create_user(username="u2", password="x")
        self.client.force_login(u)

        # Đốt hết hạn mức của CHÍNH user này
        r = _req(ip="127.0.0.1", user=u)
        for _ in range(GOI_Y_TOI_DA):
            vuot_gioi_han(khoa_theo_user(r, "goi-y"), GOI_Y_TOI_DA, GOI_Y_CUA_SO)

        from unittest.mock import patch
        with patch("recommendation.views._goi_y_uc05") as mock_ml:
            # pk không tồn tại: nếu bộ đếm KHÔNG chặn thì view sẽ 404 (đọc hồ
            # sơ trước) — 302 chứng minh chặn đã xảy ra trước bước đó.
            resp = self.client.get(reverse("recommendation:xem_goi_y", args=[999999]))
        mock_ml.assert_not_called()                       # KHONG chay ML
        self.assertEqual(resp.status_code, 302)
