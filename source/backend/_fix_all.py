# -*- coding: utf-8 -*-
"""Sua namespace + app label sau khi tach 4 app. Chay 1 lan roi xoa."""

def rw(path, subs):
    s = open(path, encoding="utf-8").read()
    for a, b in subs:
        if a not in s:
            print("  [BO QUA - khong khop]", path, "|", a[:60])
            continue
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)
    print("fixed", path)


# --- config/settings.py: INSTALLED_APPS ---
rw("config/settings.py", [
    ("    'tracuu',\n    'accounts',\n    'admissions',\n    'web',\n",
     "    'university',\n    'accounts',\n    'admissions',\n    'recommendation',\n"),
])

# --- config/urls.py: route goc ---
rw("config/urls.py", [
    ("    path('api/', include('tracuu.urls')),\n",
     "    path('api/', include('university.api_patterns')),\n"),
    ('    path("", include("web.urls")),\n',
     '    path("", include("university.urls")),\n'),
    ('    path("ho-so/", include("admissions.urls")),\n',
     '    path("ho-so/", include("admissions.urls")),\n'
     '    path("goi-y/", include("recommendation.urls")),\n'),
])

# --- admissions/urls.py: bo route goi y (da chuyen sang recommendation) ---
rw("admissions/urls.py", [
    ('    # UC-05 / UC-06 / UC-08\n'
     '    path("goi-y/<int:pk>/", views.xem_goi_y, name="xem_goi_y"),\n'
     '    path("lich-su/<int:pk>/", views.lich_su_goi_y, name="lich_su_goi_y"),\n'
     '    path("lich-su/<int:pk>/xoa/", views.xoa_lich_su, name="xoa_lich_su"),\n'
     '    path("goi-y/chi-tiet/<int:kq_id>/", views.chi_tiet_goi_y, name="chi_tiet_goi_y"),\n',
     ""),
])

# --- admissions templates: doi namespace ---
rw("admissions/templates/admissions/ho_so_detail.html", [
    ("url 'admissions:xem_goi_y'", "url 'recommendation:xem_goi_y'"),
    ("url 'admissions:lich_su_goi_y'", "url 'recommendation:lich_su_goi_y'"),
])

# --- university templates: doi namespace web: -> university: ---
for f in ("trang_chu.html", "tra_cuu.html", "danh_sach_truong.html",
          "chi_tiet_truong.html"):
    rw("university/templates/university/" + f, [("url 'web:", "url 'university:")])

# --- base.html ---
rw("templates/base.html", [
    ("url 'web:trang_chu'", "url 'university:trang_chu'"),
    ("url 'web:tra_cuu'", "url 'university:tra_cuu'"),
    ("url 'web:danh_sach_truong'", "url 'university:danh_sach_truong'"),
    ("{% url 'recommendation:danh_sach_ho_so' %}", "{% url 'admissions:danh_sach_ho_so' %}"),
])

# --- accounts templates ---
for f in ("dang_nhap.html", "dang_ky.html"):
    rw("accounts/templates/accounts/" + f, [("url 'web:", "url 'university:")])

# --- recommendation: CN-01 gio nam o university.services ---
rw("recommendation/services.py", [
    ("        from university.models import Mon, ToHop\n", ""),
    ("    from university.models import Mon, ToHop\n", ""),
])
rw("recommendation/views.py", [
    ("from admissions.services import tinh_to_hop_tu_db",
     "from university.services import tinh_to_hop_tu_db"),
])
rw("recommendation/tests.py", [
    ("from recommendation.services import chon_can_ban, giai_thich, phan_tang, tinh_to_hop",
     "from recommendation.services import chon_can_ban, giai_thich, phan_tang\n"
     "from university.services import tinh_to_hop"),
])
# recommendation/services.py: giu lai wrapper tinh_to_hop_tu_db cho tien
rw("recommendation/services.py", [
    ("from __future__ import annotations",
     "from __future__ import annotations\n\n"
     "from university.services import tinh_to_hop_tu_db  # dung lai CN-01 cua university"),
])