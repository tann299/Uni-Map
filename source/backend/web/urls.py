from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.trang_chu, name="trang_chu"),
    path("tra-cuu/", views.tra_cuu, name="tra_cuu"),
    path("truong/", views.danh_sach_truong, name="danh_sach_truong"),
    path("truong/<str:ma_truong>/", views.chi_tiet_truong, name="chi_tiet_truong"),
]