# -*- coding: utf-8 -*-
"""Rate limit dùng chung — cửa sổ cố định (fixed window) trên Django cache.

Vì sao cần: web có đăng nhập/đăng ký công khai và endpoint chạy ML. Không giới
hạn thì:
  * brute-force mật khẩu (đã chặn riêng ở accounts.views.dang_nhap),
  * bot tạo hàng loạt tài khoản (mỗi user tốn 1 lần hash mật khẩu ~100ms CPU),
  * F5 liên tục trang gợi ý = mỗi lần chạy predict_proba cả lô + ghi 2 bảng.

CÁCH ĐẾM: `cache.add()` là bước "tạo key nếu chưa có" (atomic ở backend có hỗ
trợ), sau đó `cache.incr()`. Bộ đếm tự hết hạn sau `cua_so` giây nên không cần
job dọn dẹp.

LƯU Ý BACKEND: phải dùng cache CHIA SẺ giữa các process (FileBasedCache /
DatabaseCache / Redis). `LocMemCache` là RAM riêng từng process — Passenger
chạy nhiều process thì mỗi process đếm riêng, giới hạn thành vô nghĩa.
"""
from __future__ import annotations

from django.core.cache import cache


def ip_khach(request) -> str:
    """IP khách, ưu tiên header proxy (hosting shared luôn đứng sau proxy)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (xff.split(",")[0].strip() if xff
            else request.META.get("REMOTE_ADDR", "")) or "unknown"


def khoa_theo_ip(request, ten: str) -> str:
    """Khoá cache theo IP — dùng cho khách chưa đăng nhập."""
    return f"rl:{ten}:ip:{ip_khach(request)}"


def khoa_theo_user(request, ten: str) -> str:
    """Khoá cache theo user đã đăng nhập (rơi về IP nếu chưa có user)."""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return f"rl:{ten}:u:{user.pk}"
    return khoa_theo_ip(request, ten)


def vuot_gioi_han(khoa: str, gioi_han: int, cua_so: int) -> bool:
    """Tăng bộ đếm của `khoa`, trả True nếu đã VƯỢT `gioi_han` lần trong `cua_so` giây.

    Gọi hàm này ở MỖI request cần đếm (kể cả request bị chặn) để bộ đếm tiếp tục
    tăng và người dùng không "thoát" giới hạn bằng cách chờ vài giây.
    """
    if cache.add(khoa, 1, cua_so):
        return False                      # lần đầu trong cửa sổ
    try:
        so_lan = cache.incr(khoa)
    except ValueError:
        # Key vừa hết hạn giữa add và incr -> coi như lần đầu của cửa sổ mới.
        cache.set(khoa, 1, cua_so)
        return False
    return so_lan > gioi_han
