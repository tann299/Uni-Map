# -*- coding: utf-8 -*-
"""Định tuyến Custom Admin Console (Uni Map Management Portal)."""
from django.urls import path

from . import views

app_name = "quantri"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("du-lieu/", views.du_lieu, name="du_lieu"),
    path("cap-nhat/", views.cap_nhat, name="cap_nhat"),
    path("ai/", views.ai_view, name="ai"),
    path("nguoi-dung/", views.nguoi_dung, name="nguoi_dung"),
]