# -*- coding: utf-8 -*-
"""Test cases cho các luồng đăng nhập OAuth 2.0 (Google & Facebook).

Kiểm thử xác thực OAuth không gọi mạng ngoài: mock requests.post/get.
Chạy: python manage.py test accounts
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

GOOGLE_TOKEN_OK = {"access_token": "google-token-gia"}
GOOGLE_INFO_OK = {
    "email": "HocSinh@Gmail.com",
    "email_verified": True,
    "given_name": "An",
    "family_name": "Nguyễn",
}

FB_TOKEN_OK = {"access_token": "fb-token-gia"}
FB_INFO_OK = {"id": "1", "name": "Nguyễn Văn An", "email": "HocSinh@Gmail.com"}


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@override_settings(GOOGLE_CLIENT_ID="client-gia", GOOGLE_CLIENT_SECRET="secret-gia")
class DangNhapGoogleTest(TestCase):
    def _dat_state(self, state="state-dung"):
        s = self.client.session
        s["google_state"] = state
        s.save()

    def _mock_google(self, info=None):
        return (
            patch("accounts.views_oauth.requests.post", return_value=_Resp(GOOGLE_TOKEN_OK)),
            patch("accounts.views_oauth.requests.get", return_value=_Resp(info or GOOGLE_INFO_OK)),
        )

    def test_chua_cau_hinh_thi_bao_loi(self):
        with override_settings(GOOGLE_CLIENT_ID="", GOOGLE_CLIENT_SECRET=""):
            r = self.client.get(reverse("accounts:google_login"))
        self.assertRedirects(r, reverse("accounts:dang_nhap"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)

    def test_lan_dau_tao_user_va_dang_nhap(self):
        self._dat_state()
        p1, p2 = self._mock_google()
        with p1, p2:
            r = self.client.get(
                reverse("accounts:google_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )

        self.assertRedirects(r, reverse("university:trang_chu"), fetch_redirect_response=False)
        u = User.objects.get()
        self.assertEqual(u.email, "hocsinh@gmail.com")
        self.assertEqual(u.username, "hocsinh@gmail.com")
        self.assertEqual(u.first_name, "An")
        self.assertEqual(u.last_name, "Nguyễn")
        self.assertFalse(u.has_usable_password())
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.id)

    def test_lan_hai_khong_tao_trung(self):
        User.objects.create_user(username="hocsinh@gmail.com", email="hocsinh@gmail.com")
        self._dat_state()
        p1, p2 = self._mock_google()
        with p1, p2:
            self.client.get(
                reverse("accounts:google_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )
        self.assertEqual(User.objects.count(), 1)

    def test_username_tay_trung_email_thi_them_hau_to(self):
        User.objects.create_user(username="hocsinh@gmail.com", email="khac@x.local")
        self._dat_state()
        p1, p2 = self._mock_google()
        with p1, p2:
            self.client.get(
                reverse("accounts:google_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )
        u = User.objects.get(email="hocsinh@gmail.com")
        self.assertEqual(u.username, "hocsinh@gmail.com-2")
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.id)

    def test_state_sai_bi_tu_choi(self):
        self._dat_state("state-dung")
        p1, p2 = self._mock_google()
        with p1, p2:
            r = self.client.get(
                reverse("accounts:google_callback"),
                {"state": "state-gia", "code": "code-gia"},
            )
        self.assertRedirects(r, reverse("accounts:dang_nhap"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)

    def test_email_chua_xac_thuc_bi_tu_choi(self):
        self._dat_state()
        p1, p2 = self._mock_google(info={**GOOGLE_INFO_OK, "email_verified": False})
        with p1, p2:
            r = self.client.get(
                reverse("accounts:google_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )
        self.assertRedirects(r, reverse("accounts:dang_nhap"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)

    def test_google_tra_loi_thi_khong_sap_trang(self):
        import requests

        self._dat_state()
        with patch("accounts.views_oauth.requests.post",
                   side_effect=requests.RequestException("mạng hỏng")):
            r = self.client.get(
                reverse("accounts:google_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )
        self.assertRedirects(r, reverse("accounts:dang_nhap"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)


@override_settings(FACEBOOK_APP_ID="app-gia", FACEBOOK_APP_SECRET="secret-gia")
class DangNhapFacebookTest(TestCase):
    def _dat_state(self, state="state-dung"):
        s = self.client.session
        s["facebook_state"] = state
        s.save()

    def _mock_fb(self, info=None):
        return patch(
            "accounts.views_oauth.requests.get",
            side_effect=[_Resp(FB_TOKEN_OK), _Resp(info or FB_INFO_OK)],
        )

    def test_chua_cau_hinh_thi_bao_loi(self):
        with override_settings(FACEBOOK_APP_ID="", FACEBOOK_APP_SECRET=""):
            r = self.client.get(reverse("accounts:facebook_login"))
        self.assertRedirects(r, reverse("accounts:dang_nhap"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)

    def test_lan_dau_tao_user_va_dang_nhap(self):
        self._dat_state()
        with self._mock_fb():
            r = self.client.get(
                reverse("accounts:facebook_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )

        self.assertRedirects(r, reverse("university:trang_chu"), fetch_redirect_response=False)
        u = User.objects.get()
        self.assertEqual(u.email, "hocsinh@gmail.com")
        self.assertEqual(u.username, "hocsinh@gmail.com")
        self.assertEqual(u.first_name, "Nguyễn Văn An")
        self.assertFalse(u.has_usable_password())
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.id)

    def test_lan_hai_khong_tao_trung(self):
        User.objects.create_user(username="hocsinh@gmail.com", email="hocsinh@gmail.com")
        self._dat_state()
        with self._mock_fb():
            self.client.get(
                reverse("accounts:facebook_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )
        self.assertEqual(User.objects.count(), 1)

    def test_state_sai_bi_tu_choi(self):
        self._dat_state("state-dung")
        with self._mock_fb():
            r = self.client.get(
                reverse("accounts:facebook_callback"),
                {"state": "state-gia", "code": "code-gia"},
            )
        self.assertRedirects(r, reverse("accounts:dang_nhap"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_thieu_email_bi_tu_choi(self):
        self._dat_state()
        with self._mock_fb(info={"id": "1", "name": "Nguyễn Văn An"}):
            r = self.client.get(
                reverse("accounts:facebook_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )
        self.assertRedirects(r, reverse("accounts:dang_nhap"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)

    def test_facebook_tra_loi_thi_khong_sap_trang(self):
        import requests

        self._dat_state()
        with patch("accounts.views_oauth.requests.get",
                   side_effect=requests.RequestException("mạng hỏng")):
            r = self.client.get(
                reverse("accounts:facebook_callback"),
                {"state": "state-dung", "code": "code-gia"},
            )
        self.assertRedirects(r, reverse("accounts:dang_nhap"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)
