from django.urls import path
from . import views, views_oauth

app_name = "accounts"

urlpatterns = [
    path("dang-ky/", views.dang_ky, name="dang_ky"),
    path("dang-nhap/", views.dang_nhap, name="dang_nhap"),
    path("dang-xuat/", views.dang_xuat, name="dang_xuat"),
    path("tai-khoan/", views.tai_khoan, name="tai_khoan"),
    path("google/dang-nhap/", views_oauth.google_login, name="google_login"),
    path("google/xac-thuc/", views_oauth.google_callback, name="google_callback"),
    path("facebook/dang-nhap/", views_oauth.facebook_login, name="facebook_login"),
    path("facebook/xac-thuc/", views_oauth.facebook_callback, name="facebook_callback"),
]
