from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.trang_chu, name="trang_chu"),
    path("tra-cuu/", views.tra_cuu, name="tra_cuu"),
]