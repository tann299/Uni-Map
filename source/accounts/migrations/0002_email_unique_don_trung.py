# -*- coding: utf-8 -*-
"""Chặn tràn user trùng email ở tầng DB.

Bài toán: auth_user.email vốn không UNIQUE. Gmail coi `an.nguyen+uni@`,
`an.nguyen@`, `annguyen@gmail.com` là CÙNG hộp thư, nên trước khi có chuẩn hoá
alias, mỗi lần đăng nhập Google bằng dạng alias khác đã tạo một user mới
(username `-2`, `-3`...). Dữ liệu cũ cũng có thể có trùng từ form đăng ký
thường trước khi có DangKyForm.

Migration làm 2 việc:
 1. Dọn dữ liệu cũ: xoá user trùng email (không phân biệt hoa/thường), giữ
    user CŨ NHẤT. Profile/ho_so_nang_luc/... xoá theo (ON DELETE CASCADE).
 2. Thêm UNIQUE(email) để từ nay DB tự chặn, kể cả race condition hai request
    OAuth song song.

Chú ý: unique áp trên chuỗi email; MySQL collation utf8mb4_unicode_ci so sánh
không phân biệt hoa/thường nên 'A@x.com' và 'a@x.com' bị coi trùng ở DB. Chuẩn
hoá alias Gmail (bỏ '.', '+tag') ở tầng app — không thể bỏ trên cột vì phải
giữ email gốc để gửi mail.

Dùng RunPython + schema_editor.connection.vendor thay RunSQL vì test chạy
sqlite (config không cố định DB), còn production là MySQL.
"""
import re

from django.db import migrations

# Chép logic chuẩn hoá từ accounts/gmail.py (không import: migration phải đứng
# vững độc lập với code app sau này). Gmail: bỏ '.', bỏ '+tag', gộp googlemail.
_GMAIL = {"gmail.com", "googlemail.com"}
_XOA_O = re.compile(r"\.|\+.*$")


def _chuan_hoa(email):
    email = (email or "").strip().lower()
    local, _, domain = email.partition("@")
    if not local or not domain:
        return email
    if domain in _GMAIL:
        local = _XOA_O.sub("", local)
        domain = "gmail.com"
    return f"{local}@{domain}"


def don_user_trung(apps, schema_editor):
    """Chuẩn hoá email cũ rồi xoá user trùng, giữ user cũ nhất (id nhỏ nhất)."""
    User = apps.get_model("auth", "User")
    da_thay = set()
    for u in User.objects.order_by("id").iterator():
        email = _chuan_hoa(u.email)
        if email != u.email:
            u.email = email
            u.save(update_fields=["email"])
        if email and email in da_thay:
            u.delete()
        else:
            da_thay.add(email)


def them_unique(apps, schema_editor):
    """Tạo UNIQUE(email) theo dialect: MySQL ADD UNIQUE KEY, còn lại CREATE INDEX."""
    sql = ("ALTER TABLE auth_user ADD UNIQUE KEY uq_auth_user_email_chuan (email)"
           if schema_editor.connection.vendor == "mysql" else
           "CREATE UNIQUE INDEX uq_auth_user_email_chuan ON auth_user (email)")
    with schema_editor.connection.cursor() as cur:
        cur.execute(sql)


def bo_unique(apps, schema_editor):
    sql = ("ALTER TABLE auth_user DROP KEY uq_auth_user_email_chuan"
           if schema_editor.connection.vendor == "mysql" else
           "DROP INDEX uq_auth_user_email_chuan")
    with schema_editor.connection.cursor() as cur:
        cur.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(don_user_trung, migrations.RunPython.noop),
        migrations.RunPython(them_unique, bo_unique),
    ]
