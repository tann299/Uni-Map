# -*- coding: utf-8 -*-
"""Test chuẩn hoá Gmail và chống trùng user qua alias.

Chạy: python manage.py test accounts (test DB sqlite, không cần MySQL).
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase

from accounts.gmail import chuan_hoa_email
from accounts.views_oauth import _dang_nhap_user


class ChuanHoaEmailTest(TestCase):
    def test_gmail_bo_cham_va_plus_tag(self):
        self.assertEqual(chuan_hoa_email("An.Nguyen+uni@Gmail.com"), "annguyen@gmail.com")
        self.assertEqual(chuan_hoa_email("a.b.c+x@gmail.com"), "abc@gmail.com")

    def test_googlemail_ve_gmail(self):
        self.assertEqual(chuan_hoa_email("An.Nguyen@googlemail.com"), "annguyen@gmail.com")

    def test_email_thuong_giu_nguyen(self):
        self.assertEqual(chuan_hoa_email("A.B+tag@yahoo.com"), "a.b+tag@yahoo.com")
        self.assertEqual(chuan_hoa_email("sv@edu.vn"), "sv@edu.vn")


class AliasKhongTaoUserMoiTest(TestCase):
    """Alias Gmail đăng nhập lại phải về đúng user cũ, không tạo mới."""

    def _dang_nhap(self, email):
        rf = RequestFactory()
        request = rf.get("/accounts/google/xac-thuc/")
        request.session = SessionStore()
        with patch("accounts.views_oauth.messages"), \
             patch("accounts.views_oauth.login") as lg:
            _dang_nhap_user(request, email, first_name="An")
        return lg.call_args[0][1].id

    def test_alias_khong_tao_user_moi(self):
        self._dang_nhap("annguyen@gmail.com")
        self._dang_nhap("an.nguyen@gmail.com")
        self._dang_nhap("an.nguyen+uni@gmail.com")
        self.assertEqual(User.objects.count(), 1)

    def test_email_bi_xoa_tim_theo_username_thong_bao_khong_mat_du_lieu(self):
        """Tài khoản OAuth bị mất email (form sửa để trống) — tìm theo USERNAME.

        Repro bug thật: user email='' bị login lần sau bỏ lỡ -> tạo '-2',
        avatar/hồ sơ cũ bị bỏ rơi. Lookup username cứu được + chữa lành email.
        """
        cu = User.objects.create_user(username="annguyen@gmail.com", email="")

        lan2 = self._dang_nhap("an.nguyen@gmail.com")
        self.assertEqual(User.objects.count(), 1)         # khong tao user moi
        self.assertEqual(lan2, cu.id)                     # vao dung ban cu
        cu.refresh_from_db()
        self.assertEqual(cu.email, "annguyen@gmail.com")  # email duoc chua lanh
        self.assertTrue(cu.profile)                       # profile van con
        # email lưu dạng chuẩn hoá nên các lần sau khớp lookup chính xác
        self.assertEqual(User.objects.get().email, "annguyen@gmail.com")

    def test_alias_hop_voi_user_dang_ky_form(self):
        # Sau migration 0002, email cũ đã được chuẩn hoá trong DB
        User.objects.create_user(username="an", email="annguyen@gmail.com")
        self._dang_nhap("an.nguyen+sp@gmail.com")
        self.assertEqual(User.objects.count(), 1)

    def test_email_chua_chuan_hoa_trong_db_van_bat_duoc(self):
        """DB chứa email gõ tay `an.nguyen@` (chưa chạy migration 0002),
        login Google trả dạng chuẩn `annguyen@` — PHẢI bắt được, không tạo mới.

        Đây là lỗ hổng cuối: so 2 chuỗi hụt khi DB có dạng alias lạ hơn
        input — tim_theo_email so sẵn chuẩn hoá trong Python nên bắt được.
        """
        cu = User.objects.create_user(username="khac", email="an.nguyen@gmail.com")
        lan2 = self._dang_nhap("annguyen@gmail.com")
        self.assertEqual(User.objects.count(), 1)   # KHONG tao them record
        self.assertEqual(lan2, cu.id)

    def test_dang_ky_bị_chan_khi_db_chua_email_chua_chuan_hoa(self):
        """Đăng ký form cũng chặn theo dạng chuẩn hoá, không chỉ so chuỗi."""
        from django.urls import reverse as rev
        User.objects.create_user(username="khac", email="an.nguyen@gmail.com")
        r = self.client.post(rev("accounts:dang_ky"), {
            "username": "moi", "email": "annguyen@gmail.com",
            "password1": "MatKhauKhaManh1!", "password2": "MatKhauKhaManh1!",
        })
        self.assertEqual(r.status_code, 200)
        self.assertIn("email", r.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)


class KhoaRaceTest(TestCase):
    """Khoá cache chống 2 callback song song cùng email tạo 2 user.

    DB host chưa có UNIQUE(email) nên khoá cache.add() atomic là lớp chắn duy nhất.
    """

    def setUp(self):
        # LocMemCache sống xuyên suốt process, không tự reset giữa các test —
        # khoá sót từ test trước làm test sau rơi vào nhánh chờ 4s thật.
        cache.clear()

    def _dang_nhap(self, email):
        rf = RequestFactory()
        request = rf.get("/accounts/google/xac-thuc/")
        request.session = SessionStore()
        with patch("accounts.views_oauth.messages"), \
             patch("accounts.views_oauth.login"):
            _dang_nhap_user(request, email, first_name="An")

    def test_co_khoa_va_user_da_co_lay_ngay(self):
        """Request kia giữ khoá nhưng đã tạo xong -> lấy user cũ, không chờ."""
        User.objects.create_user(username="hocsinh@gmail.com",
                                 email="hocsinh@gmail.com")
        cache.add("oauth:tao-user:hocsinh@gmail.com", 1, 10)
        with patch("accounts.views_oauth.time.sleep") as mock_sleep:
            self._dang_nhap("hocsinh@gmail.com")
        mock_sleep.assert_not_called()
        self.assertEqual(User.objects.count(), 1)

    def test_co_khoa_het_ch_tao_mot_user(self):
        """Khoá người khác giữ, hết chờ vẫn không thấy (request kia lỗi) -> tự tạo."""
        cache.add("oauth:tao-user:hocsinh@gmail.com", 1, 10)
        with patch("accounts.views_oauth.time.sleep"):   # không chờ thật 4s trong test
            self._dang_nhap("hocsinh@gmail.com")
        self.assertEqual(User.objects.count(), 1)

    def test_khoa_bi_xoa_sau_khi_tao_xong(self):
        """Ta giữ khoá, tạo xong phải giải khoá — không thì lần sau bị treo."""
        self._dang_nhap("hocsinh@gmail.com")
        self.assertIsNone(cache.get("oauth:tao-user:hocsinh@gmail.com"))
        # lần đăng nhập thứ hai vẫn chạy bình thường (không vướng khoá cũ)
        self._dang_nhap("hocsinh@gmail.com")
        self.assertEqual(User.objects.count(), 1)
