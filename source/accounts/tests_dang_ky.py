# -*- coding: utf-8 -*-
"""Test luồng đăng ký form thường: chặn trùng email.

Chạy: python manage.py test accounts
"""
from django.contrib.auth.models import User
from django.core.cache import cache
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
    def setUp(self):
        # Rate limit đăng ký đếm trên cache dùng chung: không dọn thì test thứ
        # 6 trong cùng class bị 429 (mỗi test POST 1 lần, giới hạn 5/giờ).
        cache.clear()

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
        self.assertIn("username", r.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_trung_username_khac_chu_lai_bị_tu_choi(self):
        """username__iexact: HOCSINH trùng hocsinh vẫn bị chặn."""
        User.objects.create_user(username="hocsinh", email="khac@x.local")
        r = _post_dang_ky(self.client, "HocSinh", "moi@x.local")
        self.assertEqual(r.status_code, 200)
        self.assertIn("username", r.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_trung_ca_username_lan_email_deu_hien_loi(self):
        """Cùng lúc trùng cả hai: cả hai trường đều phải báo lỗi, không tạo gì."""
        User.objects.create_user(username="hocsinh", email="hocsinh@gmail.com")
        r = _post_dang_ky(self.client, "hocsinh", "HocSinh@gmail.com")
        self.assertEqual(r.status_code, 200)
        self.assertIn("username", r.context["form"].errors)
        self.assertIn("email", r.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_username_va_email_deu_moi_van_tao_duoc(self):
        """Điều kiện tích cực: cả hai đều mới thì đăng ký thành công."""
        User.objects.create_user(username="cu", email="cu@gmail.com")
        r = _post_dang_ky(self.client, "moi", "moi@gmail.com")
        self.assertRedirects(r, reverse("university:trang_chu"),
                             fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(User.objects.get(username="moi").email, "moi@gmail.com")
