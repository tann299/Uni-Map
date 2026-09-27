# -*- coding: utf-8 -*-
"""
Views cho Custom Admin Console (Uni Map Management Portal).
Được thiết kế theo đúng chuẩn giao diện trong UI_unimap:
  - admin_dashboard
  - qu_n_l_d_li_u_tuy_n_sinh_uni_map_admin
  - admin_capnhatDL
  - admin_ai
  - ng_i_d_ng_nh_t_k_ki_m_to_n_uni_map_admin
"""
from functools import partial

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.shortcuts import render

from admissions.models import HoSoNangLuc
from recommendation.models import KetQuaGoiY, LanGoiY
from university.models import (CuaSoNam, DiemChuan, LanCapNhat, Nganh, ToHop,
                               Truong)

# staff_member_required mặc định hardcode login_url='admin:login' (trang admin
# Django). Ép về form đăng nhập chung accounts:dang_nhap.
staff_required = partial(staff_member_required, login_url="accounts:dang_nhap")


@staff_required
def dashboard(request):
    """Trang Dashboard tổng quan — KPI cards, Cảnh báo CN-08, Audit log."""
    so_truong = Truong.objects.count()
    so_nganh = Nganh.objects.count()
    so_to_hop = ToHop.objects.count()
    so_fact = DiemChuan.objects.count()

    cua_so = list(CuaSoNam.objects.values_list("nam", flat=True).order_by("vi_tri"))
    cua_so_str = f"{cua_so[0]}–{cua_so[-1]}" if cua_so else "2021–2025"

    so_tinh = Truong.objects.values("tinh_thanh").distinct().count()
    so_user = User.objects.count()
    so_hoso = HoSoNangLuc.objects.count()
    so_lan_goi_y = LanGoiY.objects.count()

    lan_cap_nhat_cuoi = LanCapNhat.objects.order_by("-thoi_diem").first()

    # Lịch sử hoạt động / Audit Log gần nhất
    recent_goi_y = LanGoiY.objects.select_related("ho_so__user").order_by("-thoi_diem")[:10]

    ctx = {
        "active": "dashboard",
        "so_truong": so_truong,
        "so_nganh": so_nganh,
        "so_to_hop": so_to_hop,
        "so_fact": so_fact,
        "cua_so_str": cua_so_str,
        "so_tinh": so_tinh,
        "so_user": so_user,
        "so_hoso": so_hoso,
        "so_lan_goi_y": so_lan_goi_y,
        "lan_cap_nhat_cuoi": lan_cap_nhat_cuoi,
        "recent_goi_y": recent_goi_y,
    }
    return render(request, "quantri/dashboard.html", ctx)


@staff_required
def du_lieu(request):
    """Quản lý dữ liệu tuyển sinh: Trường, Ngành, Tổ hợp."""
    tab = request.GET.get("tab", "truong")
    q = request.GET.get("q", "").strip()
    vung = request.GET.get("vung", "").strip()
    tinh = request.GET.get("tinh", "").strip()

    tinh_list = (Truong.objects.values_list("tinh_thanh", flat=True)
                 .distinct().order_by("tinh_thanh"))

    so_truong_bac = Truong.objects.filter(vung_mien="Miền Bắc").count()
    so_truong_trung = Truong.objects.filter(vung_mien="Miền Trung").count()
    so_truong_nam = Truong.objects.filter(vung_mien="Miền Nam").count()

    page_obj = None

    if tab == "truong":
        qs = Truong.objects.all().order_by("ma_truong")
        if q:
            qs = qs.filter(ma_truong__icontains=q) | qs.filter(ten_truong__icontains=q) | qs.filter(viet_tat__icontains=q)
        if vung:
            vung_map = {"bac": "Miền Bắc", "trung": "Miền Trung", "nam": "Miền Nam"}
            if vung in vung_map:
                qs = qs.filter(vung_mien=vung_map[vung])
        if tinh:
            qs = qs.filter(tinh_thanh=tinh)
        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get("page", 1))

    elif tab == "nganh":
        qs = Nganh.objects.all().order_by("nhom_nganh", "ten_nganh")
        if q:
            qs = qs.filter(ten_nganh__icontains=q) | qs.filter(nganh_slug__icontains=q)
        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get("page", 1))

    elif tab == "tohop":
        qs = ToHop.objects.all().order_by("ma_to_hop")
        if q:
            qs = qs.filter(ma_to_hop__icontains=q) | qs.filter(ten_to_hop__icontains=q)
        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get("page", 1))

    ctx = {
        "active": "du_lieu",
        "tab": tab,
        "q": q,
        "vung": vung,
        "tinh": tinh,
        "tinh_list": tinh_list,
        "page_obj": page_obj,
        "so_truong": Truong.objects.count(),
        "so_nganh": Nganh.objects.count(),
        "so_to_hop": ToHop.objects.count(),
        "so_truong_bac": so_truong_bac,
        "so_truong_trung": so_truong_trung,
        "so_truong_nam": so_truong_nam,
    }
    return render(request, "quantri/du_lieu.html", ctx)


@staff_required
def cap_nhat(request):
    """Trang Pipeline cập nhật dữ liệu 6 bước + Cổng kiểm tra."""
    cua_so = list(CuaSoNam.objects.values_list("nam", flat=True).order_by("vi_tri"))
    cua_so_str = f"{cua_so[0]}–{cua_so[-1]}" if cua_so else "2021–2025"

    lich_su = LanCapNhat.objects.order_by("-thoi_diem")[:10]
    so_fact = DiemChuan.objects.count()
    so_truong = Truong.objects.count()
    so_nganh = Nganh.objects.count()

    ctx = {
        "active": "cap_nhat",
        "cua_so_str": cua_so_str,
        "lich_su": lich_su,
        "so_fact": so_fact,
        "so_truong": so_truong,
        "so_nganh": so_nganh,
    }
    return render(request, "quantri/cap_nhat.html", ctx)


@staff_required
def ai_view(request):
    """Quản lý mô hình AI, Fallback Margin, Circuit Breaker."""
    tong_kq = KetQuaGoiY.objects.count()
    an_toan = KetQuaGoiY.objects.filter(tang="An toàn").count()
    vua_suc = KetQuaGoiY.objects.filter(tang="Vừa sức").count()
    thu_suc = KetQuaGoiY.objects.filter(tang="Thử sức").count()

    avg_margin = KetQuaGoiY.objects.aggregate(avg=Avg("margin"))["avg"] or 0
    avg_xs = KetQuaGoiY.objects.aggregate(avg=Avg("xac_suat_do"))["avg"] or 0

    so_lan = LanGoiY.objects.count()
    so_dung_ai = LanGoiY.objects.filter(dung_ai=True).count()

    ctx = {
        "active": "ai",
        "tong_kq": tong_kq,
        "an_toan": an_toan,
        "vua_suc": vua_suc,
        "thu_suc": thu_suc,
        "avg_margin": round(avg_margin, 2),
        "avg_xs": round(avg_xs * 100, 1),
        "so_lan": so_lan,
        "so_dung_ai": so_dung_ai,
    }
    return render(request, "quantri/ai.html", ctx)


@staff_required
def nguoi_dung(request):
    """Quản lý người dùng và hồ sơ."""
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")

    users = User.objects.annotate(so_ho_so=Count("hosonangluc")).order_by("-date_joined")
    if q:
        users = users.filter(username__icontains=q) | users.filter(email__icontains=q)
    if role == "staff":
        users = users.filter(is_staff=True)
    elif role == "student":
        users = users.filter(is_staff=False)

    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    ctx = {
        "active": "nguoi_dung",
        "page_obj": page_obj,
        "q": q,
        "role": role,
        "tong_user": User.objects.count(),
        "tong_staff": User.objects.filter(is_staff=True).count(),
        "tong_hoso": HoSoNangLuc.objects.count(),
    }
    return render(request, "quantri/nguoi_dung.html", ctx)
