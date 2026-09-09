# -*- coding: utf-8 -*-
"""
================================================================================
 CRAWLER ĐIỂM CHUẨN ĐẠI HỌC  —  dự án "Uni Map" (AI gợi ý trường/ngành)
================================================================================
Nguồn:
  * diemthi.tuyensinh247.com (API JSON công khai)
        GET /api/school/search                        -> danh sách trường
        GET /api/common/blocks                        -> tổ hợp môn
        GET /api/common/cutoff-score?school_id={id}   -> điểm chuẩn mọi năm
  * ref/to_hop_mon.csv — bảng tra tổ hợp môn (331 mã) dựng từ danh mục 344 tổ hợp
    của Bộ GD&ĐT 2025 + API. Tạo lại bằng: python source/crawler/build_ref_tohop.py

Tính năng:
  1. CACHE TÍCH LUỸ (cache/raw.csv.gz) — mỗi lần crawl GỘP vào cache cũ, không
     ghi đè. Nguồn bỏ bớt năm cũ thì lịch sử ở đây vẫn còn.
  2. CỬA SỔ TRƯỢT N năm tự động (mặc định 5) — sang năm không sửa code. Năm mới
     nhất chỉ được nhận khi đã đủ dữ liệu (xem chon_nam_cuoi).
  3. CHUẨN HOÁ TÊN NGÀNH thành slug -> nối liền chuỗi điểm nhiều năm.
  4. SCHEMA SAO: fact dựng trước, dim dẫn xuất TỪ fact -> không sinh dim rác.
  5. `cac_mon` cho 99,6% dòng -> AI ghép được điểm từng môn của học sinh.
  6. VÁ FONT: nguồn ngẫu nhiên trả byte hỏng (U+FFFD); tải lại + khớp biến thể
     sạch (xem fetch_school, repair_mojibake).
  7. SELF-CHECK chặn NULL khoá, mồ côi khoá ngoại, trùng khoá tự nhiên.

Dùng (chạy từ gốc dự án; mọi đường dẫn neo theo __file__ nên CWD nào cũng được):
    pip install -r requirements.txt
    python source/crawler/crawl_diemchuan.py                 # dùng cache nếu có
    python source/crawler/crawl_diemchuan.py --refresh       # crawl mới (hằng năm)
    python source/crawler/crawl_diemchuan.py --years 3       # đổi cửa sổ
    python source/crawler/crawl_diemchuan.py --end 2025      # khoá năm cuối
    python source/crawler/crawl_diemchuan.py --selfcheck     # chỉ kiểm dữ liệu đã xuất
================================================================================
"""

from __future__ import annotations

import argparse
import os
import random
import re
import sys
import time
import unicodedata as ud
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import numpy as np
import pandas as pd
import requests
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ============================================================================
# CẤU HÌNH
# ============================================================================
ORIGIN = "https://diemthi.tuyensinh247.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": ORIGIN + "/diem-chuan.html",
}

LATEST_N_YEARS = 5        # cửa sổ trượt: số năm mới nhất muốn giữ
END_YEAR       = None     # None = tự lấy năm mới nhất ĐỦ DỮ LIỆU
LEVEL_DAIHOC   = 2        # 2 = Đại học, 1 = Cao đẳng
MAX_WORKERS    = 8

# Nguồn ngẫu nhiên trả byte hỏng -> json.loads thay bằng U+FFFD. Mỗi lần gọi
# hỏng ở ô khác nhau (đo được 10–26 ô / 1,8 MB), nên tải lại rồi gộp bản sạch
# theo id dòng thì vá được gần hết. Xem repair_mojibake() cho phần còn lại.
BAD_CHAR        = "�"
CORRUPT_RETRIES = 3       # số lần tải lại 1 trường khi còn ô hỏng

# Năm mới nhất phải có >= tỉ lệ này so với trung vị các năm trước mới được vào
# cửa sổ. Nguồn công bố nhỏ giọt (tháng 8 mới đủ); nhận sớm sẽ làm chuỗi 5 năm
# sụp về gần 0 vì năm mới gần như rỗng.
MIN_YEAR_RATIO = 0.5

# Neo mọi đường dẫn vào gốc dự án (2 cấp trên: source/crawler/ -> gốc), không
# theo thư mục đang đứng. Nhờ vậy chạy được từ bất kỳ đâu:
#     python source/crawler/crawl_diemchuan.py
ROOT      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR   = os.path.join(ROOT, "data")
CACHE_DIR = os.path.join(ROOT, "cache")
REF_DIR   = os.path.join(ROOT, "ref")
REF_TOHOP = os.path.join(REF_DIR, "to_hop_mon.csv")   # bảng tra tổ hợp -> môn
REF_TINH      = os.path.join(REF_DIR, "tinh_thanh.csv")            # tỉnh cũ -> tỉnh mới + vùng
REF_DIADANH   = os.path.join(REF_DIR, "dia_danh.csv")              # địa danh -> tỉnh cũ
REF_TRUONGTINH = os.path.join(REF_DIR, "truong_tinh_thucong.csv")  # điền tay theo mã trường
RAW_CACHE = os.path.join(CACHE_DIR, "raw.csv.gz")
XLSX_PATH = os.path.join(OUT_DIR, "diem_chuan_daihoc.xlsx")
ENC       = "utf-8-sig"   # Excel mở CSV không lỗi tiếng Việt

# Phương thức thang 30/40 -> so sánh được giữa các trường (dùng cho AI)
SCALE30_METHODS = ("Điểm thi THPT", "Điểm học bạ")
MAX_SCALE30 = 40          # tổ hợp 3 môn, có hệ số năng khiếu tối đa ~40
MAX_ANY     = 1600        # trên mức này chắc chắn lỗi nguồn (vd 6139)

# ============================================================================
# NHÓM NGÀNH — khớp theo THỨ TỰ, nhóm cụ thể đứng trước nhóm rộng
# (vd "sư phạm tin học" phải vào Sư phạm, không vào CNTT).
# ============================================================================
MAJOR_GROUPS: list[tuple[str, list[str]]] = [
    ("Y - Dược - Sức khỏe", ["y khoa", "y hoc", "y da khoa", "duoc", "dieu duong",
        "rang ham mat", "xet nghiem y", "ho sinh", "y te cong cong", "dinh duong",
        "ky thuat hinh anh y", "phuc hoi chuc nang", "cong nghe sinh hoc y",
        "bac si", "bac sy", "da khoa"]),
    ("Sư phạm - Giáo dục", ["su pham", "giao duc mam non", "giao duc tieu hoc",
        "giao duc the chat", "giao duc dac biet", "giao duc cong dan",
        "giao duc chinh tri", "giao duc quoc phong", "giao duc hoc"]),
    ("Luật", ["luat"]),
    ("Quân đội - Công an", ["quan su", "chi huy", "bien phong", "canh sat",
        "an ninh nhan dan", "trinh sat", "quan doi", "cong an"]),
    ("Du lịch - Khách sạn - Nhà hàng", ["du lich", "khach san", "lu hanh", "nha hang",
        "quan tri dich vu", "huong dan vien"]),
    ("Báo chí - Truyền thông", ["bao chi", "truyen thong", "quan he cong chung",
        "quang cao", "xuat ban", "bien tap", "truyen hinh", "phat thanh"]),
    ("Ngôn ngữ - Quốc tế học", ["ngon ngu", "quoc te hoc", "dong phuong hoc",
        "han quoc hoc", "nhat ban hoc", "trung quoc hoc", "phien dich",
        "bien phien dich", "chau a"]),
    ("Công nghệ thông tin", ["cong nghe thong tin", "khoa hoc may tinh",
        "ky thuat phan mem", "cong nghe phan mem", "an toan thong tin", "an ninh mang",
        "tri tue nhan tao", "artificial intelligence", "khoa hoc du lieu",
        "data science", "he thong thong tin", "mang may tinh", "ky thuat may tinh",
        "cong nghe ky thuat may tinh", "information technology", "computer science",
        "software engineering", "internet van vat", " iot", "big data",
        "cong nghe da phuong tien", "thiet ke vi mach", "vi mach ban dan", "tin hoc",
        "an toan khong gian", "cyber security", "cybersecurity", "phan tich du lieu"]),
    ("Kiến trúc - Xây dựng", ["kien truc", "xay dung", "quy hoach", "do thi",
        "cau duong", "dia ky thuat", "ky thuat cong trinh", "quan ly xay dung"]),
    ("Kinh tế - Kinh doanh - Tài chính", ["kinh te", "quan tri kinh doanh",
        "tai chinh", "ngan hang", "ke toan", "kiem toan", "marketing", "logistic",
        "chuoi cung ung", "thuong mai", "kinh doanh", "quan tri nhan luc",
        "bat dong san", "bao hiem", "dau tu", "thue", "business", "economic",
        "thuong mai dien tu", "quan tri van phong", "thu ky"]),
    ("Nông - Lâm - Ngư - Thú y", ["nong nghiep", "lam nghiep", "thuy san", "thu y",
        "chan nuoi", "trong trot", "thuy loi", "nong hoc", "lam sinh",
        "bao ve thuc vat", "agricultur", "nong lam", "cay trong", "crop science"]),
    ("Khoa học XH & Nhân văn", ["xa hoi hoc", "nhan van", "tam ly",
        "cong tac xa hoi", "lich su", "dia ly", "triet hoc", "van hoc",
        "viet nam hoc", "van hoa", "nhan hoc", "chinh tri hoc", "ton giao",
        "luu tru", "thong tin thu vien", "quan ly nha nuoc", "hanh chinh",
        "thu vien", "thanh thieu nien"]),
    ("Nghệ thuật - Thiết kế - TDTT", ["thiet ke", "my thuat", "am nhac",
        "san khau", "dien anh", "thoi trang", "do hoa", "hoi hoa", "nhiep anh",
        "the duc the thao", "huan luyen", "kien truc canh quan", "bien dao",
        "bien kich", "dien vien", "quay phim", "dao dien", "bao tang hoc",
        "organ", "piano", "thanh nhac", "nhac cu", "sang tac", "mua dai chung"]),
    # rộng nhất -> để cuối
    ("Kỹ thuật - Công nghệ", ["ky thuat", "cong nghe ky thuat", "co khi", "dien tu",
        "tu dong hoa", "o to", "co dien tu", "nhiet", "hoa hoc", "hoa duoc",
        "vat lieu", "moi truong", "van tai", "hang khong", "dau khi",
        "cong nghe thuc pham", "cong nghe sinh hoc", "dieu khien", "robot",
        "nang luong", "khai thac", "trac dia", "det may", "cong nghe",
        "hang hai", "tau bien", "dong tau", "may tau", "dien tau", "xep do",
        "dien tu vien thong", "dien tu cong nghiep", "cong trinh giao thong",
        "co so ha tang", "ngoai khoi", "dien lanh", "vien thong", "toan ung dung",
        "vat ly", "sinh hoc", "thong ke", "toan hoc", "quan ly hang hai",
        "quan ly cong nghiep", "quan ly nang luong", "khoa hoc vat lieu",
        "khoa hoc moi truong", "bao duong", "bao ho lao dong", "ve sinh lao dong",
        "bien doi khi hau", "thuy van", "hai duong", "dia chat", "do luong",
        "bio-technology", "cong nghe in"]),
]

# Viết tắt phổ biến -> dạng đầy đủ, để khớp từ khoá chính xác hơn.
# Vd "CNKT Ôtô" -> "cong nghe ky thuat oto", "QTKD" -> "quan tri kinh doanh".
ABBREVIATIONS: dict[str, str] = {
    r"\bcnkt\b": "cong nghe ky thuat", r"\bcn kt\b": "cong nghe ky thuat",
    r"\bcn\b": "cong nghe",            r"\bkt\b": "ky thuat",
    r"\bxd\b": "xay dung",             r"\btdh\b": "tu dong hoa",
    r"\bdk\b": "dieu khien",           r"\bqtkd\b": "quan tri kinh doanh",
    r"\bbs\b": "bac si",               r"\bqt\b": "quan tri",
    r"\bnn\b": "ngon ngu",             r"\bttnt\b": "tri tue nhan tao",
    r"\bhttt\b": "he thong thong tin", r"\bkhmt\b": "khoa hoc may tinh",
    r"\bkhdl\b": "khoa hoc du lieu",   r"\bqlnn\b": "quan ly nha nuoc",
    r"\bctxh\b": "cong tac xa hoi",
}
_ABBR = [(re.compile(p), r) for p, r in ABBREVIATIONS.items()]

# ============================================================================
# CHUẨN HOÁ VĂN BẢN
# ============================================================================
_RE_NUMBER = re.compile(r"^\s*\d+\s*[\.\)]\s*")          # "29. Ngôn ngữ Anh"
_RE_PAREN  = re.compile(r"\s*\(.*?\)\s*")                # "(CT tiên tiến)"
# (?<=\S) bắt buộc có nội dung đứng trước -> KHÔNG xoá sạch khi cụm nằm đầu chuỗi
_RE_PROGRAM = re.compile(
    r"(?i)(?<=\S)\s+\b(ct|chương trình)\s+(tiên tiến|chuẩn|chất lượng cao|định hướng).*$")
_RE_SUFFIX  = re.compile(
    r"(?i)(?<=\S)\s+\b(tăng cường|định hướng|chuyên sâu|hợp tác)\b.*$")
_RE_PREFIX  = re.compile(r"(?i)^\s*(cntt|nhóm ngành|ngành)\s*[:\-]\s*")
# "Chương trình tiên tiến Việt-Mỹ ngành điện tử viễn thông" -> "điện tử viễn thông"
_RE_NGANH_TAIL = re.compile(r"(?i)^.*?\bngành\s+(.+)$")
_RE_NONWORD = re.compile(r"[^a-z0-9]+")
# Mã tổ hợp chuẩn: 1 chữ in + 2 số. findall để bỏ rác mà không cần liệt kê ngoại lệ.
_RE_BLOCK = re.compile(r"[A-Z]\d{2}")


def strip_accents(s: str) -> str:
    """Bỏ dấu + viết thường. Lưu ý: Đ/đ (U+0110/U+0111) không tách bằng NFD."""
    s = ud.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if ud.category(c) != "Mn").lower()
    return s.replace("đ", "d")


def slugify(s: str) -> str:
    """Khoá không dấu, không phân biệt hoa/thường -> gộp biến thể chính tả."""
    return _RE_NONWORD.sub("-", strip_accents(s)).strip("-")


def norm_major(s: str) -> str:
    """Gộp biến thể tên ngành về một dạng, KHÔNG BAO GIỜ trả chuỗi rỗng.

    "Công nghệ Thông tin Việt-Nhật (Chương trình tiên tiến)" -> "Công nghệ Thông tin Việt-Nhật"
    "CT tiên tiến Việt-Mỹ ngành điện tử viễn thông"          -> "điện tử viễn thông"
    "29. Ngôn ngữ Anh (TA hệ số 2)"                          -> "Ngôn ngữ Anh"
    "CNTT: Khoa học Máy tính"                                -> "Khoa học Máy tính"
    """
    original = " ".join(str(s).split())
    t = _RE_NUMBER.sub("", original)

    m = _RE_NGANH_TAIL.match(t)        # lấy phần sau "ngành ..." nếu có
    if m:
        t = m.group(1)

    # Chỉ áp dụng mỗi luật khi nó KHÔNG làm rỗng chuỗi -> tránh mất tên ngành.
    for rx in (_RE_PAREN, _RE_PROGRAM, _RE_SUFFIX, _RE_PREFIX):
        nxt = rx.sub(" " if rx is _RE_PAREN else "", t)
        if nxt.strip(" -–,;:"):
            t = nxt

    return " ".join(t.split()).strip(" -–,;:") or original


def major_group(name: str) -> str:
    n = " " + strip_accents(name).replace("\n", " ") + " "
    for pat, rep in _ABBR:             # "CNKT Ôtô" -> "cong nghe ky thuat oto"
        n = pat.sub(rep, n)
    for group, kws in MAJOR_GROUPS:
        if any(kw in n for kw in kws):
            return group
    return "Khác"


def norm_ws(s) -> str:
    return "" if s is None else " ".join(str(s).split())


def norm_block(b) -> str:
    """Rút mã tổ hợp chuẩn từ chuỗi bẩn của nguồn, giữ thứ tự, bỏ trùng.

    'A00;A01'             -> 'A00; A01'
    'A00\\r\\n A01'         -> 'A00; A01'
    'C0TC02'              -> 'C02'
    'Toán (× 2); Ngữ văn' -> ''          (không có mã -> bỏ dòng)
    """
    if not isinstance(b, str):
        return ""
    return "; ".join(dict.fromkeys(_RE_BLOCK.findall(b.upper())))


# ============================================================================
# TẦNG TẢI DỮ LIỆU
# ============================================================================
session = requests.Session()
session.headers.update(HEADERS)
session.mount("https://", requests.adapters.HTTPAdapter(
    pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS, max_retries=0))


def get_json(url: str, retries: int = 3):
    for i in range(retries):
        try:
            r = session.get(url, timeout=25)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(0.6 * (i + 1))          # backoff tuyến tính
    return None


def fetch_universities() -> list[dict]:
    data = (get_json(f"{ORIGIN}/api/school/search") or {}).get("data") or []
    return [s for s in data if s.get("level") == LEVEL_DAIHOC]


def fetch_school(school: dict) -> list[dict]:
    """Điểm chuẩn của 1 trường (mọi năm, chỉ dòng CÓ tổ hợp môn).

    Tải lại tối đa CORRUPT_RETRIES lần khi còn ô hỏng, gộp theo `id` dòng của
    nguồn: giữ bản sạch nếu bản nào sạch. Nguồn hỏng ngẫu nhiên nên lần sau
    thường sạch đúng ô lần trước hỏng.
    """
    url = f"{ORIGIN}/api/common/cutoff-score?school_id={school['id']}"
    tot = {}
    for lan in range(CORRUPT_RETRIES):
        for r in (get_json(url) or {}).get("data") or []:
            k = r.get("id")
            if k is None:                      # không có id -> không gộp được
                tot[f"_{len(tot)}"] = r
            elif k not in tot or (BAD_CHAR in str(tot[k].get("name", ""))
                                  and BAD_CHAR not in str(r.get("name", ""))):
                tot[k] = r
        time.sleep(0.05 + random.random() * 0.1)      # nghỉ ngắn cho lịch sự
        if not any(BAD_CHAR in str(r.get("name", "")) for r in tot.values()):
            break

    out = []
    for r in tot.values():
        if not norm_block(r.get("block")):        # bỏ ĐGNL/CCQT không có tổ hợp
            continue
        try:
            year = int(r.get("year", 0))
        except (TypeError, ValueError):
            continue
        out.append({
            "ma_truong":   school.get("code") or "",
            "ten_truong":  norm_ws(school.get("name")),
            "viet_tat":    norm_ws(school.get("orther_name")),
            "ten_nganh":   norm_ws(r.get("name")),
            "to_hop":      norm_block(r.get("block")),
            "diem_chuan":  r.get("mark"),
            "nam":         year,
            "phuong_thuc": norm_ws(r.get("admission_name")),
            "ghi_chu":     norm_ws(r.get("introtext")),
        })
    return out


def repair_mojibake(df: pd.DataFrame) -> pd.DataFrame:
    """Vá tên ngành còn ô hỏng bằng cách khớp với biến thể sạch trong dữ liệu.

    Mỗi cụm U+FFFD liền nhau = ĐÚNG 1 ký tự gốc (nguồn thay từng byte của một
    ký tự UTF-8 nhiều byte). Vậy 'Du l��ch' -> khớp 'Du l.ch' -> tìm
    được 'Du lịch'.

    Nhiều ứng viên thì chọn tên xuất hiện nhiều nhất, vì nhập nhằng gần như luôn
    do nguồn có sẵn lỗi chính tả lẻ ('Quản trj kinh doanh' 1 lần vs 'Quản trị
    kinh doanh' 2.785 lần). Không có ứng viên nào thì để nguyên — thà giữ tên
    hỏng còn hơn gán sai ngành.
    """
    if "ten_nganh" not in df.columns:
        return df
    ten = df.ten_nganh.astype(str)
    co_loi = ten.str.contains(BAD_CHAR, regex=False)
    hong = sorted(set(ten[co_loi]))
    if not hong:
        return df

    freq = ten.value_counts()
    sach = sorted(set(ten[~co_loi]))
    run = re.compile(f"{BAD_CHAR}+")
    thay = {}
    for h in hong:
        pat = re.compile("^" + ".".join(re.escape(p) for p in run.split(h)) + "$")
        khop = [s for s in sach if pat.match(s)]
        if khop:
            thay[h] = max(khop, key=lambda s: freq[s])

    if thay:
        df = df.copy()
        df["ten_nganh"] = ten.replace(thay)
    con = len(hong) - len(thay)
    print(f"   [vá] {len(thay)}/{len(hong)} tên ngành hỏng đã vá"
          + (f" | còn {con} không tìm được bản sạch" if con else ""))
    return df


def merge_cache(moi: pd.DataFrame) -> pd.DataFrame:
    """Gộp dữ liệu mới vào cache cũ thay vì ghi đè.

    Nguồn có thể bỏ bớt năm cũ giữa hai lần crawl (đã gặp: mất 2010–2014).
    Ghi đè thì mất luôn phần lịch sử đó, và không crawl lại được. Gộp thì
    dòng mới thắng dòng cũ cùng khoá, dòng chỉ có ở cache cũ được giữ lại.
    """
    cu = None
    if os.path.exists(RAW_CACHE):
        try:
            cu = pd.read_csv(RAW_CACHE, keep_default_na=False,
                             dtype=str, compression="gzip")
        except Exception as e:
            print(f"   [!] Không đọc được cache cũ ({e}) — chỉ dùng dữ liệu mới.")

    if cu is None or cu.empty:
        return repair_mojibake(moi)

    cot = [c for c in moi.columns if c in cu.columns]
    gop = pd.concat([cu[cot], moi[cot].astype(str)], ignore_index=True)
    # Vá TRƯỚC khi dedup: khoá dedup có ten_nganh, nếu vá sau thì bản hỏng và
    # bản sạch của cùng một dòng đều sống sót -> nhân bản.
    gop = repair_mojibake(gop)
    # dòng mới đứng sau -> keep='last' cho bản mới thắng khi trùng khoá
    khoa = [c for c in ["ma_truong", "ten_nganh", "to_hop", "phuong_thuc", "nam"]
            if c in cot]
    gop = gop.drop_duplicates(khoa, keep="last").reset_index(drop=True)
    them = len(gop) - len(cu)
    print(f"   [cache] gộp: cũ {len(cu):,} + mới {len(moi):,} -> {len(gop):,} "
          f"({them:+,})")
    return gop


def crawl_all() -> pd.DataFrame:
    """Crawl toàn bộ -> raw DataFrame, gộp vào cache (không ghi đè)."""
    unis = fetch_universities()
    print(f"   {len(unis)} trường đại học")

    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_school, s): s for s in unis}
        for fut in as_completed(futures):
            done += 1
            try:
                rows.extend(fut.result())
            except Exception as e:
                print(f"   [lỗi] {futures[fut].get('name')}: {e}")
            if done % 50 == 0 or done == len(unis):
                print(f"   ...{done}/{len(unis)} trường | {len(rows)} dòng thô")

    raw = merge_cache(pd.DataFrame(rows))
    os.makedirs(CACHE_DIR, exist_ok=True)
    raw.to_csv(RAW_CACHE, index=False, encoding="utf-8", compression="gzip")
    print(f"   [cache] {RAW_CACHE} ({os.path.getsize(RAW_CACHE)//1024} KB)")
    return raw


def load_cache() -> pd.DataFrame | None:
    if not os.path.exists(RAW_CACHE):
        return None
    age = (time.time() - os.path.getmtime(RAW_CACHE)) / 86400
    print(f">> Dùng cache ({age:.1f} ngày trước). Thêm --refresh để crawl mới.")
    # vá luôn ở đây: cache cũ có thể chứa ô hỏng từ những lần crawl trước
    return repair_mojibake(pd.read_csv(RAW_CACHE, keep_default_na=False, dtype=str))


def load_ref_tohop() -> pd.DataFrame:
    """Bảng tra tổ hợp -> môn (Bộ GD&ĐT + API). Thiếu file thì cảnh báo, không chết."""
    if not os.path.exists(REF_TOHOP):
        print(f"   [!] Thiếu {REF_TOHOP} — cột cac_mon sẽ trống. "
              f"Chạy: python source/crawler/build_ref_tohop.py")
        return pd.DataFrame(columns=["ma_to_hop", "ten_to_hop", "cac_mon", "nguon"])
    return pd.read_csv(REF_TOHOP).drop_duplicates("ma_to_hop")


def resolve_province(truong: pd.DataFrame) -> pd.DataFrame:
    """Gắn tinh_thanh + vung_mien cho từng trường.

    3 tầng, tầng sau ghi đè tầng trước:
      1. Suy từ địa danh trong tên trường  (ref/dia_danh.csv)
      2. Bảng điền tay cho trường không có địa danh (ref/truong_tinh_thucong.csv)
      3. Quy đổi tỉnh cũ -> tỉnh sau sáp nhập 2025 + vùng miền (ref/tinh_thanh.csv)
    """
    truong = truong.copy()
    truong["tinh_thanh"] = ""
    truong["vung_mien"] = ""

    if not os.path.exists(REF_TINH):
        print(f"   [!] Thiếu {REF_TINH} — tinh_thanh/vung_mien sẽ trống.")
        return truong
    tinh = pd.read_csv(REF_TINH)

    # --- tầng 1: địa danh trong tên trường ---
    tinh_cu = pd.Series("", index=truong.index)
    if os.path.exists(REF_DIADANH):
        dd = pd.read_csv(REF_DIADANH)
        # cụm dài khớp trước ("nam can tho" thắng "can tho")
        pairs = sorted(zip(dd.tu_khoa, dd.tinh_cu), key=lambda x: -len(x[0]))
        names = " " + truong.ten_truong.map(strip_accents) + " "
        for kw, prov in pairs:
            hit = names.str.contains(kw, regex=False) & (tinh_cu == "")
            tinh_cu = tinh_cu.mask(hit, prov)
    else:
        print(f"   [!] Thiếu {REF_DIADANH} — bỏ qua bước suy từ tên trường.")

    # --- tầng 2: bảng điền tay (ưu tiên cao hơn, sửa được ca suy sai) ---
    if os.path.exists(REF_TRUONGTINH):
        man = pd.read_csv(REF_TRUONGTINH).drop_duplicates("ma_truong")
        m = truong.ma_truong.map(man.set_index("ma_truong").tinh_cu).fillna("")
        tinh_cu = tinh_cu.mask(m != "", m)

    # --- tầng 3: quy đổi sang tỉnh sau sáp nhập + vùng miền ---
    lut = tinh.drop_duplicates("tinh_cu").set_index("tinh_cu")
    truong["tinh_thanh"] = tinh_cu.map(lut.tinh_thanh).fillna("")
    truong["vung_mien"] = tinh_cu.map(lut.vung_mien).fillna("")

    bad = tinh_cu[(tinh_cu != "") & (truong.tinh_thanh == "")].unique()
    if len(bad):
        print(f"   [!] Tỉnh cũ không có trong {REF_TINH}: {list(bad)}")
    n = int((truong.tinh_thanh != "").sum())
    print(f"   tinh_thanh: {n}/{len(truong)} trường ({n/len(truong):.1%})")
    return truong



# ============================================================================
# LÀM SẠCH + CỬA SỔ TRƯỢT
# ============================================================================
def chon_nam_cuoi(nam: pd.Series) -> int:
    """Năm mới nhất ĐỦ DỮ LIỆU để làm mốc cuối cửa sổ.

    Nguồn công bố điểm chuẩn nhỏ giọt suốt mùa tuyển sinh: đầu tháng 9/2026 chỉ
    có 445 dòng cho năm 2026 (4,5% so với trung vị các năm trước). Nhận nó làm
    mốc cuối thì cửa sổ thành 2022–2026, và số chuỗi đủ 5 năm sụp từ 9.643 xuống
    223 — `xu_huong` mất hết ý nghĩa thống kê.

    Nên bỏ dần năm mới nhất khi nó chưa đạt MIN_YEAR_RATIO so với trung vị 5 năm
    liền trước. Sang tháng 8 năm sau, khi nguồn đã đủ, năm mới tự được nhận —
    không phải sửa code (đây là điều CN-05 hứa).
    """
    dem = nam.value_counts().sort_index()
    while len(dem) > 1:
        y = int(dem.index[-1])
        truoc = dem.iloc[max(0, len(dem) - 6):-1]
        nguong = truoc.median() * MIN_YEAR_RATIO
        if dem.iloc[-1] >= nguong:
            return y
        print(f">> Bỏ năm {y}: {int(dem.iloc[-1]):,} dòng < ngưỡng "
              f"{nguong:,.0f} ({MIN_YEAR_RATIO:.0%} trung vị) — nguồn chưa công bố đủ")
        dem = dem.iloc[:-1]
    return int(dem.index[-1])


def clean(raw: pd.DataFrame, n_years: int, end_year: int | None):
    """Làm sạch điểm, chuẩn hoá tổ hợp + tên ngành, cắt về N năm mới nhất."""
    df = raw.copy()
    df["diem_chuan"] = pd.to_numeric(df["diem_chuan"], errors="coerce")
    df["nam"] = pd.to_numeric(df["nam"], errors="coerce")

    df = df[df.diem_chuan.notna() & df.nam.notna()]
    df = df[(df.diem_chuan > 0) & (df.diem_chuan <= MAX_ANY)]
    # tên ngành rỗng -> không thể tạo khoá -> bỏ
    df = df[df.ten_nganh.notna() & (df.ten_nganh.astype(str).str.strip() != "")]
    # THPT/học bạ mà > 40 điểm => lỗi nguồn (vd 6139)
    df = df[~(df.phuong_thuc.isin(SCALE30_METHODS) & (df.diem_chuan > MAX_SCALE30))].copy()

    df["nam"] = df.nam.astype("int16")
    df["diem_chuan"] = df.diem_chuan.round(2)

    # Chuẩn hoá lại tổ hợp (idempotent) -> cache cũ cũng được làm sạch theo luật mới.
    # Map trên giá trị duy nhất thay vì từng dòng cho nhanh.
    u = pd.Series(df.to_hop.astype(str).unique())
    df["to_hop"] = df.to_hop.astype(str).map(dict(zip(u, u.map(norm_block))))
    n0 = len(df)
    df = df[df.to_hop != ""].copy()
    if n0 != len(df):
        print(f">> Bỏ {n0 - len(df):,} dòng không rút được mã tổ hợp "
              f"(vd 'Toán (× 2); Ngữ văn')")

    # cửa sổ trượt: tự lấy N năm mới nhất ĐỦ DỮ LIỆU
    end = int(end_year) if end_year else chon_nam_cuoi(df.nam)
    start = end - n_years + 1
    years = list(range(start, end + 1))
    df = df[df.nam.between(start, end)].copy()

    # chuẩn hoá ngành -> slug (nối liền chuỗi nhiều năm khi nguồn đổi tên)
    u1 = pd.Series(df.ten_nganh.unique())
    df["nganh_chuan"] = df.ten_nganh.map(dict(zip(u1, u1.map(norm_major))))
    u2 = pd.Series(df.nganh_chuan.unique())
    df["nganh_slug"] = df.nganh_chuan.map(dict(zip(u2, u2.map(slugify))))
    df["nhom_nganh"] = df.nganh_chuan.map(dict(zip(u2, u2.map(major_group))))

    # chốt chặn: slug rỗng/NULL sẽ phá PRIMARY KEY khi nạp DB
    bad = df.nganh_slug.isna() | (df.nganh_slug.astype(str).str.strip() == "")
    if bad.any():
        print(f">> [!] Bỏ {int(bad.sum())} dòng có nganh_slug rỗng: "
              f"{df.loc[bad, 'ten_nganh'].unique()[:3]}")
        df = df[~bad].copy()

    df = df.drop_duplicates(
        subset=["ma_truong", "nganh_slug", "to_hop", "phuong_thuc", "nam", "diem_chuan"])
    print(f">> Cửa sổ {start}–{end}: {len(df):,} dòng | "
          f"tên ngành {df.ten_nganh.nunique():,} -> chuẩn hoá {df.nganh_slug.nunique():,}")
    return df, years, start, end


# ============================================================================
# XUẤT CSV — SCHEMA SAO (dim + fact), khớp MySQL/Django
# ============================================================================
def export_csv(df: pd.DataFrame, ref: pd.DataFrame, years: list[int]):
    os.makedirs(OUT_DIR, exist_ok=True)
    w = lambda d, name: d.to_csv(os.path.join(OUT_DIR, name), index=False, encoding=ENC)

    # ---- fact diem_chuan: 1 dòng = 1 tổ hợp, chỉ THPT + học bạ (thang 30/40) ----
    # Dựng fact TRƯỚC dim: dim phải dẫn xuất từ fact, không phải từ df. df còn
    # chứa ĐGNL/ĐGTD (có mã tổ hợp nhưng khác thang, bị loại khỏi fact) — dựng
    # dim từ df sẽ sinh ngành/tổ hợp không có dòng điểm chuẩn nào trỏ tới, và
    # chúng trôi vào DB thành dữ liệu rác không bao giờ tự mất (import chỉ upsert).
    fact = df[df.phuong_thuc.isin(SCALE30_METHODS)][
        ["ma_truong", "nganh_slug", "to_hop", "phuong_thuc", "nam",
         "diem_chuan", "ten_nganh"]].copy()
    fact["ma_to_hop"] = fact.to_hop.str.split("; ")
    fact = fact.explode("ma_to_hop").drop(columns="to_hop")
    fact = fact.rename(columns={"ten_nganh": "ten_nganh_goc"})   # giữ để truy vết
    fact = (fact.drop_duplicates(["ma_truong", "nganh_slug", "ma_to_hop",
                                  "phuong_thuc", "nam"])
                .sort_values(["ma_truong", "nganh_slug", "nam", "phuong_thuc", "ma_to_hop"])
                .reset_index(drop=True))
    fact.insert(0, "id", np.arange(1, len(fact) + 1, dtype="int32"))
    w(fact[["id", "ma_truong", "nganh_slug", "ma_to_hop", "phuong_thuc", "nam",
            "diem_chuan", "ten_nganh_goc"]], "diem_chuan.csv")

    # chỉ giữ phần df có mặt trong fact -> mọi dim sinh ra đều có dòng fact
    dim = df[df.phuong_thuc.isin(SCALE30_METHODS)]

    # ---- dim truong ----
    truong = (dim.groupby("ma_truong", as_index=False)
                 .agg(ten_truong=("ten_truong", "first"), viet_tat=("viet_tat", "first"))
                 .sort_values("ten_truong"))
    truong["viet_tat"] = truong.viet_tat.fillna("")
    truong = resolve_province(truong)      # tinh_thanh + vung_mien
    w(truong, "truong.csv")

    # ---- dim nganh ----
    # Không giữ ma_nganh: nguồn ghi biến thể theo trường/năm (1 ngành có tới 110 mã)
    # nên nó không phải thuộc tính của ngành. Không giữ so_truong: dữ liệu dẫn xuất,
    # tính bằng SQL COUNT(DISTINCT ...) luôn đúng hơn.
    nganh = (dim.groupby("nganh_slug", as_index=False)
                .agg(ten_nganh=("nganh_chuan", "first"),
                     nhom_nganh=("nhom_nganh", "first"))
                .sort_values(["nhom_nganh", "ten_nganh"]))
    w(nganh, "nganh.csv")

    # ---- dim to_hop: chỉ mã thực dùng trong fact, ghép môn từ bảng tra ----
    used = pd.Series(sorted(fact.ma_to_hop.unique()), name="ma_to_hop")
    to_hop = (used.to_frame()
                  .merge(ref[["ma_to_hop", "ten_to_hop", "cac_mon", "nguon"]],
                         on="ma_to_hop", how="left"))
    to_hop[["ten_to_hop", "cac_mon", "nguon"]] = \
        to_hop[["ten_to_hop", "cac_mon", "nguon"]].fillna("")
    to_hop["so_mon"] = to_hop.cac_mon.map(lambda s: len(s.split(",")) if s else 0)
    w(to_hop, "to_hop.csv")

    feat = build_features(fact, years)
    w(feat, "dac_trung_diemchuan.csv")

    cov = fact.ma_to_hop.isin(to_hop.loc[to_hop.cac_mon != "", "ma_to_hop"]).mean()
    print(f"   [CSV] truong({len(truong):,}) nganh({len(nganh):,}) to_hop({len(to_hop):,}) "
          f"diem_chuan({len(fact):,}) dac_trung({len(feat):,})")
    print(f"         cac_mon phủ {cov:.2%} dòng điểm chuẩn")
    return feat


def build_features(fact: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """Đặc trưng cho sklearn: chuỗi điểm N năm + tb/min/max/xu hướng (vector hoá)."""
    key = ["ma_truong", "nganh_slug", "ma_to_hop", "phuong_thuc"]
    piv = (fact.pivot_table(index=key, columns="nam", values="diem_chuan", aggfunc="max")
               .reindex(columns=years))

    V = piv.to_numpy(dtype="float64")            # (n, n_years)
    M = ~np.isnan(V)
    n = M.sum(axis=1)
    yrs = np.asarray(years, dtype="float64")

    with np.errstate(invalid="ignore", divide="ignore"):
        tb = np.nanmean(V, axis=1)
        mn = np.nanmin(V, axis=1)
        mx = np.nanmax(V, axis=1)
        last_idx = (M * np.arange(len(years))).max(axis=1)   # năm gần nhất có dữ liệu
        moi_nhat = V[np.arange(len(V)), last_idx]

        # hồi quy tuyến tính có mặt nạ -> độ dốc = xu hướng điểm/năm
        X, Y = np.where(M, yrs, 0.0), np.nan_to_num(V)
        sx, sy, sxy, sxx = X.sum(1), Y.sum(1), (X * Y).sum(1), (X * X).sum(1)
        den = n * sxx - sx ** 2
        slope = np.where(den != 0, (n * sxy - sx * sy) / np.where(den == 0, 1, den), 0.0)

    out = piv.reset_index()
    out.columns = key + [f"diem_{y}" for y in years]
    out["diem_tb"]       = np.round(tb, 2)
    out["diem_min"]      = mn
    out["diem_max"]      = mx
    out["diem_moi_nhat"] = moi_nhat
    out["bien_dong"]     = np.round(mx - mn, 2)     # độ dao động = rủi ro
    out["so_nam_co_dl"]  = n.astype("int8")
    out["xu_huong"]      = np.round(np.where(n >= 2, slope, 0.0), 3)
    return out


# ============================================================================
# XUẤT EXCEL (bản cho người xem)
# ============================================================================
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)


def style_sheet(ws, freeze="A2"):
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for col in ws.iter_cols():
        letter = get_column_letter(col[0].column)
        width = max((len(str(c.value)) for c in col[:400] if c.value is not None), default=10)
        ws.column_dimensions[letter].width = min(max(width + 2, 10), 55)
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions
    ws.row_dimensions[1].height = 30


def export_excel(df, to_hop_view, feat, years, start, end):
    COLS = {"ma_truong": "Mã trường", "ten_truong": "Tên trường", "nhom_nganh": "Nhóm ngành",
            "nganh_chuan": "Ngành (chuẩn hoá)", "ten_nganh": "Tên ngành (gốc)",
            "to_hop": "Tổ hợp môn", "diem_chuan": "Điểm chuẩn", "nam": "Năm",
            "phuong_thuc": "Phương thức", "ghi_chu": "Ghi chú"}
    is30 = df.phuong_thuc.isin(SCALE30_METHODS)

    def view(d):
        d = (d[list(COLS)].sort_values(["ten_truong", "nhom_nganh", "nganh_chuan", "nam"])
                          .rename(columns=COLS).reset_index(drop=True))
        d.insert(0, "STT", np.arange(1, len(d) + 1))
        return d

    ycols = [str(y) for y in years]
    pivot = (df[is30].pivot_table(index=["ten_truong", "nganh_chuan", "phuong_thuc"],
                                  columns="nam", values="diem_chuan", aggfunc="max")
                     .reindex(columns=years).reset_index())
    pivot.columns = ["Tên trường", "Ngành", "Phương thức"] + ycols
    pivot["Chênh lệch"] = np.round(
        pivot[ycols].bfill(axis=1).iloc[:, -1] - pivot[ycols].ffill(axis=1).iloc[:, 0], 2)

    stats = pd.DataFrame(
        [("Ngày crawl", datetime.now().strftime("%d/%m/%Y %H:%M")),
         ("Nguồn", "diemthi.tuyensinh247.com + danh mục tổ hợp Bộ GD&ĐT 2025"),
         ("Cửa sổ năm", f"{start}–{end}"),
         ("Số trường đại học", df.ma_truong.nunique()),
         ("Số ngành (sau chuẩn hoá)", df.nganh_slug.nunique()),
         ("Dòng THPT + học bạ (thang 30/40)", int(is30.sum())),
         ("Dòng phương thức khác", int((~is30).sum())),
         (f"Chuỗi có đủ {len(years)} năm", int((feat.so_nam_co_dl == len(years)).sum())),
         ("Chuỗi có >= 3 năm", int((feat.so_nam_co_dl >= 3).sum()))]
        + [(f"[Nhóm ngành] {g}", int(c)) for g, c in df.nhom_nganh.value_counts().items()],
        columns=["Chỉ tiêu", "Giá trị"])

    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as xw:
        view(df[is30]).to_excel(xw, sheet_name="DiemChuan_ToHop", index=False)
        view(df[~is30]).to_excel(xw, sheet_name="PhuongThuc_Khac", index=False)
        pivot.to_excel(xw, sheet_name=f"SoSanh_{len(years)}Nam", index=False)
        to_hop_view.to_excel(xw, sheet_name="ToHopMon", index=False)
        stats.to_excel(xw, sheet_name="ThongKe", index=False)
        for name in xw.book.sheetnames:
            style_sheet(xw.book[name], "A1" if name == "ThongKe" else "A2")
    print(f"   [Excel] {XLSX_PATH} ({os.path.getsize(XLSX_PATH)//1024} KB)")


# ============================================================================
# SELF-CHECK — python source/crawler/crawl_diemchuan.py --selfcheck
# ============================================================================
def selfcheck():
    p = lambda f: os.path.join(OUT_DIR, f)
    # dtype=str cho các cột khoá: tránh pandas suy ra float rồi biến "" thành NaN
    truong = pd.read_csv(p("truong.csv"), dtype={"tinh_thanh": str, "vung_mien": str},
                         keep_default_na=False)
    nganh  = pd.read_csv(p("nganh.csv"), keep_default_na=False)
    to_hop = pd.read_csv(p("to_hop.csv"), keep_default_na=False)
    fact   = pd.read_csv(p("diem_chuan.csv"))
    feat   = pd.read_csv(p("dac_trung_diemchuan.csv"))

    # --- khoá chính: duy nhất VÀ không rỗng ---
    for name, d, k in [("truong", truong, "ma_truong"), ("nganh", nganh, "nganh_slug"),
                       ("to_hop", to_hop, "ma_to_hop"), ("diem_chuan", fact, "id")]:
        assert d[k].is_unique, f"{name}.{k} bị trùng"
        assert d[k].notna().all(), f"{name}.{k} có NULL (MySQL sẽ từ chối PK)"
        assert (d[k].astype(str).str.strip() != "").all(), f"{name}.{k} có chuỗi rỗng"

    # --- khoá ngoại: không NULL và không mồ côi ---
    for col, dim, dk in [("ma_truong", truong, "ma_truong"),
                         ("nganh_slug", nganh, "nganh_slug"),
                         ("ma_to_hop", to_hop, "ma_to_hop")]:
        assert fact[col].notna().all(), f"diem_chuan.{col} có NULL (khoá ngoại)"
        orphan = set(fact[col]) - set(dim[dk])
        assert not orphan, f"diem_chuan.{col} mồ côi: {sorted(orphan)[:5]}"

    # --- miền giá trị ---
    assert fact.diem_chuan.between(0.01, MAX_SCALE30).all(), "điểm chuẩn ngoài thang 0-40"
    n_years = fact.nam.nunique()
    assert n_years <= LATEST_N_YEARS, f"cửa sổ có {n_years} năm > {LATEST_N_YEARS}"
    assert fact.phuong_thuc.isin(SCALE30_METHODS).all(), "fact lẫn phương thức khác thang"

    # --- vị trí trường: cần cho tính năng gợi ý theo khu vực ---
    thieu = truong.loc[truong.tinh_thanh.str.strip() == "", "ma_truong"].tolist()
    assert not thieu, f"{len(thieu)} trường thiếu tinh_thanh: {thieu[:5]}"
    assert truong.vung_mien.isin(["Miền Bắc", "Miền Trung", "Miền Nam"]).all(), \
        "vung_mien có giá trị lạ"

    # --- khoá tự nhiên: nền tảng của upsert hằng năm ---
    nat = ["ma_truong", "nganh_slug", "ma_to_hop", "phuong_thuc", "nam"]
    assert not fact.duplicated(nat).any(), "trùng khoá tự nhiên (upsert sẽ nhân bản dòng)"

    # --- dim không được có dòng thừa: mọi dòng chiều phải có dòng fact trỏ tới,
    #     nếu không nó sẽ trôi vào DB thành ngành/trường/tổ hợp rác trên UI ---
    for name, d, dk, fk in [("truong", truong, "ma_truong", "ma_truong"),
                            ("nganh", nganh, "nganh_slug", "nganh_slug"),
                            ("to_hop", to_hop, "ma_to_hop", "ma_to_hop")]:
        thua = set(d[dk]) - set(fact[fk])
        assert not thua, f"{name} có {len(thua)} dòng không dùng: {sorted(thua)[:5]}"

    # --- font: nguồn ngẫu nhiên trả byte hỏng; crawler phải vá hết trước khi xuất ---
    for name, d in [("truong", truong), ("nganh", nganh), ("to_hop", to_hop)]:
        for col, s in d.items():
            n = s.astype(str).str.contains(BAD_CHAR, regex=False).sum()
            assert n == 0, f"{name}.{col}: {n} ô còn ký tự hỏng ({BAD_CHAR})"

    # --- cột dành cho AI ---
    ycols = [c for c in feat.columns if c.startswith("diem_20")]
    assert len(ycols) == n_years, "số cột năm ở đặc trưng lệch với fact"
    assert (feat.so_nam_co_dl == feat[ycols].notna().sum(axis=1)).all(), "so_nam_co_dl sai"
    assert feat.diem_moi_nhat.notna().all(), "diem_moi_nhat có NaN"
    assert feat[["ma_truong", "nganh_slug", "ma_to_hop", "phuong_thuc"]].notna().all().all(), \
        "đặc trưng có khoá NULL"

    cov = fact.ma_to_hop.isin(to_hop.loc[to_hop.cac_mon != "", "ma_to_hop"]).mean()
    print(f"[OK] Tất cả kiểm tra đạt. trường={len(truong):,} ngành={len(nganh):,} "
          f"tổ hợp={len(to_hop):,} điểm chuẩn={len(fact):,} đặc trưng={len(feat):,}")
    print(f"     Năm: {sorted(fact.nam.unique())} | chuỗi đủ {n_years} năm: "
          f"{(feat.so_nam_co_dl == n_years).sum():,} | >=3 năm: "
          f"{(feat.so_nam_co_dl >= 3).sum():,} | cac_mon phủ {cov:.2%}")


# ============================================================================
# MAIN
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="Crawl điểm chuẩn ĐH (cửa sổ trượt N năm)")
    ap.add_argument("--refresh", action="store_true", help="crawl mới, bỏ qua cache")
    ap.add_argument("--years", type=int, default=LATEST_N_YEARS, help="số năm giữ lại")
    ap.add_argument("--end", type=int, default=END_YEAR, help="năm cuối (mặc định: mới nhất)")
    ap.add_argument("--selfcheck", action="store_true", help="chỉ kiểm tra dữ liệu đã xuất")
    a = ap.parse_args()

    if a.selfcheck:
        selfcheck()
        return

    t0 = time.time()
    raw = None if a.refresh else load_cache()
    if raw is None:
        print(">> Crawl từ nguồn ...")
        raw = crawl_all()

    ref = load_ref_tohop()
    df, years, start, end = clean(raw, a.years, a.end)
    feat = export_csv(df, ref, years)
    to_hop_view = pd.read_csv(os.path.join(OUT_DIR, "to_hop.csv"), keep_default_na=False)
    export_excel(df, to_hop_view, feat, years, start, end)
    selfcheck()
    print(f">> XONG trong {time.time() - t0:.1f}s -> {OUT_DIR}/")


if __name__ == "__main__":
    main()








