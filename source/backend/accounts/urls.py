from django.urls import path
from . import views, views_google

app_name = "accounts"

urlpatterns = [
    path("dang-ky/", views.dang_ky, name="dang_ky"),
    path("dang-nhap/", views.dang_nhap, name="dang_nhap"),
    path("dang-xuat/", views.dang_xuat, name="dang_xuat"),
    path("tai-khoan/", views.tai_khoan, name="tai_khoan"),
    path("google/dang-nhap/", views_google.google_login, name="google_login"),
    path("google/xac-thuc/", views_google.google_callback, name="google_callback"),
]
