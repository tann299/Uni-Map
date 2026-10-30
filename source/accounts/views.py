from django import forms
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (AuthenticationForm, PasswordChangeForm,
                                        UserCreationForm)
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from PIL import Image

from accounts.gmail import chuan_hoa_email, tim_theo_email
from accounts.models import Profile
from accounts.rate_limit import (khoa_theo_ip, khoa_theo_user,
                                 vuot_gioi_han)
from admissions.models import HoSoNangLuc
from university.services import tinh_to_hop_tu_db


# ==============================================================================
# #2 RATE LIMIT ĐĂNG NHẬP — chống brute-force
# ==============================================================================
# Đếm số lần đăng nhập SAI theo (IP + username) trong cache. Sau SO_LAN_TOI_DA
# lần sai liên tiếp thì khoá tạm KHOA_BAY_LAU giây. Đăng nhập đúng -> xoá bộ đếm.
# Dùng cache locmem (settings.CACHES) nên không cần Redis/Memcached trên hosting.
SO_LAN_TOI_DA = 5
KHOA_BAY_LAU = 5 * 60   # 5 phút

# Đăng ký: mỗi tài khoản tốn 1 lần hash mật khẩu (~100ms CPU) + tạo Profile.
# 5 tài khoản/IP/giờ là đủ cho người dùng thật (nhà trường, gia đình dùng chung
# IP), nhưng chặn được bot tạo hàng loạt làm nghẽn hosting shared.
DANG_KY_TOI_DA = 5
DANG_KY_CUA_SO = 60 * 60   # 1 giờ

# Upload avatar: mỗi ảnh decode + resize LANCZOS 300x300 (CPU nặng trên shared
# hosting). 10 lần/giờ đủ cho người dùng thật, chặn spam đổi ảnh liên tục.
UPLOAD_AVATAR_TOI_DA = 10
UPLOAD_AVATAR_CUA_SO = 60 * 60   # 1 giờ


def _ip_khach(request) -> str:
    """IP khách, ưu tiên header proxy (hosting shared luôn đứng sau proxy)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (xff.split(",")[0].strip() if xff
            else request.META.get("REMOTE_ADDR", "")) or "unknown"


def _khoa_rate_limit(request, username: str) -> str:
    """Khoá cache: tách theo IP và theo username để không khoá chéo người khác."""
    return f"dn-sai:{_ip_khach(request)}:{username.strip().lower()[:150]}"


def _bi_khoa(request, username: str):
    """(đang bị khoá?, số giây còn lại) — None nếu không bị khoá."""
    con_lai = cache.get(_khoa_rate_limit(request, username))
    if con_lai and con_lai >= SO_LAN_TOI_DA:
        return True, KHOA_BAY_LAU
    return False, 0


def _ghi_nhan_sai(request, username: str) -> None:
    """Tăng bộ đếm sai. Hết hạn sau KHOA_BAY_LAU giây kể từ lần sai đầu."""
    khoa = _khoa_rate_limit(request, username)
    cache.set(khoa, (cache.get(khoa) or 0) + 1, KHOA_BAY_LAU)


def _xoa_bo_dem(request, username: str) -> None:
    cache.delete(_khoa_rate_limit(request, username))


# Ô nhập mặc định của Django không có class -> xấu. Gắn 1 lần ở đây thay vì
# rải `|add_class` (không có sẵn filter đó trong project).
_O_INPUT = ("w-full h-11 px-3 rounded-lg bg-surface-container-low text-on-surface "
            "text-body-sm border border-outline-variant focus:outline-none "
            "focus:border-primary-container focus:bg-surface-container-lowest "
            "transition-colors placeholder:text-outline")

# #7 Upload ảnh đại diện: đuôi cho phép + trần kích thước pixel (chống
# decompression bomb: file 1KB có thể giải nén thành ảnh 50000x50000 tốn RAM).
DUOI_ANH_CHO_PHEP = (".jpg", ".jpeg", ".png", ".webp")
DIEM_TOI_DA = 4096
AVATAR_BYTES_TOI_DA = 5 * 1024 * 1024


class ThongTinForm(forms.ModelForm):
    avatar = forms.ImageField(
        label="Ảnh đại diện",
        required=False,
        widget=forms.FileInput(attrs={"class": "hidden", "accept": "image/png,image/jpeg,image/webp"}),
    )
    xoa_avatar = forms.BooleanField(
        label="Xóa ảnh đại diện",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "hidden"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Họ", "last_name": "Tên", "email": "Email"}
        widgets = {
            "first_name": forms.TextInput(attrs={"class": _O_INPUT, "placeholder": "Nguyễn"}),
            "last_name": forms.TextInput(attrs={"class": _O_INPUT, "placeholder": "Văn A"}),
            "email": forms.EmailInput(attrs={"class": _O_INPUT, "placeholder": "ban@example.com"}),
        }

    def clean_email(self):
        """Email đổi tại đây cũng không được trùng người khác (chuẩn hoá Gmail).

        Email TRỐNG không được ghi đè xóa email cũ: tài khoản OAuth phụ thuộc
        email để nhận diện, xóa nó là lần login sau tạo user mới, dữ liệu cũ
        (avatar, hồ sơ) bị bỏ rơi. Form có field email mà POST thiếu thì trống
        cũng rơi vào đây nên chặn luôn.
        """
        goc = (self.cleaned_data.get("email") or "").strip()
        email = chuan_hoa_email(goc)
        if not email:
            return self.instance.email or goc
        if tim_theo_email(goc, exclude_pk=self.instance.pk) is not None:
            raise forms.ValidationError("Email này đã được dùng bởi tài khoản khác.")
        return email

    def clean_avatar(self):
        """#7 Kiểm tra 3 lớp: đuôi file, dung lượng, và NỘI DUNG ảnh thật."""
        avatar = self.cleaned_data.get("avatar")
        if not avatar:
            return avatar

        ten = (avatar.name or "").lower()
        if not ten.endswith(DUOI_ANH_CHO_PHEP):
            raise forms.ValidationError(
                "Chỉ chấp nhận ảnh JPG, PNG hoặc WebP.")

        if avatar.size > AVATAR_BYTES_TOI_DA:
            raise forms.ValidationError(
                f"Ảnh đại diện không được vượt quá {AVATAR_BYTES_TOI_DA // 1024 // 1024}MB.")

        # Mở bằng Pillow để chắc chắn là ảnh THẬT (file .png chứa mã độc sẽ lỗi ở đây)
        try:
            avatar.seek(0)
            anh = Image.open(avatar)
            anh.verify()          # verify() đóng file -> phải mở lại để đọc kích thước
            avatar.seek(0)
            anh = Image.open(avatar)
            rong, cao = anh.size
        except Exception:
            raise forms.ValidationError("Tệp tải lên không phải ảnh hợp lệ.") from None

        if rong > DIEM_TOI_DA or cao > DIEM_TOI_DA:
            raise forms.ValidationError(
                f"Ảnh quá lớn ({rong}×{cao}px). Tối đa {DIEM_TOI_DA}×{DIEM_TOI_DA}px.")

        avatar.seek(0)
        return avatar



class MatKhauForm(PasswordChangeForm):
    """PasswordChangeForm gốc không set widget — thêm class cho khớp giao diện."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs["class"] = _O_INPUT
            f.widget.attrs.setdefault("autocomplete", "new-password")


class DangKyForm(UserCreationForm):
    """Đăng ký form: thêm email và CHẶN trùng email (không phân biệt hoa/thường).

    User.email mặc định không UNIQUE, nên UserCreationForm không bao giờ chặn
    hai tài khoản cùng gmail. Form này tự kiểm tra email__iexact trước khi lưu.
    """

    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={"class": _O_INPUT, "placeholder": "ban@example.com"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        goc = (self.cleaned_data.get("email") or "").strip()
        email = chuan_hoa_email(goc)
        if not email:
            raise forms.ValidationError("Vui lòng nhập email.")
        if tim_theo_email(goc) is not None:
            raise forms.ValidationError("Email này đã được dùng để đăng ký tài khoản.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


def dang_ky(request):
    if request.user.is_authenticated:
        return redirect("university:trang_chu")
    if request.method == "POST":
        # Chống bot tạo hàng loạt tài khoản: mỗi user tốn 1 lần hash mật khẩu
        # (~100ms CPU) + tạo Profile, đủ để làm nghẽn hosting shared.
        if vuot_gioi_han(khoa_theo_ip(request, "dang-ky"),
                         DANG_KY_TOI_DA, DANG_KY_CUA_SO):
            form = DangKyForm(request.POST)
            form.add_error(None, "Bạn đã thử tạo tài khoản quá nhiều lần. "
                                 "Vui lòng thử lại sau ít phút.")
            return render(request, "accounts/dang_ky.html", {"form": form},
                          status=429)
        form = DangKyForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Tạo tài khoản thành công! Chào mừng {user.username} đến với Uni Connect.")
            return redirect("university:trang_chu")
    else:
        form = DangKyForm()
    return render(request, "accounts/dang_ky.html", {"form": form})


def dang_nhap(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("quantri:dashboard")
        return redirect("university:trang_chu")
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()

        # #2 Chặn brute-force TRƯỚC khi kiểm mật khẩu.
        dang_bi_khoa, _ = _bi_khoa(request, username)
        if dang_bi_khoa:
            form = AuthenticationForm(request, data=request.POST)
            form.add_error(None, f"Bạn đã đăng nhập sai quá {SO_LAN_TOI_DA} lần. "
                                 f"Vui lòng thử lại sau {KHOA_BAY_LAU // 60} phút.")
            return render(request, "accounts/dang_nhap.html", {"form": form},
                          status=429)

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            _xoa_bo_dem(request, username)   # đăng nhập đúng -> xoá bộ đếm
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

        # Sai -> ghi nhận. Chỉ đếm khi username không rỗng (tránh khoá oan IP dùng chung).
        if username:
            _ghi_nhan_sai(request, username)
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

    # GET luôn render form UNBOUND (initial từ instance) — trước đây GET
    # ?tab=thong_tin vẫn bound với request.POST rỗng làm MỌI ô hiển thị rỗng
    # dù user có dữ liệu. POST mới bound.
    la_post = request.method == "POST"
    ft = (ThongTinForm(request.POST, request.FILES, instance=request.user, prefix="tt")
          if la_post else ThongTinForm(instance=request.user, prefix="tt"))
    fp = (MatKhauForm(request.user, request.POST, prefix="mk")
          if la_post else MatKhauForm(request.user, prefix="mk"))

    if request.method == "POST":
        # Upload avatar: mỗi ảnh tốn 1 lần decode + resize LANCZOS 300x300
        # (CPU đáng kể trên shared hosting) -> giới hạn số lần lưu có ảnh.
        if tab == "thong_tin" and request.FILES.get("tt-avatar"):
            if vuot_gioi_han(khoa_theo_user(request, "upload-avatar"),
                             UPLOAD_AVATAR_TOI_DA, UPLOAD_AVATAR_CUA_SO):
                messages.error(request, "Bạn đã đổi ảnh đại diện quá nhiều lần. "
                                        "Vui lòng thử lại sau ít phút.")
                return redirect("/accounts/tai-khoan/?tab=thong_tin")
        if tab == "thong_tin" and ft.is_valid():
            user = ft.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            # Xử lý avatar
            if ft.cleaned_data.get("xoa_avatar"):
                profile.xoa_file_avatar()
                profile.save()
            elif request.FILES.get("tt-avatar"):
                # Xóa ảnh cũ trước khi lưu ảnh mới
                if profile.avatar:
                    profile.xoa_file_avatar()
                profile.avatar = request.FILES.get("tt-avatar")
                profile.save()

            messages.success(request, "Đã cập nhật thông tin cá nhân và ảnh đại diện.")
            return redirect("/accounts/tai-khoan/?tab=thong_tin")
        if tab == "mat_khau" and fp.is_valid():
            u = fp.save()
            update_session_auth_hash(request, u)  # không bị văng ra
            messages.success(request, "Đã đổi mật khẩu.")
            return redirect("/accounts/tai-khoan/?tab=mat_khau")

    hs = list(HoSoNangLuc.objects.filter(user=request.user)
              .prefetch_related("diemmon_set", "langoiy_set")
              .order_by("-ngay_sua"))

    # Thẻ số liệu ở sidebar. Đếm tổ hợp bằng CN-01; điểm môn và lần gợi ý đã
    # prefetch nên không phát sinh truy vấn trong vòng lặp.
    so_to_hop = 0
    for h in hs:
        h.ds_diem_mon = list(h.diemmon_set.all())
        h.so_lan_goi_y = len(h.langoiy_set.all())
        h.so_to_hop = len(tinh_to_hop_tu_db({d.ma_mon_id: float(d.diem)
                                             for d in h.ds_diem_mon}))
        so_to_hop += h.so_to_hop
    so_lan_goi_y = sum(h.so_lan_goi_y for h in hs)

    return render(request, "accounts/tai_khoan.html", {
        "nav_active": "tai_khoan", "tab": tab,
        "form_tt": ft, "form_mk": fp, "danh_sach": hs,
        "thong_ke": {
            "so_ho_so": len(hs),
            "so_to_hop": so_to_hop,
            "so_lan_goi_y": so_lan_goi_y,
            "ho_so_moi_nhat": hs[0] if hs else None,
        },
    })
