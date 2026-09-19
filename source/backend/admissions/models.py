# -*- coding: utf-8 -*-
"""
App `admissions` — hồ sơ năng lực học sinh (SRS UC-04, US-06..US-11).

Ba bảng `ho_so_nang_luc`, `diem_mon`, `nhom_nganh_quan_tam` đã khai trong
`tracuu/models.py` (mục C — D LIỆU NGƯỜI DÙNG) và `tracuu/migrations/0001_initial`.
Khai lại ở đây là hai nguồn sự thật cho cùng một bảng -> Django báo fields.E304
(reverse accessor trùng). Nên chỉ import lại; app này lo form/view/template CRUD.
"""
from tracuu.models import DiemMon, HoSoNangLuc, NhomNganhQuanTam

__all__ = ["HoSoNangLuc", "DiemMon", "NhomNganhQuanTam"]
