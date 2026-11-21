from django.urls import path

from . import views

app_name = "admissions"

urlpatterns = [
    path("", views.danh_sach_ho_so, name="danh_sach_ho_so"),
    path("tao/", views.tao_ho_so, name="tao_ho_so"),
    path("chi-tiet/<int:pk>/", views.chi_tiet_ho_so, name="chi_tiet_ho_so"),
    path("sua/<int:pk>/", views.sua_ho_so, name="sua_ho_so"),
    path("xoa/<int:pk>/", views.xoa_ho_so, name="xoa_ho_so"),

]