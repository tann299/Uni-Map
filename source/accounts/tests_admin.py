# -*- coding: utf-8 -*-
"""Test form admin cho tài khoản: chuẩn hoá + chặn email trùng.

Regression chính: `add_fieldsets` của Django 5.2 tham chiếu `usable_password`,
nếu kế thừa sai form (UserCreationForm thay vì AdminUserCreationForm) thì
trang /admin/auth/user/add/ nổ FieldError.

Invariant post-migration (accounts.0002): mọi email trong DB đều đã chuẩn hoá,
nên input chuẩn hoá rồi so iexact là đủ. Test thứ hai phủ cửa sổ transition:
DB còn email CHƯA chuẩn hoá (migration chưa chạy) thì vẫn bắt được khi input
dùng đúng dạng đó.

Chạy: python manage.py test accounts (test DB sqlite, không cần MySQL).
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.admin import (UniMapUserAdmin, UniMapUserChangeForm,
                            UniMapUserCreationForm)


def _form_them(email="Admin.Moi+uni@Gmail.com"):
    """Form thêm user hợp lệ."""
    return UniMapUserCreationForm(data={
        "username": "admin_moi",
        "email": email,
        "password1": "MatKhauKhaManh1!",
        "password2": "MatKhauKhaManh1!",
    })


class FormAdminTest(TestCase):
    def test_add_form_con_field_usable_password(self):
        """Fieldset Django 5.2 tham chiếu usable_password — thiếu là trang admin nổ."""
        form = _form_them()
        self.assertIn("usable_password", form.fields)
        self.assertIn("email", form.fields)

    def test_add_form_chuan_hoa_email(self):
        # Gmail bỏ cả '.' lẫn '+tag' -> adminmoi, không phải admin.moi
        form = _form_them()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().email, "adminmoi@gmail.com")

    def test_add_form_chan_email_trung(self):
        """DB đã chuẩn hoá (post-migration) — input alias khác vẫn bị chặn."""
        User.objects.create_user(username="khac", email="adminmoi@gmail.com")
        form = _form_them()
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_add_form_email_trung_cach_hoa_thuong(self):
        User.objects.create_user(username="khac", email="ADMINMOI@gmail.com")
        form = _form_them()
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_add_form_chan_email_trung_khi_db_chua_chuan_hoa(self):
        """Cửa sổ transition: migration chưa chạy, DB còn email dạng gõ tay."""
        User.objects.create_user(username="cu", email="admin.moi@gmail.com")
        form = _form_them(email="admin.moi@gmail.com")
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_add_form_email_trong_van_hop_le(self):
        """User.email blank=True — bỏ trống vẫn tạo được tài khoản."""
        form = _form_them(email="")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().email, "")

    def test_change_form_bo_qua_chinh_minh(self):
        u = User.objects.create_user(username="toi", email="toi@gmail.com")
        form = UniMapUserChangeForm(instance=u)
        form.cleaned_data = {"email": "Toi+sp@gmail.com"}   # alias cùng hộp thư
        self.assertEqual(form.clean_email(), "toi@gmail.com")

    def test_change_form_chan_email_nguoi_khac(self):
        User.objects.create_user(username="khac", email="khac@gmail.com")
        u = User.objects.create_user(username="toi", email="toi@gmail.com")
        form = UniMapUserChangeForm(instance=u)
        form.cleaned_data = {"email": "khac@gmail.com"}
        with self.assertRaises(ValidationError):
            form.clean_email()

    def test_change_form_trung_cach_hoa_thuong_cua_minh_van_duoc(self):
        u = User.objects.create_user(username="toi", email="Toi@Gmail.com")
        form = UniMapUserChangeForm(instance=u)
        form.cleaned_data = {"email": "toi@gmail.com"}
        self.assertEqual(form.clean_email(), "toi@gmail.com")

    def test_admin_dang_ky_form_dung(self):
        """UniMapUserAdmin phải trỏ đúng 2 form đã override."""
        self.assertIs(UniMapUserAdmin.add_form, UniMapUserCreationForm)
        self.assertIs(UniMapUserAdmin.form, UniMapUserChangeForm)
        self.assertIn("email", UniMapUserAdmin.add_fieldsets[0][1]["fields"])


class EmailKhongDuBiXoaTest(TestCase):
    """Email TRỐNG khi sửa không được xoá email cũ (bug làm mất dữ liệu).

    Repro: user OAuth sửa thông tin/avatar, form gửi email rỗng -> email cũ
    bị xóa -> lần login Google sau không tìm thấy -> tạo user '-2', avatar
    và hồ sơ cũ bị bỏ rơi ở tài khoản cũ.
    """

    def test_admin_change_trong_giu_email_cu(self):
        u = User.objects.create_user(username="toi", email="toi@gmail.com")
        form = UniMapUserChangeForm(instance=u)
        form.cleaned_data = {"email": "  "}
        self.assertEqual(form.clean_email(), "toi@gmail.com")

    def test_thong_tin_form_trong_giu_email_cu(self):
        from accounts.views import ThongTinForm
        u = User.objects.create_user(username="toi", email="toi@gmail.com")
        form = ThongTinForm(data={"first_name": "Toi", "last_name": "Trong",
                                  "email": ""}, instance=u)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["email"], "toi@gmail.com")

    def test_thong_tin_form_doi_sang_moi_van_chay(self):
        from accounts.views import ThongTinForm
        u = User.objects.create_user(username="toi", email="cu@gmail.com")
        form = ThongTinForm(data={"first_name": "Toi", "last_name": "Trong",
                                  "email": "Moi@gmail.com"}, instance=u)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["email"], "moi@gmail.com")

    def test_thong_tin_form_email_trung_nguoi_khac_bi_chan(self):
        from accounts.views import ThongTinForm
        User.objects.create_user(username="khac", email="khac@gmail.com")
        u = User.objects.create_user(username="toi", email="toi@gmail.com")
        form = ThongTinForm(data={"first_name": "Toi", "last_name": "Trong",
                                  "email": "khac@gmail.com"}, instance=u)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
