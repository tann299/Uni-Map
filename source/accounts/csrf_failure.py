"""View hiển thị khi CSRF token sai/hết hạn.

Mặc định Django trả trang 403 khô khan hoặc (khi DEBUG=1) trang vàng lộ chi tiết
request. Hàm này trả trang 403_csrf.html tự viết — thân thiện, không lộ thông tin,
và luôn dùng được kể cả khi session/context processor gặp sự cố.
"""
from django.shortcuts import render


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", status=403)
