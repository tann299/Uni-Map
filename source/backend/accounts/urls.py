from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("dang-ky/", views.dang_ky, name="dang_ky"),
    path("dang-nhap/", views.dang_nhap, name="dang_nhap"),
    path("dang-xuat/", views.dang_xuat, name="dang_xuat"),
]
