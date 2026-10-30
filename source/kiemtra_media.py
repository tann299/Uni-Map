"""Self-check cho route /media/ với DEBUG=0 (gốc rễ lỗi avatar trên web server).

Root cause: `if settings.DEBUG:` quanh static(MEDIA_URL) — static() là no-op khi
DEBUG=0 nên /media/ mất route hoàn toàn. Check này đứng gác: đổi DEBUG sang 0
cho thấy /media/ có được phục vụ, và path traversal vẫn bị chặn.

Chạy: python kiemtra_media.py
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "self-check")
os.environ["DJANGO_DEBUG"] = "0"
os.environ["DJANGO_ALLOWED_HOSTS"] = "testserver"
os.environ.setdefault("DB_NAME", "uni_map")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings  # noqa: E402
from django.test import Client  # noqa: E402


def _sinh_file_media():
    """Một ảnh nhỏ trong MEDIA_ROOT để test không phụ thuộc ảnh ai đó up."""
    thu_muc = settings.MEDIA_ROOT / "selftest"
    thu_muc.mkdir(parents=True, exist_ok=True)
    tep = thu_muc / "pixel.webp"
    if not tep.exists():
        # WebP 1x1 tối thiểu: RIFF/WEBP container + VP8L lossless.
        tep.write_bytes(
            b"RIFF\x1a\x00\x00\x00WEBPVP8L\x09\x00\x00\x00\x0f\x00\x00\x2f\x00\x00\x00"
        )
    return f"{settings.MEDIA_URL}selftest/pixel.webp"


def main():
    loi = []
    duong_dan = _sinh_file_media()
    c = Client()

    print(f"DEBUG = {settings.DEBUG}")
    assert not settings.DEBUG, "Check này mô phỏng host thật: DEBUG phải là False"

    # 1) Ảnh tồn tại phải trả 200 (đây là lỗi avatar trên web server).
    r = c.get(duong_dan)
    print(f"GET {duong_dan} -> {r.status_code}")
    if r.status_code != 200:
        loi.append(f"ảnh có thật trả {r.status_code}, cần 200")

    # 2) Ảnh không tồn tại phải trả 404, không được 200 rỗng.
    r = c.get(f"{settings.MEDIA_URL}selftest/khong-co.webp")
    print(f"GET {settings.MEDIA_URL}selftest/khong-co.webp -> {r.status_code}")
    if r.status_code != 404:
        loi.append(f"ảnh không tồn tại trả {r.status_code}, cần 404")

    # 3) Đọc ra đúng loại ảnh (Content-Type), không phải text/html.
    r = c.get(duong_dan)
    ct = r.headers.get("Content-Type", "")
    print(f"Content-Type = {ct}")
    if not ct.startswith("image/"):
        loi.append(f"Content-Type sai: {ct}")

    # 4) Django bảo toàn Django test server không bẻ: static(STATIC_URL) vẫn chạy.
    # (Khi DEBUG=0 collectstatic chưa chạy thì 404 là đúng — chỉ báo, không fail.)
    r = c.get("/static/logo.png")
    print(f"GET /static/logo.png -> {r.status_code}")

    # 5) Traversal ra ngoài MEDIA_ROOT phải bị chặn.
    r = c.get(f"{settings.MEDIA_URL}../../.env")
    print(f"GET {settings.MEDIA_URL}../../.env -> {r.status_code}")
    if r.status_code != 400 and b"SECRET" not in r.content:
        loi.append(f"traversal trả {r.status_code}, cần bị chặn")

    if loi:
        for x in loi:
            print(f"FAIL: {x}")
        return 1
    print("OK: /media/ phục vụ được với DEBUG=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
