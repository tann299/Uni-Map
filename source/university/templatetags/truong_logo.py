from pathlib import Path

from django import template
from django.templatetags.static import static

register = template.Library()

# Thư mục logo thật: university/static/university/logos/<ma_truong>.png
# Đặt file tên đúng mã trường (vd BKA.png) là web tự ưu tiên hiển thị ảnh,
# không có file thì trả None -> template dùng monogram SVG tự sinh.
_LOGO_ROOT = Path(__file__).resolve().parent.parent / "static" / "university" / "logos"
_DUOI = (".png", ".jpg", ".jpeg", ".svg", ".webp")


@register.simple_tag
def logo_truong(ma_truong: str):
    """Trả URL logo thật nếu có file, ngược lại None."""
    if not ma_truong:
        return None
    ma = ma_truong.strip().upper()
    for duoi in _DUOI:
        if (_LOGO_ROOT / f"{ma}{duoi}").exists():
            return static(f"university/logos/{ma}{duoi}")
    return None
