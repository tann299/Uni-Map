from django.urls import path

from . import views

app_name = "recommendation"

urlpatterns = [
    # UC-05 — nhận gợi ý (pk = hồ sơ năng lực)
    path("goi-y/<int:pk>/", views.xem_goi_y, name="xem_goi_y"),
    # UC-06 — xem lời giải thích (kq_id = 1 dòng ket_qua_goi_y)
    path("chi-tiet/<int:kq_id>/", views.chi_tiet_goi_y, name="chi_tiet_goi_y"),
    # UC-07 — so sánh nguyện vọng
    path("so-sanh/<int:pk>/", views.so_sanh, name="so_sanh"),
    # UC-08 — lịch sử gợi ý
    path("lich-su/<int:pk>/", views.lich_su_goi_y, name="lich_su_goi_y"),
    path("lich-su/<int:pk>/xoa/", views.xoa_lich_su, name="xoa_lich_su"),
]