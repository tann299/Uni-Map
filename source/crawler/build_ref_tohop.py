# -*- coding: utf-8 -*-
"""
================================================================================
 BẢNG TRA TỔ HỢP MÔN  ->  ref/to_hop_mon.csv
================================================================================
Hợp nhất 2 nguồn để biết mỗi mã tổ hợp (A00, D90, X26...) gồm những MÔN nào —
dữ liệu này cần cho AI ghép điểm từng môn của học sinh với tổ hợp xét tuyển.

  1. Danh mục 344 tổ hợp xét tuyển 2025 của Bộ GD&ĐT (PDF, ưu tiên)
  2. API /api/common/blocks của tuyensinh247 (bổ sung mã PDF không có)

API của tuyensinh247 chỉ trả 279 mã, trong khi dữ liệu điểm chuẩn thực tế dùng
330 mã — nên thiếu PDF thì ~12% dòng không có tên môn.

Chạy lại khi Bộ GD&ĐT công bố danh mục mới:
    pip install pdfplumber requests pandas
    python build_ref_tohop.py
================================================================================
"""

import os
import re
import sys
import unicodedata as ud

import pandas as pd
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PDF_URL = ("https://dcdn.dantri.com.vn/2025/08/10/"
           "danh-sach-344-to-hop-xet-tuyen-dai-hoc-nam-2025-1754765568569.pdf")
API_URL = "https://diemthi.tuyensinh247.com/api/common/blocks"
# Neo vào gốc dự án (2 cấp trên: source/crawler/ -> gốc), không theo CWD.
ROOT    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT     = os.path.join(ROOT, "ref", "to_hop_mon.csv")
PDF_TMP = os.path.join(ROOT, "ref", "_tohop_bogd.pdf")
UA      = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0 Safari/537.36"}
RE_CODE = re.compile(r"[A-Z]\d{2}")

# Tên môn (đã bỏ dấu, viết thường) -> mã môn dùng trong cột cac_mon
SUBJECTS: dict[str, str] = {
    "toan": "TOAN", "toan hoc": "TOAN",
    "ngu van": "VAN", "van": "VAN",
    "vat ly": "LI", "vat li": "LI", "ly": "LI", "li": "LI",
    "hoa hoc": "HOA", "hoa": "HOA",
    "sinh hoc": "SINH", "sinh": "SINH",
    "lich su": "SU", "su": "SU",
    "dia ly": "DIA", "dia li": "DIA", "dia": "DIA",
    "tieng anh": "ANH", "anh": "ANH",
    "tieng nga": "NGA", "tieng phap": "PHAP", "tieng nhat": "NHAT",
    "tieng duc": "DUC", "tieng han": "HAN",
    "tieng trung": "TRUNG", "tieng trung quoc": "TRUNG",
    "ngoai ngu": "NGOAI_NGU",
    "tin hoc": "TIN", "tin": "TIN",
    "giao duc cong dan": "GDCD", "gdcd": "GDCD",
    "giao duc kinh te va phap luat": "GDKTPL",
    "giao duc kinh te phap luat": "GDKTPL", "gdktpl": "GDKTPL",
    "cong nghe cong nghiep": "CN_CN", "cong nghe nong nghiep": "CN_NN",
    "cong nghe": "CN", "ki thuat nghe": "KT_NGHE", "ky thuat nghe": "KT_NGHE",
    "khoa hoc tu nhien": "KHTN", "khtn": "KHTN",
    "khoa hoc xa hoi": "KHXH", "khxh": "KHXH",
    "tu duy dinh luong": "DGTD_DL", "tu duy dinh tinh": "DGTD_DT",
    "khoa hoc/ tieng anh": "KHOAHOC_ANH",
}
# Môn năng khiếu do trường tự tổ chức -> gộp thành NK (không có trong điểm THPT)
NK_HINTS = ("nang khieu", "nk", "ve ", "bo cuc", "kich ban", "tdtt", "am nhac",
            "mam non", "bao chi", "thuyet trinh", "nghe thuat", "skda",
            "xuong am", "hat", "bieu dien", "mua", "hinh hoa", "my thuat")


def strip_accents(s: str) -> str:
    """Bỏ dấu + viết thường. Đ/đ (U+0110/U+0111) không tách bằng NFD nên thay tay."""
    s = ud.normalize("NFD", str(s))
    s = "".join(c for c in s if ud.category(c) != "Mn").lower()
    return s.replace("đ", "d").strip()


def subject_code(raw: str) -> str:
    key = strip_accents(raw).replace("hôi", "hoi").replace("*", "").strip()
    if key in SUBJECTS:
        return SUBJECTS[key]
    if any(h in key for h in NK_HINTS):
        return "NK"
    return "?" + key            # để lộ ra ngoài, không âm thầm bỏ qua


def split_subjects(name: str) -> str:
    parts = [p.strip() for p in re.split(r"[,;]", str(name)) if p.strip()]
    return ",".join(subject_code(p) for p in parts)


def from_pdf() -> pd.DataFrame:
    """Danh mục Bộ GD&ĐT. Tải 1 lần rồi cache vào ref/."""
    import pdfplumber

    os.makedirs("ref", exist_ok=True)
    if not os.path.exists(PDF_TMP):
        r = requests.get(PDF_URL, headers=UA, timeout=60)
        r.raise_for_status()
        if r.content[:4] != b"%PDF":
            raise RuntimeError("URL không trả về PDF")
        with open(PDF_TMP, "wb") as f:
            f.write(r.content)
        print(f"   tải PDF: {os.path.getsize(PDF_TMP)//1024} KB")

    rows = []
    with pdfplumber.open(PDF_TMP) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                rows.extend(table)

    df = pd.DataFrame([r for r in rows if r and r[0] != "STT"],
                      columns=["stt", "ma_to_hop", "ten_to_hop"])
    df["ma_to_hop"] = df.ma_to_hop.str.strip().str.upper()
    df["ten_to_hop"] = df.ten_to_hop.str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df.ma_to_hop.str.fullmatch(r"[A-Z]\d{2}", na=False)]
    df = df.drop_duplicates("ma_to_hop")[["ma_to_hop", "ten_to_hop"]]
    df["nguon"] = "BoGD2025"
    return df


def from_api() -> pd.DataFrame:
    data = requests.get(API_URL, headers={**UA, "Accept": "application/json"},
                        timeout=25).json()["data"]
    df = pd.DataFrame([{"ma_to_hop": b["code"], "ten_to_hop": b["name"]} for b in data])
    df = df[df.ma_to_hop.str.fullmatch(r"[A-Z]\d{2}", na=False)]
    df["nguon"] = "tuyensinh247"
    return df.drop_duplicates("ma_to_hop")


def main():
    pdf_df, api_df = from_pdf(), from_api()

    # PDF ưu tiên (chính thống), API chỉ bù mã PDF không có
    extra = api_df[~api_df.ma_to_hop.isin(pdf_df.ma_to_hop)]
    ref = pd.concat([pdf_df, extra], ignore_index=True)
    ref["cac_mon"] = ref.ten_to_hop.map(split_subjects)

    unknown = sorted({c for row in ref.cac_mon for c in row.split(",")
                      if c.startswith("?")})
    if unknown:
        print(f"   [!] Môn chưa map ({len(unknown)}): {unknown}")
        print("       -> bổ sung vào SUBJECTS hoặc NK_HINTS rồi chạy lại")

    ref = ref.sort_values("ma_to_hop")[["ma_to_hop", "ten_to_hop", "cac_mon", "nguon"]]
    os.makedirs("ref", exist_ok=True)
    ref.to_csv(OUT, index=False, encoding="utf-8-sig")

    print(f">> {OUT}: {len(ref)} mã "
          f"(Bộ GD&ĐT {len(pdf_df)} + tuyensinh247 {len(extra)})")
    print(ref.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
