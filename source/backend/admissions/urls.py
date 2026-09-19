from django.urls import path

from . import views

app_name = "admissions"

urlpatterns = [
    path("", views.danh_sach_ho_so, name="danh_sach_ho_so"),
    path("tao/", views.tao_ho_so, name="tao_ho_so"),
    path("chi-tiet/<int:pk>/", views.chi_tiet_ho_so, name="chi_tiet_ho_so"),
    path("sua/<int:pk>/", views.sua_ho_so, name="sua_ho_so"),
    path("xoa/<int:pk>/", views.xoa_ho_so, name="xoa_ho_so"),

    # UC-05 / UC-06 / UC-08
    path("goi-y/<int:pk>/", views.xem_goi_y, name="xem_goi_y"),
    path("lich-su/<int:pk>/", views.lich_su_goi_y, name="lich_su_goi_y"),
    path("lich-su/<int:pk>/xoa/", views.xoa_lich_su, name="xoa_lich_su"),
    path("goi-y/chi-tiet/<int:kq_id>/", views.chi_tiet_goi_y, name="chi_tiet_goi_y"),
]