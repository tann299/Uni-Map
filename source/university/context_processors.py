# -*- coding: utf-8 -*-
"""Biến template dùng chung: khoảng năm của cửa sổ trượt (CN-05).

Cửa sổ đổi được (2016–2025 -> 2020–2025 -> 2022–2026) mà KHÔNG sửa template,
nên mọi chỗ hiện "Dữ liệu 20xx–20xx" phải đọc từ `cua_so_nam` chứ không viết cứng.
"""
from __future__ import annotations


def cua_so_nam(request):
    """`cua_so_text` = '2016–2025', `so_nam_cua_so` = 10 (theo `cua_so_nam`).

    Bọc try/except: bảng `cua_so_nam` là managed=False nên không tồn tại trong
    DB test — lỗi ở đây sẽ làm chết MỌI trang render, kể cả trang đăng nhập.
    """
    try:
        from .models import CuaSoNam, Truong

        ds = list(CuaSoNam.objects.all())
        so_truong = Truong.objects.count()
    except Exception:  # noqa: BLE001 — thiếu bảng/DB chưa migrate
        return {"cua_so_text": "", "so_nam_cua_so": 0, "so_truong": 0}
    if not ds:
        return {"cua_so_text": "", "so_nam_cua_so": 0, "so_truong": so_truong}
    return {
        "cua_so_text": f"{ds[0].nam}–{ds[-1].nam}",
        "so_nam_cua_so": len(ds),
        # Số trường đổi theo cửa sổ (trường chỉ có dữ liệu cũ tự rơi ra), nên
        # footer cũng phải đọc từ DB chứ không viết cứng "288 trường".
        "so_truong": so_truong,
    }
