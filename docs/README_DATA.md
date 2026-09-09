# Uni Map — Dữ liệu tuyển sinh & cách tổ chức

Dữ liệu cho **hệ thống AI gợi ý trường/ngành đại học** theo `Plan.docx`:
Python crawler → Pandas → **MySQL** → **Django** → **Scikit-learn** → Web.

---

## 1. Chạy

Chạy từ **gốc dự án**. Mọi script neo đường dẫn theo `__file__` nên thật ra CWD
nào cũng được.

```bash
pip install -r requirements.txt
python source/crawler/build_ref_tohop.py               # 1 lần: dựng bảng tra tổ hợp -> môn
python source/crawler/crawl_diemchuan.py               # dùng cache (~10s)
python source/crawler/crawl_diemchuan.py --refresh     # crawl mới từ nguồn (~40s) — hằng năm
python source/crawler/crawl_diemchuan.py --years 3     # đổi cửa sổ sang 3 năm
python source/crawler/crawl_diemchuan.py --end 2025    # khoá năm cuối
python source/crawler/crawl_diemchuan.py --selfcheck   # chỉ kiểm tra dữ liệu đã xuất
```

`build_ref_tohop.py` cần thêm `pdfplumber` (không có trong `requirements.txt` vì
chỉ chạy một lần, `ref/to_hop_mon.csv` đã có sẵn trong repo).

| | |
|---|---|
| Nguồn điểm chuẩn | `diemthi.tuyensinh247.com` (API JSON công khai) |
| Nguồn tổ hợp môn | Danh mục **344 tổ hợp xét tuyển 2025 của Bộ GD&ĐT** + API trên |
| Phạm vi | **Đại học** (level = 2) — 288 trường có dữ liệu tra cứu được |
| Thời gian | **Cửa sổ trượt 5 năm mới nhất đã đủ dữ liệu** (hiện: 2021–2025) |
| Bộ lọc | Chỉ dòng rút được mã tổ hợp chuẩn (`A00`, `D01`, `X26`…) |
| Làm sạch | Bỏ điểm ≤ 0, lỗi nguồn (>1600), THPT/học bạ > 40, tên ngành rỗng, slug rỗng, dòng trùng; vá ký tự hỏng font từ nguồn |

---

## 2. Cập nhật hằng năm — cửa sổ trượt tự động

Script **tự phát hiện năm mới nhất** trong dữ liệu rồi lùi lại 5 năm. Khi nguồn có
điểm 2026, chạy `--refresh` sẽ **tự thành 2022–2026 — không sửa code**.

Nạp vào MySQL bằng **upsert** theo khoá tự nhiên:

```python
# khoá tự nhiên: (ma_truong, nganh_slug, ma_to_hop, phuong_thuc, nam)
for r in rows:
    DiemChuan.objects.update_or_create(
        truong_id=r.ma_truong, nganh_id=r.nganh_slug, to_hop_id=r.ma_to_hop,
        phuong_thuc=r.phuong_thuc, nam=r.nam,
        defaults={"diem_chuan": r.diem_chuan})
DiemChuan.objects.filter(nam__lt=nam_min).delete()   # bỏ năm rơi khỏi cửa sổ
```

Đơn giản hơn: `TRUNCATE` rồi `LOAD DATA INFILE 'diem_chuan.csv'` — file đã cắt sẵn đúng 5 năm.

**Cache:** `cache/raw.csv.gz` (~1 MB, **tích luỹ** mọi năm 2010→nay). Mỗi lần crawl
gộp vào cache cũ, không ghi đè — nguồn đã từng bỏ toàn bộ 2010–2012 giữa hai lần
crawl, ghi đè thì mất luôn. Sửa logic làm sạch / nhóm ngành rồi chạy lại
**không cần crawl** lần nào.

---

## 3. Các file dữ liệu — chức năng từng file

```
truong ──┐
nganh  ──┼──< diem_chuan (fact) ──> dac_trung_diemchuan (input cho sklearn)
to_hop ──┘
```

| File | Chức năng | Dòng |
|---|---|---|
| `ref/to_hop_mon.csv` | **Bảng tra tổ hợp → môn** (Bộ GD&ĐT + API). | 331 |
| `ref/tinh_thanh.csv` | **Tỉnh cũ → tỉnh sau sáp nhập 2025 + vùng miền** (63 → 34 tỉnh). | 64 |
| `ref/dia_danh.csv` | **Địa danh trong tên trường → tỉnh** (suy tự động ~98% trường). | 127 |
| `ref/truong_tinh_thucong.csv` | **Điền tay** cho trường không có địa danh trong tên (học viện quân đội, ĐH Bách Khoa HCM…). | 81 |
| `cache/raw.csv.gz` | **Dữ liệu thô tích luỹ**, mọi năm, chưa lọc. Gộp mỗi lần crawl, không ghi đè. | ~104k |
| `data/truong.csv` | **Dim trường** — `ma_truong` (PK), `ten_truong`, `viet_tat`, `tinh_thanh`, `vung_mien` | 288 |
| `data/nganh.csv` | **Dim ngành** — `nganh_slug` (khoá tự nhiên), `ten_nganh`, `nhom_nganh` (15 nhóm). DB dùng `nganh_id` làm PK. | 2.163 |
| `data/to_hop.csv` | **Dim tổ hợp** — `ma_to_hop` (PK), `ten_to_hop`, `cac_mon`, `nguon`, `so_mon` | 328 |
| `data/diem_chuan.csv` | **Bảng fact** — mỗi dòng = 1 điểm chuẩn của (trường × ngành × tổ hợp × phương thức × năm). File chính nạp DB. | 178.825 |
| `data/dac_trung_diemchuan.csv` | **Đặc trưng cho sklearn** — chuỗi điểm 5 năm đã pivot + thống kê. Lưu DB để engine gợi ý đạt PC-01 (< 3s). | 91.581 |
| `data/diem_chuan_daihoc.xlsx` | Bản cho người xem (5 sheet). Không dùng để import. | — |

**Ba dim đều dẫn xuất TỪ bảng fact**, không phải từ dữ liệu thô. Dựng từ thô sẽ
sinh ngành/tổ hợp thuộc phương thức ĐGNL/ĐGTD — có mã tổ hợp nhưng khác thang điểm
nên bị loại khỏi fact — và chúng thành dữ liệu rác trên UI. Self-check chặn điều
này: mọi dòng dim phải có ít nhất một dòng fact trỏ tới.

### `tinh_thanh` / `vung_mien` — vị trí trường (phủ 100%)

Nguồn không có dữ liệu này, nên script tự dựng qua **3 tầng, tầng sau ghi đè tầng trước**:

1. **Suy từ tên trường** (`ref/dia_danh.csv`) — cụm dài khớp trước để `"Nam Cần Thơ"`
   không bị `"Cần Thơ"` chiếm → phủ khoảng **98%**
2. **Điền tay theo mã trường** (`ref/truong_tinh_thucong.csv`) — 80 trường không có
   địa danh trong tên (Học viện Quân Y, ĐH Bách Khoa HCM, Đông Á…). Tầng này ưu tiên
   cao hơn nên **sửa được cả ca tầng 1 suy sai**
3. **Quy đổi tỉnh cũ → tỉnh sau sáp nhập 2025** (`ref/tinh_thanh.csv`) — 63 tỉnh về
   34, kèm vùng miền

Kết quả: **288/288 trường (100%)** — 29 tỉnh/thành; Miền Bắc 139, Miền Nam 83, Miền Trung 66.

> Sửa một trường bị gán sai: thêm 1 dòng vào `ref/truong_tinh_thucong.csv` rồi chạy lại.
> Không cần sửa code.

**`diem_chuan.csv` chỉ chứa THPT + học bạ** (thang 30/40) để so sánh và huấn luyện
được. Phương thức khác (ĐGNL, ĐGTD, V-SAT, CCQT…) có thang hoàn toàn khác (600,
1200 điểm…) nên nằm riêng ở sheet `PhuongThuc_Khac` trong Excel, **không trộn**.

### `cac_mon` — mã môn để AI ghép điểm

```
A00 → TOAN,LI,HOA        C14 → VAN,TOAN,GDCD
D01 → VAN,TOAN,ANH       D90 → TOAN,KHTN,ANH
X26 → TOAN,TIN,ANH       (NK = năng khiếu do trường tự tổ chức)
```

Phủ **99,58%** dòng điểm chuẩn. API tuyensinh247 chỉ có 279 mã trong khi dữ liệu
thực dùng 330 mã, nên phải ghép thêm danh mục Bộ GD&ĐT.

### Chuẩn hoá tên ngành (`nganh_slug`)

Nguồn đổi tên ngành mỗi năm nên chuỗi 5 năm bị đứt. Script gộp biến thể về 1 slug:

```
"Công nghệ Thông tin Việt-Nhật (Chương trình tiên tiến)"  ─┐
"Công nghệ thông tin (Việt - Nhật)"                        ├─> cong-nghe-thong-tin
"CNTT: Khoa học Máy tính"                                  ─┘
"CT tiên tiến Việt-Mỹ ngành điện tử viễn thông"            ──> dien-tu-vien-thong
```

5.829 tên gốc → **2.312 ngành**; chuỗi đủ 5 năm **9.643** (trước chuẩn hoá: 5.877, **+64%**).

---

## 4. Model Django (Tuần 2)

```python
class Truong(models.Model):
    ma_truong  = models.CharField(max_length=10, primary_key=True)
    ten_truong = models.CharField(max_length=255)
    viet_tat   = models.CharField(max_length=50, blank=True)
    tinh_thanh = models.CharField(max_length=50, blank=True, db_index=True)
    vung_mien  = models.CharField(max_length=30, blank=True)

class Nganh(models.Model):
    nganh_slug = models.SlugField(max_length=120, primary_key=True)
    ten_nganh  = models.CharField(max_length=255)
    nhom_nganh = models.CharField(max_length=50, db_index=True)

class ToHop(models.Model):
    ma_to_hop  = models.CharField(max_length=5, primary_key=True)   # A00
    ten_to_hop = models.CharField(max_length=150, blank=True)
    cac_mon    = models.CharField(max_length=100, blank=True)        # TOAN,LI,HOA

class DiemChuan(models.Model):
    truong      = models.ForeignKey(Truong, on_delete=models.CASCADE)
    nganh       = models.ForeignKey(Nganh,  on_delete=models.CASCADE)
    to_hop      = models.ForeignKey(ToHop,  on_delete=models.PROTECT)
    phuong_thuc = models.CharField(max_length=50)
    nam         = models.PositiveSmallIntegerField(db_index=True)
    diem_chuan  = models.FloatField()
    class Meta:
        unique_together = ("truong", "nganh", "to_hop", "phuong_thuc", "nam")
        indexes = [models.Index(fields=["nganh", "nam"])]
```

---

## 5. Đặc trưng cho AI (`dac_trung_diemchuan.csv`)

Mỗi dòng = 1 tổ hợp tuyển sinh (trường × ngành × tổ hợp × phương thức):

| cột | ý nghĩa |
|---|---|
| `diem_2021 … diem_2025` | chuỗi điểm chuẩn 5 năm (rỗng = năm đó không tuyển) |
| `diem_tb`, `diem_min`, `diem_max` | thống kê 5 năm |
| `diem_moi_nhat` | điểm năm gần nhất có dữ liệu — **feature quan trọng nhất** |
| `bien_dong` | `max − min`, độ dao động (rủi ro) |
| `xu_huong` | độ dốc hồi quy (điểm/năm): `> 0` tăng, `< 0` giảm |
| `so_nam_co_dl` | 1–5, dùng lọc chuỗi đáng tin (`>= 3`) |

**Dùng trong sklearn (Tuần 5):**

```python
# margin = năng lực học sinh so với điểm chuẩn mới nhất -> feature mạnh nhất
X["margin"] = diem_hoc_sinh - df.diem_moi_nhat
# nhãn khi chưa có dữ liệu đỗ/trượt thực: sinh từ lịch sử
y = (diem_hoc_sinh >= df.diem_chuan_nam_do).astype(int)
# hoặc 3 lớp: An toàn (margin >= 1) / Vừa (-0.5..1) / Khó (< -0.5)
RandomForestClassifier(n_estimators=300, min_samples_leaf=5)
```

Features: `margin`, `diem_moi_nhat`, `diem_tb`, `xu_huong`, `bien_dong`,
`so_nam_co_dl`, one-hot `nhom_nganh` + `vung_mien` → xác suất đỗ → **xếp hạng**
trường, giải thích bằng `margin` và `xu_huong`.

Ghép điểm học sinh với tổ hợp qua `cac_mon`:

```python
diem_hs = {"TOAN": 8.5, "LI": 7.75, "HOA": 8.0, "ANH": 9.0}
diem_to_hop = sum(diem_hs[m] for m in row.cac_mon.split(","))   # A00 -> 24.25
```

---

## 6. Khoảng trống dữ liệu

| Thiếu | Vì sao cần | Cách bổ sung |
|---|---|---|
| `nhom_nganh = "Khác"` — 218 ngành (**9,4%**) | phân loại chưa trúng | thêm từ khoá vào `MAJOR_GROUPS`; một phần là rác nguồn (`7340101`, `CTĐT`) không cứu được |
| 47/330 mã tổ hợp chưa có môn (**0,42%** dòng) | chủ yếu mã `R*`/`E*`/`T*` do trường tự đặt | bổ sung tay vào `SUBJECTS` trong `build_ref_tohop.py` |
| Chỉ tiêu, học phí, điểm sàn | tăng chất lượng gợi ý | đề án tuyển sinh / website trường |

> `tinh_thanh` / `vung_mien` **đã lấp xong** (100%) — xem mục 3.

---

## 7. Kiểm tra chất lượng

`--selfcheck` chạy tự động sau mỗi lần crawl:

- Khoá chính: **duy nhất + không NULL + không rỗng** (cả 4 bảng)
- Khoá ngoại: **không NULL + không mồ côi** (3 FK trong fact)
- Miền giá trị: điểm trong thang 0,01–40 · cửa sổ ≤ N năm · fact chỉ chứa 2 phương thức thang 30/40
- **Vị trí trường**: mọi trường có `tinh_thanh` · `vung_mien` chỉ nhận 3 giá trị hợp lệ
- **Không trùng khoá tự nhiên** — điều kiện để upsert hằng năm không nhân bản dòng
- Bảng đặc trưng: số cột năm khớp fact · `so_nam_co_dl` khớp số năm có dữ liệu ·
  `diem_moi_nhat` không NaN · khoá không NULL

Đã kiểm chứng bằng **negative test** (cố tình làm hỏng dữ liệu → self-check phải dừng):
NULL ở `nganh.nganh_slug`, xoá `tinh_thanh`, đặt `vung_mien = "Miền Tây"` — cả 3 đều
`AssertionError` (exit 1); dữ liệu thật exit 0.
