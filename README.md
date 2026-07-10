# stic-binh-sai-spinter250 — Bình sai Lưới Độ cao (Thủy chuẩn) & Xuất Báo cáo

Chương trình bình sai lưới khống chế độ cao (đo thủy chuẩn hình học) bằng
phương pháp gián tiếp (LSQ), kiểm tra sai số khép vòng, đánh giá độ chính
xác và xuất báo cáo `.docx` theo mẫu "THÀNH QUẢ TÍNH TOÁN BÌNH SAI LƯỚI ĐỘ
CAO". Đặc tả đầy đủ: xem [SPEC.md](SPEC.md).

Tên repo có "spinter250" vì hướng tới hỗ trợ nhập liệu trực tiếp từ máy
thủy chuẩn điện tử Leica Sprinter 250M (GSI/Excel) — xem mục 10 của
SPEC.md; phần này **chưa triển khai**, xem "Trạng thái" bên dưới.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Sử dụng

```bash
python -m binh_sai_do_cao.main --input du_lieu.json --output bao_cao.docx
```

Định dạng file JSON đầu vào: xem SPEC.md mục 2 (`project`, `settings`,
`known_points`, `observations`). Ví dụ đầy đủ đã kiểm chứng bằng bộ số liệu
thật "Cầu Cửa Đại lần 3": `binh_sai_do_cao/tests/fixtures/cua_dai_input.json`.

## Kiến trúc

```
binh_sai_do_cao/
├── io/
│   ├── input_loader.py      # đọc JSON, validate schema
│   └── report_writer.py     # dựng báo cáo .docx (python-docx)
├── core/
│   ├── network_graph.py     # dựng đồ hình, kiểm tra liên thông
│   ├── loop_finder.py       # spanning tree + fundamental cycles
│   ├── closure_check.py     # Wh, Wh(gh), cờ "sát giới hạn"
│   ├── adjustment.py        # bình sai gián tiếp LSQ
│   └── accuracy.py          # Mo, Qxx, SSTP điểm/trị đo
├── models/schema.py          # dataclass Point, Observation, ProjectSettings
├── main.py                   # CLI, điều phối pipeline end-to-end
└── tests/                    # pytest — 21/21 pass, gồm hồi quy Cầu Cửa Đại
```

## Trạng thái triển khai (đối chiếu SPEC.md mục 9)

- [x] Phase 1 — Input & đồ hình lưới (schema, input_loader, network_graph)
- [x] Phase 2 — Kiểm tra sai số khép (loop_finder, closure_check) — khớp
      chính xác 13/13 vòng khép của bộ số liệu Cầu Cửa Đại, gồm cờ "sát
      giới hạn" ở vòng MC6→M24TL→M24HL→MC6
- [x] Phase 3 — Bình sai gián tiếp LSQ (adjustment, accuracy) — Mo, 53 độ
      cao sau bình sai, SSTP điểm/trị đo đều khớp file mẫu (chi tiết bên dưới)
- [x] Phase 4 — Xuất báo cáo `.docx` — **chưa có file mẫu `.docx` đã đánh
      dấu placeholder**, nên báo cáo được dựng trực tiếp bằng `python-docx`
      theo đúng nội dung/thứ tự các mục ở SPEC.md mục 4 (không phải
      `docxtpl` điền vào template như spec đề xuất ban đầu). Khi có file
      mẫu thật, thay phần dựng doc trong `report_writer.py` bằng
      `docxtpl` — các hàm chuẩn bị dữ liệu (context) có thể tái dùng.
- [x] Phase 5 — `main.py` nối toàn bộ pipeline, xử lý lỗi biên (lưới phân
      mảnh, hệ vô định, ma trận suy biến) — SPEC.md mục 7
- [ ] Phase 6 — GSI Import (Sprinter 250M): **chưa triển khai**. Cần 1 file
      GSI-8/GSI-16 hoặc Excel xuất thật từ máy Sprinter 250M/Sprinter
      DataLoader làm dữ liệu mẫu trước khi viết `io/gsi_parser.py` (SPEC.md
      mục 10, TODO Phase 6) — hiện chưa có file mẫu.
- [ ] Phase 7 — Mobile Field App (PWA): **chưa triển khai**. Xem SPEC.md
      mục 11 — cần thiết lập GitHub Pages riêng và kiểm thử trên thiết bị
      Android/iOS thật.

## Kiểm thử

```bash
python3 -m pytest binh_sai_do_cao/tests/ -v
```

21/21 test pass, gồm:
- Unit test từng module (TC-01 → TC-13, SPEC.md mục 6.1) — TC-12 đối
  chiếu với lời giải tay một lưới 3 điểm/4 trị đo.
- **Hồi quy bằng bộ số liệu thật "Cầu Cửa Đại lần 3"** (TC-20 → TC-27,
  SPEC.md mục 6.2) — trích xuất trực tiếp từ file
  `SỐ_LIỆU_CẦU_CỬA_ĐẠI_LẦN_3_11_7_25x.docx` do người dùng cung cấp
  (2 điểm gốc, 53 điểm mới, 67 trị đo, 13 vòng khép độc lập). Toàn bộ
  53 độ cao sau bình sai khớp file mẫu trong sai số ≤ 0.5mm, Mo = 0.13
  mm/Tr khớp chính xác, SSTP điểm lớn nhất/nhỏ nhất đúng tên điểm
  (T13TL/M24TL). Riêng 2/13 giá trị Wh lệch ≤ 0.02–0.1mm so với file mẫu
  do làm tròn hiển thị trị đo về 4 chữ số thập phân trước khi cộng dồn ở
  nguồn dữ liệu gốc — đúng như cảnh báo ở SPEC.md mục 7 (không phải lỗi
  thuật toán).

## Việc còn mở

1. File `.docx` mẫu có placeholder thật (để chuyển sang `docxtpl`, giữ
   đúng style/font gốc thay vì layout mặc định của `python-docx`).
2. File GSI/Excel mẫu thật từ Sprinter 250M cho Phase 6.
3. PWA mobile field app (Phase 7) — xem SPEC.md mục 11.
