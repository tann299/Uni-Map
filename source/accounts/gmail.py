# -*- coding: utf-8 -*-
"""Chuẩn hoá Gmail: chống tràn user trùng qua alias Gmail.

Gmail bỏ qua dấu chấm trong phần local và mọi chuỗi sau '+' (alias). Tức là
`an.nguyen+uni@gmail.com`, `annguyen@gmail.com`, `an.nguyen@gmail.com` đều là
CÙNG MỘT HỘP THƯ. Không chuẩn hoá thì mỗi lần đăng nhập Google bằng alias khác
nhau, `_dang_nhap_user` không tìm thấy user theo email chuỗi -> tạo user mới
với username `...-2`, `-3`... (hàm `_username_tu_email`) — tràn DB mà code nhìn
vào "đã có kiểm tra trùng email".

Chỉ áp dụng cho gmail.com / googlemail.com. Email ngoài Gmail giữ nguyên vì
không có quy tắc alias. Chuẩn hoá dạng chuỗi (lowercase + bỏ chấm/+tag) chứ
không đổi hộp thư thật, nên vẫn gửi được mail bình thường.
"""
from __future__ import annotations

import re

# gmail.com và googlemail.com là cùng một dịch vụ (Google sở hữu cả hai).
_GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}
_XOA_O = re.compile(r"\.|\+.*$")


def chuan_hoa_email(email: str | None) -> str:
    """Trả email dạng chuẩn để so khớp: lowercase, Gmail bỏ '.' và '+tag'."""
    if not email:
        return ""
    email = email.strip().lower()
    local, _, domain = email.partition("@")
    if not local or not domain:
        return email
    if domain in _GMAIL_DOMAINS:
        local = _XOA_O.sub("", local)
        domain = "gmail.com"
    return f"{local}@{domain}"
