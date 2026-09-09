# -*- coding: utf-8 -*-
"""
================================================================================
 IMPORT DỮ LIỆU VÀO MYSQL  —  dự án "Uni Map"
================================================================================
Nạp data/*.csv vào cơ sở dữ liệu uni_map (lược đồ: db/schema.sql).

Đặc điểm:
  * IDEMPOTENT — dùng INSERT ... ON DUPLICATE KEY UPDATE trên các khoá tự nhiên
    nên chạy lại nhiều lần không nhân bản dòng.
  * TRANSACTION — lỗi giữa chừng thì rollback, DB giữ nguyên trạng thái trước đó.
  * CỬA SỔ TRƯỢT — sau khi nạp, tự xoá năm đã rơi khỏi cửa sổ. Cửa sổ nhỏ hơn 5
    năm (`--years 3`) chạy được không cần ALTER TABLE: cột năm thừa để NULL.
  * DỌN RÁC — xoá dòng fact không còn trong CSV và dòng chiều mồ côi. Không có
    bước này, dữ liệu cũ (slug đổi vì sửa font, ngành nguồn đã bỏ) nằm lại vĩnh
    viễn vì upsert chỉ thêm/cập nhật, không xoá. Lịch sử gợi ý của học sinh
    (`ket_qua_goi_y`) được giữ nguyên.
  * GHI NHẬT KÝ — mỗi lần chạy ghi 1 dòng vào bảng lan_cap_nhat.

Thứ tự bắt buộc (SRS UC-09):
    1. python source/crawler/crawl_diemchuan.py --refresh   (trượt cửa sổ + self-check)
    2. python db/import_mysql.py                            (chỉ chạy nếu self-check ĐẠT)
    3. PYTHONIOENCODING=utf-8 python source/backend/manage.py kiemtra   (kiểm tầng ORM)

Dùng (mọi đường dẫn neo theo __file__ nên chạy từ CWD nào cũng được):
    pip install -r requirements.txt
    python db/import_mysql.py
    python db/import_mysql.py --host 127.0.0.1 --port 3306 --user root --password ''
    python db/import_mysql.py --dry-run        # chỉ kiểm tra, không ghi
================================================================================
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import pandas as pd
import pymysql

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
BATCH    = 2000            # số dòng mỗi lần executemany
SO_COT_NAM = 5             # số cột diem_nam_* trong schema.sql


def read_csv(name: str) -> pd.DataFrame:
    """Đọc CSV giữ nguyên chuỗi rỗng (không để pandas biến '' thành NaN)."""
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        sys.exit(f"Thiếu {path}. Chạy: python source/crawler/crawl_diemchuan.py")
    return pd.read_csv(path, keep_default_na=False)


def upsert(cur, sql: str, rows: list[tuple], label: str) -> int:
    """Chạy executemany theo lô, in tiến độ."""
    if not rows:
        print(f"   {label:22} 0 dòng")
        return 0
    for i in range(0, len(rows), BATCH):
        cur.executemany(sql, rows[i:i + BATCH])
    print(f"   {label:22} {len(rows):>7,} dòng")
    return len(rows)


# ============================================================================
# CÁC BƯỚC NẠP
# ============================================================================
def nap_truong(cur) -> pd.DataFrame:
    df = read_csv("truong.csv")
    sql = """INSERT INTO truong (ma_truong, ten_truong, viet_tat, tinh_thanh, vung_mien)
             VALUES (%s, %s, %s, %s, %s)
             ON DUPLICATE KEY UPDATE
               ten_truong = VALUES(ten_truong), viet_tat  = VALUES(viet_tat),
               tinh_thanh = VALUES(tinh_thanh), vung_mien = VALUES(vung_mien)"""
    upsert(cur, sql, list(df[["ma_truong", "ten_truong", "viet_tat",
                              "tinh_thanh", "vung_mien"]].itertuples(index=False, name=None)),
           "truong")
    return df


def nap_nganh(cur) -> dict[str, int]:
    """Nạp ngành rồi trả map nganh_slug -> nganh_id (khoá thay thế)."""
    df = read_csv("nganh.csv")
    # slug trong DB là VARCHAR(120); đã kiểm chứng cắt 120 không gây trùng
    df["nganh_slug"] = df.nganh_slug.str.slice(0, 120).str.rstrip("-")
    assert df.nganh_slug.is_unique, "cắt slug 120 ký tự gây trùng — cần nới cột"

    sql = """INSERT INTO nganh (nganh_slug, ten_nganh, nhom_nganh)
             VALUES (%s, %s, %s)
             ON DUPLICATE KEY UPDATE
               ten_nganh = VALUES(ten_nganh), nhom_nganh = VALUES(nhom_nganh)"""
    upsert(cur, sql, list(df[["nganh_slug", "ten_nganh", "nhom_nganh"]]
                          .itertuples(index=False, name=None)), "nganh")

    cur.execute("SELECT nganh_slug, nganh_id FROM nganh")
    return dict(cur.fetchall())


def nap_to_hop(cur) -> pd.DataFrame:
    df = read_csv("to_hop.csv")
    sql = """INSERT INTO to_hop (ma_to_hop, ten_to_hop, cac_mon, so_mon, nguon)
             VALUES (%s, %s, %s, %s, %s)
             ON DUPLICATE KEY UPDATE
               ten_to_hop = VALUES(ten_to_hop), cac_mon = VALUES(cac_mon),
               so_mon     = VALUES(so_mon),     nguon   = VALUES(nguon)"""
    upsert(cur, sql, list(df[["ma_to_hop", "ten_to_hop", "cac_mon", "so_mon", "nguon"]]
                          .itertuples(index=False, name=None)), "to_hop")

    # Bảng nối to_hop_mon: chuẩn hoá từ cột cac_mon ('TOAN,LI,HOA')
    cur.execute("SELECT ma_mon FROM mon")
    mon_co = {r[0] for r in cur.fetchall()}
    rows, thieu = [], set()
    for ma, cac_mon in zip(df.ma_to_hop, df.cac_mon):
        for vi_tri, m in enumerate(filter(None, str(cac_mon).split(",")), start=1):
            if m in mon_co:
                rows.append((ma, m, vi_tri))
            else:
                thieu.add(m)
    if thieu:
        print(f"   [!] Môn chưa có trong bảng mon: {sorted(thieu)}")
    cur.execute("DELETE FROM to_hop_mon")        # dựng lại, tránh sót dòng cũ
    upsert(cur, "INSERT INTO to_hop_mon (ma_to_hop, ma_mon, vi_tri) VALUES (%s,%s,%s)",
           rows, "to_hop_mon")
    return df


def nap_diem_chuan(cur, slug2id: dict[str, int]) -> pd.DataFrame:
    df = read_csv("diem_chuan.csv")
    df["nganh_slug"] = df.nganh_slug.str.slice(0, 120).str.rstrip("-")
    df["nganh_id"] = df.nganh_slug.map(slug2id)
    mat = df.nganh_id.isna()
    if mat.any():
        sys.exit(f"{int(mat.sum())} dòng có nganh_slug không khớp bảng nganh")
    df["nganh_id"] = df.nganh_id.astype(int)
    df["ten_nganh_goc"] = df.ten_nganh_goc.str.slice(0, 512)

    sql = """INSERT INTO diem_chuan
               (ma_truong, nganh_id, ma_to_hop, phuong_thuc, nam, diem_chuan, ten_nganh_goc)
             VALUES (%s, %s, %s, %s, %s, %s, %s)
             ON DUPLICATE KEY UPDATE
               diem_chuan = VALUES(diem_chuan), ten_nganh_goc = VALUES(ten_nganh_goc)"""
    upsert(cur, sql, list(df[["ma_truong", "nganh_id", "ma_to_hop", "phuong_thuc",
                              "nam", "diem_chuan", "ten_nganh_goc"]]
                          .itertuples(index=False, name=None)), "diem_chuan")
    return df


def nap_dac_trung(cur, slug2id: dict[str, int]) -> list[int]:
    """Nạp bảng đặc trưng + ánh xạ cửa sổ năm. Trả danh sách năm trong cửa sổ."""
    df = read_csv("dac_trung_diemchuan.csv")
    df["nganh_slug"] = df.nganh_slug.str.slice(0, 120).str.rstrip("-")
    df["nganh_id"] = df.nganh_slug.map(slug2id).astype(int)

    ycols = sorted(c for c in df.columns if c.startswith("diem_2"))
    years = [int(c.split("_")[1]) for c in ycols]

    # Bảng có đúng 5 cột diem_nam_1..5. Cửa sổ nhỏ hơn (`--years 3`) thì các cột
    # cuối phải là NULL, nếu không số placeholder sẽ lệch số cột -> INSERT nổ.
    # Cửa sổ lớn hơn 5 thì phải ALTER TABLE, chặn ngay ở đây cho rõ nguyên nhân.
    if len(years) > SO_COT_NAM:
        sys.exit(f"Cửa sổ {len(years)} năm > {SO_COT_NAM} cột diem_nam_* trong "
                 f"schema.sql. Thêm cột rồi cập nhật SO_COT_NAM.")

    # cua_so_nam: vị trí cột -> năm thật (đổi cửa sổ không cần ALTER TABLE)
    cur.execute("DELETE FROM cua_so_nam")
    cur.executemany("INSERT INTO cua_so_nam (vi_tri, nam) VALUES (%s, %s)",
                    [(i, y) for i, y in enumerate(years, start=1)])

    # read_csv(keep_default_na=False) biến ô số rỗng thành chuỗi '' -> phải ép
    # lại về số rồi đổi sang None, nếu không MySQL báo "Incorrect decimal value".
    for c in ycols:
        s = pd.to_numeric(df[c], errors="coerce")
        df[c] = s.astype(object).where(s.notna(), None)

    # cột năm còn thiếu so với 5 cột của bảng -> None
    for i in range(len(years), SO_COT_NAM):
        df[f"_trong_{i}"] = None
    ycols += [f"_trong_{i}" for i in range(len(years), SO_COT_NAM)]

    cols = (["ma_truong", "nganh_id", "ma_to_hop", "phuong_thuc"] + ycols
            + ["diem_tb", "diem_min", "diem_max", "diem_moi_nhat",
               "bien_dong", "xu_huong", "so_nam_co_dl"])
    ph = ", ".join(["%s"] * len(cols))
    sql = f"""INSERT INTO dac_trung_diemchuan
                (ma_truong, nganh_id, ma_to_hop, phuong_thuc,
                 diem_nam_1, diem_nam_2, diem_nam_3, diem_nam_4, diem_nam_5,
                 diem_tb, diem_min, diem_max, diem_moi_nhat,
                 bien_dong, xu_huong, so_nam_co_dl)
              VALUES ({ph})
              ON DUPLICATE KEY UPDATE
                diem_nam_1 = VALUES(diem_nam_1), diem_nam_2 = VALUES(diem_nam_2),
                diem_nam_3 = VALUES(diem_nam_3), diem_nam_4 = VALUES(diem_nam_4),
                diem_nam_5 = VALUES(diem_nam_5),
                diem_tb    = VALUES(diem_tb),    diem_min   = VALUES(diem_min),
                diem_max   = VALUES(diem_max),   diem_moi_nhat = VALUES(diem_moi_nhat),
                bien_dong  = VALUES(bien_dong),  xu_huong   = VALUES(xu_huong),
                so_nam_co_dl = VALUES(so_nam_co_dl)"""
    upsert(cur, sql, list(df[cols].itertuples(index=False, name=None)), "dac_trung")
    return years


def don_fact_la(cur, slug2id: dict[str, int]):
    """Xoá dòng fact/đặc trưng không còn trong CSV.

    Import chỉ upsert theo khoá tự nhiên, nên dòng cũ không tự mất. Khi crawler
    sửa tên ngành hỏng font, `nganh_slug` đổi -> `nganh_id` đổi -> khoá tự nhiên
    đổi, và bản cũ nằm lại vĩnh viễn (đã đo: 290 dòng rác sau một lần sửa font).
    Nguồn bỏ bớt ngành giữa hai năm cũng để lại rác y như vậy.

    An toàn với dữ liệu người dùng: `ket_qua_goi_y` không tham chiếu bảng nào ở
    đây (nó trỏ thẳng tới truong/nganh/to_hop), nên xoá fact không xoá lịch sử
    gợi ý. Chạy TRƯỚC don_dim_mo_coi để dòng chiều mất fact thành mồ côi và
    được dọn cùng lượt.
    """
    for bang, csv_name, co_nam in (
            ("diem_chuan", "diem_chuan.csv", True),
            ("dac_trung_diemchuan", "dac_trung_diemchuan.csv", False)):
        df = read_csv(csv_name)
        df["nganh_slug"] = df.nganh_slug.str.slice(0, 120).str.rstrip("-")
        df["nganh_id"] = df.nganh_slug.map(slug2id).astype(int)
        if not co_nam:
            df["nam"] = 0

        # TEMPORARY TABLE không gây implicit commit -> --dry-run vẫn rollback được.
        # COLLATE khớp bảng thật, thiếu nó MySQL báo "Illegal mix of collations".
        cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_khoa")
        cur.execute("""
            CREATE TEMPORARY TABLE tmp_khoa (
                ma_truong   VARCHAR(10) COLLATE utf8mb4_unicode_ci NOT NULL,
                nganh_id    INT UNSIGNED NOT NULL,
                ma_to_hop   VARCHAR(5)  COLLATE utf8mb4_unicode_ci NOT NULL,
                phuong_thuc VARCHAR(20) COLLATE utf8mb4_unicode_ci NOT NULL,
                nam         SMALLINT UNSIGNED NOT NULL,
                PRIMARY KEY (ma_truong, nganh_id, ma_to_hop, phuong_thuc, nam)
            ) ENGINE=InnoDB""")

        rows = list(df[["ma_truong", "nganh_id", "ma_to_hop", "phuong_thuc", "nam"]]
                    .itertuples(index=False, name=None))
        for i in range(0, len(rows), BATCH):
            cur.executemany("INSERT IGNORE INTO tmp_khoa VALUES (%s, %s, %s, %s, %s)",
                            rows[i:i + BATCH])

        nam_on = "AND k.nam = d.nam" if co_nam else ""
        cur.execute(f"""
            DELETE d FROM {bang} d
             LEFT JOIN tmp_khoa k
                    ON k.ma_truong   = d.ma_truong
                   AND k.nganh_id    = d.nganh_id
                   AND k.ma_to_hop   = d.ma_to_hop
                   AND k.phuong_thuc = d.phuong_thuc {nam_on}
             WHERE k.ma_truong IS NULL""")
        if cur.rowcount:
            print(f"   {'dọn ' + bang + ' lạ':22} xoá {cur.rowcount:,} dòng")
        cur.execute("DROP TEMPORARY TABLE tmp_khoa")


def don_nam_cu(cur, years: list[int]):
    """Xoá năm đã rơi khỏi cửa sổ trượt."""
    cur.execute("DELETE FROM diem_chuan WHERE nam < %s", (min(years),))
    if cur.rowcount:
        print(f"   {'dọn năm cũ':22} xoá {cur.rowcount:,} dòng < {min(years)}")


def don_dim_mo_coi(cur):
    """Xoá dòng chiều không còn dòng fact nào trỏ tới.

    Import chỉ upsert nên dòng cũ không tự mất. Khi crawler sửa được tên ngành
    hỏng font, slug đổi -> slug cũ nằm lại trong bảng `nganh` mãi mãi, làm trang
    tra cứu hiện ngành rác. Cùng lý do với trường/tổ hợp mà nguồn đã bỏ, hoặc
    trường có điểm chuẩn nhưng không rút được mã tổ hợp nào (vd Nhạc Viện TPHCM:
    tổ hợp ghi '1') — không tra cứu được thì không nên hiện.

    Giữ lại dòng còn được `ket_qua_goi_y` tham chiếu: FK đó là ON DELETE CASCADE
    nên xoá sẽ xoá luôn lịch sử gợi ý của học sinh.
    """
    for bang, khoa in (("nganh", "nganh_id"), ("to_hop", "ma_to_hop"),
                       ("truong", "ma_truong")):
        cur.execute(f"""
            DELETE d FROM {bang} d
             LEFT JOIN diem_chuan     dc ON dc.{khoa} = d.{khoa}
             LEFT JOIN ket_qua_goi_y  kq ON kq.{khoa} = d.{khoa}
             WHERE dc.{khoa} IS NULL AND kq.{khoa} IS NULL""")
        if cur.rowcount:
            print(f"   {'dọn ' + bang + ' mồ côi':22} xoá {cur.rowcount:,} dòng")


def ghi_nhat_ky(cur, years, n_truong, n_nganh, n_diem):
    cur.execute(
        """INSERT INTO lan_cap_nhat
             (nguon, nam_bat_dau, nam_ket_thuc, so_truong, so_nganh,
              so_dong_diem, selfcheck_dat, ghi_chu)
           VALUES (%s, %s, %s, %s, %s, %s, 1, %s)""",
        ("diemthi.tuyensinh247.com + danh mục tổ hợp Bộ GD&ĐT 2025",
         min(years), max(years), n_truong, n_nganh, n_diem,
         "import từ data/*.csv"))


# ============================================================================
# KIỂM TRA SAU IMPORT
# ============================================================================
def kiem_tra(cur):
    print("\n>> Kiểm tra sau import")
    q = lambda s: (cur.execute(s), cur.fetchone())[1][0]

    dem = {t: q(f"SELECT COUNT(*) FROM {t}") for t in
           ("truong", "nganh", "to_hop", "to_hop_mon", "diem_chuan",
            "dac_trung_diemchuan", "cua_so_nam")}
    for t, n in dem.items():
        print(f"   {t:22} {n:>7,}")

    # khoá ngoại đã do InnoDB đảm bảo; ở đây kiểm các bất biến nghiệp vụ
    assert q("SELECT COUNT(*) FROM truong WHERE tinh_thanh = ''") == 0, \
        "có trường thiếu tinh_thanh"
    assert q("SELECT COUNT(DISTINCT nam) FROM diem_chuan") <= 5, "cửa sổ > 5 năm"
    assert q("SELECT COUNT(*) FROM diem_chuan WHERE diem_chuan <= 0 OR diem_chuan > 40") == 0, \
        "điểm chuẩn ngoài thang"
    assert dem["cua_so_nam"] == q("SELECT COUNT(DISTINCT nam) FROM diem_chuan"), \
        "cua_so_nam lệch số năm thực có"

    # Sau don_fact_la + don_dim_mo_coi, DB phải khớp CSV: không dòng lạ, không
    # dòng chiều mồ côi. Đây là bất biến giữ cho trang tra cứu không hiện ngành,
    # trường hoặc tổ hợp đã bị nguồn bỏ hoặc đã được sửa tên.
    for bang, khoa in (("nganh", "nganh_id"), ("to_hop", "ma_to_hop"),
                       ("truong", "ma_truong")):
        assert q(f"""SELECT COUNT(*) FROM {bang} d
                      LEFT JOIN diem_chuan dc ON dc.{khoa} = d.{khoa}
                      LEFT JOIN ket_qua_goi_y kq ON kq.{khoa} = d.{khoa}
                      WHERE dc.{khoa} IS NULL AND kq.{khoa} IS NULL""") == 0, \
            f"còn dòng mồ côi trong bảng {bang}"
    assert q("""SELECT COUNT(*) FROM dac_trung_diemchuan dt
                 WHERE NOT EXISTS (SELECT 1 FROM diem_chuan dc
                    WHERE dc.ma_truong = dt.ma_truong AND dc.nganh_id = dt.nganh_id
                      AND dc.ma_to_hop = dt.ma_to_hop
                      AND dc.phuong_thuc = dt.phuong_thuc)""") == 0, \
        "bảng đặc trưng có chuỗi không còn dòng fact tương ứng"

    cur.execute("SELECT MIN(nam), MAX(nam) FROM diem_chuan")
    lo, hi = cur.fetchone()
    cov = q("""SELECT ROUND(100 * SUM(th.cac_mon <> '') / COUNT(*), 2)
               FROM diem_chuan dc JOIN to_hop th ON th.ma_to_hop = dc.ma_to_hop""")
    print(f"   cửa sổ năm: {lo}–{hi} | cac_mon phủ {cov}% dòng điểm chuẩn")
    print("[OK] Mọi kiểm tra đạt.")


# ============================================================================
# MAIN
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="Nạp data/*.csv vào MySQL")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default="")
    ap.add_argument("--database", default="uni_map")
    ap.add_argument("--dry-run", action="store_true", help="chạy rồi rollback")
    a = ap.parse_args()

    t0 = time.time()
    conn = pymysql.connect(host=a.host, port=a.port, user=a.user,
                           password=a.password, database=a.database,
                           charset="utf8mb4", autocommit=False)
    try:
        with conn.cursor() as cur:
            print(f">> Nạp vào {a.user}@{a.host}:{a.port}/{a.database}")
            truong  = nap_truong(cur)
            slug2id = nap_nganh(cur)
            nap_to_hop(cur)
            diem    = nap_diem_chuan(cur, slug2id)
            years   = nap_dac_trung(cur, slug2id)
            don_fact_la(cur, slug2id)
            don_nam_cu(cur, years)
            don_dim_mo_coi(cur)
            ghi_nhat_ky(cur, years, len(truong), len(slug2id), len(diem))
            kiem_tra(cur)

        if a.dry_run:
            conn.rollback()
            print(">> --dry-run: đã rollback, DB không thay đổi.")
        else:
            conn.commit()
            print(f">> Đã commit. Xong trong {time.time() - t0:.1f}s")
    except Exception:
        conn.rollback()
        print(">> LỖI — đã rollback, DB giữ nguyên trạng thái trước import.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
