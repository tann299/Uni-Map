# Cấu hình URL cho dự án config.
# Danh sách `urlpatterns` định tuyến các URL tới các view. Để biết thêm thông tin, vui lòng xem:
# https://docs.djangoproject.com/en/5.2/topics/http/urls/
# Ví dụ:
# Các view dạng hàm
# 1. Thêm một import: from my_app import views
# 2. Thêm một URL vào urlpatterns: path('', views.home, name='home')
# Các view dạng lớp
# 1. Thêm một import: from other_app.views import Home
# 2. Thêm một URL vào urlpatterns: path('', Home.as_view(), name='home')
# Bao gồm một URLconf khác
# 1. Import hàm include(): from django.urls import include, path
# 2. Thêm một URL vào urlpatterns: path('blog/', include('blog.urls'))

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(('university.api_urls', 'api'))),
    path("accounts/", include("accounts.urls")),
    path("ho-so/", include("admissions.urls")),
    path("goi-y/", include("recommendation.urls")),
    path("", include("university.urls")),
]
