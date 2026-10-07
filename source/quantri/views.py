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
import json
import os
import subprocess
import sys
import threading

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from admissions.models import HoSoNangLuc
# gen_dataset, train chỉ import khi bấm nút huấn luyện (lazy import)
# để Django không crash khi môi trường deploy nhẹ chưa có numpy/sklearn.
from recommendation.ml.predict import ML_DIR, nap_lai, phien_ban
from recommendation.models import KetQuaGoiY, LanGoiY
from university.models import (CuaSoNam, DiemChuan, LanCapNhat, Nganh, ToHop,
                               Truong)

# staff_member_required mặc định hardcode login_url='admin:login' (trang admin
# Django). Ép về form đăng nhập chung accounts:dang_nhap.
staff_required = partial(staff_member_required, login_url="accounts:dang_nhap")

# UC-10 — huấn luyện chạy nền: 863k dòng mất ~30–90s, không giữ request.
_trang_thai = {
    "dang_chay": False, "buoc": "", "loi": "", "ket_qua": None,
    "bat_dau": None, "ket_thuc": None,
}
_khoa_hl = threading.Lock()

# Pipeline cào + import chạy nền: crawl (~30s từ cache, phút nếu mạng mới) +
# import (~50s). Chọn số năm chu kỳ ở UI (CN-05 slider).
_trang_thai_cao = {
    "dang_chay": False, "buoc": "", "loi": "", "so_nam": None,
    "bat_dau": None, "ket_thuc": None, "log": [],
}
_khoa_cao = threading.Lock()

# Chu kỳ năm cho phép: 3..10, khớp số cột diem_nam_1..10 trong schema.sql.
SO_NAM_CHO_PHEP = tuple(range(3, 11))


def _db_env() -> dict:
    """Truyền creds DB Django sang script `import_mysql.py` (subprocess)."""
    cfg = settings.DATABASES["default"]
    return {
        "DB_HOST": str(cfg.get("HOST") or "127.0.0.1"),
        "DB_PORT": str(cfg.get("PORT") or "3306"),
        "DB_USER": str(cfg.get("USER") or "root"),
        "DB_PASSWORD": str(cfg.get("PASSWORD") or ""),
        "DB_NAME": str(cfg.get("NAME") or "uni_map"),
    }


def _chay_lenh(cmd: list[str], env: dict | None = None) -> str:
    """Chạy 1 lệnh, trả stdout. Raise RuntimeError kèm tail log khi lỗi."""
    log = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=1800,
        env={**os.environ, **(env or {})},
    )
    tail = (log.stdout or "")[-1500:]
    if log.returncode != 0:
        raise RuntimeError(
            f"{' '.join(cmd[-1:])} lỗi (mã {log.returncode}): "
            f"{(log.stderr or tail)[-500:]}")
    return tail


def _chay_cao_va_import(so_nam: int, refresh: bool, huan_luyen: bool) -> None:
    """Chạy nền: crawl (`--years N`) -> import MySQL -> (tuỳ chọn) train lại.

    Một luồng cho cả chuỗi vì bước sau phụ thuộc bước trước: train đọc DB vừa
    nạp. Chạy 2 luồng song song sẽ train trên dữ liệu cũ.
    """
    try:
        root = os.path.dirname(settings.BASE_DIR)
        crawl = os.path.join(root, "datas", "crawler", "crawl_diemchuan.py")
        import_db = os.path.join(root, "database", "import_mysql.py")

        _trang_thai_cao.update(buoc=f"Đang cào dữ liệu {so_nam} năm"
                                    f"{' (từ web)' if refresh else ' (từ cache)'}…")
        cmd = [sys.executable, crawl, "--years", str(so_nam)]
        if refresh:
            cmd.append("--refresh")
        log_cao = _chay_lenh(cmd)
        _trang_thai_cao["log"].append(f"[crawl]\n{log_cao}")

        _trang_thai_cao.update(buoc="Đang nạp vào MySQL…")
        log_imp = _chay_lenh([sys.executable, import_db], env=_db_env())
        _trang_thai_cao["log"].append(f"[import]\n{log_imp}")

        if huan_luyen:
            from recommendation.ml import gen_dataset, train
            # UC-10 — cùng ngưỡng an toàn: chỉ thay model.pkl nếu acc không giảm.
            with _khoa_hl:
                bao = _doc_bao_cao()
                acc_cu = None
                if bao and bao.get("ket_qua"):
                    acc_cu = max(k["accuracy"] for k in bao["ket_qua"]
                                 if k.get("ten", "").startswith("RandomForest"))
                _trang_thai.update(dang_chay=True, buoc="Đang dựng đặc trưng…",
                                   loi="", ket_qua=None)
                _trang_thai_cao.update(buoc="Đang sinh dataset và huấn luyện…")
                gen_dataset.main(ML_DIR, 0)
                _trang_thai.update(buoc="Đang huấn luyện RandomForest…")
                ket_qua = train.huan_luyen(ML_DIR, acc_cu)
                _trang_thai.update(buoc="", ket_qua=ket_qua, loi="", dang_chay=False)
                nap_lai()
                _trang_thai_cao["log"].append(
                    f"[train] acc={ket_qua.get('thay_the')} thay_the")

        _trang_thai_cao.update(buoc="", loi="")
    except Exception as e:  # noqa: BLE001 — báo lên UI thay vì chết im
        _trang_thai.update(dang_chay=False)
        _trang_thai_cao.update(buoc="", loi=f"{type(e).__name__}: {e}"[:500])
    finally:
        import time
        _trang_thai_cao.update(dang_chay=False, ket_thuc=time.strftime("%H:%M:%S"))
        _trang_thai_cao["log"] = _trang_thai_cao["log"][-4:]


def _doc_bao_cao() -> dict | None:
    """Đọc `bao_cao_danh_gia.json` của mô hình đang có trên đĩa."""
    duong = os.path.join(ML_DIR, "bao_cao_danh_gia.json")
    try:
        with open(duong, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _doc_meta() -> dict | None:
    """Đọc `dataset_meta.json` — phiên bản dữ liệu đã dùng (UC-10 bước 6)."""
    try:
        with open(os.path.join(ML_DIR, "dataset_meta.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _chay_huan_luyen(sample: int, acc_cu: float | None) -> None:
    """Chạy nền: sinh dataset -> train -> ghi trạng thái (UC-10 bước 2–6)."""
    try:
        from recommendation.ml import gen_dataset, train

        _trang_thai.update(buoc="Đang dựng bảng đặc trưng và sinh mẫu…")
        gen_dataset.main(ML_DIR, sample)
        _trang_thai.update(buoc="Đang huấn luyện RandomForest…")
        bao = train.huan_luyen(ML_DIR, acc_cu)
        # Từ chối thay thế KHÔNG phải lỗi — template đã hiện trạng thái thay_the
        # riêng, nên `loi` giữ rỗng khi train chạy xong dù thay hay không.
        _trang_thai.update(buoc="", ket_qua=bao, loi="")
    except Exception as e:  # noqa: BLE001 — báo lên UI thay vì chết im
        _trang_thai.update(buoc="", loi=f"{type(e).__name__}: {e}"[:300])
    finally:
        import time
        _trang_thai.update(dang_chay=False, ket_thuc=time.strftime("%H:%M:%S"))
        # Model vừa đổi trên đĩa -> nạp lại ở request sau.
        nap_lai()


@staff_required
def dashboard(request):
    """Trang Dashboard tổng quan — KPI cards, Cảnh báo CN-08, Audit log."""
    so_truong = Truong.objects.count()
    so_nganh = Nganh.objects.count()
    so_to_hop = ToHop.objects.count()
    so_fact = DiemChuan.objects.count()

    cua_so = list(CuaSoNam.objects.values_list("nam", flat=True).order_by("vi_tri"))
    cua_so_str = f"{cua_so[0]}–{cua_so[-1]}" if cua_so else "2020–2025"

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
    cua_so_str = f"{cua_so[0]}–{cua_so[-1]}" if cua_so else "2020–2025"

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
        "so_nam_cho_phep": SO_NAM_CHO_PHEP,
        "so_nam_hien_tai": len(cua_so),
        "trang_thai_cao": _trang_thai_cao,
    }
    return render(request, "quantri/cap_nhat.html", ctx)


@staff_required
@require_POST
def cap_nhat_chay(request):
    """POST — cào + import chạy nền. Chọn số năm chu kỳ (3–6) ở form."""
    if _trang_thai_cao["dang_chay"]:
        messages.warning(request, "Pipeline đang chạy — đợi xong rồi chạy lại.")
        return redirect("quantri:cap_nhat")

    try:
        so_nam = int(request.POST.get("so_nam") or 0)
    except (TypeError, ValueError):
        so_nam = 0
    if so_nam not in SO_NAM_CHO_PHEP:
        messages.error(
            request,
            f"Chu kỳ không hợp lệ — chỉ nhận {', '.join(map(str, SO_NAM_CHO_PHEP))} năm.")
        return redirect("quantri:cap_nhat")

    refresh = request.POST.get("refresh") == "on"
    huan_luyen = request.POST.get("huan_luyen") == "on"

    import time
    _trang_thai_cao.update(
        dang_chay=True, buoc="Đang khởi động…", loi="", so_nam=so_nam,
        bat_dau=time.strftime("%H:%M:%S"), ket_thuc=None, log=[])
    threading.Thread(
        target=_chay_cao_va_import, args=(so_nam, refresh, huan_luyen),
        daemon=True).start()

    messages.success(
        request,
        f"Đã bắt đầu cào {so_nam} năm"
        f"{' từ web (bỏ cache)' if refresh else ' từ cache'} + nạp DB"
        f"{' + huấn luyện lại' if huan_luyen else ''}. "
        "Theo dõi tiến trình bên dưới.")
    return redirect("quantri:cap_nhat")


@staff_required
def ai_view(request):
    """Quản lý mô hình AI, Fallback Margin, Circuit Breaker (SRS UC-10)."""
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
        # UC-10 — trạng thái mô hình đang chạy + báo cáo mô hình trên đĩa.
        "phien_ban": phien_ban(),
        "bao_cao": _doc_bao_cao(),
        "meta": _doc_meta(),
        "trang_thai": _trang_thai,
    }
    return render(request, "quantri/ai.html", ctx)


@staff_required
def ai_huan_luyen(request):
    """UC-10 bước 1–6 — nút "Huấn luyện lại". Chỉ nhận POST (không train bằng
    GET — bấm nhầm link cũng không chạy). Trả về ngay, trạng thái xem ở `ai_view`.
    """
    if request.method != "POST":
        return redirect("quantri:ai")
    with _khoa_hl:
        if _trang_thai["dang_chay"]:
            messages.info(request, "Đang huấn luyện — đợi lần chạy hiện tại xong.")
            return redirect("quantri:ai")
        # UC-10 bước 5 — accuracy bản đang chạy làm ngưỡng thay thế.
        bao = _doc_bao_cao()
        acc_cu = None
        if bao and bao.get("ket_qua"):
            acc_cu = max(k["accuracy"] for k in bao["ket_qua"]
                         if k.get("ten", "").startswith("RandomForest"))
        sample = int(request.POST.get("sample") or 0)
        import time

        _trang_thai.update(dang_chay=True, buoc="Đang bắt đầu…", loi="",
                           ket_qua=None, bat_dau=time.strftime("%H:%M:%S"),
                           ket_thuc=None)
        t = threading.Thread(target=_chay_huan_luyen, args=(sample, acc_cu),
                             daemon=True)
        t.start()
    messages.success(request, "Đã bắt đầu huấn luyện. Trang này tự tải lại sau 10 giây.")
    return redirect("quantri:ai")


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


# ===========================================================================
# Thêm / sửa / xoá người dùng (chỉ staff). Tất cả qua POST — không đổi dữ
# liệu bằng GET. Mật khẩu để trống khi sửa = giữ nguyên mật khẩu cũ.
# ===========================================================================

def _du_lieu_form(request) -> dict:
    """Đọc form người dùng -> dict field của `User` (chưa gồm mật khẩu)."""
    return {
        "username": (request.POST.get("username") or "").strip(),
        "email": (request.POST.get("email") or "").strip(),
        "first_name": (request.POST.get("first_name") or "").strip(),
        "last_name": (request.POST.get("last_name") or "").strip(),
        "is_staff": request.POST.get("is_staff") == "on",
        "is_active": request.POST.get("is_active") == "on",
    }


def _chan_superuser(request, user) -> bool:
    """Superuser chỉ bị đụng bởi superuser — tránh staff tự khoá tài khoản gốc."""
    return user.is_superuser and not request.user.is_superuser


@staff_required
@require_POST
def nguoi_dung_them(request):
    """Tạo tài khoản mới. Mật khẩu bắt buộc (tài khoản thường, không phải OAuth)."""
    du_lieu = _du_lieu_form(request)
    mat_khau = request.POST.get("password") or ""

    if not du_lieu["username"]:
        messages.error(request, "Tên đăng nhập không được để trống.")
    elif not mat_khau:
        messages.error(request, "Mật khẩu không được để trống khi tạo tài khoản.")
    elif User.objects.filter(username=du_lieu["username"]).exists():
        messages.error(request, f"Tên đăng nhập “{du_lieu['username']}” đã tồn tại.")
    else:
        User.objects.create_user(password=mat_khau, **du_lieu)
        messages.success(request, f"Đã tạo tài khoản “{du_lieu['username']}”.")
    return redirect("quantri:nguoi_dung")


@staff_required
@require_POST
def nguoi_dung_sua(request, user_id):
    """Sửa tài khoản. Mật khẩu trống = giữ nguyên."""
    u = get_object_or_404(User, pk=user_id)
    if _chan_superuser(request, u):
        messages.error(request, "Chỉ superadmin được sửa tài khoản superadmin.")
        return redirect("quantri:nguoi_dung")

    du_lieu = _du_lieu_form(request)
    trung = User.objects.filter(username=du_lieu["username"]).exclude(pk=u.pk).exists()
    if not du_lieu["username"]:
        messages.error(request, "Tên đăng nhập không được để trống.")
    elif trung:
        messages.error(request, f"Tên đăng nhập “{du_lieu['username']}” đã tồn tại.")
    else:
        for truong, gia_tri in du_lieu.items():
            setattr(u, truong, gia_tri)
        # Tự bỏ quyền staff của chính mình sẽ tự đá khỏi trang quản trị này.
        if u.pk == request.user.pk and not u.is_staff:
            messages.error(request, "Không thể tự bỏ quyền quản trị của chính mình.")
            return redirect("quantri:nguoi_dung")
        mat_khau = request.POST.get("password") or ""
        if mat_khau:
            u.set_password(mat_khau)
        u.save()
        messages.success(request, f"Đã cập nhật tài khoản “{u.username}”.")
    return redirect("quantri:nguoi_dung")


@staff_required
@require_POST
def nguoi_dung_xoa(request, user_id):
    """Xoá tài khoản. Hồ sơ năng lực + lịch sử gợi ý xoá theo (CASCADE)."""
    u = get_object_or_404(User, pk=user_id)
    if u.pk == request.user.pk:
        messages.error(request, "Không thể xoá tài khoản đang đăng nhập.")
    elif _chan_superuser(request, u):
        messages.error(request, "Chỉ superadmin được xoá tài khoản superadmin.")
    else:
        ten = u.username
        u.delete()
        messages.success(request, f"Đã xoá tài khoản “{ten}” cùng hồ sơ liên quan.")
    return redirect("quantri:nguoi_dung")
