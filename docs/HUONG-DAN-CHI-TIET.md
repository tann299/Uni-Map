# Hướng dẫn chi tiết — Uni Connect

Tài liệu kỹ thuật đầy đủ. Nội dung bìa nhanh xem [README.md](../README.md).

> Dự án thuộc sở hữu của **Nguyễn Ngọc Tân** — `Tanngao333@gmail.com`. Repository chưa công bố license; không tự ý sử dụng lại mã nguồn, dữ liệu hoặc tài sản thiết kế khi chưa có sự đồng ý của chủ sở hữu.

## Mục lục

1. [Cấu trúc repository](#1-cấu-trúc-repository)
2. [Cài đặt local từng bước](#2-cài-đặt-local-từng-bước)
3. [Biến môi trường](#3-biến-môi-trường)
4. [Dựng MySQL và nạp dữ liệu](#4-dựng-mysql-và-nạp-dữ-liệu)
5. [Migration Django](#5-migration-django)
6. [OAuth redirect URI](#6-oauth-redirect-uri)
7. [Chống trùng Gmail](#7-chống-trùng-gmail)
8. [Migration email unique](#8-migration-email-unique)
9. [Rate limit](#9-rate-limit)
10. [Mô hình AI](#10-mô-hình-ai)
11. [Kiểm thử](#11-kiểm-thử)
12. [Deploy hosting thủ công](#12-deploy-hosting-thủ-công)
13. [Cập nhật hằng năm](#13-cập-nhật-hằng-năm)
14. [Những điều dễ sai trên Windows](#14-những-điều-dễ-sai-trên-windows)

## 1. Cấu trúc repository

```text
Uni-Map/
├── source/                    Django project
│   ├── config/                settings, URL root, WSGI/ASGI
│   ├── accounts/              auth thường, OAuth, profile, rate limit
│   ├── admissions/            hồ sơ năng lực và điểm môn
│   ├── university/            tra cứu, trường, ngành, API /api/tra-cuu/
│   ├── recommendation/        gợi ý AI, so sánh, lịch sử, pipeline ML
│   ├── quantri/               console quản trị
│   ├── templates/             base template dùng chung
│   └── manage.py
├── database/
│   ├── schema.sql             schema MySQL nguồn sự thật
│   ├── import_mysql.py        import dữ liệu CSV vào MySQL (idempotent)
│   └── ve_so_do.py            sinh ERD so_do_csdl.png
├── datas/                     crawler và dữ liệu nguồn
│   ├── crawler/crawl_diemchuan.py
│   └── data/                  CSV do crawler sinh (không commit)
├── docs/                      SRS, mô hình dữ liệu, slide
├── requirements.txt
└── README.md
```

API tra cứu MVP: `GET /api/tra-cuu/` hỗ trợ `q`, `nganh`, `truong`, `tinh_thanh`, `vung_mien`, `ma_to_hop`, `phuong_thuc`, `nam`, `limit`, `offset`. Response gồm `data`, `pagination`, `years`, `source`, `updated_at`.

```bash
curl "http://127.0.0.1:8000/api/tra-cuu/?q=công nghệ&nam=2025&limit=20"
```

## 2. Cài đặt local từng bước

### 1. Clone

```bash
git clone https://github.com/tann299/Uni-Map.git
cd Uni-Map
```

### 2. Virtual environment

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Tạo `.env`

Sao chép `.env.example` thành `.env` rồi điền giá trị thật (xem [mục 3](#3-biến-môi-trường)).

### 4. Chạy server

```bash
cd source
python manage.py runserver
```

Mở <http://127.0.0.1:8000/>.

## 3. Biến môi trường

`.env` không được commit. Django đọc nó bằng loader tích hợp trong `source/config/settings.py` (biến môi trường thật luôn thắng giá trị trong file).

| Biến | Ý nghĩa | Ví dụ |
|---|---|---|
| `DJANGO_SECRET_KEY` | Khóa bí mật Django | chuỗi ngẫu nhiên dài |
| `DJANGO_DEBUG` | `1` = dev, `0` = production | `1` |
| `DJANGO_ALLOWED_HOSTS` | Host được phép, phân cách bằng dấu phẩy | `127.0.0.1,localhost` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Kết nối MySQL | `uni_map` / `root` / mật khẩu |
| `DB_HOST` / `DB_PORT` | Host/port MySQL | `127.0.0.1` / `3306` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth Google | từ Google Cloud Console |
| `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` | OAuth Facebook | từ Facebook for Developers |

Mặc định khi thiếu biến: `root@127.0.0.1:3306/uni_map` không mật khẩu — đủ cho dev, không dùng cho production.

Key mới cho `DJANGO_SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## 4. Dựng MySQL và nạp dữ liệu

Yêu cầu MySQL 8.0+. Cửa sổ index tối thiểu 3072 byte (MySQL 8 với row format DYNAMIC) vì `nganh.nganh_slug` dài 320 ký tự.

### Tạo schema

`--default-character-set=utf8mb4` là **bắt buộc**: thiếu nó, MySQL client trên Windows dùng cp1252 và làm hỏng giá trị ENUM tiếng Việt ngay lúc `CREATE TABLE`:

```bash
mysql -u root -p --default-character-set=utf8mb4 < database/schema.sql
```

`schema.sql` là nguồn sự thật. Các bảng dữ liệu nghiệp vụ (`truong`, `nganh`, `to_hop`, `diem_chuan`, ...) do crawler/import quản lý, model Django tương ứng đặt `managed = False` — Django không tự tạo/xóa các bảng đó.

### Nạp dữ liệu

Crawler xuất CSV vào `datas/data/`, import nạp vào MySQL:

```bash
python datas/crawler/crawl_diemchuan.py --refresh   # crawl + self-check
python database/import_mysql.py                     # nạp (idempotent)
```

Import có các đặc tính:

- **IDEMPOTENT** — `INSERT ... ON DUPLICATE KEY UPDATE` theo khoá tự nhiên, chạy lại không nhân bản dòng;
- **TRANSACTION** — lỗi giữa chừng thì rollback;
- **DỌN RÁC** — xoá dòng fact/chiều không còn trong CSV, giữ lịch sử gợi ý của học sinh;
- **GHI NHẬT KÝ** — mỗi lần chạy ghi 1 dòng vào `lan_cap_nhat`.

Kiểm trước khi ghi thật:

```bash
python database/import_mysql.py --dry-run
```

Thứ tự bắt buộc khi dựng mới: crawl → import → `manage.py kiemtra`.

## 5. Migration Django

Django chỉ quản lý bảng dữ liệu người dùng (`auth_user`, `accounts_profile`, `ho_so_nang_luc`, `diem_mon`, ...). Chạy:

```bash
cd source
python manage.py migrate --fake-initial
```

`--fake-initial` vì `auth_user` đã có sẵn từ `schema.sql`.

Kiểm tầng ORM khớp DB (chỉ đọc, 8 phép kiểm):

```bash
PYTHONIOENCODING=utf-8 python manage.py kiemtra
```

## 6. OAuth redirect URI

Google Cloud Console → Credentials → OAuth client ID, mục **Authorized redirect URIs**:

```text
http://localhost:8000/accounts/google/xac-thuc/    # local
https://uniconnect.id.vn/accounts/google/xac-thuc/ # production
```

Facebook for Developers → Valid OAuth Redirect URIs:

```text
https://uniconnect.id.vn/accounts/facebook/xac-thuc/
```

Các điểm hay sai: `http` vs `https`, có/không `www.`, dấu `/` cuối, tham chiếu đúng client ID mà code đang dùng.

## 7. Chống trùng Gmail

Gmail coi `an.nguyen+uni@gmail.com`, `an.nguyen@gmail.com`, `annguyen@gmail.com` là cùng hộp thư nhưng chuỗi khác nhau. Mọi đường tạo/sửa user dùng `accounts/gmail.py`:

- `chuan_hoa_email()` — lowercase, Gmail bỏ `.` và `+tag`, gộp `googlemail.com` về `gmail.com`;
- `tim_theo_email()` — so chuỗi 2 dạng (index, nhanh) + lưới an toàn quét chuẩn hoá trong Python cho Gmail, bắt được cả email gõ tay chưa chuẩn trong DB cũ.

Chính sách: **email đã từng tồn tại → không bao giờ tạo record mới**. Áp ở 5 đường: OAuth Google/Facebook, đăng ký form, sửa thông tin cá nhân, quantri thêm/sửa user, Django admin. Email trống khi sửa không được ghi đè xóa email cũ (tránh mất nhận diện tài khoản OAuth).

## 8. Migration email unique

`accounts/migrations/0002_email_unique_don_trung.py`:

1. Chuẩn hoá email cũ, xoá user trùng (giữ user cũ nhất, dữ liệu CASCADE theo);
2. Thêm cột generated + UNIQUE:

```sql
ALTER TABLE auth_user
  ADD COLUMN email_duy_nhat VARCHAR(254)
    GENERATED ALWAYS AS (NULLIF(LOWER(TRIM(email)), '')) STORED,
  ADD UNIQUE KEY uq_auth_user_email_chuan (email_duy_nhat);
```

Không unique thẳng trên `email` vì `User.email` blank=True: nhiều user có `email = ''` → MySQL báo `#1062 - Duplicate entry ''`. Cột generated đổi rỗng thành NULL, MySQL bỏ qua NULL khi check UNIQUE. Trên hosting không có SSH, chạy câu ALTER này trong phpMyAdmin rồi đánh dấu migration đã áp:

```bash
python manage.py migrate accounts 0002 --fake
```

## 9. Rate limit

Module dùng chung `accounts/rate_limit.py` — bộ đếm cửa sổ cố định trên Django cache (`cache.add()` atomic + `cache.incr()`, key tự hết hạn).

| Chỗ | Giới hạn | Khoá |
|---|---|---|
| Đăng nhập sai | 5 lần / (IP+username) / 5 phút | `dn-sai:{ip}:{username}` |
| Đăng ký | 5 tài khoản / IP / giờ | `rl:dang-ky:ip:*` |
| Gợi ý AI (`xem_goi_y` + `so_sanh`) | 20 lần / phút / user | `rl:goi-y:u:{pk}` |
| Upload avatar | 10 lần / giờ / user | `rl:upload-avatar:u:{pk}` |

- `so_sanh` dùng **chung** bộ đếm với `xem_goi_y` để không lách bằng cách qua lại 2 trang;
- Gợi ý AI chặn **trước** khi đọc hồ sơ — không tốn query nào khi bị chặn;
- Cache: `FileBasedCache` tại `source/.cache/django/` ( chia sẻ giữa các process Passenger/Gunicorn; `LocMemCache` là RAM riêng từng process, rate limit thành vô nghĩa).

**Chống giả mạo XFF:** chỉ tin `HTTP_X_FORWARDED_FOR` khi `REMOTE_ADDR` là loopback/nội bộ; client ngoài gửi XFF giả thì dùng `REMOTE_ADDR`. Có thể ép bằng `settings.RATE_LIMIT_TIN_XFF` (`True`/`False`/`None`=tự nhận).

Xoá nội dung `source/.cache/django/` để reset bộ đếm ngay khi đang test.

## 10. Mô hình AI

Pipeline: `gen_dataset.py` → `train.py` → `predict.py`, danh mục đặc trưng dùng chung ở `constants.py`.

### Đặc trưng — 27 chiều

7 đặc trưng số:

| Đặc trưng | Ý nghĩa |
|---|---|
| `diem_thi` | điểm tổ hợp của học sinh (đã cộng ưu tiên) |
| `margin` | `diem_thi − diem_moi_nhat` |
| `diem_moi_nhat` | điểm chuẩn gần nhất |
| `diem_tb` | điểm chuẩn trung bình trong cửa sổ |
| `xu_huong` | độ dốc hồi quy tuyến tính điểm chuẩn/năm |
| `bien_dong` | `diem_max − diem_min` |
| `so_nam_co_dl` | số năm có dữ liệu |

+ one-hot 3 nhóm phân loại với danh mục cố định: 15 nhóm ngành, 3 vùng miền, 2 phương thức. Giá trị lạ chưa từng thấy thành vector toàn 0 thay vì lỗi.

### Sinh nhãn

Chưa có dữ liệu đỗ/trượt thật nên nhãn sinh từ fact `diem_chuan`: mỗi dòng điểm chuẩn `C` của năm `t` là một "sự thật" — thí sinh giả lập điểm `X = C + delta` (DELTAS từ −3.0 đến +3.0) thì đỗ khi `X >= C`.

### Chống data leakage

Đặc trưng của mẫu năm `t` **chỉ** tính từ các năm `< t` (công thức khớp `build_features` của crawler). Chia tập theo **năm**, không ngẫu nhiên: train 2021–2024, test 2025. AI nhìn 6 năm gần nhất (`NAM_LOOKBACK = 6`) dù DB giữ 10 năm để hiển thị — phổ điểm kỳ thi cũ 2016–2019 gây nhiễu.

### Huấn luyện

```bash
python -m recommendation.ml.gen_dataset        # sinh CSV + meta
python -m recommendation.ml.train              # fit + lưu pkl
```

```python
RF_KW = dict(n_estimators=100, min_samples_leaf=5, max_depth=14,
             n_jobs=-1, random_state=42)
```

Decision Tree (`min_samples_leaf=5`) được train song song làm baseline. Chỉ số đánh giá: accuracy, ROC-AUC, Brier, precision/recall/F1 theo lớp đỗ. UC-10 bước 5: chỉ thay thế `model.pkl` nếu accuracy mới **không thấp hơn** bản đang chạy; báo cáo của lần train bị từ chối ghi vào `bao_cao_danh_gia_moi.json`, không đè báo cáo đang chạy. RB-3: `model.pkl` phải < 100 MB.

### Suy luận

- Mô hình nạp **một lần** cho mỗi process (`nap_mo_hinh` + khoá thread); `nap_lai()` gọi sau khi train xong để request kế tiếp nạp bản mới;
- `predict_proba` chạy **theo lô** cho toàn bộ ứng viên, không gọi từng dòng;
- Mọi lỗi (thiếu file, sklearn lệch bản, vector sai kích thước) trả `None` thay vì raise — view rơi về chế độ dự phòng UC-05/5b: xếp hạng theo `margin`, ghi `dung_ai=False`. Suy giảm chất lượng còn hơn HTTP 500.

Kết quả tham chiếu trên tập test 2025: Random Forest accuracy 74,56% / ROC-AUC 0,8354 / Brier 0,1763; Decision Tree baseline 72,14% / 0,7535.

## 11. Kiểm thử

Chạy bằng SQLite in-memory (không cần MySQL local):

```bash
cd source
$env:DJANGO_SETTINGS_MODULE="config.test_sqlite"      # PowerShell
python manage.py test
```

Linux/macOS:

```bash
DJANGO_SETTINGS_MODULE=config.test_sqlite python manage.py test
```

Phạm vi: đăng ký trùng username/email, alias Gmail và login lặp lại, email cũ chưa chuẩn hoá, admin add/change user, rate limit + chống giả mạo XFF, migration email unique, OAuth Google/Facebook.

Kiểm route media khi `DEBUG=0`:

```bash
python kiemtra_media.py
```

`manage.py test` **không** dựng được bảng `managed = False` từ schema.sql — dùng `manage.py kiemtra` để kiểm dữ liệu crawl trên DB thật.

## 12. Deploy hosting thủ công

1. Backup database và `source/media/` trước.
2. Upload code trong `source/`, **không ghi đè** `.env` và `source/media/`.
3. Đảm bảo `source/.cache/` tồn tại và writable (755).
4. Migration `accounts.0002` khi host có Python tương thích Django; nếu không, chạy ALTER trong phpMyAdmin (mục 8) + `--fake` khi có SSH.
5. `pip install -r requirements.txt` (Pillow cần cho avatar).
6. `python manage.py collectstatic --noinput`.
7. Restart Python/Passenger application.
8. Kiểm `/`, `/accounts/dang-ky/`, `/accounts/dang-nhap/`, `/tra-cuu/` và login Google lặp lại.

Không commit: `.env`, password, OAuth secret, database dump, `media/`, `staticfiles/`, cache, `node_modules/`.

## 13. Cập nhật hằng năm

Khoảng tháng 8, sau khi các trường công bố điểm chuẩn — ba lệnh, không cần đổi cấu trúc bảng:

```bash
python datas/crawler/crawl_diemchuan.py --refresh
python database/import_mysql.py
PYTHONIOENCODING=utf-8 python source/manage.py kiemtra
```

Nếu self-check ở bước 1 thất bại thì **dừng, không import** — dữ liệu đang chạy được bảo vệ.

Tuỳ chọn crawler:

```bash
python datas/crawler/crawl_diemchuan.py              # dùng cache, không gọi mạng
python datas/crawler/crawl_diemchuan.py --years 3    # đổi cửa sổ sang 3 năm
python datas/crawler/crawl_diemchuan.py --end 2025   # khoá năm cuối
python datas/crawler/crawl_diemchuan.py --selfcheck  # chỉ kiểm dữ liệu đã xuất
```

## 14. Những điều dễ sai trên Windows

`PYTHONIOENCODING=utf-8` cần cho mọi management command in tiếng Việt. Không có nó, lệnh chết giữa đường với `UnicodeEncodeError` — trông như đã chạy xong.

`manage.py test` không dựng nổi test DB cho model `managed = False` — dùng `manage.py kiemtra` trên DB thật, chỉ đọc.

---

© 2025–2026 Nguyễn Ngọc Tân — `Tanngao333@gmail.com` — All rights reserved.
