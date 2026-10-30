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


def truy_van_theo_email(email: str | None, exclude_pk=None):
    """QuerySet `auth_user` khớp email — thử CẢ dạng chuẩn hoá lẫn dạng gõ tay.

    PHẢI truyền email GỐC (chưa chuẩn hoá) để sinh được cả hai dạng. DB cũ
    (trước migration 0002) còn email dạng gõ tay (`an.nguyen@gmail.com`), còn
    dạng chuẩn hoá là `annguyen@gmail.com` — so iexact một dạng là sót. Khi DB
    đã chuẩn hoá hết, hai dạng trùng nhau, query vẫn đúng.
    """
    from django.contrib.auth.models import User
    from django.db.models import Q

    goc = (email or "").strip().lower()
    cac_dang = {chuan_hoa_email(email), goc} - {""}
    if not cac_dang:
        return User.objects.none()
    q = Q()
    for dang in cac_dang:
        q |= Q(email__iexact=dang)
    qs = User.objects.filter(q)
    return qs.exclude(pk=exclude_pk) if exclude_pk else qs


def tim_theo_email(email: str | None, exclude_pk=None):
    """Tìm USER theo email, coi TRÙNG là bất kỳ dạng alias nào của cùng hộp thư.

    Bước 1: so chuỗi 2 dạng (index, nhanh) — đủ khi DB đã chuẩn hoá.
    Bước 2 (lưới an toàn cho DB chưa chạy migration 0002): nếu input là Gmail
    mà bước 1 hụt thì tải các user Gmail về so SẴN DẠNG CHUẨN HOÁ trong Python
    — email gõ tay `an.nguyen@...` trong DB vẫn bắt được, từ đó KHÔNG bao giờ
    tạo thêm record cho một Gmail đã có. Số user Gmail có giới hạn, mỗi lần
    login chỉ duyệt 1 lượt nhỏ.

    Trả về `user | None`.
    """
    if not (email or "").strip():
        return None

    user = truy_van_theo_email(email, exclude_pk=exclude_pk).first()
    if user is not None:
        return user

    chuan = chuan_hoa_email(email)
    if not chuan.endswith("@gmail.com"):   # lưới an toàn chỉ cho Gmail/Googlemail
        return None
    from django.contrib.auth.models import User
    from django.db.models import Q

    # KHÔNG thoát sớm khi input đã là dạng chuẩn: DB có thể đang chứa dạng
    # CHƯA chuẩn của cùng hộp thư (`an.nguyen@gmail.com`) — chính case cần bắt.
    qs = User.objects.filter(
        Q(email__iendswith="@gmail.com") | Q(email__iendswith="@googlemail.com"))
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    for u in qs.only("id", "email"):
        if chuan_hoa_email(u.email) == chuan:
            return u
    return None
