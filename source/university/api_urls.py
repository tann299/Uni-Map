"""API JSON của app university, mount dưới /api/ (SRS README)."""
from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("tra-cuu/", views.api_tra_cuu, name="tra_cuu"),
]