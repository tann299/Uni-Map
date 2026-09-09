-- =============================================================================
--  UNI MAP — LƯỢC ĐỒ CƠ SỞ DỮ LIỆU (MySQL 8.0+)
-- =============================================================================
--  Hệ thống gợi ý trường/ngành đại học bằng AI.
--  Tài liệu liên quan: docs/SRS.md (mục 8), docs/README_DATA.md
--
--  Gồm 3 nhóm bảng:
--    A. DỮ LIỆU THAM CHIẾU  — trường, ngành, tổ hợp, môn  (crawl 1 lần/năm)
--    B. DỮ LIỆU SỰ KIỆN     — điểm chuẩn + đặc trưng cho AI
--    C. DỮ LIỆU NGƯỜI DÙNG  — hồ sơ năng lực, lịch sử gợi ý
--
--  Chạy:  mysql -u root --default-character-set=utf8mb4 -p < schema.sql
--
--  BẮT BUỘC có --default-character-set=utf8mb4. Thiếu nó, MySQL client trên
--  Windows dùng cp1252 và làm hỏng giá trị ENUM tiếng Việt ('Miền Bắc') ngay
--  lúc CREATE TABLE -> mọi INSERT sau đó fail "Data truncated for column".
--  Kiểm tra: SHOW CREATE TABLE truong; enum phải đọc được, không phải ký tự lạ.
-- =============================================================================

DROP DATABASE IF EXISTS uni_map;
CREATE DATABASE uni_map
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;      -- utf8mb4: cần cho tiếng Việt + emoji
USE uni_map;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
--  A. DỮ LIỆU THAM CHIẾU
-- =============================================================================

-- -----------------------------------------------------------------------------
--  truong — 289 trường đại học
--  ma_truong dùng làm khoá chính vì nó là mã tự nhiên, ngắn (≤3 ký tự),
--  ổn định qua các năm và xuất hiện trong mọi nguồn dữ liệu.
-- -----------------------------------------------------------------------------
CREATE TABLE truong (
    ma_truong    VARCHAR(10)  NOT NULL COMMENT 'Mã trường, vd BKA, QSB',
    ten_truong   VARCHAR(150) NOT NULL,
    viet_tat     VARCHAR(20)  NOT NULL DEFAULT '' COMMENT 'vd HUST, HCMUT',
    tinh_thanh   VARCHAR(30)  NOT NULL COMMENT 'Tỉnh sau sáp nhập 2025',
    vung_mien    ENUM('Miền Bắc','Miền Trung','Miền Nam') NOT NULL,

    PRIMARY KEY (ma_truong),
    KEY idx_truong_tinh (tinh_thanh),
    KEY idx_truong_vung (vung_mien)
) ENGINE=InnoDB COMMENT='Trường đại học';

-- -----------------------------------------------------------------------------
--  nganh — 2.312 ngành (tên đã chuẩn hoá, gộp biến thể theo năm)
--
--  QUYẾT ĐỊNH THIẾT KẾ: dùng khoá thay thế nganh_id INT thay vì nganh_slug.
--  Lý do: slug dài tới 287 ký tự; nếu làm khoá chính thì bảng diem_chuan
--  (178k dòng) tốn ~3,6 MB chỉ riêng cột khoá (INT chỉ 0,7 MB) và mọi
--  index phụ đều phải chứa lại khoá chính đó.
--  Slug vẫn giữ UNIQUE để dùng cho URL và cho bước import (đối chiếu CSV).
--  Đã kiểm chứng: cắt slug ở 120 ký tự KHÔNG gây trùng (2.312/2.312 vẫn duy nhất).
-- -----------------------------------------------------------------------------
CREATE TABLE nganh (
    nganh_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nganh_slug  VARCHAR(120) NOT NULL COMMENT 'Khoá tự nhiên, dùng cho URL',
    ten_nganh   VARCHAR(320) NOT NULL COMMENT 'Tên đã chuẩn hoá',
    nhom_nganh  VARCHAR(40)  NOT NULL COMMENT '15 nhóm, vd Công nghệ thông tin',

    PRIMARY KEY (nganh_id),
    UNIQUE KEY uq_nganh_slug (nganh_slug),
    KEY idx_nganh_nhom (nhom_nganh)
) ENGINE=InnoDB COMMENT='Ngành học (tên đã chuẩn hoá)';

-- -----------------------------------------------------------------------------
--  mon — 26 môn xét tuyển. Tách riêng để:
--    * học sinh nhập điểm theo môn (US-07)
--    * biết môn nào là năng khiếu -> cảnh báo "cần thi năng khiếu"
-- -----------------------------------------------------------------------------
CREATE TABLE mon (
    ma_mon      VARCHAR(15) NOT NULL COMMENT 'TOAN, LI, HOA, GDKTPL...',
    ten_mon     VARCHAR(60) NOT NULL,
    la_nang_khieu TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1 = trường tự tổ chức thi',
    thu_tu      TINYINT UNSIGNED NOT NULL DEFAULT 99 COMMENT 'Thứ tự hiển thị trên form',

    PRIMARY KEY (ma_mon)
) ENGINE=InnoDB COMMENT='Môn xét tuyển';

-- -----------------------------------------------------------------------------
--  to_hop — 330 tổ hợp môn
--  Giữ cột cac_mon dạng chuỗi 'TOAN,LI,HOA' để đọc nhanh khi hiển thị,
--  đồng thời chuẩn hoá thành bảng to_hop_mon để JOIN/lọc bằng SQL.
-- -----------------------------------------------------------------------------
CREATE TABLE to_hop (
    ma_to_hop   VARCHAR(5)  NOT NULL COMMENT 'A00, D01, X26...',
    ten_to_hop  VARCHAR(80) NOT NULL DEFAULT '' COMMENT 'Toán, Vật lý, Hóa học',
    cac_mon     VARCHAR(60) NOT NULL DEFAULT '' COMMENT 'TOAN,LI,HOA (phi chuẩn hoá, để đọc nhanh)',
    so_mon      TINYINT UNSIGNED NOT NULL DEFAULT 0,
    nguon       VARCHAR(20) NOT NULL DEFAULT '' COMMENT 'BoGD2025 | tuyensinh247',

    PRIMARY KEY (ma_to_hop)
) ENGINE=InnoDB COMMENT='Tổ hợp môn xét tuyển';

-- -----------------------------------------------------------------------------
--  to_hop_mon — bảng nối tổ hợp <-> môn (dạng chuẩn hoá của to_hop.cac_mon)
--  Cho phép truy vấn kiểu: "tổ hợp nào chỉ gồm các môn học sinh đã nhập?"
-- -----------------------------------------------------------------------------
CREATE TABLE to_hop_mon (
    ma_to_hop  VARCHAR(5)  NOT NULL,
    ma_mon     VARCHAR(15) NOT NULL,
    vi_tri     TINYINT UNSIGNED NOT NULL COMMENT 'Vị trí môn trong tổ hợp (1..3)',

    PRIMARY KEY (ma_to_hop, ma_mon, vi_tri),
    KEY idx_thm_mon (ma_mon),
    CONSTRAINT fk_thm_tohop FOREIGN KEY (ma_to_hop) REFERENCES to_hop (ma_to_hop)
        ON DELETE CASCADE,
    CONSTRAINT fk_thm_mon   FOREIGN KEY (ma_mon)    REFERENCES mon (ma_mon)
        ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Nối tổ hợp - môn';

-- =============================================================================
--  B. DỮ LIỆU SỰ KIỆN
-- =============================================================================

-- -----------------------------------------------------------------------------
--  diem_chuan — BẢNG FACT, 178.821 dòng
--  Mỗi dòng = điểm chuẩn của (trường × ngành × tổ hợp × phương thức × năm).
--
--  KHOÁ TỰ NHIÊN (uq_diem_chuan) là nền tảng của cập nhật hằng năm:
--  import dùng INSERT ... ON DUPLICATE KEY UPDATE nên chạy lại nhiều lần
--  cũng không nhân bản dòng (idempotent).
--
--  Chỉ chứa 2 phương thức cùng thang 30/40. ĐGNL/ĐGTD/CCQT có thang khác
--  (600, 1200 điểm...) nên KHÔNG trộn vào đây - xem SRS mục 2.3 GĐ-2.
-- -----------------------------------------------------------------------------
CREATE TABLE diem_chuan (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    ma_truong    VARCHAR(10)  NOT NULL,
    nganh_id     INT UNSIGNED NOT NULL,
    ma_to_hop    VARCHAR(5)   NOT NULL,
    phuong_thuc  ENUM('Điểm thi THPT','Điểm học bạ') NOT NULL,
    nam          SMALLINT UNSIGNED NOT NULL,
    diem_chuan   DECIMAL(4,2) NOT NULL COMMENT 'Thang 0-40 (có hệ số năng khiếu)',
    ten_nganh_goc VARCHAR(512) NOT NULL DEFAULT '' COMMENT 'Tên gốc từ nguồn, để truy vết',

    PRIMARY KEY (id),
    UNIQUE KEY uq_diem_chuan (ma_truong, nganh_id, ma_to_hop, phuong_thuc, nam),

    -- Index cho truy vấn tra cứu (UC-01): điểm chuẩn 1 ngành qua các năm
    KEY idx_dc_nganh_nam (nganh_id, nam),
    -- Index cho bước lọc cứng của engine gợi ý (UC-05 bước 3)
    KEY idx_dc_tohop_nam (ma_to_hop, nam),
    KEY idx_dc_truong_nam (ma_truong, nam),

    CONSTRAINT fk_dc_truong FOREIGN KEY (ma_truong) REFERENCES truong (ma_truong)
        ON DELETE CASCADE,
    CONSTRAINT fk_dc_nganh  FOREIGN KEY (nganh_id)  REFERENCES nganh (nganh_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_dc_tohop  FOREIGN KEY (ma_to_hop) REFERENCES to_hop (ma_to_hop)
        ON DELETE RESTRICT,

    CONSTRAINT chk_dc_diem CHECK (diem_chuan > 0 AND diem_chuan <= 40),
    CONSTRAINT chk_dc_nam  CHECK (nam BETWEEN 2000 AND 2100)
) ENGINE=InnoDB COMMENT='Điểm chuẩn theo năm (bảng fact)';

-- -----------------------------------------------------------------------------
--  dac_trung_diemchuan — 91.782 dòng, INPUT CHO AI (SRS mục 6.4)
--
--  Đây là bảng DẪN XUẤT: tổng hợp từ diem_chuan, dựng lại sau mỗi lần cập nhật.
--  Lưu vào DB (thay vì tính lúc chạy) vì engine gợi ý cần đọc nó cho hàng trăm
--  ứng viên trong mỗi request, phải đạt yêu cầu < 3 giây (SRS PC-01).
--
--  Các cột diem_nam_1..5 là chuỗi điểm theo cửa sổ trượt. Đặt tên theo VỊ TRÍ
--  (không phải diem_2021) để sang năm không phải ALTER TABLE - bảng
--  cua_so_nam cho biết vị trí nào ứng với năm nào.
-- -----------------------------------------------------------------------------
CREATE TABLE dac_trung_diemchuan (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    ma_truong     VARCHAR(10)  NOT NULL,
    nganh_id      INT UNSIGNED NOT NULL,
    ma_to_hop     VARCHAR(5)   NOT NULL,
    phuong_thuc   ENUM('Điểm thi THPT','Điểm học bạ') NOT NULL,

    -- chuỗi điểm theo cửa sổ trượt; NULL = năm đó ngành không tuyển
    diem_nam_1    DECIMAL(4,2) NULL COMMENT 'Năm cũ nhất trong cửa sổ',
    diem_nam_2    DECIMAL(4,2) NULL,
    diem_nam_3    DECIMAL(4,2) NULL,
    diem_nam_4    DECIMAL(4,2) NULL,
    diem_nam_5    DECIMAL(4,2) NULL COMMENT 'Năm mới nhất trong cửa sổ',

    -- đặc trưng tổng hợp
    diem_tb       DECIMAL(4,2) NOT NULL,
    diem_min      DECIMAL(4,2) NOT NULL,
    diem_max      DECIMAL(4,2) NOT NULL,
    diem_moi_nhat DECIMAL(4,2) NOT NULL COMMENT 'Điểm năm gần nhất CÓ dữ liệu',
    bien_dong     DECIMAL(5,2) NOT NULL COMMENT 'max - min, độ dao động = rủi ro',
    xu_huong      DECIMAL(6,3) NOT NULL COMMENT 'Độ dốc hồi quy điểm/năm',
    so_nam_co_dl  TINYINT UNSIGNED NOT NULL COMMENT '1-5, độ tin cậy của chuỗi',

    PRIMARY KEY (id),
    UNIQUE KEY uq_dt (ma_truong, nganh_id, ma_to_hop, phuong_thuc),

    -- Index chính cho bước lọc cứng: engine tìm theo tổ hợp trước
    KEY idx_dt_tohop (ma_to_hop, so_nam_co_dl),
    KEY idx_dt_nganh (nganh_id),
    KEY idx_dt_truong (ma_truong),

    CONSTRAINT fk_dt_truong FOREIGN KEY (ma_truong) REFERENCES truong (ma_truong)
        ON DELETE CASCADE,
    CONSTRAINT fk_dt_nganh  FOREIGN KEY (nganh_id)  REFERENCES nganh (nganh_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_dt_tohop  FOREIGN KEY (ma_to_hop) REFERENCES to_hop (ma_to_hop)
        ON DELETE RESTRICT,

    CONSTRAINT chk_dt_sonam CHECK (so_nam_co_dl BETWEEN 1 AND 5)
) ENGINE=InnoDB COMMENT='Đặc trưng cho mô hình AI (bảng dẫn xuất)';

-- -----------------------------------------------------------------------------
--  cua_so_nam — vị trí cột -> năm thật. Chỉ 5 dòng.
--  Cho phép đổi cửa sổ (2021-2025 -> 2022-2026) mà KHÔNG ALTER TABLE.
-- -----------------------------------------------------------------------------
CREATE TABLE cua_so_nam (
    vi_tri  TINYINT UNSIGNED NOT NULL COMMENT '1..5, khớp diem_nam_1..5',
    nam     SMALLINT UNSIGNED NOT NULL,

    PRIMARY KEY (vi_tri),
    UNIQUE KEY uq_csn_nam (nam)
) ENGINE=InnoDB COMMENT='Ánh xạ vị trí cột -> năm (cửa sổ trượt)';

-- -----------------------------------------------------------------------------
--  lan_cap_nhat — nhật ký cập nhật dữ liệu (SRS UC-09, PC-11)
--  Dùng để hiển thị "Dữ liệu cập nhật ngày ..." và để truy vết khi có sự cố.
-- -----------------------------------------------------------------------------
CREATE TABLE lan_cap_nhat (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    thoi_diem     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    nguon         VARCHAR(100) NOT NULL,
    nam_bat_dau   SMALLINT UNSIGNED NOT NULL,
    nam_ket_thuc  SMALLINT UNSIGNED NOT NULL,
    so_truong     SMALLINT UNSIGNED NOT NULL,
    so_nganh      SMALLINT UNSIGNED NOT NULL,
    so_dong_diem  INT UNSIGNED NOT NULL,
    selfcheck_dat TINYINT(1)   NOT NULL COMMENT '0 = không import',
    ghi_chu       VARCHAR(500) NOT NULL DEFAULT '',

    PRIMARY KEY (id),
    KEY idx_lcn_thoidiem (thoi_diem)
) ENGINE=InnoDB COMMENT='Nhật ký cập nhật dữ liệu';

-- =============================================================================
--  C. DỮ LIỆU NGƯỜI DÙNG
-- =============================================================================
--  auth_user do Django tạo (django.contrib.auth). Khai báo dưới đây khớp đúng
--  định nghĩa của Django và dùng IF NOT EXISTS, nên:
--    * Chạy schema.sql trước  -> bảng được tạo, `manage.py migrate` dùng lại được
--    * Chạy migrate trước     -> câu lệnh này bị bỏ qua, không ảnh hưởng
--  Mục đích: schema.sql chạy được độc lập để kiểm thử, không cần dựng Django.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_user (
    id           INT          NOT NULL AUTO_INCREMENT,
    password     VARCHAR(128) NOT NULL,
    last_login   DATETIME(6)  NULL,
    is_superuser TINYINT(1)   NOT NULL,
    username     VARCHAR(150) NOT NULL,
    first_name   VARCHAR(150) NOT NULL,
    last_name    VARCHAR(150) NOT NULL,
    email        VARCHAR(254) NOT NULL,
    is_staff     TINYINT(1)   NOT NULL,
    is_active    TINYINT(1)   NOT NULL,
    date_joined  DATETIME(6)  NOT NULL,

    PRIMARY KEY (id),
    UNIQUE KEY username (username)
) ENGINE=InnoDB COMMENT='Người dùng (do Django quản lý)';

-- -----------------------------------------------------------------------------
--  ho_so_nang_luc — hồ sơ của học sinh (SRS UC-04, US-07..US-11)
--  Một học sinh có thể có nhiều hồ sơ (thi thử nhiều lần, hoặc thử "nếu điểm
--  cao hơn thì sao") -> KHÔNG đặt UNIQUE trên user_id.
-- -----------------------------------------------------------------------------
CREATE TABLE ho_so_nang_luc (
    id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id        INT          NOT NULL,
    ten_ho_so      VARCHAR(100) NOT NULL DEFAULT 'Hồ sơ của tôi',
    phuong_thuc    ENUM('Điểm thi THPT','Điểm học bạ') NOT NULL DEFAULT 'Điểm thi THPT',
    diem_uu_tien   DECIMAL(3,2) NOT NULL DEFAULT 0 COMMENT 'Điểm ưu tiên KV/đối tượng (US-11)',
    vung_mien_uu_tien VARCHAR(60) NOT NULL DEFAULT '' COMMENT 'Rỗng = không giới hạn',
    ngay_tao       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ngay_sua       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_hs_user (user_id, ngay_sua),

    CONSTRAINT fk_hs_user FOREIGN KEY (user_id) REFERENCES auth_user (id)
        ON DELETE CASCADE,
    CONSTRAINT chk_hs_uutien CHECK (diem_uu_tien BETWEEN 0 AND 2.75)
) ENGINE=InnoDB COMMENT='Hồ sơ năng lực của học sinh';

-- -----------------------------------------------------------------------------
--  diem_mon — điểm từng môn của một hồ sơ (US-07)
--  Lưu theo môn, KHÔNG lưu theo tổ hợp: hệ thống tự suy ra mọi tổ hợp học sinh
--  đủ điều kiện (CN-01). Nhập 1 lần, quét được toàn bộ cơ hội.
-- -----------------------------------------------------------------------------
CREATE TABLE diem_mon (
    ho_so_id  INT UNSIGNED NOT NULL,
    ma_mon    VARCHAR(15)  NOT NULL,
    diem      DECIMAL(4,2) NOT NULL,

    PRIMARY KEY (ho_so_id, ma_mon),

    CONSTRAINT fk_dm_hoso FOREIGN KEY (ho_so_id) REFERENCES ho_so_nang_luc (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_dm_mon  FOREIGN KEY (ma_mon)   REFERENCES mon (ma_mon)
        ON DELETE RESTRICT,
    CONSTRAINT chk_dm_diem CHECK (diem BETWEEN 0 AND 10)
) ENGINE=InnoDB COMMENT='Điểm từng môn của hồ sơ';

-- -----------------------------------------------------------------------------
--  nhom_nganh_quan_tam — nhóm ngành học sinh chọn (US-09)
-- -----------------------------------------------------------------------------
CREATE TABLE nhom_nganh_quan_tam (
    ho_so_id   INT UNSIGNED NOT NULL,
    nhom_nganh VARCHAR(40)  NOT NULL,

    PRIMARY KEY (ho_so_id, nhom_nganh),
    CONSTRAINT fk_nnqt_hoso FOREIGN KEY (ho_so_id) REFERENCES ho_so_nang_luc (id)
        ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Nhóm ngành học sinh quan tâm';

-- -----------------------------------------------------------------------------
--  lan_goi_y — mỗi lần chạy engine gợi ý (SRS UC-05, US-18)
--  Lưu phiên bản mô hình để truy vết: nếu sau này mô hình đổi, vẫn biết kết quả
--  cũ được sinh bởi bản nào.
-- -----------------------------------------------------------------------------
CREATE TABLE lan_goi_y (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    ho_so_id      INT UNSIGNED NOT NULL,
    thoi_diem     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    phien_ban_mo_hinh VARCHAR(50) NOT NULL DEFAULT '' COMMENT 'Rỗng = chế độ dự phòng (UC-05/5b)',
    dung_ai       TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '0 = xếp hạng bằng margin thuần',
    so_ket_qua    SMALLINT UNSIGNED NOT NULL DEFAULT 0,

    PRIMARY KEY (id),
    KEY idx_lgy_hoso (ho_so_id, thoi_diem),

    CONSTRAINT fk_lgy_hoso FOREIGN KEY (ho_so_id) REFERENCES ho_so_nang_luc (id)
        ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Lịch sử các lần gợi ý';

-- -----------------------------------------------------------------------------
--  ket_qua_goi_y — từng nguyện vọng trong một lần gợi ý (SRS UC-05, UC-06)
--
--  Lưu lại xac_suat_do và margin ĐÚNG THỜI ĐIỂM gợi ý. Không tính lại khi
--  xem lại lịch sử, vì điểm chuẩn trong DB có thể đã cập nhật -> con số sẽ
--  khác với những gì học sinh đã thấy.
-- -----------------------------------------------------------------------------
CREATE TABLE ket_qua_goi_y (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    lan_goi_y_id  INT UNSIGNED NOT NULL,
    ma_truong     VARCHAR(10)  NOT NULL,
    nganh_id      INT UNSIGNED NOT NULL,
    ma_to_hop     VARCHAR(5)   NOT NULL,
    phuong_thuc   ENUM('Điểm thi THPT','Điểm học bạ') NOT NULL,

    diem_hoc_sinh DECIMAL(4,2) NOT NULL COMMENT 'Điểm tổ hợp của học sinh (đã cộng ưu tiên)',
    margin        DECIMAL(5,2) NOT NULL COMMENT 'diem_hoc_sinh - diem_moi_nhat',
    xac_suat_do   DECIMAL(5,4) NOT NULL COMMENT 'Đầu ra của mô hình, 0.0000-1.0000',
    tang          ENUM('An toàn','Vừa sức','Thử sức') NOT NULL,
    thu_hang      SMALLINT UNSIGNED NOT NULL,
    da_luu        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'Học sinh đánh dấu quan tâm',

    PRIMARY KEY (id),
    UNIQUE KEY uq_kqgy (lan_goi_y_id, ma_truong, nganh_id, ma_to_hop, phuong_thuc),
    KEY idx_kqgy_lan (lan_goi_y_id, thu_hang),
    KEY idx_kqgy_luu (lan_goi_y_id, da_luu),

    CONSTRAINT fk_kqgy_lan    FOREIGN KEY (lan_goi_y_id) REFERENCES lan_goi_y (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_kqgy_truong FOREIGN KEY (ma_truong) REFERENCES truong (ma_truong)
        ON DELETE CASCADE,
    CONSTRAINT fk_kqgy_nganh  FOREIGN KEY (nganh_id)  REFERENCES nganh (nganh_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_kqgy_tohop  FOREIGN KEY (ma_to_hop) REFERENCES to_hop (ma_to_hop)
        ON DELETE RESTRICT,

    CONSTRAINT chk_kqgy_xs CHECK (xac_suat_do BETWEEN 0 AND 1)
) ENGINE=InnoDB COMMENT='Kết quả từng nguyện vọng được gợi ý';

-- =============================================================================
--  D. VIEW TIỆN DỤNG
-- =============================================================================

-- Điểm chuẩn kèm tên đầy đủ - dùng cho trang tra cứu (UC-01, UC-02)
CREATE OR REPLACE VIEW v_diem_chuan AS
SELECT dc.id, dc.nam, dc.diem_chuan, dc.phuong_thuc,
       t.ma_truong, t.ten_truong, t.viet_tat, t.tinh_thanh, t.vung_mien,
       n.nganh_id, n.nganh_slug, n.ten_nganh, n.nhom_nganh,
       th.ma_to_hop, th.ten_to_hop, th.cac_mon
FROM diem_chuan dc
JOIN truong t  ON t.ma_truong = dc.ma_truong
JOIN nganh  n  ON n.nganh_id  = dc.nganh_id
JOIN to_hop th ON th.ma_to_hop = dc.ma_to_hop;

-- Ứng viên cho engine gợi ý: đặc trưng + thông tin lọc, đã bỏ chuỗi 0 năm
CREATE OR REPLACE VIEW v_ung_vien AS
SELECT dt.*,
       t.ten_truong, t.tinh_thanh, t.vung_mien,
       n.nganh_slug, n.ten_nganh, n.nhom_nganh,
       th.cac_mon, th.so_mon
FROM dac_trung_diemchuan dt
JOIN truong t  ON t.ma_truong = dt.ma_truong
JOIN nganh  n  ON n.nganh_id  = dt.nganh_id
JOIN to_hop th ON th.ma_to_hop = dt.ma_to_hop
WHERE dt.so_nam_co_dl >= 1;

-- =============================================================================
--  E. DỮ LIỆU HẠT GIỐNG: bảng mon (26 môn)
-- =============================================================================
INSERT INTO mon (ma_mon, ten_mon, la_nang_khieu, thu_tu) VALUES
  ('TOAN','Toán',0,1),
  ('VAN','Ngữ văn',0,2),
  ('ANH','Tiếng Anh',0,3),
  ('LI','Vật lý',0,4),
  ('HOA','Hóa học',0,5),
  ('SINH','Sinh học',0,6),
  ('SU','Lịch sử',0,7),
  ('DIA','Địa lý',0,8),
  ('GDKTPL','Giáo dục kinh tế và pháp luật',0,9),
  ('TIN','Tin học',0,10),
  ('CN_CN','Công nghệ công nghiệp',0,11),
  ('CN_NN','Công nghệ nông nghiệp',0,12),
  ('GDCD','Giáo dục công dân',0,13),
  ('KHTN','Khoa học tự nhiên',0,14),
  ('KHXH','Khoa học xã hội',0,15),
  ('NGA','Tiếng Nga',0,16),
  ('PHAP','Tiếng Pháp',0,17),
  ('TRUNG','Tiếng Trung',0,18),
  ('NHAT','Tiếng Nhật',0,19),
  ('DUC','Tiếng Đức',0,20),
  ('HAN','Tiếng Hàn',0,21),
  ('NGOAI_NGU','Ngoại ngữ (bất kỳ)',0,22),
  ('KT_NGHE','Kĩ thuật nghề',0,23),
  ('KHOAHOC_ANH','Khoa học / Tiếng Anh',0,24),
  ('NK','Năng khiếu',1,90),
  ('DGTD_DL','Tư duy định lượng',1,91),
  ('DGTD_DT','Tư duy định tính',1,92);

-- =============================================================================
--  F. GHI CHÚ VẬN HÀNH
-- =============================================================================
--  Cập nhật hằng năm (SRS UC-09) — thứ tự bắt buộc:
--    1. python crawl_diemchuan.py --refresh     (tự trượt cửa sổ + self-check)
--    2. python db/import_mysql.py               (chỉ chạy nếu self-check ĐẠT)
--
--  Import dùng INSERT ... ON DUPLICATE KEY UPDATE trên các khoá tự nhiên
--  (uq_diem_chuan, uq_dt, uq_nganh_slug) nên chạy lại nhiều lần vẫn an toàn.
--
--  Sau import, xoá năm đã rơi khỏi cửa sổ:
--    DELETE FROM diem_chuan WHERE nam < (SELECT MIN(nam) FROM cua_so_nam);
--
--  Bảng dac_trung_diemchuan được dựng lại toàn bộ mỗi lần (TRUNCATE + INSERT)
--  vì nó là dữ liệu dẫn xuất, không có giá trị lịch sử riêng.
-- =============================================================================



