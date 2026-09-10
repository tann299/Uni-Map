from django.urls import path

from . import views

app_name = "tracuu"

urlpatterns = [
    path("tra-cuu/", views.tra_cuu, name="tra_cuu"),
]
