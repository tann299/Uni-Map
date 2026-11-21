# -*- coding: utf-8 -*-
"""Định tuyến Custom Admin Console (Uni Connect Management Portal)."""
from django.urls import path

from . import views

app_name = "quantri"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("du-lieu/", views.du_lieu, name="du_lieu"),
    path("cap-nhat/", views.cap_nhat, name="cap_nhat"),
    # Pipeline cào + import chạy nền (POST, chọn chu kỳ năm ở form).
    path("cap-nhat/chay/", views.cap_nhat_chay, name="cap_nhat_chay"),
    path("ai/", views.ai_view, name="ai"),
    # UC-10 — huấn luyện lại mô hình (POST, chạy nền).
    path("ai/huan-luyen/", views.ai_huan_luyen, name="ai_huan_luyen"),
    path("nguoi-dung/", views.nguoi_dung, name="nguoi_dung"),
    path("nguoi-dung/them/", views.nguoi_dung_them, name="nguoi_dung_them"),
    path("nguoi-dung/<int:user_id>/sua/", views.nguoi_dung_sua, name="nguoi_dung_sua"),
    path("nguoi-dung/<int:user_id>/xoa/", views.nguoi_dung_xoa, name="nguoi_dung_xoa"),
]