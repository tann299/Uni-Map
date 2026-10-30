const pptxgen = require("pptxgenjs");
const pres = new pptxgen();

pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.author = "Nguyễn Ngọc Tân";
pres.title = "Hệ thống gợi ý nguyện vọng đại học bằng AI (Uni Connect)";

const THEME = {
  name: "Uni Connect DAU",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0E2841", lt1: "FFFFFF", dk2: "990000", lt2: "F3F4F6",
    accent1: "990000", accent2: "FBAE40", accent3: "0E2841",
    accent4: "196B24", accent5: "6B7280", accent6: "FCEFD9",
    hlink: "990000", folHlink: "6B7280",
  },
};

const NAVY = "0E2841", MAROON = "990000", GOLD = "FBAE40",
      WHITE = "FFFFFF", GRAY = "6B7280", LIGHT = "F3F4F6",
      WARM = "FCEFD9", GREEN = "196B24";

const W = 13.33, H = 7.5;

// ---------- Layout frames ----------
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: NAVY },
  objects: [],
  slideNumber: { x: W - 0.9, y: H - 0.38, w: 0.6, h: 0.3, color: "8FA3B8", fontSize: 10 },
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { text: { text: "Uni Connect · Đồ án TTNT AIP202", options: {
        x: 0.5, y: H - 0.42, w: 5, h: 0.3, fontSize: 9, color: GRAY,
        fontFace: "Calibri", margin: 0 } } },
  ],
  slideNumber: { x: W - 0.9, y: H - 0.38, w: 0.6, h: 0.3, color: GRAY, fontSize: 10 },
});

pres.defineSlideMaster({
  title: "SECTION",
  background: { color: MAROON },
  objects: [],
  slideNumber: { x: W - 0.9, y: H - 0.38, w: 0.6, h: 0.3, color: "E8B7B7", fontSize: 10 },
});

const C = pres.SchemeColor;

function titleBar(slide, kicker, title) {
  slide.addText(kicker.toUpperCase(), {
    x: 0.5, y: 0.28, w: 12.3, h: 0.32, fontSize: 12, bold: true,
    color: MAROON, fontFace: "Calibri", charSpacing: 2, margin: 0,
  });
  slide.addText(title, {
    x: 0.5, y: 0.58, w: 12.3, h: 0.75, fontSize: 30, bold: true,
    color: NAVY, fontFace: "Cambria", margin: 0,
  });
}

function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, fill: { color: fill || LIGHT },
    rectRadius: 0.06, line: { type: "none" },
  });
}

// =====================================================================
// S1 — BÌA
// =====================================================================
{
  const s = pres.addSlide({ masterName: "TITLE_DARK" });
  s.addText("TRƯỜNG ĐẠI HỌC KIẾN TRÚC ĐÀ NẴNG · KHOA CÔNG NGHỆ THÔNG TIN", {
    x: 0.9, y: 0.85, w: 11.5, h: 0.35, align: "center", fontSize: 13,
    color: "8FA3B8", fontFace: "Calibri", charSpacing: 2, margin: 0,
  });
  s.addText("HỆ THỐNG GỢI Ý NGUYỆN VỌNG ĐẠI HỌC\nBẰNG TRÍ TUỆ NHÂN TẠO", {
    x: 0.9, y: 1.6, w: 11.5, h: 1.9, align: "center", fontSize: 40,
    bold: true, color: WHITE, fontFace: "Cambria", margin: 0,
  });
  s.addText("UNI CONNECT", {
    x: 0.9, y: 3.55, w: 11.5, h: 0.75, align: "center", fontSize: 32,
    bold: true, color: GOLD, fontFace: "Calibri", charSpacing: 6, margin: 0,
  });
  s.addText("Con đường đến đại học — Tra cứu điểm chuẩn 10 năm & định hướng nguyện vọng bằng AI", {
    x: 0.9, y: 4.35, w: 11.5, h: 0.4, align: "center", fontSize: 15,
    italic: true, color: "CADCFC", fontFace: "Calibri", margin: 0,
  });
  s.addShape(pres.ShapeType.rect, { x: 5.92, y: 4.95, w: 1.5, h: 0.03, fill: { color: GOLD }, line: { type: "none" } });
  s.addText([
    { text: "Sinh viên thực hiện:  ", options: { color: "8FA3B8", fontSize: 14 } },
    { text: "Nguyễn Ngọc Tân — 2351220242 — 23CT1", options: { color: WHITE, fontSize: 14, bold: true } },
  ], { x: 0.9, y: 5.3, w: 11.5, h: 0.4, align: "center", fontFace: "Calibri", margin: 0 });
  s.addText([
    { text: "GVHD:  ", options: { color: "8FA3B8", fontSize: 14 } },
    { text: "TS. Đỗ Phúc Hảo", options: { color: WHITE, fontSize: 14, bold: true } },
  ], { x: 0.9, y: 5.75, w: 11.5, h: 0.4, align: "center", fontFace: "Calibri", margin: 0 });
  s.addText("Học phần AIP202 — Trí tuệ nhân tạo · Đà Nẵng, ngày 29 tháng 10 năm 2026", {
    x: 0.9, y: 6.55, w: 11.5, h: 0.35, align: "center", fontSize: 11,
    color: "8FA3B8", fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Chào thầy cô và các bạn. Em là Nguyễn Ngọc Tân, lớp 23CT1. Hôm nay em trình bày đồ án: Hệ thống gợi ý nguyện vọng đại học bằng trí tuệ nhân tạo — Uni Connect, dưới sự hướng dẫn của TS. Đỗ Phúc Hảo.");
}

// =====================================================================
// S2 — VẤN ĐỀ
// =====================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Mở đầu", "Bài toán: chọn nguyện vọng như đặt cược 1 triệu thí sinh");
  const items = [
    ["Dữ liệu phân tán", "Điểm chuẩn 10 năm rải rác trên hàng trăm cổng thông tin của từng trường, nhiều định dạng, khó so sánh.", "FBAE40"],
    ["Thiếu phân tích rủi ro", "Thí sinh chỉ so sánh cảm tính với điểm chuẩn năm gần nhất, bỏ qua xu hướng và độ dao động.", "FBAE40"],
    ["Chiến lược thiếu an toàn", "Đặt toàn bộ nguyện vọng sát điểm thi hoặc quá cao — nguy cơ trượt toàn bộ danh sách.", "FBAE40"],
  ];
  let y = 1.75;
  for (const [h, d, c] of items) {
    card(s, 0.5, y, 7.4, 1.5, LIGHT);
    s.addShape(pres.ShapeType.ellipse, { x: 0.85, y: y + 0.5, w: 0.5, h: 0.5, fill: { color: MAROON }, line: { type: "none" } });
    s.addText(String(items.indexOf([h, d, c]) + 1) === "NaN" ? "" : "", { x: 0, y: 0, w: 0.01, h: 0.01 });
    s.addText(items.indexOf([h, d, c]) === 0 ? "1" : items.indexOf([h, d, c]) === 1 ? "2" : "3", {
      x: 0.85, y: y + 0.5, w: 0.5, h: 0.5, align: "center", valign: "middle",
      fontSize: 20, bold: true, color: WHITE, fontFace: "Cambria", margin: 0,
    });
    s.addText(h, { x: 1.65, y: y + 0.22, w: 5.9, h: 0.4, fontSize: 17, bold: true, color: NAVY, fontFace: "Cambria", margin: 0 });
    s.addText(d, { x: 1.65, y: y + 0.62, w: 5.9, h: 0.75, fontSize: 12.5, color: "374151", fontFace: "Calibri", margin: 0 });
    y += 1.72;
  }
  // Cột phải: stat
  card(s, 8.2, 1.75, 4.6, 5.0, NAVY);
  s.addText("~1 TRIỆU", { x: 8.5, y: 2.15, w: 4.0, h: 0.8, fontSize: 54, bold: true, color: GOLD, fontFace: "Cambria", margin: 0 });
  s.addText("thí sinh mỗi mùa tuyển sinh", { x: 8.5, y: 2.95, w: 4.0, h: 0.4, fontSize: 14, color: WHITE, fontFace: "Calibri", margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: 8.5, y: 3.6, w: 4.0, h: 0.02, fill: { color: "2E4A68" }, line: { type: "none" } });
  s.addText("không giới hạn nguyện vọng", { x: 8.5, y: 3.8, w: 4.0, h: 0.35, fontSize: 13, color: "CADCFC", fontFace: "Calibri", margin: 0 });
  s.addText("chỉ trúng tuyển 1", { x: 8.5, y: 4.12, w: 4.0, h: 0.35, fontSize: 13, color: "CADCFC", fontFace: "Calibri", margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: 8.5, y: 4.75, w: 4.0, h: 0.02, fill: { color: "2E4A68" }, line: { type: "none" } });
  s.addText("10 năm", { x: 8.5, y: 4.95, w: 4.0, h: 0.6, fontSize: 34, bold: true, color: GOLD, fontFace: "Cambria", margin: 0 });
  s.addText("chuỗi dữ liệu điểm chuẩn 2016–2025 mà hệ thống khai thác", { x: 8.5, y: 5.55, w: 4.0, h: 0.7, fontSize: 13, color: WHITE, fontFace: "Calibri", margin: 0 });
  s.addNotes("Vấn đề đặt ra: dữ liệu phân tán, thiếu công cụ phân tích định lượng rủi ro, và chiến lược đặt nguyện vọng cảm tính. Mỗi mùa có gần 1 triệu thí sinh, đặt không giới hạn nguyện vọng nhưng chỉ đỗ 1 — sai lầm rất đắt.");
}

// =====================================================================
// S3 — MỤC TIÊU
// =====================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Mở đầu", "Bốn mục tiêu của đồ án");
  const goals = [
    ["Dữ liệu", "Thu thập & chuẩn hóa ≥ 250 trường, ≥ 200.000 bản ghi điểm chuẩn 10 năm (2016–2025)", "295 trường · 240.483 bản ghi — VƯỢT", GREEN],
    ["Mô hình AI", "27 đặc trưng; Random Forest đạt > 70% Accuracy, ROC-AUC > 0,80", "74,56% · ROC-AUC 0,8354 — ĐẠT", GREEN],
    ["Phân tầng & giải thích", "3 tầng An toàn / Vừa sức / Thử sức kèm lời giải thích minh bạch", "Vận hành ổn định — ĐẠT", GREEN],
    ["Ứng dụng web", "Django 5.2 + MySQL, phản hồi < 3 giây", "0,42 giây — ĐẠT", GREEN],
  ];
  let y = 1.8;
  for (const [t, d, r, c] of goals) {
    card(s, 0.5, y, 12.33, 1.16, LIGHT);
    s.addText(t, { x: 0.85, y: y + 0.14, w: 2.9, h: 0.85, valign: "middle", fontSize: 16, bold: true, color: MAROON, fontFace: "Cambria", margin: 0 });
    s.addText(d, { x: 3.9, y: y + 0.14, w: 5.6, h: 0.85, valign: "middle", fontSize: 12.5, color: "374151", fontFace: "Calibri", margin: 0 });
    s.addText(r, { x: 9.7, y: y + 0.14, w: 2.95, h: 0.85, valign: "middle", fontSize: 12.5, bold: true, color: c, fontFace: "Calibri", margin: 0 });
    y += 1.34;
  }
  s.addNotes("Bốn mục tiêu: dữ liệu, mô hình AI, phân tầng giải thích, và ứng dụng web. Cột phải là kết quả thực tế — cả 4 mục tiêu đều đạt, mục tiêu dữ liệu vượt mức.");
}

// =====================================================================
// S4 — SECTION: KIẾN TRÚC
// =====================================================================
{
  const s = pres.addSlide({ masterName: "SECTION" });
  s.addText("PHẦN 2", { x: 0.9, y: 2.5, w: 11.5, h: 0.4, align: "center", fontSize: 15, bold: true, color: "F0C9C9", fontFace: "Calibri", charSpacing: 4, margin: 0 });
  s.addText("Thiết kế hệ thống & cơ sở dữ liệu", {
    x: 0.9, y: 3.0, w: 11.5, h: 1.0, align: "center", fontSize: 36, bold: true, color: WHITE, fontFace: "Cambria", margin: 0,
  });
  s.addText("15 bảng quan hệ · 27 đặc trưng · Cửa sổ trượt 10 năm", {
    x: 0.9, y: 4.05, w: 11.5, h: 0.4, align: "center", fontSize: 15, italic: true, color: "F0C9C9", fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Phần 2: thiết kế hệ thống — kiến trúc tổng thể, cơ sở dữ liệu và bộ đặc trưng của mô hình AI.");
}

// =====================================================================
// S5 — KIẾN TRÚC 4 TẦNG
// =====================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Thiết kế", "Kiến trúc khép kín 4 tầng");
  const flow = [
    ["1. THU THẬP", "crawler + CSV", "Tải, làm sạch tự động từ cổng tuyensinh247; chặn năm thiếu dữ liệu"],
    ["2. CSDL MySQL", "15 bảng quan hệ", "Fact diem_chuan 240.483 dòng; cửa sổ trượt cua_so_nam"],
    ["3. MÔ HÌNH AI", "Random Forest", "27 đặc trưng; model.pkl ~52 MB nạp 1 lần vào RAM"],
    ["4. WEB DJANGO", "Tra cứu + gợi ý", "6 app: university, api, accounts, admissions, recommendation, quantri"],
  ];
  let x = 0.5;
  for (const [t, st, d] of flow) {
    card(s, x, 2.0, 2.83, 3.3, LIGHT);
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.25, y: 2.3, w: 2.4, h: 0.62, fill: { color: NAVY }, rectRadius: 0.05, line: { type: "none" } });
    s.addText(t, { x: x + 0.25, y: 2.3, w: 2.4, h: 0.62, align: "center", valign: "middle", fontSize: 13.5, bold: true, color: WHITE, fontFace: "Calibri", margin: 0 });
    s.addText(st, { x: x + 0.25, y: 3.1, w: 2.4, h: 0.4, align: "center", fontSize: 14, bold: true, color: MAROON, fontFace: "Cambria", margin: 0 });
    s.addText(d, { x: x + 0.25, y: 3.55, w: 2.4, h: 1.5, align: "center", fontSize: 11.5, color: "374151", fontFace: "Calibri", margin: 0 });
    if (x < 10.0) s.addText("→", { x: x + 2.83, y: 3.3, w: 0.42, h: 0.5, align: "center", fontSize: 22, bold: true, color: GOLD, fontFace: "Calibri", margin: 0 });
    x += 3.245;
  }
  card(s, 0.5, 5.75, 12.33, 1.0, WARM);
  s.addText([
    { text: "Chịu lỗi:  ", options: { bold: true, color: MAROON } },
    { text: "mô hình lỗi → tự chuyển xếp hạng theo margin, không bao giờ trả lỗi 500 cho người dùng.", options: { color: "374151" } },
  ], { x: 0.85, y: 5.75, w: 11.6, h: 1.0, valign: "middle", fontSize: 14, fontFace: "Calibri", margin: 0 });
  s.addNotes("Kiến trúc 4 tầng khép kín: thu thập, CSDL, mô hình AI, ứng dụng web. Điểm nhấn: cơ chế dự phòng — khi mô hình lỗi, hệ thống xếp hạng theo margin và báo rõ trạng thái, không bao giờ sập.");
}

// =====================================================================
// S6 — SỐ LIỆU CSDL (chart)
// =====================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Thiết kế dữ liệu", "Quy mô dữ liệu thực tế sau chuẩn hóa");
  const stats = [
    ["295", "Trường đại học", "phủ 3 miền"],
    ["3.037", "Ngành đào tạo", "15 nhóm ngành chuẩn"],
    ["340", "Tổ hợp xét tuyển", "A00, B00, D01…"],
    ["240.483", "Bản ghi điểm chuẩn", "10 năm 2016–2025"],
    ["100.363", "Chuỗi đặc trưng", "mỗi nguyện vọng 1 dòng"],
  ];
  let x = 0.5;
  for (const [n, t, d] of stats) {
    card(s, x, 1.85, 2.33, 2.1, LIGHT);
    s.addText(n, { x: x + 0.15, y: 2.05, w: 2.03, h: 0.7, align: "center", fontSize: n.length > 5 ? 24 : 32, bold: true, color: MAROON, fontFace: "Cambria", margin: 0 });
    s.addText(t, { x: x + 0.15, y: 2.78, w: 2.03, h: 0.4, align: "center", fontSize: 12, bold: true, color: NAVY, fontFace: "Calibri", margin: 0 });
    s.addText(d, { x: x + 0.15, y: 3.18, w: 2.03, h: 0.6, align: "center", fontSize: 10, color: GRAY, fontFace: "Calibri", margin: 0 });
    x += 2.51;
  }
  card(s, 0.5, 4.35, 12.33, 2.35, NAVY);
  s.addText("Cửa sổ trượt — cơ chế cập nhật không cần ALTER TABLE", {
    x: 0.85, y: 4.55, w: 11.6, h: 0.4, fontSize: 15, bold: true, color: GOLD, fontFace: "Cambria", margin: 0 });
  s.addText("Bảng cua_so_nam ánh xạ vị trí cột 1–10 sang năm thực 2016–2025. Năm 2026, quản trị viên chỉ đổi ánh xạ qua giao diện: hiển thị tự trượt cửa sổ, AI dùng 6 năm gần nhất. Không sửa mã nguồn, không đổi cấu trúc bảng (yêu cầu CN-05).", {
    x: 0.85, y: 5.0, w: 11.6, h: 1.5, fontSize: 13.5, color: WHITE, fontFace: "Calibri", margin: 0 });
  s.addNotes("Năm con số cốt lõi của CSDL. Điểm thiết kế nổi bật: bảng cửa sổ năm cho phép cập nhật dữ liệu hằng năm chỉ bằng giao diện — hệ thống tự trượt, không phải ALTER TABLE.");
}

// =====================================================================
// S7 — SECTION: MÔ HÌNH AI
// =====================================================================
{
  const s = pres.addSlide({ masterName: "SECTION" });
  s.addText("PHẦN 3", { x: 0.9, y: 2.5, w: 11.5, h: 0.4, align: "center", fontSize: 15, bold: true, color: "F0C9C9", fontFace: "Calibri", charSpacing: 4, margin: 0 });
  s.addText("Mô hình AI & kết quả thực nghiệm", {
    x: 0.9, y: 3.0, w: 11.5, h: 1.0, align: "center", fontSize: 36, bold: true, color: WHITE, fontFace: "Cambria", margin: 0,
  });
  s.addText("27 đặc trưng · nhãn giả lập đối xứng · kiểm thử độc lập năm 2025", {
    x: 0.9, y: 4.05, w: 11.5, h: 0.4, align: "center", fontSize: 15, italic: true, color: "F0C9C9", fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Phần 3: cách huấn luyện mô hình và kết quả thực nghiệm trên tập kiểm thử độc lập.");
}

// =====================================================================
// S8 — 27 ĐẶC TRƯNG & SINH NHÃN
// =====================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Mô hình", "27 đặc trưng và chiến lược sinh nhãn");
  card(s, 0.5, 1.85, 6.0, 4.9, LIGHT);
  s.addText("BỘ 27 ĐẶC TRƯNG", { x: 0.85, y: 2.1, w: 5.3, h: 0.4, fontSize: 15, bold: true, color: MAROON, fontFace: "Cambria", margin: 0 });
  const feats = [
    ["7 số", "margin, diem_thi, diem_moi_nhat, diem_tb, xu_huong, bien_dong, so_nam_co_dl"],
    ["15 one-hot", "nhóm ngành (CNTT, Kinh tế, Y dược…)"],
    ["3", "vùng miền Bắc / Trung / Nam"],
    ["2", "phương thức: thi THPT, học bạ"],
  ];
  let y = 2.6;
  for (const [t, d] of feats) {
    s.addShape(pres.ShapeType.roundRect, { x: 0.85, y: y, w: 1.35, h: 0.5, fill: { color: NAVY }, rectRadius: 0.04, line: { type: "none" } });
    s.addText(t, { x: 0.85, y: y, w: 1.35, h: 0.5, align: "center", valign: "middle", fontSize: 11.5, bold: true, color: WHITE, fontFace: "Calibri", margin: 0 });
    s.addText(d, { x: 2.35, y: y - 0.05, w: 3.95, h: 0.62, valign: "middle", fontSize: 11.5, color: "374151", fontFace: "Calibri", margin: 0 });
    y += 0.72;
  }
  s.addText([
    { text: "margin ", options: { bold: true, color: MAROON, fontFace: "Courier New", fontSize: 12 } },
    { text: "= điểm thí sinh − chuẩn mới nhất — đặc trưng trung tâm (60,6% đóng góp).", options: { color: "374151", fontSize: 12 } },
  ], { x: 0.85, y: 5.6, w: 5.3, h: 0.95, fontFace: "Calibri", margin: 0 });

  card(s, 6.85, 1.85, 5.98, 4.9, LIGHT);
  s.addText("SINH NHÃN GIẢ LẬP & CHỐNG RÒ RỈ", { x: 7.2, y: 2.1, w: 5.3, h: 0.4, fontSize: 15, bold: true, color: MAROON, fontFace: "Cambria", margin: 0 });
  s.addText("Mỗi điểm chuẩn C của năm t là “sự thật tuyển sinh”: thí sinh giả lập X ≥ C thì đỗ. 11 mức DELTAS đối xứng (±0,2 … ±3,0) tạo mẫu đỗ/trượt cân bằng.", {
    x: 7.2, y: 2.55, w: 5.3, h: 1.3, fontSize: 12.5, color: "374151", fontFace: "Calibri", margin: 0 });
  s.addText("Đặc trưng của năm t chỉ tính từ các năm < t — ngăn tuyệt đối data leakage.", {
    x: 7.2, y: 3.9, w: 5.3, h: 0.7, fontSize: 12.5, bold: true, color: NAVY, fontFace: "Calibri", margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: 7.2, y: 4.75, w: 5.3, h: 1.55, fill: { color: NAVY }, rectRadius: 0.06, line: { type: "none" } });
  s.addText([
    { text: "Chia cứng theo thời gian\n", options: { bold: true, color: GOLD, fontSize: 14 } },
    { text: "Huấn luyện 2021–2024 (913.924 mẫu)\nKiểm thử độc lập 2025 (244.123 mẫu)", options: { color: WHITE, fontSize: 13 } },
  ], { x: 7.45, y: 4.75, w: 4.8, h: 1.55, valign: "middle", fontFace: "Calibri", margin: 0 });
  s.addNotes("Vector 27 chiều gồm 7 đặc trưng số, 15 one-hot nhóm ngành, 3 vùng miền, 2 phương thức. Nhãn huấn luyện sinh giả lập đối xứng quanh điểm chuẩn, đặc trưng chỉ dùng quá khứ để chống rò rỉ, chia tập cứng theo thời gian.");
}

// =====================================================================
// S9 — KẾT QUẢ (chart so sánh DT vs RF)
// =====================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Kết quả", "Random Forest vượt trội Decision Tree trên 244.123 mẫu");
  const rows = [
    [
      { text: "Chỉ số", options: { bold: true, color: WHITE, fill: { color: NAVY }, align: "left" } },
      { text: "Decision Tree", options: { bold: true, color: WHITE, fill: { color: NAVY }, align: "center" } },
      { text: "Random Forest", options: { bold: true, color: WHITE, fill: { color: NAVY }, align: "center" } },
    ],
    ["Accuracy", "0,7214", "0,7456"],
    ["ROC-AUC", "0,7535", "0,8354"],
    ["Brier score ↓", "0,2550", "0,1763"],
    ["F1 (lớp Đỗ)", "0,7183", "0,7493"],
  ];
  s.addTable(rows.map((r, i) => i === 0 ? r : r.map((c, j) => ({
    text: c,
    options: {
      align: j === 0 ? "left" : "center",
      bold: j === 2, color: j === 2 ? MAROON : "374151",
      fill: { color: i % 2 ? LIGHT : WHITE },
    },
  }))), {
    x: 0.5, y: 1.95, w: 6.2, h: 3.2, fontSize: 13.5, fontFace: "Calibri",
    border: { type: "solid", color: "DADEE2", pt: 0.75 }, valign: "middle",
  });
  const bars = [
    ["ROC-AUC tăng", "+0,0819", "khả năng xếp hạng Đỗ/Trượt nhờ trung bình 100 cây"],
    ["Brier giảm", "−0,0787", "xác suất hiệu chuẩn tốt — quan trọng cho phân tầng"],
    ["Recall Đỗ", "+0,0459", "bắt thêm cơ hội đỗ, Recall Trượt giữ ≈ 0,80"],
  ];
  let y = 1.95;
  for (const [t, v, d] of bars) {
    card(s, 7.05, y, 5.78, 1.35, LIGHT);
    s.addText(v, { x: 7.3, y: y + 0.15, w: 1.8, h: 1.05, valign: "middle", fontSize: 21, bold: true, color: GREEN, fontFace: "Cambria", margin: 0 });
    s.addText([
      { text: t + "\n", options: { bold: true, color: NAVY, fontSize: 13 } },
      { text: d, options: { color: "374151", fontSize: 11.5 } },
    ], { x: 9.2, y: y + 0.12, w: 3.5, h: 1.15, valign: "middle", fontFace: "Calibri", margin: 0 });
    y += 1.52;
  }
  card(s, 0.5, 5.5, 12.33, 1.25, WARM);
  s.addText([
    { text: "Đọc quan trọng nhất:  ", options: { bold: true, color: MAROON } },
    { text: "lợi ích lớn nhất nằm ở chất lượng xếp hạng và hiệu chuẩn xác suất — đúng thứ hệ thống cần, vì phân tầng phụ thuộc toàn bộ vào giá trị p.", options: { color: "374151" } },
  ], { x: 0.85, y: 5.5, w: 11.6, h: 1.25, valign: "middle", fontSize: 14, fontFace: "Calibri", margin: 0 });
  s.addNotes("Trên 244.123 mẫu kiểm thử độc lập năm 2025: RF thắng DT ở cả 4 chỉ số. ROC-AUC tăng 0,0819 — nhiều nhất; Brier giảm mạnh nghĩa là xác suất đáng tin, điều kiện tiên quyết cho phân tầng 3 mức.");
}

// =====================================================================
// S10 — TẦM QUAN TRỌNG ĐẶC TRƯNG (bar chart)
// =====================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Kết quả", "margin và diem_thi quyết định hơn 82% dự đoán");
  s.addChart(pres.charts.BAR, [{
    name: "Mức đóng góp",
    labels: ["margin", "diem_thi", "diem_moi_nhat", "diem_tb", "bien_dong", "xu_huong"],
    values: [0.6060, 0.2181, 0.0509, 0.0425, 0.0164, 0.0164],
  }], {
    x: 0.5, y: 1.9, w: 7.3, h: 4.8, barDir: "bar",
    chartColors: [MAROON],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: NAVY, dataLabelFontSize: 11, dataLabelFontFace: "Calibri", dataLabelFormatCode: "0.0000",
    catAxisLabelColor: NAVY, catAxisLabelFontSize: 12, catAxisLabelFontFace: "Calibri",
    valAxisLabelColor: GRAY, valAxisLabelFontSize: 10, valAxisLabelFontFace: "Calibri",
    valGridLine: { color: "E5E7EB", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: false, showTitle: false,
  });
  card(s, 8.15, 1.9, 4.68, 4.8, LIGHT);
  s.addText("DIỄN GIẢCH", { x: 8.5, y: 2.15, w: 4.0, h: 0.4, fontSize: 15, bold: true, color: MAROON, fontFace: "Cambria", margin: 0 });
  s.addText([
    { text: "margin (0,606) ", options: { bold: true, color: MAROON, fontFace: "Courier New" } },
    { text: "— khoảng cách năng lực so với chuẩn mới nhất, trực giác tuyển sinh được dữ liệu xác nhận.\n\n", options: { color: "374151" } },
    { text: "diem_thi (0,218) ", options: { bold: true, color: MAROON, fontFace: "Courier New" } },
    { text: "— năng lực tuyệt đối của thí sinh.\n\n", options: { color: "374151" } },
    { text: "Nhóm lịch sử ", options: { bold: true, color: NAVY } },
    { text: "(diem_moi_nhat, diem_tb, bien_dong, xu_huong) — hiệu chỉnh rủi ro, phân biệt các ngành cùng margin nhưng độ ổn định khác nhau.", options: { color: "374151" } },
  ], { x: 8.5, y: 2.6, w: 4.0, h: 3.9, fontSize: 12, fontFace: "Calibri", margin: 0 });
  s.addNotes("Từ feature_importances_: margin chiếm 60,6%, diem_thi 21,8% — hai đặc trưng chiếm hơn 82%. Nhóm đặc trưng lịch sử đóng vai trò hiệu chỉnh rủi ro.");
}

// =====================================================================
// S11 — SECTION: DEMO
// =====================================================================
{
  const s = pres.addSlide({ masterName: "SECTION" });
  s.addText("PHẦN 4", { x: 0.9, y: 2.5, w: 11.5, h: 0.4, align: "center", fontSize: 15, bold: true, color: "F0C9C9", fontFace: "Calibri", charSpacing: 4, margin: 0 });
  s.addText("Giao diện thực tế của hệ thống", {
    x: 0.9, y: 3.0, w: 11.5, h: 1.0, align: "center", fontSize: 36, bold: true, color: WHITE, fontFace: "Cambria", margin: 0,
  });
  s.addText("uniconnect.id.vn — Django 5.2 · Tailwind CSS · MySQL 8.0", {
    x: 0.9, y: 4.05, w: 11.5, h: 0.4, align: "center", fontSize: 15, italic: true, color: "F0C9C9", fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Phần 4: xem giao diện thực tế đang chạy tại uniconnect.id.vn.");
}

// =====================================================================
// S12..14 — ẢNH GIAO DIỆN THẬT
// =====================================================================
function imgSlide(no, img, caption, notes) {
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Demo giao diện", caption);
  s.addImage({ path: img, x: 0.5, y: 1.7, w: 12.33, h: 12.33 * (notes.h / notes.w), rounding: false });
  s.addText(notes.txt, { x: 0.5, y: 6.85, w: 12.33, h: 0.35, fontSize: 11, italic: true, color: GRAY, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes(notes.txt);
  return s;
}

// S12 — trang chủ (2000x1062)
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Demo giao diện", "Trang chủ — tra cứu điểm chuẩn 10 năm & định hướng AI");
  s.addImage({ path: "uniconnect-p1.png", x: 2.17, y: 1.72, w: 9.0, h: 9.0 * (1062 / 2000) });
  s.addText("Bộ lọc đa chiều: tên trường/ngành · phương thức · khu vực · tổ hợp — cùng 4 chỉ số hệ thống trực tiếp.", {
    x: 0.5, y: 6.55, w: 12.33, h: 0.35, fontSize: 11.5, italic: true, color: GRAY, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("Trang chủ: thanh bộ lọc tra cứu nhanh toàn quốc với dữ liệu 2016–2025, các thẻ thống kê trực tiếp từ CSDL: 295 trường, 3.037 ngành, 240.483 dòng điểm, 3 tầng phân loại AI.");
}

// S13 — tra cứu chi tiết (2000x1132)
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Demo giao diện", "Tra cứu điểm chuẩn — chuỗi 10 năm từng nguyện vọng");
  s.addImage({ path: "uniconnect-p2.png", x: 2.17, y: 1.72, w: 9.0, h: 9.0 * (1132 / 2000) });
  s.addText("Bảng điểm chuẩn đầy đủ 10 năm (thang 30) kèm bộ lọc thông minh đa chiều và gợi ý nhanh.", {
    x: 0.5, y: 6.75, w: 12.33, h: 0.35, fontSize: 11.5, italic: true, color: GRAY, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("Trang tra cứu: tìm theo tên trường, bộ lọc tỉnh thành/vùng miền/nhóm ngành/tổ hợp/phương thức, và bảng chuỗi điểm chuẩn đủ 10 năm cho từng nguyện vọng.");
}

// S14 — danh sách trường (2000x1164)
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Demo giao diện", "Danh sách trường — 295 đại học trên toàn quốc");
  s.addImage({ path: "uniconnect-p3.png", x: 2.17, y: 1.72, w: 9.0, h: 9.0 * (1164 / 2000) });
  s.addText("Thẻ trường kèm logo, mã tuyển sinh, số ngành và điểm chuẩn trung bình; lọc theo vùng miền, tỉnh thành.", {
    x: 0.5, y: 6.85, w: 12.33, h: 0.35, fontSize: 11.5, italic: true, color: GRAY, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("Trang danh sách trường: 295 trường dạng thẻ, mỗi trường có logo, mã, số ngành, điểm trung bình; bộ lọc theo vùng và tỉnh.");
}

// S14b — trang gợi ý AI (2000x1085) — slide trung tâm của demo
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Demo giao diện", "Gợi ý nguyện vọng AI — phân tầng An toàn · Vừa sức · Thử sức");
  s.addImage({ path: "uniconnect-goiy.png", x: 2.17, y: 1.72, w: 9.0, h: 9.0 * (1085 / 2000) });
  s.addText("30 nguyện vọng xếp theo xác suất đỗ; thẻ nguyện vọng hiển thị khả năng đỗ %, khoảng cách điểm và chuỗi 10 năm.", {
    x: 0.5, y: 6.75, w: 12.33, h: 0.35, fontSize: 11.5, italic: true, color: GRAY, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("Trang gợi ý AI — trái tim của hệ thống: mỗi thẻ nguyện vọng hiển thị tổ hợp xét tuyển, khả năng đỗ (vd 95,12%), điểm bản, chuẩn mới nhất, độ dốc so với chuẩn, và đồ thị chuỗi 10 năm. Ba tầng An toàn / Vừa sức / Thử sức ứng với p ≥ 80%, 40–80%, < 40%.");
}

// S15 — admin console (2000x1020)
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Demo giao diện", "Admin Console — giám sát CSDL, chất lượng và mô hình AI");
  s.addImage({ path: "uniconnect-p4.png", x: 2.17, y: 1.72, w: 9.0, h: 9.0 * (1020 / 2000) });
  s.addText("Dashboard: 240.483 dòng Fact · self-check chất lượng · trạng thái AI · nhật ký 10 lần gợi ý gần nhất.", {
    x: 0.5, y: 6.5, w: 12.33, h: 0.35, fontSize: 11.5, italic: true, color: GRAY, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("Admin Console: theo dõi quy mô dữ liệu, kiểm tra chất lượng (UTF-8 100%, 0 lỗi font), trạng thái mô hình AI, và nhật ký hoạt động gần nhất — nơi quản trị viên cập nhật dữ liệu và huấn luyện lại mô hình.");
}

// =====================================================================
// S16 — HƯỚNG PHÁT TRIỂN
// =====================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  titleBar(s, "Kết luận", "Kết luận & hướng phát triển");
  card(s, 0.5, 1.85, 6.0, 4.9, LIGHT);
  s.addText("ĐÃ LÀM ĐƯỢC", { x: 0.85, y: 2.1, w: 5.3, h: 0.4, fontSize: 15, bold: true, color: GREEN, fontFace: "Cambria", margin: 0 });
  const done = [
    "CSDL thật 10 năm: 295 trường · 240.483 bản ghi",
    "Random Forest: Accuracy 74,56% · ROC-AUC 0,8354",
    "Phân tầng 3 mức minh bạch, có lời giải thích",
    "Web hoàn chỉnh, phản hồi 0,42 s, không lỗi 500",
  ];
  let y = 2.6;
  for (const d of done) {
    s.addText("✓", { x: 0.85, y: y, w: 0.4, h: 0.4, fontSize: 15, bold: true, color: GREEN, fontFace: "Calibri", margin: 0 });
    s.addText(d, { x: 1.3, y: y, w: 4.9, h: 0.55, fontSize: 12.5, color: "374151", fontFace: "Calibri", valign: "top", margin: 0 });
    y += 0.72;
  }
  s.addText("Bài học: chất lượng dữ liệu đóng góp nhiều hơn tinh chỉnh siêu tham số; chia tập theo thời gian là điều kiện bắt buộc.", {
    x: 0.85, y: 5.55, w: 5.3, h: 1.0, fontSize: 11.5, italic: true, color: GRAY, fontFace: "Calibri", margin: 0 });

  card(s, 6.85, 1.85, 5.98, 4.9, NAVY);
  s.addText("HƯỚNG PHÁT TRIỂN", { x: 7.2, y: 2.1, w: 5.3, h: 0.4, fontSize: 15, bold: true, color: GOLD, fontFace: "Cambria", margin: 0 });
  const next = [
    ["Mở rộng phương thức", "Đánh giá năng lực & tư duy — chuẩn hóa thang điểm tương đương"],
    ["Nhãn đỗ/trượt thật", "Khảo sát thí sinh sau mỗi mùa, thay nhãn giả lập DELTAS"],
    ["Tối ưu thứ tự NV", "Lý thuyết trò chơi / quy hoạch tuyến tính tối đa hóa xác suất trúng"],
    ["Kiểm thử tải & đám mây", "Đo tải đồng thời mùa cao điểm, auto-scaling"],
  ];
  y = 2.6;
  for (const [t, d] of next) {
    s.addText([
      { text: t + "  —  ", options: { bold: true, color: WHITE } },
      { text: d, options: { color: "CADCFC" } },
    ], { x: 7.2, y: y, w: 5.3, h: 0.95, fontSize: 12.5, fontFace: "Calibri", valign: "top", margin: 0 });
    y += 1.02;
  }
  s.addNotes("Tổng kết: 4 kết quả chính đều đạt hoặc vượt mục tiêu. Hướng phát triển: mở rộng phương thức xét tuyển, thu thập nhãn thật, tối ưu thứ tự nguyện vọng và kiểm thử tải trên đám mây.");
}

// =====================================================================
// S17 — CẢM ƠN
// =====================================================================
{
  const s = pres.addSlide({ masterName: "TITLE_DARK" });
  s.addText("CẢM ƠN THẦY CÔ VÀ CÁC BẠN ĐÃ LẮNG NGHE!", {
    x: 0.9, y: 2.7, w: 11.5, h: 1.0, align: "center", fontSize: 36, bold: true, color: WHITE, fontFace: "Cambria", margin: 0,
  });
  s.addText("Rất mong nhận được câu hỏi và góp ý của hội đồng", {
    x: 0.9, y: 3.85, w: 11.5, h: 0.5, align: "center", fontSize: 16, italic: true, color: "CADCFC", fontFace: "Calibri", margin: 0,
  });
  s.addShape(pres.ShapeType.rect, { x: 5.92, y: 4.6, w: 1.5, h: 0.03, fill: { color: GOLD }, line: { type: "none" } });
  s.addText("Nguyễn Ngọc Tân — 2351220242 — 23CT1", {
    x: 0.9, y: 4.85, w: 11.5, h: 0.4, align: "center", fontSize: 14, bold: true, color: GOLD, fontFace: "Calibri", margin: 0,
  });
  s.addText("uniconnect.id.vn", {
    x: 0.9, y: 5.3, w: 11.5, h: 0.4, align: "center", fontSize: 13, color: "8FA3B8", fontFace: "Calibri", margin: 0,
  });
  s.addNotes("Em xin hết phần trình bày. Em rất mong nhận được câu hỏi và góp ý của thầy cô và các bạn. Xin cảm ơn!");
}

pres.writeFile({ fileName: "Uni-Connect-slide-bao-cao-v2.pptx" }).then(() => console.log("written"));
