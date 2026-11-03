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

from django.conf import settings
from django.core.cache import cache

# Dải IP được coi là proxy tin cậy (LiteSpeed/Apache của hosting chạy cùng máy
# hoặc trong mạng nội bộ). CHỈ khi request đến từ các IP này mới đọc
# X-Forwarded-For; ngược lại client tự đặt header đó để lách rate limit.
_DAI_PROXY = ("127.", "::1", "10.", "192.168.", "172.16.", "172.17.", "172.18.",
              "172.19.", "172.2", "172.30.", "172.31.")


def _la_proxy(ip: str) -> bool:
    return any(ip.startswith(d) for d in _DAI_PROXY)


def ip_khach(request) -> str:
    """IP khách — chỉ tin X-Forwarded-For khi request đến từ proxy tin cậy.

    Trước đây đọc XFF vô điều kiện: kẻ tấn công gửi `X-Forwarded-For: <ngẫu
    nhiên>` mỗi request là mỗi lần một khoá cache mới -> lách sạch rate limit
    (đã kiểm chứng trên host: 3 request -> 3 khoá khác nhau). Giờ:
      * request từ loopback/nội bộ (proxy thật) -> lấy IP thật trong XFF
      * request từ ngoài -> dùng REMOTE_ADDR (client không giả được)
    Có thể ép qua settings.RATE_LIMIT_TIN_XFF nếu hosting có proxy IP công khai.
    """
    remote = request.META.get("REMOTE_ADDR", "") or "unknown"
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    tin_xff = getattr(settings, "RATE_LIMIT_TIN_XFF", None)
    if xff and (tin_xff is True or (tin_xff is None and _la_proxy(remote))):
        return xff.split(",")[0].strip() or remote
    return remote


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
