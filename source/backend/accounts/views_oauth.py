# -*- coding: utf-8 -*-
"""Đăng nhập / đăng ký bằng OAuth 2.0 (Google & Facebook).

Cùng luồng Authorization Code chuẩn:
  1. Redirect sang trang cấp quyền của bên thứ 3 (kèm CSRF state dùng 1 lần)
  2. Bên thứ 3 redirect về callback kèm code
  3. Server đổi code lấy access token -> lấy thông tin người dùng (email, họ tên)
  4. Tìm hoặc tạo Django User (không cần mật khẩu) -> login()
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

TIMEOUT = 10

# Endpoint Google OAuth 2.0
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Endpoint Facebook Graph API v21.0
FB_AUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/v21.0/oauth/access_token"
FB_USERINFO_URL = "https://graph.facebook.com/v21.0/me"
FB_FIELDS = "id,name,email"


def _ve_dang_nhap(request, thong_bao: str):
    messages.error(request, thong_bao)
    return redirect("accounts:dang_nhap")


def _username_tu_email(email: str) -> str:
    """Sinh username duy nhất từ email (auth_user.username là UNIQUE, max 150 ký tự)."""
    goc = email if len(email) <= 150 else f"{email[:137]}~{hashlib.md5(email.encode()).hexdigest()[:8]}"
    ten, i = goc, 1
    while User.objects.filter(username=ten).exists():
        i += 1
        duoi = f"-{i}"
        ten = goc[:150 - len(duoi)] + duoi
    return ten


def _dang_nhap_user(request, email: str, first_name: str = "", last_name: str = ""):
    """Tìm hoặc tạo User dựa trên email đã xác thực rồi đăng nhập."""
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User(
            username=_username_tu_email(email),
            email=email,
            first_name=first_name[:150],
            last_name=last_name[:150],
        )
        user.set_unusable_password()
        user.save()

    login(request, user)
    chao = user.first_name or user.email
    messages.success(request, f"Đăng nhập thành công! Chào mừng {chao} đến với Uni Map.")

    next_url = request.session.pop("oauth_next", None)
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    if user.is_staff:
        return redirect("quantri:dashboard")
    return redirect("university:trang_chu")


# ==================== GOOGLE ====================


def google_login(request):
    if request.user.is_authenticated:
        return redirect("university:trang_chu")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return _ve_dang_nhap(
            request, "Chưa cấu hình đăng nhập Google (thiếu GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET)."
        )

    state = secrets.token_urlsafe(32)
    request.session["google_state"] = state
    next_url = request.GET.get("next")
    if next_url:
        request.session["oauth_next"] = next_url

    redirect_uri = request.build_absolute_uri(reverse("accounts:google_callback"))
    return redirect(
        GOOGLE_AUTH_URL
        + "?"
        + urlencode({
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        })
    )


def google_callback(request):
    state = request.session.pop("google_state", None)
    if request.GET.get("error"):
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Bạn đã huỷ đăng nhập Google.")
    if not state or request.GET.get("state") != state:
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Phiên đăng nhập Google không hợp lệ, vui lòng thử lại.")
    code = request.GET.get("code")
    if not code:
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Google không trả về mã xác thực.")

    redirect_uri = request.build_absolute_uri(reverse("accounts:google_callback"))
    try:
        r = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        token = r.json()["access_token"]

        r = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        info = r.json()
    except (requests.RequestException, KeyError, ValueError):
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Không kết nối được tới Google, vui lòng thử lại sau.")

    email = (info.get("email") or "").strip().lower()
    if not email or not info.get("email_verified"):
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Tài khoản Google chưa xác thực email.")

    return _dang_nhap_user(
        request,
        email=email,
        first_name=info.get("given_name") or "",
        last_name=info.get("family_name") or "",
    )


# ==================== FACEBOOK ====================


def facebook_login(request):
    if request.user.is_authenticated:
        return redirect("university:trang_chu")
    if not settings.FACEBOOK_APP_ID or not settings.FACEBOOK_APP_SECRET:
        return _ve_dang_nhap(
            request, "Chưa cấu hình đăng nhập Facebook (thiếu FACEBOOK_APP_ID / FACEBOOK_APP_SECRET)."
        )

    state = secrets.token_urlsafe(32)
    request.session["facebook_state"] = state
    next_url = request.GET.get("next")
    if next_url:
        request.session["oauth_next"] = next_url

    redirect_uri = request.build_absolute_uri(reverse("accounts:facebook_callback"))
    return redirect(
        FB_AUTH_URL
        + "?"
        + urlencode({
            "client_id": settings.FACEBOOK_APP_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "email,public_profile",
            "state": state,
        })
    )


def facebook_callback(request):
    state = request.session.pop("facebook_state", None)
    if request.GET.get("error"):
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Bạn đã huỷ đăng nhập Facebook.")
    if not state or request.GET.get("state") != state:
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Phiên đăng nhập Facebook không hợp lệ, vui lòng thử lại.")
    code = request.GET.get("code")
    if not code:
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Facebook không trả về mã xác thực.")

    redirect_uri = request.build_absolute_uri(reverse("accounts:facebook_callback"))
    try:
        r = requests.get(
            FB_TOKEN_URL,
            params={
                "code": code,
                "client_id": settings.FACEBOOK_APP_ID,
                "client_secret": settings.FACEBOOK_APP_SECRET,
                "redirect_uri": redirect_uri,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        token = r.json()["access_token"]

        r = requests.get(
            FB_USERINFO_URL,
            params={"fields": FB_FIELDS, "access_token": token},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        info = r.json()
    except (requests.RequestException, KeyError, ValueError):
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(request, "Không kết nối được tới Facebook, vui lòng thử lại sau.")

    email = (info.get("email") or "").strip().lower()
    if not email:
        request.session.pop("oauth_next", None)
        return _ve_dang_nhap(
            request,
            "Tài khoản Facebook không có email hoặc bạn chưa đồng ý chia sẻ email. "
            "Hãy dùng cách đăng nhập khác.",
        )

    return _dang_nhap_user(
        request,
        email=email,
        first_name=info.get("name") or "",
        last_name="",
    )
