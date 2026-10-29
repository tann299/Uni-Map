# -*- coding: utf-8 -*-
"""Test chuẩn hoá Gmail và chống trùng user qua alias.

Chạy: python manage.py test accounts (test DB sqlite, không cần MySQL).
"""
from unittest.mock import patch

from django.contrib.auth.models import User
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
             patch("accounts.views_oauth.login"):
            _dang_nhap_user(request, email, first_name="An")

    def test_alias_khong_tao_user_moi(self):
        self._dang_nhap("annguyen@gmail.com")
        self._dang_nhap("an.nguyen@gmail.com")
        self._dang_nhap("an.nguyen+uni@gmail.com")
        self.assertEqual(User.objects.count(), 1)
        # email lưu dạng chuẩn hoá nên các lần sau khớp lookup chính xác
        self.assertEqual(User.objects.get().email, "annguyen@gmail.com")

    def test_alias_hop_voi_user_dang_ky_form(self):
        # Sau migration 0002, email cũ đã được chuẩn hoá trong DB
        User.objects.create_user(username="an", email="annguyen@gmail.com")
        self._dang_nhap("an.nguyen+sp@gmail.com")
        self.assertEqual(User.objects.count(), 1)
