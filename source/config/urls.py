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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('quan-tri/', include('quantri.urls')),
    path('api/', include(('university.api_urls', 'api'))),
    path("accounts/", include("accounts.urls")),
    path("ho-so/", include("admissions.urls")),
    path("goi-y/", include("recommendation.urls")),
    path("", include("university.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

# /media/ (avatar) và /static/ PHẢI phục vụ được cả khi DEBUG=0 trên host thật.
# `static()` là no-op khi DEBUG=0 nên không dùng được ở đây; `serve` chạy được
# mọi lúc. Trên host có nginx/Apache thì web server phục vụ /media/ trước và
# Django không bao giờ nhận request đó — route dưới chỉ là lưới an toàn cho
# trường hợp web server không cấu hình location /media/.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
]
