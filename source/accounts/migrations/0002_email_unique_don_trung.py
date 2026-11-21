# -*- coding: utf-8 -*-
"""Chặn tràn user trùng email ở tầng DB.

Bài toán: auth_user.email vốn không UNIQUE. Gmail coi `an.nguyen+uni@`,
`an.nguyen@`, `annguyen@gmail.com` là CÙNG hộp thư, nên trước khi có chuẩn hoá
alias, mỗi lần đăng nhập Google bằng dạng alias khác đã tạo một user mới
(username `-2`, `-3`...). Dữ liệu cũ cũng có thể có trùng từ form đăng ký
thường trước khi có DangKyForm.

Migration làm 2 việc:
 1. Dọn dữ liệu cũ: chuẩn hoá email rồi xoá user trùng (không phân biệt hoa/
    thường), giữ user CŨ NHẤT. Profile/ho_so_nang_luc/... xoá theo (CASCADE).
 2. Thêm cột generated `email_duy_nhat` + UNIQUE trên cột đó để từ nay DB tự
    chặn, kể cả race condition hai request OAuth song song.

VÌ SAO KHÔNG UNIQUE TRỰC TIẾP TRÊN `email`:
User.email blank=True nên admin/QRHTT để trống được -> nhiều user có
`email = ''`. MySQL unique cho `''` là 1 dòng duy nhất, ALTER đầu tiên chạy
thật đã báo `#1062 - Duplicate entry '' for key`. Cột generated
`NULLIF(LOWER(TRIM(email)), '')` đổi rỗng thành NULL, MySQL bỏ qua NULL khi
check UNIQUE -> không email thì thoải mái, có email thì bắt trùng.

Chú ý: unique áp trên chuỗi đã LOWER+TRIM; alias Gmail (bỏ '.', '+tag') không
làm được ở SQL nên chặn ở tầng app (accounts/gmail.py) — app chuẩn hoá input
trước, DB chặn race cuối.

Dùng RunPython + schema_editor.connection.vendor thay RunSQL vì test chạy
sqlite (config không cố định DB), còn production là MySQL. Mọi bước idempotent
(quét cột/index đã có) để chạy lại sau khi đã ALTER tay trong phpMyAdmin không
bị Duplicate column/key name.
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
    """Tạo UNIQUE trên cột generated `email_duy_nhat`.

    Không unique thẳng trên `email` được vì User.email blank=True: nhiều user
    có `email = ''` -> `Duplicate entry '' for key ...` ngay khi ALTER. Cột
    generated `NULLIF(LOWER(TRIM(email)), '')` đổi rỗng thành NULL, và MySQL
    bỏ qua NULL khi check UNIQUE -> nhiều user không email vẫn chấp nhận,
    còn email thật thì unique (đã lowercase + trim). Alias Gmail (bỏ '.'/+tag)
    không làm được trong SQL -> chặn ở tầng app (gmail.chuan_hoa_email).
    """
    mysql = schema_editor.connection.vendor == "mysql"
    with schema_editor.connection.cursor() as cur:
        if not _co_cot(cur, "email_duy_nhat", mysql):
            cur.execute(
                f"ALTER TABLE auth_user ADD COLUMN email_duy_nhat "
                f"{'VARCHAR(254)' if mysql else 'TEXT'} "
                f"GENERATED ALWAYS AS (NULLIF(LOWER(TRIM(email)), '')) STORED")
        if not _co_index(cur, "uq_auth_user_email_chuan", mysql):
            cur.execute(
                "ALTER TABLE auth_user ADD UNIQUE KEY "
                "uq_auth_user_email_chuan (email_duy_nhat)" if mysql else
                "CREATE UNIQUE INDEX uq_auth_user_email_chuan "
                "ON auth_user (email_duy_nhat)")


def bo_unique(apps, schema_editor):
    """Reverse: bỏ index rồi bỏ cột generated (không đụng cột email thật)."""
    mysql = schema_editor.connection.vendor == "mysql"
    with schema_editor.connection.cursor() as cur:
        if _co_index(cur, "uq_auth_user_email_chuan", mysql):
            cur.execute("ALTER TABLE auth_user DROP KEY uq_auth_user_email_chuan"
                        if mysql else
                        "DROP INDEX uq_auth_user_email_chuan")
        if _co_cot(cur, "email_duy_nhat", mysql):
            cur.execute("ALTER TABLE auth_user DROP COLUMN email_duy_nhat")


def _co_cot(cur, ten, mysql):
    """Cột đã tồn tại chưa — ALTER chạy lại sẽ báo Duplicate column name.

    Vendor truyền vào vì `cursor.connection` là DB-API connection (sqlite3/
    MySQLdb) chứ không phải connection wrapper của Django: không có `.vendor`.
    """
    if mysql:
        cur.execute("SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'auth_user' AND COLUMN_NAME = %s", [ten])
        return cur.fetchone()[0] > 0
    cur.execute("PRAGMA table_info(auth_user)")
    return any(r[1] == ten for r in cur.fetchall())


def _co_index(cur, ten, mysql):
    """Index đã tồn tại chưa — ADD lại báo Duplicate key name."""
    if mysql:
        cur.execute("SELECT COUNT(*) FROM information_schema.STATISTICS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'auth_user' AND INDEX_NAME = %s", [ten])
        return cur.fetchone()[0] > 0
    cur.execute("PRAGMA index_list(auth_user)")
    return any(r[1] == ten for r in cur.fetchall())


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(don_user_trung, migrations.RunPython.noop),
        migrations.RunPython(them_unique, bo_unique),
    ]
