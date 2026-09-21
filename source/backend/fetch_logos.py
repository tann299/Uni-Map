"""Tải logo trường đại học vào university/static/university/logos/.

Nguồn: infobox bài viết trên Wikipedia tiếng Việt (ưu tiên), quét ảnh bài,
Wikimedia Commons, hoặc link ảnh trực tiếp trong infobox.

Chạy:  python fetch_logos.py              # tải hết, bỏ qua trường đã có logo
       python fetch_logos.py --thu        # chỉ in ứng viên, không ghi file
       python fetch_logos.py --ma BKA KHA # chỉ vài mã trường

Trường không có bài / không có logo -> giữ monogram fallback trong template.
"""

import argparse
import json
import os
import re
import ssl
import time
import unicodedata
import urllib.parse
import urllib.request
from html.parser import HTMLParser

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from university.models import Truong  # noqa: E402

# Một số site có chứng chỉ TLS lỗi — bỏ qua verify cho logo (chỉ ảnh tĩnh)
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
UA_WEB = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# UA mô tả rõ mục đích — Wikimedia chặn UA bot chung chung
UA = "UniMap-LogoFetch/1.0 (https://github.com/unimap; student project) urllib"
VI = "https://vi.wikipedia.org/w/api.php"
EN = "https://en.wikipedia.org/w/api.php"
CM = "https://commons.wikimedia.org/w/api.php"
OUT = os.path.join("university", "static", "university", "logos")
DUOI = (".svg", ".png", ".jpg", ".jpeg", ".webp")

# File không phải logo trường
RAC = ("commons-logo", "wikimedia", "wiki", "edit-icon", "question_book",
       "disambig", "flag_of", "symbol_support", "padlock", "crystal")


def goi(params: dict, base: str = VI):
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def bo_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def chuan_hoa(s: str) -> str:
    """Chuỗi để so khớp: không dấu, không dấu câu, gộp khoảng trắng."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", bo_dau(s).lower())).strip()


def tim_bai(truong) -> str | None:
    """Tìm bài Wikipedia tiếng Việt đúng là trường này.

    Dùng chiến lược 2 bước: (1) search theo tên trường, (2) search thêm tỉnh
    thành nếu bước 1 chưa chắc. Chọn bài khớp nhiều token tên nhất, bài danh
    sách/tỉnh bị loại, trường 'Đại học Quốc gia' chỉ nhận khi tên trường cũng là
    ĐHQG."""
    ten = truong.ten_truong
    ct_ten = chuan_hoa(ten)
    tinh = chuan_hoa(truong.tinh_thanh or "")
    qua_tinh = any(k in ct_ten for k in ("phan hieu", "co so", "phu hieu", "phan vien"))
    chung = "quoc gia" in ct_ten
    tok_ten = set(ct_ten.split()) - {"truong", "dai", "hoc", "vien",
                                     "cua", "va", "tai", "quoc", "gia"}

    def chon(hoat_dong: list) -> str | None:
        ung = []
        for i, h in enumerate(hoat_dong):
            tieu_de = h["title"]
            ct = chuan_hoa(tieu_de)
            if ct.startswith("danh sach"):
                continue
            if not chung and "dai hoc quoc gia" in ct:
                continue
            mo_hinh = ("dai hoc", "hoc vien", "truong", "university")
            if not any(k in ct for k in mo_hinh):
                continue
            giong = len(tok_ten & set(ct.split()))
            # Đòi khớp phần lớn tên trường: tránh bài trùng vài token chung
            # (vd "Tài chính Ngân hàng Hà Nội" dính "Bách khoa Hà Nội").
            if not tok_ten or giong / len(tok_ten) < 0.6:
                continue
            if giong >= max(1, len(tok_ten) - 1):
                return tieu_de
            diem = giong * 10 - i
            if tinh and tinh in ct:
                diem += 3
            ung.append((diem, tieu_de))
        if not ung:
            return None
        ung.sort(reverse=True)
        return ung[0][1]

    try:
        d1 = goi({"action": "query", "format": "json", "list": "search",
                  "srsearch": ten, "srlimit": 6})
    except Exception:
        d1 = {"query": {"search": []}}
    bai = chon(d1.get("query", {}).get("search", []))
    if bai:
        return bai
    if tinh and not qua_tinh:
        try:
            d2 = goi({"action": "query", "format": "json", "list": "search",
                      "srsearch": f"{ten} {truong.tinh_thanh}", "srlimit": 6})
        except Exception:
            d2 = {"query": {"search": []}}
        return chon(d2.get("query", {}).get("search", []))
    return None


def tim_logo(tieu_de: str, truong) -> str | None:
    """Lấy tên file logo trong bài. Nhận file nếu:
    - Chứa viết tắt trường (NEU, PTIT, HUST...), HOẶC
    - Chứa token của tên trường (kinh te, bach khoa...).
    Loại logo tỉnh/tp/quốc gia."""
    ten = truong.ten_truong
    vt = (truong.viet_tat or "").strip().lower()
    tok_ten = set(chuan_hoa(ten).split()) - {"truong", "dai", "hoc", "vien", "cua",
                                              "va", "tai", "quoc", "gia", "phan", "hieu"}
    # 1) Ưu tiên trường logo trong infobox (nhiều template viết inline '|logo=...|')
    try:
        d = goi({"action": "parse", "format": "json", "page": tieu_de,
                 "prop": "wikitext", "section": 0})
    except Exception:
        d = {}
    wt = d.get("parse", {}).get("wikitext", {}).get("*", "")
    if wt:
        # Tìm trường `logo = ...` hoặc `hình = ...` bất kể ngắt dòng hay ngắt `|`
        # Ưu tiên logo trước hình (hình thường là ảnh tòa nhà)
        for key in (r"logo", r"hình", r"image", r"symbol"):
            m = re.search(r"\|\s*" + key + r"\s*=\s*([^|\n}]+)", wt, re.I)
            if not m:
                continue
            raw = m.group(1).strip()
            if not raw:
                continue
            fm = re.search(r"\[\[\s*(?:Tập tin|File|Hình|Image)\s*:\s*([^|\]]+)", raw, re.I)
            if fm:
                raw = fm.group(1)
            ten_file = raw.strip()
            # Bỏ tiền tố namespace nếu còn (vd "File:DHV Logo.png")
            ten_file = re.sub(r"^(?:Tập tin|File|Hình|Image)\s*:\s*", "", ten_file, flags=re.I)
            low = bo_dau(ten_file).lower()
            if low.endswith(DUOI) and any(k in low for k in ("logo", "huy", "emblem", "csnd", "annd", "hup")):
                return ten_file
    # 2) Fallback: quét danh sách ảnh của bài
    try:
        d = goi({"action": "parse", "format": "json", "page": tieu_de,
                 "prop": "images"})
    except Exception:
        return None
    ung = []
    for ten_file in d.get("parse", {}).get("images", []):
        low = bo_dau(ten_file).lower()
        if any(r in low for r in RAC):
            continue
        if not low.endswith(DUOI):
            continue
        if "logo" not in low and "huy" not in low and "emblem" not in low:
            continue
        # Bỏ logo địa phương/huyện/tỉnh/thành phố/quốc gia
        if any(k in low for k in ("tinh_", "tinh ", "thanh_pho", "thanh pho", "quoc_gia")):
            continue
        tokens_file = set(re.split(r"[_\s\-.]+", low))
        # Khớp 1: chứa viết tắt trường (token riêng biệt)
        khop_vt = bool(vt) and (vt in tokens_file)
        # Khớp 2: chứa token của tên trường
        khop_ten = len(tok_ten & tokens_file)
        if not khop_vt and khop_ten == 0:
            continue
        diem = (100 if khop_vt else 0) + khop_ten * 10 + (2 if low.endswith(".svg") else 0)
        ung.append((diem, ten_file))
    if not ung:
        return None
    ung.sort(reverse=True)
    return ung[0][1]


def _tai_url(url: str, ma: str) -> str | None:
    """Tải 1 URL ảnh về đĩa. Trả đuôi đã lưu hoặc None."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA_WEB, "Referer": "https://vi.wikipedia.org/",
        "Accept": "image/*,*/*"})
    try:
        data = urllib.request.urlopen(req, timeout=30, context=_CTX).read()
    except Exception:
        return None
    if len(data) < 500:
        return None
    duoi = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    if duoi not in DUOI:
        duoi = ".png"
    with open(os.path.join(OUT, f"{ma}{duoi}"), "wb") as f:
        f.write(data)
    return duoi


def tai_ve(ten_file: str, ma: str) -> str | None:
    """Tải logo, trả đuôi đã lưu hoặc None.

    Nhận cả URL trực tiếp (một số infobox ghi thẳng link website trường) lẫn
    tên file Wikimedia. File thiếu ở vi.wikipedia sẽ thử tiếp Commons."""
    if ten_file.startswith(("http://", "https://")):
        return _tai_url(ten_file, ma)
    for base in (VI, CM):
        try:
            d = goi({"action": "query", "format": "json", "prop": "imageinfo",
                     "iiprop": "url", "titles": f"File:{ten_file}"}, base=base)
        except Exception:
            continue
        pg = list(d.get("query", {}).get("pages", {}).values())
        if not pg or "missing" in pg[0]:
            continue
        ii = pg[0].get("imageinfo")
        if not ii:
            continue
        duoi = _tai_url(ii[0]["url"], ma)
        if duoi:
            return duoi
    return None


def co_logo(ma: str) -> bool:
    return any(os.path.exists(os.path.join(OUT, f"{ma}{d}")) for d in DUOI)


class _TrichLogoWeb(HTMLParser):
    """Thu thập ứng viên ảnh logo từ trang chủ trường."""

    def __init__(self):
        super().__init__()
        self.og = ""
        self.icons: list[str] = []
        self.imgs: list[str] = []
        self._t = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and a.get("property", "").lower() == "og:image" and a.get("content"):
            self.og = a["content"]
        elif tag == "link" and "icon" in a.get("rel", "").lower() and a.get("href"):
            self.icons.append(a["href"])
        elif tag == "img":
            ul = [a.get("src", ""), a.get("data-src", "")]
            for u in ul:
                if u and ("logo" in (u + a.get("alt", "") + a.get("class", "")).lower()):
                    self.imgs.append(u)
        elif tag == "title":
            self._t = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._t = False

    def handle_data(self, d):
        if self._t:
            self.title += d


def lay_web(tieu_de: str) -> str | None:
    """URL website trường từ infobox Wikipedia (trường website/web/trang web)."""
    try:
        d = goi({"action": "parse", "format": "json", "page": tieu_de,
                 "prop": "wikitext", "section": 0})
    except Exception:
        return None
    wt = d.get("parse", {}).get("wikitext", {}).get("*", "")
    m = re.search(r"\|\s*(?:website|web|trang web|url)\s*=\s*([^\n}]+)", wt, re.I)
    if not m:
        return None
    raw = m.group(1)
    u = re.search(r"https?://[^\s\|\]\}<>]+", raw)
    if u:
        return u.group(0).rstrip(".,;")
    u = re.search(r"\[(https?://[^\s\]]+)", raw)
    return u.group(1) if u else None


def tim_web_logo(tieu_de: str, ma: str) -> str | None:
    """Tìm logo trên trang chủ trường, dùng khi Wikipedia không có ảnh.

    Scrape trang chủ lấy og:image / thẻ icon / img có chữ 'logo', ưu tiên
    thứ tự: og:image > img (càng to, vuông, tên 'logo' càng đúng) > icon."""
    web = lay_web(tieu_de)
    if not web:
        return None
    host = urllib.parse.urlparse(web).netloc
    for proto in ("https", "http"):
        base = f"{proto}://{host}"
        req = urllib.request.Request(base, headers={
            "User-Agent": UA_WEB, "Accept-Language": "vi-VN,vi;q=0.9"})
        try:
            html = urllib.request.urlopen(req, timeout=12, context=_CTX) \
                .read(400000).decode("utf-8", errors="ignore")
        except Exception:
            continue
        p = _TrichLogoWeb()
        p.feed(html)
        cands = []
        if p.og:
            cands.append((3, urllib.parse.urljoin(base, p.og)))
        for u in p.imgs:
            low = u.lower()
            score = 2 if ".svg" in low else 1
            if "small" in low or "mini" in low:
                score -= 1
            cands.append((score, urllib.parse.urljoin(base, u)))
        for h in p.icons[:3]:
            cands.append((0, urllib.parse.urljoin(base, h)))
        seen, out = set(), []
        for score, u in sorted(cands, key=lambda x: -x[0]):
            key = u.lower()
            if key in ("/favicon.ico", base.lower()[:-1] + "/favicon.ico"):
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(u)
        for u in out:
            if _tai_url(u, ma):
                return u
    return None


def phu_huynh(truong) -> str | None:
    """Mã trường mẹ đã có logo, cho phân hiệu/cơ sở dùng chung logo.

    Khớp khi tên trường mẹ là tiền tố của tên phân hiệu (vd 'Đại học Ngoại
    thương'  'Đại học Ngoại thương (Cơ sở II)')."""
    ct = chuan_hoa(truong.ten_truong)
    if not any(k in ct for k in ("co so", "phan hieu", "phu hieu", "phan vien", "csvc")):
        return None
    tot = None
    for m in Truong.objects.all():
        if m.ma_truong == truong.ma_truong or not co_logo(m.ma_truong):
            continue
        cm = chuan_hoa(m.ten_truong)
        if cm and cm in ct and len(cm) < len(ct) and (tot is None or len(cm) > len(tot[1])):
            tot = (m.ma_truong, cm)
    return tot[0] if tot else None


def sao_chep(ma_nguon: str, ma_dich: str) -> str | None:
    """Copy file logo của trường nguồn sang mã đích. Trả tên file mới hoặc None."""
    for d in DUOI:
        src = os.path.join(OUT, f"{ma_nguon}{d}")
        if os.path.exists(src):
            dst = os.path.join(OUT, f"{ma_dich}{d}")
            with open(src, "rb") as f:
                data = f.read()
            with open(dst, "wb") as g:
                g.write(data)
            return f"{ma_dich}{d}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thu", action="store_true", help="chỉ thử, không ghi file")
    ap.add_argument("--ma", nargs="*", help="chỉ chạy vài mã trường")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    qs = Truong.objects.all().order_by("ma_truong")
    if args.ma:
        qs = qs.filter(ma_truong__in=[m.upper() for m in args.ma])

    trung = 0
    for i, t in enumerate(qs, 1):
        if co_logo(t.ma_truong):
            print(f"[{i}] {t.ma_truong:5} đã có logo, bỏ qua")
            trung += 1
            continue
        bai = tim_bai(t)
        logo = tim_logo(bai, t) if bai else None
        if not logo and bai:
            # Wikipedia không có ảnh logo -> thử trang chủ trường
            logo_web = tim_web_logo(bai, t.ma_truong)
            if logo_web:
                print(f"[{i}] {t.ma_truong:5} OK  (web {bai[:20]}) -> {t.ma_truong}")
                trung += 1
                continue
        if not logo:
            me = phu_huynh(t)
            if me:
                if args.thu:
                    print(f"[{i}] {t.ma_truong:5} THỬ phân hiệu -> {me}")
                    trung += 1
                    continue
                f = sao_chep(me, t.ma_truong)
                if f:
                    print(f"[{i}] {t.ma_truong:5} OK  phân hiệu -> {f}")
                    trung += 1
                    continue
            print(f"[{i}] {t.ma_truong:5} —  ({bai}: {'không có logo' if bai else 'không thấy bài'})")
            continue
        if args.thu:
            print(f"[{i}] {t.ma_truong:5} THỬ {bai} -> {logo}")
            trung += 1
            continue
        duoi = tai_ve(logo, t.ma_truong)
        if not duoi and bai:
            # Link trong infobox hỏng (404) -> thử trang chủ trường
            if tim_web_logo(bai, t.ma_truong):
                print(f"[{i}] {t.ma_truong:5} OK  (web {bai[:20]}) -> {t.ma_truong}")
                trung += 1
                continue
        if duoi:
            print(f"[{i}] {t.ma_truong:5} OK  {bai} -> {t.ma_truong}{duoi}")
            trung += 1
        else:
            print(f"[{i}] {t.ma_truong:5} lỗi tải: {logo}")
        time.sleep(0.3)

    print(f"\n== {trung} trường có logo ==")


if __name__ == "__main__":
    main()
