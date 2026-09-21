from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


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
            return redirect("university:trang_chu")
    else:
        form = AuthenticationForm()
    return render(request, "accounts/dang_nhap.html", {"form": form})


@require_POST
def dang_xuat(request):
    logout(request)
    return redirect("university:trang_chu")
