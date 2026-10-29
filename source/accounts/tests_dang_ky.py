# -*- coding: utf-8 -*-
"""Test luồng đăng ký form thường: chặn trùng email.

Chạy: python manage.py test accounts
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


def _post_dang_ky(client, username, email, pw="MatKhauKhaManh1!", pw2=None):
    return client.post(
        reverse("accounts:dang_ky"),
        {
            "username": username,
            "email": email,
            "password1": pw,
            "password2": pw2 or pw,
        },
    )


class DangKyTest(TestCase):
    def test_dang_ky_thanh_cong_luu_email(self):
        r = _post_dang_ky(self.client, "hocsinh", "HocSinh@Gmail.com")
        self.assertRedirects(r, reverse("university:trang_chu"), fetch_redirect_response=False)
        u = User.objects.get()
        self.assertEqual(u.email, "hocsinh@gmail.com")  # chuẩn hoá về thường
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.id)

    def test_trung_email_bi_tu_choi(self):
        """Email đã có trong DB (kể cả do OAuth tạo) không đăng ký thêm được."""
        User.objects.create_user(username="hocsinh@gmail.com", email="hocsinh@gmail.com")
        r = _post_dang_ky(self.client, "hocsinh2", "hocsinh@gmail.com")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Email này đã được dùng để đăng ký tài khoản.")
        self.assertEqual(User.objects.count(), 1)

    def test_trung_email_khac_chu_lai_bị_tu_choi(self):
        User.objects.create_user(username="a", email="hocsinh@gmail.com")
        r = _post_dang_ky(self.client, "b", "HocSinh@GMAIL.com")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_trung_username_nhung_email_khac_van_bị_tu_choi_username(self):
        User.objects.create_user(username="hocsinh", email="khac@x.local")
        r = _post_dang_ky(self.client, "hocsinh", "hocsinh@gmail.com")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
