# Uni Map

Hệ thống gợi ý trường/ngành đại học bằng AI, dành cho học sinh lớp 12. Nhập điểm
từng môn → nhận danh sách trường/ngành xếp theo xác suất đỗ, chia ba tầng
**An toàn / Vừa sức / Thử sức**, kèm lời giải thích dựa trên điểm chuẩn 5 năm.

Đặc tả đầy đủ: [docs/SRS.md](docs/SRS.md) · Mô hình dữ liệu: [docs/README_DATA.md](docs/README_DATA.md)

## Cấu trúc

```
Uni-Map/
├── source/
│   ├── crawler/         Script cào + chuẩn hoá dữ liệu (Python thuần)
│   │   ├── crawl_diemchuan.py     crawl · làm sạch · self-check
│   │   └── build_ref_tohop.py     dựng bảng tra tổ hợp → môn
│   └── backend/         Django project
│       ├── config/      settings, urls, wsgi
│       ├── manage.py
│       └── tracuu/      14 model (managed=False) + lệnh kiemtra
├── data/                CSV do crawler sinh ra → nạp vào DB
├── db/                  schema.sql · import_mysql.py · sơ đồ CSDL
├── ref/                 dữ liệu tham chiếu sửa tay được (tỉnh, tổ hợp)
├── cache/               raw.csv.gz — dữ liệu thô tích luỹ mọi năm
└── docs/                SRS, mô hình dữ liệu, kế hoạch
```

## API tra cứu MVP

Backend dùng Django thuần + ORM, không thêm REST framework. Chạy từ gốc dự án:

```bash
cd source/backend
PYTHONIOENCODING=utf-8 python manage.py runserver
```

Endpoint `GET /api/tra-cuu/` hỗ trợ `q`, `nganh`, `truong`, `tinh_thanh`,
`vung_mien`, `ma_to_hop`, `phuong_thuc`, `nam`, `limit`, `offset`.
Ví dụ:

```bash
curl "http://127.0.0.1:8000/api/tra-cuu/?q=công nghệ&nam=2025&limit=20"
```

Response gồm `data`, `pagination`, `years`, `source`, `updated_at`. Cần dựng
MySQL và import dữ liệu trước khi gọi API. Kiểm parser không cần DB:

```bash
cd source/backend
PYTHONIOENCODING=utf-8 python -m tracuu.check_api
```

Cây code backend hiện tại:

```
source/backend/
├── config/                 cấu hình Django + route gốc
├── manage.py
└── tracuu/
    ├── models.py           ORM ánh xạ schema.sql
    ├── views.py            API tra cứu điểm chuẩn
    ├── urls.py             route /api/tra-cuu/
    ├── check_api.py        assert parser query
    └── management/commands/kiemtra.py
```

## Cài đặt

```bash
pip install -r requirements.txt
```

Cần MySQL 8.0+. Backend đọc thông tin kết nối từ biến môi trường, mặc định
`root@127.0.0.1:3306/uni_map` không mật khẩu (đủ cho môi trường phát triển):
`DB_NAME` · `DB_USER` · `DB_PASSWORD` · `DB_HOST` · `DB_PORT`.

## Dựng lần đầu

Chạy đúng thứ tự 1 → 5.

1. Crawl dữ liệu. Tự gộp cache, vá font, chặn năm chưa đủ, chạy self-check cuối cùng:

```bash
python source/crawler/crawl_diemchuan.py --refresh
```

2. Dựng lược đồ. `--default-character-set=utf8mb4` là **bắt buộc** — thiếu nó, MySQL client trên Windows dùng cp1252 và làm hỏng giá trị ENUM tiếng Việt ngay lúc `CREATE TABLE`:

```bash
mysql -u root --default-character-set=utf8mb4 < db/schema.sql
```

3. Nạp dữ liệu:

```bash
python db/import_mysql.py
```

4. Đăng ký migration Django. `--fake-initial` vì `auth_user` đã có sẵn từ `schema.sql`:

```bash
PYTHONIOENCODING=utf-8 python source/backend/manage.py migrate --fake-initial
```

5. Kiểm tra tầng ORM khớp DB (8 phép kiểm, chỉ đọc):

```bash
PYTHONIOENCODING=utf-8 python source/backend/manage.py kiemtra
```

## Cập nhật hằng năm

Khoảng tháng 8, sau khi các trường công bố điểm chuẩn. Chỉ ba lệnh, **không** cần
đổi cấu trúc bảng — cửa sổ trượt tự nhận năm mới:

```bash
python source/crawler/crawl_diemchuan.py --refresh
python db/import_mysql.py
PYTHONIOENCODING=utf-8 python source/backend/manage.py kiemtra
```

Nếu self-check ở bước 1 thất bại thì **dừng, không import** — dữ liệu đang chạy
được bảo vệ. Bước 2 luôn `--dry-run` được trước khi ghi thật:

```bash
python db/import_mysql.py --dry-run
```

## Hai điều dễ sai trên Windows

`PYTHONIOENCODING=utf-8` cần cho mọi management command in tiếng Việt. Không có
nó, lệnh chết giữa đường với `UnicodeEncodeError` — trông như đã chạy xong.

`manage.py test` **không dùng được**: mọi model đặt `managed = False` nên Django
không dựng nổi test DB. Dùng `manage.py kiemtra` thay thế — nó chạy assert trên
DB thật, chỉ đọc.

## Tuỳ chọn khác của crawler

```bash
python source/crawler/crawl_diemchuan.py              # dùng cache, không gọi mạng
python source/crawler/crawl_diemchuan.py --years 3    # đổi cửa sổ sang 3 năm
python source/crawler/crawl_diemchuan.py --end 2025   # khoá năm cuối
python source/crawler/crawl_diemchuan.py --selfcheck  # chỉ kiểm dữ liệu đã xuất
```
