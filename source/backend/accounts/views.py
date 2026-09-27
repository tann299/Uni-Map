from django import forms
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (AuthenticationForm, PasswordChangeForm,
                                        UserCreationForm)
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from admissions.models import HoSoNangLuc


class ThongTinForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Họ", "last_name": "Tên", "email": "Email"}


def dang_ky(request):
    if request.user.is_authenticated:
        return redirect("university:trang_chu")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Tạo tài khoản thành công! Chào mừng {user.username} đến với Uni Map.")
            return redirect("university:trang_chu")
    else:
        form = UserCreationForm()
    return render(request, "accounts/dang_ky.html", {"form": form})


def dang_nhap(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("quantri:dashboard")
        return redirect("university:trang_chu")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if not request.POST.get("remember_me"):
                request.session.set_expiry(0)  # không tick "Nhớ tôi" -> hết phiên khi đóng trình duyệt
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            # Nhân viên quản trị vào thẳng console /quan-tri/, không qua trang chủ.
            if form.get_user().is_staff:
                return redirect("quantri:dashboard")
            return redirect("university:trang_chu")
    else:
        form = AuthenticationForm()
    return render(request, "accounts/dang_nhap.html", {"form": form})


@require_POST
def dang_xuat(request):
    logout(request)
    return redirect("university:trang_chu")


@login_required
def tai_khoan(request):
    """Trang thông tin tài khoản — hồ sơ năng lực dọn từ header vào đây."""
    # Tab phải suy từ POST, không chỉ từ query. Nếu không, submit form lỗi sẽ
    # render lại ở tab "ho_so" -> lỗi validate không bao giờ hiện ra.
    if "luu_thong_tin" in request.POST:
        tab = "thong_tin"
    elif "doi_mat_khau" in request.POST:
        tab = "mat_khau"
    else:
        tab = request.GET.get("tab", "ho_so")

    ft = (ThongTinForm(request.POST, instance=request.user, prefix="tt")
          if tab == "thong_tin" else ThongTinForm(instance=request.user, prefix="tt"))
    fp = (PasswordChangeForm(request.user, request.POST, prefix="mk")
          if tab == "mat_khau" else PasswordChangeForm(request.user, prefix="mk"))

    if request.method == "POST":
        if tab == "thong_tin" and ft.is_valid():
            ft.save()
            messages.success(request, "Đã cập nhật thông tin cá nhân.")
            return redirect("accounts:tai_khoan")
        if tab == "mat_khau" and fp.is_valid():
            u = fp.save()
            update_session_auth_hash(request, u)  # không bị văng ra
            messages.success(request, "Đã đổi mật khẩu.")
            return redirect("accounts:tai_khoan")

    hs = (HoSoNangLuc.objects.filter(user=request.user).order_by("-ngay_sua"))
    return render(request, "accounts/tai_khoan.html", {
        "nav_active": "tai_khoan", "tab": tab,
        "form_tt": ft, "form_mk": fp, "danh_sach": hs,
    })
