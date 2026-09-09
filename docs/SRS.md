# SRS — Uni Map
## Hệ thống gợi ý trường/ngành đại học bằng AI

# 1. Giới thiệu

## 1.1 Mục đích

Tài liệu đặc tả yêu cầu cho **Uni Map** — hệ thống web giúp học sinh lớp 12 tìm
trường/ngành đại học phù hợp với **điểm thi, tổ hợp môn, sở thích ngành và khu vực**
của mình. Hệ thống dùng **mô hình học máy** huấn luyện trên điểm chuẩn 5 năm gần nhất
để xếp hạng và **giải thích** mức độ phù hợp của từng nguyện vọng.

## 1.2 Phạm vi

**Trong phạm vi:**
- Tra cứu điểm chuẩn 2021–2025 của 288 trường đại học, 2.163 ngành, 328 tổ hợp môn
- Nhập điểm học sinh → gợi ý danh sách trường/ngành xếp hạng theo xác suất đỗ
- Phân tầng nguyện vọng: **An toàn / Vừa sức / Thử sức**
- Giải thích lý do gợi ý (khoảng cách điểm, xu hướng, độ dao động)
- Tài khoản người dùng, lưu lịch sử tra cứu
- Cập nhật dữ liệu hằng năm theo cơ chế cửa sổ trượt 5 năm

**Ngoài phạm vi:**
- Không đăng ký nguyện vọng thay học sinh (việc này thuộc hệ thống của Bộ GD&ĐT)
- Không dự đoán điểm chuẩn năm tới thành một con số tuyệt đối
- Không xử lý phương thức ĐGNL/ĐGTD/chứng chỉ quốc tế (khác thang điểm)
- Không tư vấn học phí, học bổng, ký túc xá

## 1.3 Thuật ngữ

| Thuật ngữ | Định nghĩa |
|---|---|
| **Tổ hợp môn** | Bộ 3 môn xét tuyển, có mã (`A00` = Toán, Lý, Hóa) |
| **Điểm chuẩn** | Điểm trúng tuyển thấp nhất của một ngành trong một năm |
| **Nguyện vọng (NV)** | Một lựa chọn (trường + ngành + tổ hợp) của học sinh |
| **`margin`** | Điểm học sinh − điểm chuẩn mới nhất. Dương = có lợi thế |
| **`xu_huong`** | Độ dốc hồi quy điểm chuẩn theo năm. Dương = ngành đang khó dần |
| **`bien_dong`** | max − min điểm chuẩn 5 năm. Cao = khó đoán, rủi ro |
| **Cửa sổ trượt** | Cơ chế luôn giữ đúng N năm mới nhất, tự bỏ năm cũ |
| **Chuỗi điểm** | Dãy điểm chuẩn nhiều năm của cùng một (trường, ngành, tổ hợp) |

# 2. Tổng quan hệ thống

## 2.1 Kiến trúc

```
┌─────────────┐   HTTP    ┌──────────────────────────────┐
│  Trình duyệt│ ────────► │  Django (view + REST)        │
│ HTML/CSS/JS │ ◄──────── │                              │
└─────────────┘           │  ┌────────────────────────┐  │
                          │  │ Recommendation Engine  │  │
                          │  │  ├ Lọc cứng (SQL)      │  │
                          │  │  ├ Tính margin         │  │
                          │  │  ├ RandomForest (AI)   │  │◄── model.pkl
                          │  │  └ Sinh lời giải thích │  │
                          │  └────────────────────────┘  │
                          └──────────────┬───────────────┘
                                         │ ORM
                                  ┌──────▼──────┐
                                  │    MySQL    │
                                  └──────▲──────┘
                                         │ import
        ┌────────────────────────────────┴──────────────┐
        │  crawl_diemchuan.py  (offline, chạy hằng năm) │
        │  requests → Pandas → CSV chuẩn hoá            │
        └───────────────────────────────────────────────┘
```

**Công nghệ** (theo `Plan.docx`): Python · Requests · Pandas/NumPy · Scikit-learn ·
Django · MySQL · HTML/CSS/JavaScript.

## 2.2 Tác nhân

| Tác nhân | Mô tả | Quyền |
|---|---|---|
| **Khách** | Chưa đăng nhập | Tra cứu điểm chuẩn, xem chi tiết trường |
| **Học sinh** | Đã đăng nhập | Toàn bộ quyền của Khách + nhập điểm, nhận gợi ý, lưu/so sánh nguyện vọng |
| **Quản trị viên** | Vận hành hệ thống | Cập nhật dữ liệu, huấn luyện lại mô hình, xem thống kê |
| **Bộ thu thập dữ liệu** | Tiến trình offline (không phải người) | Crawl nguồn, chuẩn hoá, xuất CSV |

## 2.3 Giả định và ràng buộc

| # | Nội dung |
|---|---|
| GĐ-1 | Điểm chuẩn lấy từ nguồn tổng hợp (`diemthi.tuyensinh247.com`), không phải đề án gốc từng trường → **phải ghi rõ nguồn trên UI** |
| GĐ-2 | Hệ thống chỉ dùng phương thức **Điểm thi THPT** và **Điểm học bạ** (thang 30/40) vì các phương thức khác không cùng thang, không so sánh được |
| GĐ-3 | Không có dữ liệu đỗ/trượt thật của học sinh → nhãn huấn luyện **sinh từ lịch sử điểm chuẩn** (mục 6.3) |
| RB-1 | Chỉ 9.709/91.581 chuỗi có đủ 5 năm → gợi ý phải hiển thị `so_nam_co_dl` để người dùng biết độ tin cậy |
| RB-2 | Dữ liệu cập nhật 1 lần/năm sau khi các trường công bố điểm chuẩn (khoảng tháng 8) |
| RB-3 | Chạy được trên máy sinh viên: không yêu cầu GPU, mô hình < 100 MB |
| RB-4 | Nguồn hỏng font ngẫu nhiên và công bố điểm chuẩn nhỏ giọt suốt mùa tuyển sinh → crawler phải tự vá và tự chặn năm chưa đủ dữ liệu (CN-08) |

# 3. Use case

## 3.1 Sơ đồ

```
                        ┌─────────────────────────────────┐
                        │          UNI MAP                │
                        │                                 │
   ┌───────┐            │  UC-01 Tra cứu điểm chuẩn       │
   │ Khách │────────────┤  UC-02 Xem chi tiết trường      │
   └───┬───┘            │  UC-03 Đăng ký / Đăng nhập      │
       │ kế thừa        │                                 │
   ┌───▼──────┐         │  UC-04 Nhập hồ sơ năng lực      │
   │ Học sinh │─────────┤  UC-05 Nhận gợi ý (AI)      ★   │
   └──────────┘         │  UC-06 Xem lời giải thích   ★   │
                        │  UC-07 So sánh nguyện vọng      │
                        │  UC-08 Lưu / xem lại hồ sơ      │
                        │                                 │
   ┌─────────────┐      │  UC-09 Cập nhật dữ liệu năm mới │
   │ Quản trị    │──────┤  UC-10 Huấn luyện lại mô hình ★ │
   └─────────────┘      │  UC-11 Xem thống kê hệ thống    │
                        └─────────────────────────────────┘
                                    ★ = có AI tham gia
```

## 3.2 Đặc tả use case chính

### UC-05 — Nhận gợi ý trường/ngành *(use case trung tâm)*

| | |
|---|---|
| **Tác nhân** | Học sinh |
| **Mục tiêu** | Nhận danh sách trường/ngành xếp hạng theo mức độ phù hợp |
| **Tiền điều kiện** | Đã đăng nhập; đã hoàn tất UC-04 (nhập hồ sơ năng lực) |
| **Hậu điều kiện** | Danh sách gợi ý được lưu vào lịch sử tra cứu |

**Luồng chính:**

1. Học sinh chọn "Xem gợi ý" từ trang hồ sơ
2. Hệ thống đọc hồ sơ: điểm từng môn, tổ hợp, nhóm ngành ưu tiên, khu vực ưu tiên
3. **Lọc cứng** (SQL): loại các nguyện vọng không khả thi
   - tổ hợp môn học sinh không có đủ điểm môn
   - không thuộc nhóm ngành / khu vực học sinh chọn
   - `so_nam_co_dl = 0` (không có dữ liệu lịch sử)
4. Hệ thống tính `margin = điểm_tổ_hợp − diem_moi_nhat` cho từng ứng viên còn lại
5. **Mô hình AI** nhận vector đặc trưng, trả **xác suất đỗ** cho từng nguyện vọng
6. Hệ thống phân tầng theo xác suất: An toàn (≥ 0,8) · Vừa sức (0,4–0,8) · Thử sức (< 0,4)
7. Hiển thị tối đa 30 gợi ý, sắp theo xác suất giảm dần, kèm chỉ báo độ tin cậy
8. Lưu kết quả vào lịch sử

**Luồng phụ / ngoại lệ:**

| Mã | Tình huống | Xử lý |
|---|---|---|
| 5a | Không có nguyện vọng nào qua bước lọc cứng | Thông báo + đề xuất nới điều kiện (bỏ giới hạn khu vực, thêm nhóm ngành) |
| 5b | Mô hình chưa được huấn luyện / lỗi tải | Chuyển sang **chế độ dự phòng**: xếp hạng bằng `margin` thuần, ghi rõ "chưa dùng AI" |
| 5c | Ít hơn 5 gợi ý | Vẫn hiển thị + gợi ý nới điều kiện |
| 7a | Chuỗi chỉ có 1–2 năm dữ liệu | Hiển thị nhãn cảnh báo "dữ liệu ít, độ tin cậy thấp" |

### UC-06 — Xem lời giải thích gợi ý

| | |
|---|---|
| **Tác nhân** | Học sinh |
| **Mục tiêu** | Hiểu **vì sao** hệ thống xếp một nguyện vọng ở tầng đó |

**Luồng chính:**

1. Học sinh bấm vào một nguyện vọng trong danh sách gợi ý
2. Hệ thống hiển thị:
   - Biểu đồ điểm chuẩn 5 năm của ngành đó
   - `margin`: "Bạn hơn điểm chuẩn 2025 là **+1,3 điểm**"
   - `xu_huong`: "Điểm chuẩn đang **tăng 0,4 điểm/năm**" (kèm cảnh báo nếu tăng)
   - `bien_dong`: "Dao động 5 năm: **2,1 điểm** — khá ổn định"
   - `so_nam_co_dl`: "Dựa trên **5/5 năm** dữ liệu"
   - Mức đóng góp của từng đặc trưng vào quyết định của mô hình
3. Hệ thống nêu rõ đây là **tham khảo dựa trên lịch sử**, không phải cam kết

### UC-09 — Cập nhật dữ liệu năm mới

| | |
|---|---|
| **Tác nhân** | Quản trị viên |
| **Tần suất** | 1 lần/năm (khoảng tháng 8, sau khi công bố điểm chuẩn) |

**Luồng chính:**

1. Quản trị chạy `python source/crawler/crawl_diemchuan.py --refresh`
2. Hệ thống crawl toàn bộ trường đại học của nguồn, gộp vào cache, vá font, làm
   sạch, **tự trượt cửa sổ** sang 5 năm mới nhất đã đủ dữ liệu
3. Self-check chạy tự động: khoá chính/ngoại, miền giá trị, khoá tự nhiên, vị trí trường
4. Nếu self-check thất bại → **dừng, không import** (bảo vệ dữ liệu đang chạy)
5. Import vào MySQL bằng upsert theo khoá tự nhiên; xoá năm rơi khỏi cửa sổ
6. Chuyển sang UC-10 để huấn luyện lại mô hình

**Ngoại lệ:**

| Mã | Tình huống | Xử lý |
|---|---|---|
| 2a | Nguồn đổi cấu trúc API | Crawler báo lỗi, giữ nguyên dữ liệu cũ, cần sửa crawler |
| 3a | Self-check thất bại | Ghi log lỗi cụ thể, không ghi vào DB |
| 5a | Import lỗi giữa chừng | Rollback transaction, DB giữ trạng thái trước import |

### UC-10 — Huấn luyện lại mô hình

| | |
|---|---|
| **Tác nhân** | Quản trị viên |
| **Tiền điều kiện** | UC-09 hoàn tất |

**Luồng chính:**

1. Quản trị chạy lệnh huấn luyện
2. Hệ thống dựng bảng đặc trưng, sinh nhãn từ lịch sử (mục 6.3)
3. Chia tập train/test theo **năm** (train 2021–2024, test 2025) — không chia ngẫu nhiên
4. Huấn luyện `RandomForestClassifier`, đánh giá bằng `accuracy_score` + `classification_report`
5. **So sánh với mô hình đang chạy**: chỉ thay thế nếu độ chính xác không giảm
6. Lưu `model.pkl` + báo cáo đánh giá + phiên bản dữ liệu đã dùng

# 4. User story

Ký hiệu ưu tiên: **P0** = bắt buộc cho MVP · **P1** = nên có · **P2** = nếu còn thời gian.

## 4.1 Nhóm: Tra cứu (Khách)

| ID | User story | Ưu tiên | Tuần |
|---|---|---|---|
| US-01 | Là **khách**, tôi muốn **tra điểm chuẩn một ngành qua các năm** để biết ngành đó đang dễ hay khó vào. | P0 | 6 |
| US-02 | Là **khách**, tôi muốn **lọc theo tỉnh/thành và vùng miền** để chỉ xem trường gần nhà. | P0 | 6 |
| US-03 | Là **khách**, tôi muốn **lọc theo tổ hợp môn** để chỉ thấy ngành tôi đủ môn xét tuyển. | P0 | 6 |
| US-04 | Là **khách**, tôi muốn **xem trang chi tiết một trường** với danh sách ngành và điểm chuẩn. | P1 | 6 |
| US-05 | Là **khách**, tôi muốn **biết nguồn dữ liệu và thời điểm cập nhật** để đánh giá độ tin cậy. | P0 | 6 |

**Tiêu chí chấp nhận US-01:**
- Nhập tên ngành (có gợi ý tự động) → hiện bảng điểm chuẩn 5 năm
- Có biểu đồ đường thể hiện xu hướng
- Năm không tuyển ngành đó hiển thị "—", không hiển thị 0
- Hiện rõ `so_nam_co_dl` nếu chuỗi thiếu năm

## 4.2 Nhóm: Hồ sơ năng lực (Học sinh)

| ID | User story | Ưu tiên | Tuần |
|---|---|---|---|
| US-06 | Là **học sinh**, tôi muốn **tạo tài khoản** để lưu lại hồ sơ và kết quả. | P0 | 6 |
| US-07 | Là **học sinh**, tôi muốn **nhập điểm từng môn** (Toán, Văn, Anh, Lý, Hóa…) thay vì phải tự cộng tổ hợp. | P0 | 6 |
| US-08 | Là **học sinh**, tôi muốn hệ thống **tự tính điểm mọi tổ hợp tôi đủ môn** để không bỏ sót cơ hội. | P0 | 7 |
| US-09 | Là **học sinh**, tôi muốn **chọn nhóm ngành quan tâm** để gợi ý sát nguyện vọng. | P0 | 6 |
| US-10 | Là **học sinh**, tôi muốn **chọn khu vực muốn học** để không nhận gợi ý quá xa. | P1 | 6 |
| US-11 | Là **học sinh**, tôi muốn **khai điểm ưu tiên (khu vực, đối tượng)** để kết quả chính xác hơn. | P2 | 9 |

**Tiêu chí chấp nhận US-07 / US-08:**
- Form nhập theo môn, ràng buộc 0 ≤ điểm ≤ 10
- Hệ thống dùng `to_hop.cac_mon` để xác định tổ hợp nào tính được
- Ví dụ: nhập `TOAN=8.5, LI=7.75, HOA=8.0, ANH=9.0` → tính được `A00 = 24.25`, `A01 = 25.25`
- Tổ hợp thiếu môn thì **bỏ qua im lặng**, không báo lỗi
- Tổ hợp chứa môn năng khiếu (`NK`) được đánh dấu "cần thi năng khiếu"

## 4.3 Nhóm: Gợi ý AI (Học sinh)

| ID | User story | Ưu tiên | Tuần |
|---|---|---|---|
| US-12 | Là **học sinh**, tôi muốn **nhận danh sách trường/ngành xếp theo mức phù hợp** để biết nên ưu tiên cái nào. | P0 | 7 |
| US-13 | Là **học sinh**, tôi muốn thấy nguyện vọng **chia thành An toàn / Vừa sức / Thử sức** để xếp thứ tự nguyện vọng hợp lý. | P0 | 8 |
| US-14 | Là **học sinh**, tôi muốn **biết vì sao** hệ thống gợi ý ngành đó, không chỉ thấy một con số. | P0 | 8 |
| US-15 | Là **học sinh**, tôi muốn **được cảnh báo khi điểm chuẩn ngành đang tăng nhanh** để lường rủi ro. | P1 | 8 |
| US-16 | Là **học sinh**, tôi muốn **biết gợi ý dựa trên bao nhiêu năm dữ liệu** để tự đánh giá độ tin cậy. | P0 | 8 |
| US-17 | Là **học sinh**, tôi muốn **so sánh 2–3 nguyện vọng cạnh nhau** để chọn giữa các phương án gần bằng nhau. | P1 | 9 |
| US-18 | Là **học sinh**, tôi muốn **xem lại các lần tra cứu trước** để theo dõi khi điểm thay đổi. | P2 | 9 |

**Tiêu chí chấp nhận US-13:**
- Ba tầng hiển thị riêng, có màu phân biệt và giải thích ngưỡng
- Mỗi tầng có ít nhất 1 gợi ý nếu dữ liệu cho phép
- Ngưỡng phân tầng ghi rõ trên UI, không để người dùng tự đoán

**Tiêu chí chấp nhận US-14:**
- Mỗi gợi ý nêu được: khoảng cách điểm (`margin`), xu hướng, độ dao động, số năm dữ liệu
- Có biểu đồ điểm chuẩn 5 năm
- Diễn đạt bằng tiếng Việt tự nhiên, không phơi tên biến kỹ thuật ra người dùng
- Có câu miễn trừ: kết quả là **tham khảo dựa trên lịch sử**, không đảm bảo đỗ

## 4.4 Nhóm: Vận hành (Quản trị viên)

| ID | User story | Ưu tiên | Tuần |
|---|---|---|---|
| US-19 | Là **quản trị**, tôi muốn **cập nhật dữ liệu bằng một lệnh** và tự động trượt sang 5 năm mới nhất. | P0 | 3–4 |
| US-20 | Là **quản trị**, tôi muốn **dữ liệu bị chặn khi không đạt kiểm tra chất lượng** để không phá DB đang chạy. | P0 | 4 |
| US-21 | Là **quản trị**, tôi muốn **huấn luyện lại mô hình và xem báo cáo đánh giá** trước khi thay thế bản đang dùng. | P0 | 5 |
| US-22 | Là **quản trị**, tôi muốn **sửa dữ liệu gán sai (tỉnh, nhóm ngành) bằng cách chỉnh file CSV**, không phải sửa code. | P1 | 4 |
| US-23 | Là **quản trị**, tôi muốn **xem thống kê lượt tra cứu và ngành được quan tâm nhất**. | P2 | 11 |

**Tiêu chí chấp nhận US-19:** ✅ *đã hoàn thành*
- `python source/crawler/crawl_diemchuan.py --refresh` chạy trọn quy trình
- Tự phát hiện năm mới nhất **đã đủ dữ liệu**; khi 2026 đủ → cửa sổ tự thành
  2022–2026, không sửa code, không `ALTER TABLE`
- Self-check chạy tự động cuối quy trình

**Tiêu chí chấp nhận US-22:** ✅ *đã hoàn thành*
- Sửa tỉnh của một trường = thêm 1 dòng vào `ref/truong_tinh_thucong.csv`
- Sửa phân nhóm ngành = thêm từ khoá vào `MAJOR_GROUPS`

# 5. Chức năng đặc thù

Đây là các chức năng **không có ở một trang tra cứu điểm chuẩn thông thường** — chúng
là điểm khác biệt của Uni Map và đều bắt nguồn từ cách dữ liệu đã được chuẩn hoá.

## CN-01 — Tự tính điểm mọi tổ hợp từ điểm từng môn

**Vấn đề:** Học sinh có 4–6 môn, hệ thống có 328 tổ hợp. Tự dò xem mình đủ điều kiện
tổ hợp nào là việc rất mệt và dễ bỏ sót.

**Cách làm:** Bảng `to_hop.cac_mon` lưu mã môn dạng máy đọc được:

```
A00 → TOAN,LI,HOA        D01 → VAN,TOAN,ANH
C14 → VAN,TOAN,GDCD      D90 → TOAN,KHTN,ANH
X26 → TOAN,TIN,ANH       H00 → VAN,NK,NK      (NK = năng khiếu)
```

```python
diem_hs = {"TOAN": 8.5, "LI": 7.75, "HOA": 8.0, "ANH": 9.0}
for to_hop in ToHop.objects.all():
    mon = to_hop.cac_mon.split(",")
    if all(m in diem_hs for m in mon):          # đủ môn thì mới tính
        diem_to_hop = sum(diem_hs[m] for m in mon)
```

→ Một lần nhập điểm, hệ thống quét **toàn bộ** cơ hội xét tuyển.

**Phụ thuộc dữ liệu:** `cac_mon` phủ **99,58%** dòng điểm chuẩn. Dựng từ danh mục
344 tổ hợp của Bộ GD&ĐT 2025 + API nguồn (API một mình chỉ có 279/330 mã).

## CN-02 — Nối chuỗi điểm nhiều năm qua tên ngành đã chuẩn hoá

**Vấn đề:** Nguồn đổi tên ngành gần như mỗi năm. Nếu so khớp theo tên thô, chuỗi 5
năm bị **cắt vụn** thành nhiều mảnh 1 năm → không tính được xu hướng.

```
"Công nghệ Thông tin Việt-Nhật (Chương trình tiên tiến)"   ─┐
"Công nghệ thông tin (Việt - Nhật)"                         ├─→ cong-nghe-thong-tin
"CNTT: Khoa học Máy tính"                                   ─┘
"CT tiên tiến Việt-Mỹ ngành điện tử viễn thông"             ──→ dien-tu-vien-thong
```

**Kết quả đo được:** 4.754 tên gốc trong cửa sổ → **2.163 ngành**. Số chuỗi đủ 5
năm là **9.709** (so với 5.877 nếu khớp theo tên thô). Đây là điều kiện để
`xu_huong` có ý nghĩa thống kê.


## CN-03 — Phân tầng nguyện vọng An toàn / Vừa sức / Thử sức

**Vấn đề:** Biết "xác suất đỗ 62%" không giúp học sinh **xếp thứ tự nguyện vọng**.

**Cách làm:** Chuyển xác suất thành 3 tầng hành động được:

| Tầng | Ngưỡng | Ý nghĩa với học sinh |
|---|---|---|
| 🟢 **An toàn** | p ≥ 0,80 | Đặt cuối danh sách làm chốt an toàn |
| 🟡 **Vừa sức** | 0,40 ≤ p < 0,80 | Nhóm chính, nên đặt giữa |
| 🔴 **Thử sức** | p < 0,40 | Đặt đầu danh sách, được thì tốt |

Mỗi tầng luôn có gợi ý (nếu dữ liệu cho phép) → học sinh có ngay một danh sách
nguyện vọng cân bằng rủi ro.

## CN-04 — Giải thích gợi ý bằng ngôn ngữ tự nhiên

**Vấn đề:** Mô hình xác suất là hộp đen. Học sinh sẽ không tin một con số không có
lý do kèm theo.

**Cách làm:** Mỗi gợi ý sinh ra 4 câu từ đặc trưng thật:

| Đặc trưng | Câu hiển thị |
|---|---|
| `margin = +1.3` | "Bạn **hơn 1,3 điểm** so với điểm chuẩn 2025" |
| `xu_huong = +0.4` | "⚠️ Điểm chuẩn đang **tăng ~0,4 điểm/năm** — cân nhắc rủi ro" |
| `bien_dong = 2.1` | "Dao động 5 năm: **2,1 điểm** — tương đối ổn định" |
| `so_nam_co_dl = 5` | "Dựa trên **5/5 năm** dữ liệu — độ tin cậy cao" |

Không phơi tên biến kỹ thuật ra người dùng. Kèm biểu đồ điểm 5 năm và câu miễn trừ.

## CN-05 — Cửa sổ trượt 5 năm tự động

**Vấn đề:** Điểm chuẩn 2015 không còn giá trị tham chiếu; nhưng nếu cắt cứng
`2021–2025` trong code thì mỗi năm phải sửa lại.

**Cách làm:** Script tự phát hiện năm mới nhất trong dữ liệu rồi lùi N năm.

```bash
python source/crawler/crawl_diemchuan.py --refresh   # 2026 đủ dữ liệu → tự thành 2022–2026
python source/crawler/crawl_diemchuan.py --years 3   # muốn 3 năm
```

Cache dữ liệu thô (`cache/raw.csv.gz`, giữ mọi năm từ 2010) cho phép **đổi cửa sổ
mà không crawl lại**.

**Trạng thái:** ✅ đã hoàn thành và kiểm chứng.

## CN-06 — Lọc theo khu vực đã hợp nhất tỉnh 2025

**Vấn đề:** Nguồn không có tỉnh/thành của trường. Thêm nữa, Việt Nam vừa sáp nhập
63 tỉnh còn 34 (2025) → dữ liệu địa danh cũ đã lệch.

**Cách làm:** Dựng qua 3 tầng, tầng sau ghi đè tầng trước:

1. Suy từ địa danh trong tên trường (`ref/dia_danh.csv`) → phần lớn trường (~98%)
2. Điền tay theo mã trường cho trường không có địa danh trong tên
   (`ref/truong_tinh_thucong.csv`) — học viện quân đội/công an, ĐH Bách Khoa HCM…
3. Quy đổi tỉnh cũ → tỉnh sau sáp nhập + vùng miền (`ref/tinh_thanh.csv`)

**Kết quả:** **288/288 trường (100%)** — 29 tỉnh/thành; Miền Bắc 139, Nam 83, Trung 66.


**Trạng thái:** ✅ đã hoàn thành.

## CN-07 — Cổng chất lượng dữ liệu (data quality gate)

**Vấn đề:** Nếu nguồn đổi cấu trúc, dữ liệu rác lặng lẽ chảy vào DB rồi vào cả mô
hình — lỗi phát hiện rất muộn.

**Cách làm:** `--selfcheck` chạy tự động cuối mỗi lần crawl, **chặn import** nếu sai:

- Khoá chính: duy nhất + không NULL + không rỗng (4 bảng)
- Khoá ngoại: không NULL + không mồ côi (3 FK)
- Miền giá trị: điểm ∈ [0,01 ; 40] · cửa sổ ≤ N năm · chỉ 2 phương thức cùng thang
- Vị trí trường: mọi trường có `tinh_thanh` · `vung_mien` ∈ {Bắc, Trung, Nam}
- **Không trùng khoá tự nhiên** — điều kiện để upsert hằng năm không nhân bản dòng
- **Không có dòng chiều thừa** — mọi trường/ngành/tổ hợp phải có dòng điểm chuẩn
  trỏ tới, nếu không nó thành dữ liệu rác trên UI
- **Không còn ký tự hỏng font** (`U+FFFD`) trong các bảng chiều
- Bảng đặc trưng khớp bảng fact

Đã kiểm chứng bằng **negative test**: cố tình làm hỏng 6 kiểu dữ liệu (3 kiểu ban
đầu + tiêm ký tự hỏng + bỏ dòng chiều + thêm dòng chiều thừa) → cả 6 đều
`AssertionError` (exit 1); dữ liệu thật exit 0.

**Trạng thái:** ✅ đã hoàn thành.

## CN-08 — Chịu được nguồn hỏng font và công bố nhỏ giọt

**Vấn đề:** Nguồn có ba hành vi phá dữ liệu, cả ba đều âm thầm:

1. **Hỏng font ngẫu nhiên.** Cùng một URL, mỗi lần gọi trả về 10–26 ô có ký tự
   `U+FFFD` ở **những vị trí khác nhau** (đo trên 1,8 MB JSON của ĐH Kinh Tế Quốc
   Dân, 6 lần gọi liên tiếp: không lần nào sạch). Byte trên đường truyền hợp lệ
   UTF-8 — lỗi nằm ở dữ liệu của nguồn, không phải ở tầng mạng.
2. **Bỏ bớt năm cũ.** Giữa hai lần crawl, nguồn bỏ toàn bộ 2010–2012 và phần lớn
   2013–2015 (mất 22.054 dòng).
3. **Công bố nhỏ giọt.** Đầu tháng 9/2026 chỉ có 445 dòng cho năm 2026 — 4,5% so
   với trung vị các năm trước.

**Hậu quả nếu không xử lý:** Hỏng font làm một ngành bị tách thành nhiều slug
(`Quản trị kinh doanh` và `Quản tr␦␦ kinh doanh` là hai ngành khác nhau) → chuỗi
điểm bị cắt vụn, đúng cái CN-02 phải chống. Cửa sổ nhận năm 2026 thì số chuỗi đủ
5 năm sụp từ **9.643 xuống 223** → `xu_huong` mất ý nghĩa thống kê.

**Cách làm — bốn tầng:**

| Tầng | Cách | Kết quả đo được |
|---|---|---|
| Tải lại và gộp | Mỗi trường tải tối đa 3 lần, gộp theo `id` dòng của nguồn, giữ bản sạch | Phần lớn ô hỏng biến mất ngay ở tầng này |
| Vá theo biến thể | Mỗi cụm `U+FFFD` = đúng 1 ký tự → khớp `Du l␦␦ch` với `Du l.ch` → tìm `Du lịch`. Nhiều ứng viên thì chọn tên xuất hiện nhiều nhất | **137/141** tên hỏng được vá; 4 tên còn lại nằm ngoài cửa sổ |
| Cache tích luỹ | Crawl **gộp** vào `cache/raw.csv.gz`, không ghi đè | Giữ được 2010–2026 dù nguồn chỉ còn từ 2013 |
| Cổng năm mới | Năm mới nhất phải đạt ≥ 50% trung vị các năm trước mới vào cửa sổ | 2026 bị loại tự động, cửa sổ giữ 2021–2025, chuỗi đủ 5 năm **9.709** |

Cổng năm mới **không phải ngưỡng cứng theo lịch**: sang tháng 8/2027 khi nguồn đã
công bố đủ, năm mới tự được nhận — vẫn không phải sửa code, đúng điều CN-05 hứa.

**Trạng thái:** ✅ đã hoàn thành, còn 0 ô hỏng trong toàn bộ DB.

## CN-09 — Dọn rác khi cập nhật hằng năm

**Vấn đề:** Import dùng upsert nên chỉ **thêm và cập nhật**, không bao giờ xoá.
Khi crawler sửa được một tên ngành hỏng font, `nganh_slug` đổi → khoá tự nhiên
đổi → bản cũ nằm lại trong DB vĩnh viễn. Đo thực tế sau một lần sửa font: **290
dòng fact và 150 dòng ngành** rác. Nguồn bỏ bớt ngành giữa hai năm để lại rác y
như vậy. Người dùng sẽ thấy ngành `Quản tr␦␦ kinh doanh` trên trang tra cứu.

**Cách làm:** Sau khi nạp, so DB với CSV rồi xoá phần thừa, theo thứ tự:

1. `don_fact_la` — xoá dòng `diem_chuan` / `dac_trung_diemchuan` không còn trong CSV
2. `don_nam_cu` — xoá năm đã rơi khỏi cửa sổ trượt
3. `don_dim_mo_coi` — xoá trường/ngành/tổ hợp không còn dòng fact nào trỏ tới

**An toàn với dữ liệu học sinh:** Bước 3 giữ lại mọi dòng còn được
`ket_qua_goi_y` tham chiếu, vì FK đó là `ON DELETE CASCADE` — xoá ngành sẽ xoá
luôn lịch sử gợi ý. Toàn bộ chạy trong transaction, `--dry-run` rollback được
(bảng tạm dùng `TEMPORARY TABLE` nên không gây implicit commit).

**Chống tái phát tại gốc:** `export_csv` giờ dựng **fact trước, dim dẫn xuất từ
fact**. Trước đây dim dựng từ `df` — vốn còn chứa ĐGNL/ĐGTD (có mã tổ hợp nhưng
khác thang, bị loại khỏi fact) — nên sinh ra 88 ngành và 2 tổ hợp không có dòng
điểm chuẩn nào. Sửa gốc thì cổng CN-07 mới có thể yêu cầu "không dòng chiều thừa".

**Kiểm chứng:** chạy import lần hai trên cùng dữ liệu → 0 dòng bị dọn
(idempotent). Đổi cửa sổ sang 3 năm → dọn đúng 48.117 dòng fact và 415 ngành,
`cua_so_nam` thành 3 dòng, không cần `ALTER TABLE`.

**Trạng thái:** ✅ đã hoàn thành.

# 6. AI nằm ở bước nào

## 6.1 Vị trí AI trong luồng xử lý

AI **không** đứng ở đầu luồng và **không** làm mọi việc. Nó nằm ở **bước 4** trong
chuỗi 6 bước, và chỉ đảm nhiệm đúng một việc: **cho điểm xác suất đỗ**.

```
   Học sinh nhập điểm từng môn
              │
   ┌──────────▼───────────────────────────────────────────────┐
   │ BƯỚC 1 — GHÉP TỔ HỢP            (Python thuần, KHÔNG AI) │
   │ Dùng to_hop.cac_mon: đủ môn thì cộng điểm                │
   │ Ra: danh sách (tổ hợp, điểm) học sinh đạt được           │
   └──────────┬───────────────────────────────────────────────┘
              │
   ┌──────────▼───────────────────────────────────────────────┐
   │ BƯỚC 2 — LỌC CỨNG                     (SQL, KHÔNG AI)    │
   │ Loại: sai tổ hợp · sai nhóm ngành · sai khu vực ·        │
   │       so_nam_co_dl = 0                                   │
   │ ~92k ứng viên → còn vài trăm                             │
   └──────────┬───────────────────────────────────────────────┘
              │
   ┌──────────▼───────────────────────────────────────────────┐
   │ BƯỚC 3 — DỰNG ĐẶC TRƯNG           (Pandas, KHÔNG AI)     │
   │ margin = điểm_tổ_hợp − diem_moi_nhat                     │
   │ + diem_tb, xu_huong, bien_dong, so_nam_co_dl,            │
   │   one-hot nhom_nganh & vung_mien                         │
   └──────────┬───────────────────────────────────────────────┘
              │
   ╔══════════▼═══════════════════════════════════════════════╗
   ║ BƯỚC 4 — CHO ĐIỂM               ★★★ ĐÂY LÀ AI ★★★        ║
   ║ RandomForestClassifier.predict_proba(X)                   ║
   ║ Vào : vector đặc trưng của từng nguyện vọng               ║
   ║ Ra  : xác suất đỗ p ∈ [0, 1]                              ║
   ╚══════════┬═══════════════════════════════════════════════╝
              │
   ┌──────────▼───────────────────────────────────────────────┐
   │ BƯỚC 5 — PHÂN TẦNG + XẾP HẠNG      (ngưỡng, KHÔNG AI)    │
   │ p ≥ 0,8 An toàn · 0,4–0,8 Vừa sức · < 0,4 Thử sức        │
   └──────────┬───────────────────────────────────────────────┘
              │
   ┌──────────▼───────────────────────────────────────────────┐
   │ BƯỚC 6 — SINH LỜI GIẢI THÍCH   (template, KHÔNG AI sinh) │
   │ Đọc lại đặc trưng thật + độ quan trọng đặc trưng của     │
   │ mô hình → 4 câu tiếng Việt                               │
   └──────────────────────────────────────────────────────────┘
```

**Tóm lại:** AI chỉ ở **bước 4**. Năm bước còn lại là logic tường minh — điều này
làm hệ thống **kiểm thử được, giải thích được**, và vẫn chạy khi mô hình lỗi
(chế độ dự phòng UC-05/5b: xếp hạng bằng `margin` thuần).

## 6.2 Vì sao không dùng AI ở các bước khác

| Bước | Vì sao không cần AI |
|---|---|
| 1 — Ghép tổ hợp | Quy tắc xác định: đủ môn thì cộng. Dùng AI ở đây là sai — sẽ tạo ra kết quả không đúng quy chế tuyển sinh |
| 2 — Lọc cứng | Điều kiện loại trừ tuyệt đối (không đủ môn = không được xét). Phải chắc chắn, không xác suất |
| 3 — Dựng đặc trưng | Phép trừ và tra bảng. AI chỉ làm chậm và mờ đi |
| 5 — Phân tầng | Ngưỡng phải công khai để học sinh hiểu, không nên ẩn trong mô hình |
| 6 — Giải thích | Template từ số liệu thật thì **luôn đúng**. Sinh văn bản bằng LLM có nguy cơ nói sai số liệu |

## 6.3 Nhãn huấn luyện: bài toán không có dữ liệu đỗ/trượt thật

Hệ thống **không có** dữ liệu học sinh nào đỗ/trượt (GĐ-3). Nhãn được **sinh từ
lịch sử điểm chuẩn** — mỗi dòng điểm chuẩn lịch sử là một "sự thật" đã xảy ra:

> Nếu một thí sinh có điểm `X` xét vào ngành có điểm chuẩn `C` năm đó,
> thì kết quả là **đỗ khi `X ≥ C`**.

```python
# Sinh mẫu huấn luyện từ 178.825 dòng điểm chuẩn lịch sử
# Với mỗi (trường, ngành, tổ hợp) và mỗi năm t, tạo các thí sinh giả lập
# có điểm quanh điểm chuẩn, rồi gán nhãn theo kết quả thật của năm đó.
X = features(diem_gia_lap, dac_trung_tinh_den_nam_t_tru_1)
y = (diem_gia_lap >= diem_chuan_nam_t).astype(int)
```

**Điểm cốt yếu:** đặc trưng chỉ được tính từ **các năm trước năm `t`**. Nếu dùng
điểm chuẩn của chính năm `t` để dự đoán năm `t` thì mô hình chỉ học lại đáp án
(data leakage) — độ chính xác đẹp nhưng vô dụng khi triển khai.

**Chia tập theo năm, không chia ngẫu nhiên:**

| Tập | Năm | Vai trò |
|---|---|---|
| Train | 2021–2024 | Học quy luật |
| Test | 2025 | Mô phỏng đúng tình huống thật: dùng quá khứ dự đoán năm chưa biết |

Chia ngẫu nhiên sẽ để năm 2025 lọt vào tập train → rò rỉ thông tin tương lai.

## 6.4 Đặc trưng đưa vào mô hình

| Đặc trưng | Nguồn | Vai trò kỳ vọng |
|---|---|---|
| **`margin`** | tính lúc chạy | **Mạnh nhất** — khoảng cách năng lực với ngưỡng |
| `diem_moi_nhat` | `dac_trung_diemchuan` | Mốc tham chiếu gần nhất |
| `diem_tb` | `dac_trung_diemchuan` | Mức chung của ngành, giảm ảnh hưởng năm bất thường |
| `xu_huong` | `dac_trung_diemchuan` | Ngành đang khó dần hay dễ dần |
| `bien_dong` | `dac_trung_diemchuan` | Độ khó đoán → rủi ro |
| `so_nam_co_dl` | `dac_trung_diemchuan` | Cho mô hình biết dữ liệu dày hay mỏng |
| `nhom_nganh` (one-hot) | `nganh` | Mức cạnh tranh theo khối ngành |
| `vung_mien` (one-hot) | `truong` | Chênh lệch điểm theo vùng |
| `phuong_thuc` | `diem_chuan` | THPT và học bạ có mức điểm khác nhau |

Toàn bộ đặc trưng **đã có sẵn** trong `data/dac_trung_diemchuan.csv` (91.581 dòng)
— nhưng **không dùng trực tiếp để huấn luyện**: các cột ở đó tổng hợp trên cả 5
năm, kể cả năm cần dự đoán. Dùng thẳng là data leakage (mục 6.6). Khi huấn luyện
phải dựng lại đặc trưng theo từng năm cắt: với mỗi năm `t`, chỉ dùng điểm chuẩn
của các năm `< t`. File này chỉ dùng để **suy luận** — lúc chạy thật, mọi năm
trong cửa sổ đều là quá khứ.


## 6.5 Thuật toán và pipeline

Theo `Plan.docx`, dùng đúng bộ thư viện đã chốt:

```python
from sklearn.model_selection import train_test_split      # chia theo năm
from sklearn.preprocessing   import StandardScaler
from sklearn.tree            import DecisionTreeClassifier
from sklearn.ensemble        import RandomForestClassifier
from sklearn.metrics         import accuracy_score, classification_report
```

| Bước | Nội dung |
|---|---|
| Baseline | `DecisionTreeClassifier` — dễ đọc luật, dùng để đối chiếu |
| Chính | `RandomForestClassifier(n_estimators=300, min_samples_leaf=5)` |
| Chuẩn hoá | `StandardScaler` cho đặc trưng số |
| Đánh giá | `accuracy_score` + `classification_report` (precision/recall theo lớp) |
| Giải thích | `feature_importances_` → hiển thị mức đóng góp ở UC-06 |

**Vì sao Random Forest:** dữ liệu dạng bảng, quan hệ phi tuyến (margin +2 điểm không
gấp đôi giá trị margin +1), có `feature_importances_` sẵn để giải thích, không cần
GPU (RB-3), và chịu được đặc trưng thiếu (`so_nam_co_dl` nhỏ).

## 6.6 Rủi ro của AI và cách giảm

| Rủi ro | Ảnh hưởng | Cách giảm |
|---|---|---|
| **Data leakage** — dùng điểm năm `t` để dự đoán năm `t` | Độ chính xác ảo, sai khi chạy thật | Đặc trưng chỉ từ năm < `t`; test riêng năm 2025 |
| **Nhãn sinh từ lịch sử ≠ thực tế** | Bỏ qua biến động số thí sinh, đề thi, chỉ tiêu | Nêu rõ giới hạn trên UI; ưu tiên xếp hạng tương đối hơn là con số tuyệt đối |
| **Chuỗi 1–2 năm dữ liệu** | `xu_huong` không đáng tin | Đưa `so_nam_co_dl` vào cả mô hình và UI; cảnh báo khi < 3 năm |
| **Học sinh coi xác suất là cam kết** | Kỳ vọng sai, quyết định sai | Câu miễn trừ bắt buộc; dùng chữ "tham khảo"; không hiển thị số lẻ quá chi tiết |
| **Mô hình mới kém hơn bản đang chạy** | Chất lượng gợi ý tụt | UC-10 bước 5: chỉ thay thế nếu độ chính xác không giảm |
| **Mô hình lỗi khi chạy** | Không có gợi ý | Chế độ dự phòng: xếp hạng bằng `margin`, ghi rõ "chưa dùng AI" |

# 7. Yêu cầu phi chức năng

| Mã | Loại | Yêu cầu |
|---|---|---|
| PC-01 | Hiệu năng | Trả gợi ý trong **< 3 giây** với 1 hồ sơ (lọc cứng bằng SQL có index, không quét toàn bảng) |
| PC-02 | Hiệu năng | Trang tra cứu điểm chuẩn phản hồi **< 1 giây**; phân trang khi > 50 dòng |
| PC-03 | Bảo mật | Mật khẩu băm bằng cơ chế mặc định của Django (PBKDF2), không lưu dạng thô |
| PC-04 | Bảo mật | Chống SQL injection và XSS bằng Django ORM + auto-escape template; bật CSRF cho mọi form |
| PC-05 | Bảo mật | Điểm và hồ sơ của học sinh chỉ chủ tài khoản xem được |
| PC-06 | Khả dụng | UI tiếng Việt, dùng được trên điện thoại (đa số học sinh tra cứu bằng điện thoại) |
| PC-07 | Khả dụng | Mọi form có kiểm tra hợp lệ và thông báo lỗi bằng tiếng Việt rõ nghĩa |
| PC-08 | Truy cập | Tương phản màu đạt WCAG AA; **không dùng màu làm cách phân biệt duy nhất** giữa 3 tầng nguyện vọng (kèm nhãn chữ + biểu tượng) |
| PC-09 | Bảo trì | Sửa dữ liệu gán sai (tỉnh, nhóm ngành, tổ hợp) bằng cách chỉnh CSV trong `ref/`, không sửa code |
| PC-10 | Toàn vẹn | Import bị chặn nếu self-check thất bại; import chạy trong transaction, lỗi thì rollback |
| PC-11 | Minh bạch | Mọi trang có dữ liệu điểm chuẩn phải ghi **nguồn + thời điểm cập nhật** |
| PC-12 | Minh bạch | Mọi kết quả gợi ý kèm câu miễn trừ: tham khảo dựa trên lịch sử, không đảm bảo đỗ |

---

# 8. Mô hình dữ liệu

Chi tiết đầy đủ trong `docs/README_DATA.md`. Sơ đồ quan hệ:

```
truong (288)          nganh (2.163)         to_hop (328)
  ma_truong  PK         nganh_id   PK         ma_to_hop PK
  ten_truong            nganh_slug UQ         ten_to_hop
  viet_tat              ten_nganh             cac_mon    ← CN-01
  tinh_thanh  ← CN-06   nhom_nganh            so_mon
  vung_mien   ← CN-06
      │                     │                     │
      └─────────────────────┼─────────────────────┘
                            │
                 diem_chuan (178.825)  ← bảng fact
                   id PK
                   ma_truong   FK
                   nganh_id    FK
                   ma_to_hop   FK
                   phuong_thuc      (THPT | học bạ)
                   nam              (2021–2025)
                   diem_chuan
                   UNIQUE(ma_truong, nganh_id, ma_to_hop, phuong_thuc, nam)
                            │
                            ▼ tổng hợp (lưu DB để đạt PC-01 < 3s)
                 dac_trung_diemchuan (91.581)  ← input cho AI, bước 3–4
                   diem_nam_1 … diem_nam_5     ← đặt theo VỊ TRÍ, không theo năm
                   diem_tb, diem_min, diem_max, diem_moi_nhat
                   bien_dong, so_nam_co_dl, xu_huong
                            │
                 cua_so_nam (5)  ← vị trí cột 1..5 → năm thật
                   vi_tri PK, nam UQ
```

Hai chi tiết khiến cập nhật hằng năm **không cần đổi cấu trúc bảng**:

`diem_nam_1..5` đặt tên theo **vị trí**, không theo năm. Cửa sổ trượt sang
2022–2026 thì chỉ nội dung đổi, không `ALTER TABLE`. Bảng `cua_so_nam` cho biết
vị trí nào ứng với năm nào; cửa sổ nhỏ hơn 5 năm thì các cột cuối để NULL.

`nganh_id` (surrogate key) làm khoá ngoại thay cho `nganh_slug`. Slug có thể đổi
khi crawler sửa được tên hỏng font hoặc nguồn đổi tên ngành; `nganh_slug` vẫn giữ
`UNIQUE` để dùng cho URL và cho import khớp CSV.

**Trạng thái dữ liệu hiện tại:**

| Hạng mục | Tình trạng |
|---|---|
| Khoá chính / khoá ngoại | ✅ không NULL, không mồ côi, không trùng |
| Khoá tự nhiên (nền tảng upsert) | ✅ không trùng |
| Dòng chiều thừa (không có fact) | ✅ 0 — dim dẫn xuất từ fact |
| Ký tự hỏng font (`U+FFFD`) | ✅ 0 trong toàn bộ DB (vá 137/141 tên) |
| `tinh_thanh` / `vung_mien` | ✅ 100% (288/288) |
| `cac_mon` | ✅ 99,58% dòng |
| `nhom_nganh` | ⚠️ ~9% còn "Khác" |
| Cửa sổ 5 năm tự động | ✅ 2021–2025, tự trượt, có cổng chặn năm chưa đủ |

Số trường là **288**, không phải 289: Nhạc Viện TPHCM bị loại vì nguồn ghi tổ hợp
là `1` — không rút được mã tổ hợp nào nên không có dòng điểm chuẩn hợp lệ. Trường
không tra cứu được thì không nên xuất hiện trên UI.

---

# 9. Truy vết yêu cầu → tuần thực hiện

| Tuần (`Plan.docx`) | Trọng tâm | Use case / User story | Trạng thái |
|---|---|---|---|
| 1 | Phân tích & thiết kế | Toàn bộ SRS này | ✅ |
| 2 | Database & Backend | Mục 8 · US-19 | ✅ |
| 3 | Cào dữ liệu | UC-09 · US-19 · CN-05 | ✅ |
| 4 | Xử lý dữ liệu | CN-01, CN-02, CN-06, CN-07 · US-20, US-22 | ✅ |
| 5 | Xây dựng AI | UC-10 · Mục 6 · US-21 | ⏳ |
| 6 | Website & tài khoản | UC-01→04 · US-01→11 | ⏳ |
| 7 | Tích hợp AI + Web | UC-05 · US-08, US-12 | ⏳ |
| 8 | Trang kết quả & giải thích | UC-06 · CN-03, CN-04 · US-13→16 | ⏳ |
| 9 | Hoàn thiện & cải tiến AI | US-11, US-17, US-18 | ⏳ |
| 10 | Đóng gói | PC-01→12 | ⏳ |
| 11–12 | Kiểm thử + báo cáo | Toàn bộ tiêu chí chấp nhận · US-23 | ⏳ |

**Đã xong (tuần 2–4):** thu thập và chuẩn hoá dữ liệu (CN-01, CN-02, CN-06, CN-07),
lược đồ MySQL đã dựng và nạp đủ dữ liệu, tầng model Django đã khớp lược đồ.

**Việc kế tiếp:** tuần 5 — pipeline sklearn (mục 6). Nền dữ liệu và ORM đã sẵn sàng.

## 9.1 Trạng thái backend (tuần 2)

```
Uni-Map/
├── source/
│   ├── crawler/    crawl_diemchuan.py · build_ref_tohop.py   (Python thuần)
│   └── backend/    config/ · manage.py · tracuu/             (Django 5.2.8)
├── data/  db/  ref/  cache/     ← dùng chung giữa crawler và backend
└── docs/                        ← SRS.md · README_DATA.md · Plan.docx

uni_map (MySQL 8.0.30)  truong 288 · nganh 2.163 · to_hop 328 · mon 27
                        to_hop_mon 848 · diem_chuan 178.825
                        dac_trung_diemchuan 91.581 · cua_so_nam 5 (2021–2025)

tracuu/models.py  14 model, tất cả managed=False — schema.sql là nguồn sự thật
```

Dữ liệu và `db/` để ở gốc, không nhét vào `source/`, vì crawler ghi và backend
đọc cùng bộ file đó — không thuộc riêng bên nào. Mọi script neo đường dẫn theo
`__file__` nên chạy được từ bất kỳ thư mục nào.

**Lệnh vận hành hằng năm (SRS UC-09) — theo đúng thứ tự:**

1. Crawl và tự trượt cửa sổ. Tự gộp cache, vá font, chặn năm chưa đủ, chạy self-check cuối cùng:

```bash
python source/crawler/crawl_diemchuan.py --refresh
```

2. Dựng lược đồ — **chỉ lần đầu**. Câu lệnh này mở đầu bằng `DROP DATABASE IF EXISTS uni_map`, tức là xoá sạch dữ liệu đang có. Không chạy lại sau khi đã import:

```bash
mysql -u root --default-character-set=utf8mb4 < db/schema.sql
```

3. Thử import rồi rollback, không ghi gì vào DB:

```bash
python db/import_mysql.py --dry-run
```

4. Import thật (chỉ chạy nếu bước 1 và 3 đều đạt):

```bash
python db/import_mysql.py
```

5. Đăng ký migration Django — **chỉ lần đầu**. `--fake-initial` vì `auth_user` đã có sẵn từ `schema.sql`:

```bash
PYTHONIOENCODING=utf-8 python source/backend/manage.py migrate --fake-initial
```

6. Kiểm tra tầng ORM khớp DB (8 phép kiểm, chỉ đọc):

```bash
PYTHONIOENCODING=utf-8 python source/backend/manage.py kiemtra
```

**Hai điều dễ sai trên Windows:**

`--default-character-set=utf8mb4` ở bước 2 là **bắt buộc**. Thiếu nó, MySQL client
dùng cp1252 và làm hỏng giá trị ENUM tiếng Việt (`'Miền Bắc'`) ngay lúc
`CREATE TABLE` → mọi INSERT sau đó fail `Data truncated for column 'vung_mien'`.

`PYTHONIOENCODING=utf-8` cần cho mọi management command in tiếng Việt, nếu không
lệnh chết giữa đường với `UnicodeEncodeError` — trông như đã chạy xong.







