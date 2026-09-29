# -*- coding: utf-8 -*-
"""
Đăng nhập / đăng ký bằng Google (OAuth 2.0 Authorization Code).

Không dùng django-allauth: chỉ một nút bấm nên luồng chuẩn 3 endpoint của Google
gọn hơn nhiều so với thêm app + migrate + SocialApp qua admin.
Lần đầu một Gmail đăng nhập -> tạo User luôn (username = email), không cần
mật khẩu (set_unusable_password) vì Google đã xác thực chủ email.
"""
import hashlib
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
TIMEOUT = 10


def _redirect_uri(request):
    # Phải khớp từng ký tự với Authorized redirect URI khai trên Google Console.
    return request.build_absolute_uri(reverse("accounts:google_callback"))


def _ve_dang_nhap(request, thong_bao):
    messages.error(request, thong_bao)
    return redirect("accounts:dang_nhap")


def google_login(request):
    if request.user.is_authenticated:
        return redirect("university:trang_chu")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return _ve_dang_nhap(
            request, "Chưa cấu hình đăng nhập Google (thiếu GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET).")

    state = secrets.token_urlsafe(32)
    request.session["google_state"] = state
    next_url = request.GET.get("next")
    if next_url:
        request.session["google_next"] = next_url

    return redirect(AUTH_URL + "?" + urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }))


def google_callback(request):
    state = request.session.pop("google_state", None)
    next_url = request.session.pop("google_next", None)

    if request.GET.get("error"):
        return _ve_dang_nhap(request, "Bạn đã huỷ đăng nhập Google.")
    # state dùng một lần: chặn kẻ khác mớm code lạ vào callback.
    if not state or request.GET.get("state") != state:
        return _ve_dang_nhap(request, "Phiên đăng nhập Google không hợp lệ, vui lòng thử lại.")
    code = request.GET.get("code")
    if not code:
        return _ve_dang_nhap(request, "Google không trả về mã xác thực.")

    try:
        r = requests.post(TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": _redirect_uri(request),
            "grant_type": "authorization_code",
        }, timeout=TIMEOUT)
        r.raise_for_status()
        access_token = r.json()["access_token"]

        r = requests.get(USERINFO_URL,
                         headers={"Authorization": f"Bearer {access_token}"},
                         timeout=TIMEOUT)
        r.raise_for_status()
        info = r.json()
    except (requests.RequestException, KeyError, ValueError):
        return _ve_dang_nhap(request, "Không kết nối được tới Google, vui lòng thử lại sau.")

    email = (info.get("email") or "").strip().lower()
    if not email or not info.get("email_verified"):
        return _ve_dang_nhap(request, "Tài khoản Google chưa xác thực email.")

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User(username=_username_tu_email(email),
                    email=email,
                    first_name=(info.get("given_name") or "")[:150],
                    last_name=(info.get("family_name") or "")[:150])
        user.set_unusable_password()
        user.save()

    login(request, user)
    messages.success(request, f"Đăng nhập thành công! Chào mừng {user.first_name or user.email} đến với Uni Map.")

    if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    if user.is_staff:
        return redirect("quantri:dashboard")
    return redirect("university:trang_chu")


def _username_tu_email(email):
    """Sinh username chưa tồn tại — auth_user.username là UNIQUE, tối đa 150 ký tự.

    Trùng xảy ra khi email quá dài bị cắt, hoặc khi tên đăng nhập gõ tay trùng
    chuỗi email. Thêm hậu tố băm (hashlib, ổn định giữa các tiến trình) rồi tăng dần.
    """
    goc = email if len(email) <= 150 else f"{email[:137]}~{hashlib.md5(email.encode()).hexdigest()[:8]}"
    ten, i = goc, 1
    while User.objects.filter(username=ten).exists():
        i += 1
        duoi = f"-{i}"
        ten = goc[:150 - len(duoi)] + duoi
    return ten
