# SPEC: Chương trình Bình sai Lưới Độ cao (Thủy chuẩn) & Xuất Báo cáo

Tài liệu đặc tả kỹ thuật cho chương trình tính bình sai lưới khống chế độ cao (đo thủy chuẩn hình học), tham chiếu theo mẫu báo cáo "THÀNH QUẢ TÍNH TOÁN BÌNH SAI LƯỚI ĐỘ CAO" (dạng phần mềm HHMAPS 2019) — file `SỐ_LIỆU_CẦU_CỬA_ĐẠI_LẦN_3_11_7_25x.docx`.

---

## 1. Mục tiêu & Phạm vi

Chương trình nhận vào:
- Danh sách điểm gốc (đã biết độ cao)
- Danh sách trị đo chênh cao giữa các điểm (kèm số trạm đo), qua 3 nguồn: (a) file JSON/Excel tổng hợp sẵn, (b) file GSI/Excel xuất từ Leica Sprinter 150M/250M, (c) nhập tay qua ứng dụng mobile (xem mục 11)

Và thực hiện:
1. Kiểm tra sai số khép cho các vòng đo khép kín trong lưới (QC trước bình sai)
2. Bình sai toàn mạng lưới bằng phương pháp gián tiếp (bình phương nhỏ nhất — LSQ)
3. Đánh giá độ chính xác (sai số trung phương trọng số đơn vị, sai số trung phương từng điểm, từng trị đo)
4. Xuất báo cáo `.docx` đúng bố cục mẫu

Không thuộc phạm vi: đo GNSS/lưới mặt bằng, bình sai lưới độ cao hạng đặc biệt bằng thủy chuẩn hình học chính xác cao dùng công nghệ số (digital level) có hiệu chỉnh khí quyển riêng — có thể mở rộng sau.

---

## 2. Mô hình dữ liệu đầu vào

Đề xuất định dạng JSON (hoặc Excel/CSV import tương đương) để tách biệt dữ liệu khỏi logic tính toán. **Đây là định dạng "chuẩn nội bộ"** — dữ liệu từ máy Sprinter (mục 10) hay từ app mobile (mục 11) đều phải được chuyển đổi về đúng schema này trước khi vào pipeline xử lý ở mục 3.

```json
{
  "project": {
    "name": "LƯỚI KHỐNG CHẾ ĐỘ CAO",
    "date": "2025-07-11",
    "surveyor": "",
    "computer": "",
    "checker": ""
  },
  "settings": {
    "adjustment_method": "indirect",       // "indirect" (gián tiếp/phụ thuộc) | "conditional" (điều kiện)
    "closure_formula": "k_sqrt_n",          // "k_sqrt_n" | "k_sqrt_L"
    "k_coefficient_mm": 0.3,                 // hệ số k trong Wh(gh) = k*sqrt(n)
    "weight_basis": "station_count"          // "station_count" | "distance_km"
  },
  "known_points": [
    { "name": "MC2", "height_m": 0.7614 },
    { "name": "MC6", "height_m": 1.7587 }
  ],
  "observations": [
    {
      "id": 1,
      "from": "MC2",
      "to": "MC6",
      "measured_dh_m": 0.9973,
      "stations": 61,
      "distance_km": null
    },
    { "id": 2, "from": "MC6", "to": "MC2", "measured_dh_m": -0.9975, "stations": 59 }
  ]
}
```

**Ràng buộc dữ liệu đầu vào:**
- Mỗi `observation` phải có `from`, `to` là tên điểm tồn tại trong `known_points` hoặc sẽ được suy ra là điểm mới.
- `stations` bắt buộc nếu `weight_basis = station_count`; `distance_km` bắt buộc nếu `weight_basis = distance_km`.
- Đồ hình lưới (graph vô hướng có trọng số) phải liên thông — nếu không, báo lỗi "lưới bị phân mảnh, điểm X không liên kết".
- Phải có ít nhất 1 điểm gốc.

---

## 3. Quy trình xử lý (Pipeline)

### Bước 3.1 — Nạp & kiểm tra dữ liệu
- Parse JSON/Excel.
- Kiểm tra trùng lặp tên điểm, đoạn đo trùng, giá trị NaN/rỗng.
- Dựng đồ hình lưới: mỗi điểm là 1 node, mỗi trị đo là 1 cạnh (có hướng, mang giá trị chênh cao + trọng số).

### Bước 3.2 — Phát hiện vòng khép độc lập (fundamental cycles)
Dùng thuật toán: dựng cây khung (spanning tree) của đồ hình bằng BFS/DFS; mỗi cạnh **không** thuộc cây khung khi thêm vào sẽ tạo đúng 1 vòng khép độc lập (fundamental cycle). Số vòng độc lập = (số cạnh) − (số đỉnh) + (số thành phần liên thông).

> Đây chính là cách phần mềm mẫu sinh ra 13 vòng khép trong file tham chiếu — mỗi vòng dùng để kiểm tra QC, **không phải** phương pháp phân phối sai số cuối cùng.

Với mỗi vòng độc lập tìm được:
```
Wh = Σ (chênh cao đo, có dấu, đi hết vòng)     [mm]
n  = Σ (số trạm đo của các đoạn trong vòng)
Wh(gh) = k × √n     [mm]   (mặc định k = 0.3 nếu không cấu hình khác — tùy cấp hạng lưới)
```
- Nếu `weight_basis = distance_km`: `Wh(gh) = k × √L` với L = tổng chiều dài (km).
- Kết luận: `|Wh| ≤ Wh(gh)` → Đạt; ngược lại → Cảnh báo/Lỗi, yêu cầu đo lại đoạn nghi vấn.
- **Cờ cảnh báo riêng**: nếu `|Wh| / Wh(gh) ≥ 0.9` → đánh dấu "sát giới hạn" trong báo cáo (như vòng số 6 trong ví dụ thực tế, tỉ lệ = 1.0).

### Bước 3.3 — Bình sai gián tiếp toàn mạng (Least Squares)
Áp dụng khi lưới có nút (nhiều vòng nối nhau) — không dùng phân phối tỉ lệ đơn giản theo từng vòng riêng lẻ vì sẽ sai khi 1 đoạn đo thuộc nhiều vòng.

1. **Ẩn số**: độ cao gần đúng H⁰ᵢ của mỗi điểm mới + số hiệu chỉnh Xᵢ. Điểm gốc: H cố định, không là ẩn số.
2. **Phương trình số hiệu chỉnh** cho từng trị đo (i→j):
   ```
   v_ij = (H⁰_j + X_j) - (H⁰_i + X_i) - h_đo,ij
   ```
   (điểm gốc thì H⁰+X = H gốc cố định, X = 0)
3. **Ma trận thiết kế A** (số hàng = số trị đo, số cột = số ẩn số): mỗi hàng có +1 tại cột điểm cuối, −1 tại cột điểm đầu (0 nếu là điểm gốc).
4. **Trọng số P** (ma trận đường chéo):
   ```
   P_i = c / n_i        (nếu weight_basis = station_count)
   P_i = c / L_i         (nếu weight_basis = distance_km)
   ```
   **c = 1** (chốt cố định). Đây là hằng số quy ước "trọng số đơn vị"; về mặt toán học c triệt tiêu trong nghiệm X (độ cao sau bình sai) và trong m_H (SSTP điểm) vì Mo² tỉ lệ thuận c còn Qxx tỉ lệ nghịch c. Chọn c=1 khớp quy ước của phần mềm tham chiếu (Mo hiển thị đơn vị "mm/Tr" = mm/√1 trạm).
5. **Giải hệ phương trình chuẩn**:
   ```
   (AᵀPA) X = AᵀP·L        (L = vector số hạng tự do = h_đo - (H⁰_j - H⁰_i))
   X = (AᵀPA)⁻¹ AᵀP·L
   ```
6. **Số hiệu chỉnh (SHC)** từng trị đo: `V = A·X − L`
7. **Trị bình sai** từng trị đo: `h_BS = h_đo + V`
8. **Độ cao sau bình sai**: `H = H⁰ + X`

### Bước 3.4 — Đánh giá độ chính xác
```
Mo = √( (VᵀPV) / (n_đo - n_ẩn) )        // sai số trung phương trọng số đơn vị
Qxx = (AᵀPA)⁻¹                            // ma trận hiệp phương sai ẩn số
m_Hi = Mo × √(Qxx[i][i])                  // SSTP độ cao điểm i
m_hij = Mo × √(qii của trị đo ij)         // SSTP trị đo chênh cao ij (qua lan truyền sai số)
```
Xuất giá trị lớn nhất/nhỏ nhất cho cả 2 nhóm (điểm & trị đo) kèm tên điểm/đoạn tương ứng — đúng như mục "Kết quả đánh giá độ chính xác lưới" trong mẫu.

---

## 4. Đặc tả báo cáo đầu ra (điền vào mẫu Word có sẵn)

**Xác nhận:** dùng phương án **điền vào file `.docx` mẫu có sẵn** (không sinh báo cáo từ đầu). File mẫu (`SỐ_LIỆU_CẦU_CỬA_ĐẠI_LẦN_3_11_7_25x.docx` hoặc bản mẫu trống tương đương) đóng vai trò template — chương trình chỉ thay nội dung động, giữ nguyên toàn bộ style/format/font gốc.

**Cách tiếp cận kỹ thuật (để phiên code sau tham khảo):**
- Với đoạn text tĩnh (tên công trình, số điểm gốc, Mo, ngày tháng...): dùng `docxtpl` với placeholder dạng `{{ project_name }}`, `{{ mo_value }}`... chèn sẵn vào file mẫu.
- Với 3 bảng có số hàng thay đổi theo dữ liệu (bảng độ cao khởi tính, bảng thành quả độ cao, bảng trị đo/SHC) và mục "kiểm tra sai số khép" có số vòng thay đổi: dùng cú pháp lặp bảng của `docxtpl` (`{%tr for row in rows %} ... {%tr endfor %}`) để nhân dòng theo đúng số điểm/trị đo/vòng thực tế — **không hard-code số hàng cố định**, vì mỗi công trình có số điểm/trị đo khác nhau (ví dụ Cầu Cửa Đại: 53 điểm, 67 trị đo, 13 vòng — công trình khác sẽ khác).
- Cần file mẫu gốc (`.docx` có đánh dấu placeholder) làm input cho `report_writer.py` — **việc mở còn lại**: bạn cung cấp file mẫu này (có thể dùng luôn file Cầu Cửa Đại làm mẫu, xóa số liệu, giữ placeholder) ở phiên code tiếp theo.

Báo cáo phải tái tạo đúng các mục sau, theo đúng thứ tự và tiêu đề (in đậm, gạch chân) như file mẫu:

| # | Mục | Nội dung |
|---|---|---|
| 1 | Tiêu đề | "THÀNH QUẢ TÍNH TOÁN BÌNH SAI LƯỚI ĐỘ CAO" |
| 2 | Tên công trình | Từ `project.name` |
| 3 | Chỉ tiêu kỹ thuật lưới | Số điểm gốc, số điểm mới, số chênh cao đo, công thức Wh(gh), phương pháp bình sai |
| 4 | Số liệu độ cao khởi tính | Bảng: TT, Tên điểm, H(m), Ghi chú — từ `known_points` |
| 5 | Bảng thành quả độ cao sau bình sai | Bảng: TT, Tên điểm, H(m), Sai số TP (mm), Ghi chú |
| 6 | Bảng trị đo, SHC, trị bình sai chênh cao | Bảng: TT, Điểm đầu, Điểm cuối, Trị đo(m), SHC(m), Trị BS(m), SSTP(mm), Trạm đo |
| 7 | Kết quả đánh giá độ chính xác lưới | Mo, m_H max/min (+tên điểm), m_h max/min (+tên đoạn) |
| 8 | Kết quả kiểm tra sai số khép | Với mỗi vòng độc lập: đường đi vòng, N (số đoạn), [N] (tổng trạm), Wh, Wh(gh) |
| 9 | Chữ ký | Ngày, Người đo đạc, Người tính toán, Người kiểm tra |
| 10 | Footer | "Kết quả được tính toán bằng phần mềm [tên phần mềm]" |

**Định dạng số:** độ cao/chênh cao 4 chữ số thập phân (mm); sai số trung phương 2 chữ số thập phân (0.01mm); Wh/Wh(gh) 2 chữ số thập phân (mm).

**Công cụ tạo file:** dùng thư viện tạo `.docx` theo template có sẵn (điền bảng động theo số điểm/số trị đo thực tế — số hàng bảng co giãn theo dữ liệu, không cố định).

> **Trạng thái triển khai thực tế (phiên code này):** chưa nhận được file mẫu `.docx` đã đánh dấu placeholder, nên `io/report_writer.py` dựng báo cáo trực tiếp bằng `python-docx` (không phải điền template qua `docxtpl`) — vẫn tái tạo đúng nội dung/thứ tự 10 mục trên và bảng động co giãn theo dữ liệu. Xem `binh_sai_do_cao/README.md` mục "Việc còn mở".

---

## 5. Kiến trúc phần mềm (module hóa)

```
binh_sai_do_cao/
├── io/
│   ├── input_loader.py      # đọc JSON/Excel, validate schema
│   ├── gsi_parser.py         # đọc file GSI-8/GSI-16 hoặc Excel xuất từ Sprinter 150M/250M, convert sang schema mục 2
│   └── report_writer.py     # điền dữ liệu vào file .docx mẫu có sẵn qua docxtpl (mục 4)
├── core/
│   ├── network_graph.py     # dựng đồ hình, kiểm tra liên thông
│   ├── loop_finder.py       # spanning tree + fundamental cycles (Bước 3.2)
│   ├── closure_check.py     # tính Wh, Wh(gh), kết luận (Bước 3.2)
│   ├── adjustment.py        # LSQ: lập A, P, giải hệ, tính V, H (Bước 3.3)
│   └── accuracy.py          # Mo, Qxx, SSTP (Bước 3.4)
├── models/
│   └── schema.py             # dataclass: Point, Observation, ProjectSettings
├── main.py                   # điều phối pipeline end-to-end
└── tests/
    └── test_cua_dai_case.py  # dùng chính bộ số liệu Cầu Cửa Đại làm test hồi quy
```

**Công nghệ đề xuất:**
- Python 3.10+
- `numpy` — đại số ma trận (AᵀPA, nghịch đảo)
- `networkx` — dựng đồ hình, spanning tree, fundamental cycles (`networkx.cycle_basis` hoặc tự cài đặt qua BFS)
- `python-docx` hoặc `docxtpl` (Jinja2-in-docx) — điền báo cáo theo template Word có sẵn, giữ nguyên định dạng gốc
- `openpyxl`/`pandas` — nếu input là Excel

---

## 6. Test Cases

### 6.1 Unit test — từng module

| TC | Module | Mô tả | Input | Kỳ vọng |
|---|---|---|---|---|
| TC-01 | network_graph | Dựng đồ hình từ danh sách trị đo | 5 điểm, 6 cạnh | Graph liên thông, đúng số node/edge |
| TC-02 | network_graph | Phát hiện lưới phân mảnh | 1 điểm không nối với phần còn lại | Raise lỗi rõ tên điểm cô lập |
| TC-03 | loop_finder | Đếm số vòng độc lập | Graph có V đỉnh, E cạnh, 1 thành phần | Số vòng = E − V + 1 |
| TC-04 | loop_finder | Lưới dạng cây (không có vòng) | Graph không có cạnh dư | 0 vòng phát hiện, không lỗi |
| TC-05 | closure_check | Tính Wh cho 1 vòng đơn giản | 3 đoạn đo giá trị đã biết tổng ≠ 0 | Wh = đúng tổng đại số (mm), sai số ≤ 1e-6 |
| TC-06 | closure_check | Tính Wh(gh) = k√n | n=120, k=0.3 | Wh(gh) = 3.286 (làm tròn 3.29) |
| TC-07 | closure_check | Gắn cờ "sát giới hạn" | Wh = 0.60, Wh(gh) = 0.60 | flag = "sát giới hạn" (tỉ lệ ≥ 0.9) |
| TC-08 | closure_check | Vượt giới hạn | Wh = 5.0, Wh(gh) = 3.0 | status = "Không đạt", có cảnh báo |
| TC-09 | adjustment | Lưới tối giản: 2 điểm gốc, 1 tuyến đơn không dư thừa | 1 trị đo giữa 2 điểm gốc | V = 0 tại trị đo (không có bậc tự do dư — hoặc raise cảnh báo "không có trị đo dư") |
| TC-10 | adjustment | Lưới có 1 điểm mới, 2 trị đo tới nó từ 2 điểm gốc khác nhau | 2 trị đo, 1 ẩn số | X giải đúng theo weighted mean có trọng số P=1/n |
| TC-11 | adjustment | Ma trận AᵀPA suy biến (thiếu trị đo dư) | Số ẩn ≥ số trị đo | Raise lỗi rõ ràng, không crash |
| TC-12 | accuracy | Tính Mo, Qxx cho lưới nhỏ đã biết đáp số tay | Lưới 3 điểm, 4 trị đo | Mo, m_H khớp tính tay trong sai số làm tròn |
| TC-13 | report_writer | Bảng động co giãn đúng số hàng | 10 điểm, 15 trị đo, 3 vòng | File .docx xuất ra có đúng 10/15/3 hàng tương ứng, không hàng thừa/thiếu |
| TC-14 | report_writer | Giữ nguyên style mẫu | So sánh font/style bảng trước/sau khi điền | Style không đổi (**chưa áp dụng được** — chưa có file mẫu thật, xem mục 4) |

### 6.2 Integration test — bộ số liệu Cầu Cửa Đại (Regression test)

Dùng chính bộ dữ liệu "Cầu Cửa Đại lần 3" đã kiểm chứng thủ công làm test end-to-end:

- **TC-20 — Input**: 2 điểm gốc, 53 điểm mới, 67 trị đo (theo bảng đã trích xuất từ file mẫu)
- **TC-21 — Phát hiện vòng**: đúng 13 vòng độc lập được phát hiện tự động (khớp danh sách 13 vòng trong file mẫu — không thiếu/thừa vòng nào)
- **TC-22 — Wh(gh) từng vòng**: khớp công thức `0.3×√n` cho cả 13 vòng (đã verify thủ công, sai số ≤ 0.01mm do làm tròn)
- **TC-23 — Cờ cảnh báo**: vòng "MC6→M24TL→M24HL→MC6" (n=4) phải được gắn cờ **"sát giới hạn"** vì |Wh| = Wh(gh) = 0.60mm
- **TC-24 — Mo**: kết quả Mo ≈ 0.13 mm/√trạm (giá trị tham chiếu từ file mẫu, sai số cho phép ≤ 0.01)
- **TC-25 — SSTP điểm**: giá trị lớn nhất tại T13TL ≈ 0.41mm, nhỏ nhất tại M24TL ≈ 0.11mm
- **TC-26 — Độ cao sau bình sai**: toàn bộ 53 giá trị H khớp bảng "thành quả độ cao sau bình sai" trong file mẫu, sai số ≤ 0.0001m (0.1mm)
- **TC-27 — Báo cáo xuất ra**: file `.docx` sinh ra có đủ 9 mục theo mục 4, đúng số hàng ở cả 3 bảng động (53/67/13), mở được bằng Word không lỗi định dạng

Đây là bộ test hồi quy tốt vì có sẵn kết quả "đúng" đã được đối chiếu độc lập trong phiên trước, không cần tính tay lại.

> **Kết quả thực tế (phiên code này):** toàn bộ TC-20 → TC-26 pass (xem
> `tests/test_cua_dai_case.py`). Wh so khớp trong dung sai ±0.15mm (rộng
> hơn ±0.01mm nêu trên) do dữ liệu trích xuất từ file mẫu chỉ có 4 chữ số
> thập phân — cộng dồn 8 đoạn đo có thể lệch tới ~0.4mm về mặt lý thuyết
> làm tròn, thực tế lệch lớn nhất quan sát được là 0.1mm, đúng như cảnh
> báo ở mục 7. TC-27 (file .docx mở được, đủ 9 mục, đúng số hàng động)
> pass qua `test_report_writer.py`.

### 6.3 GSI Import (mục 10)

| TC | Mô tả | Input | Kỳ vọng |
|---|---|---|---|
| TC-30 | Parse file GSI-8 hợp lệ | File mẫu GSI-8 từ Sprinter 250M | Ra đúng danh sách (điểm, giá trị đọc mia, loại đọc BS/IS/FS) |
| TC-31 | Parse file GSI-16 hợp lệ | File mẫu GSI-16 | Tương tự TC-30, đúng độ chính xác 16-bit |
| TC-32 | Convert số đọc mia → chênh cao trạm | Chuỗi BS/FS 1 trạm | dh = BS − FS đúng công thức thủy chuẩn hình học |
| TC-33 | Convert kết quả GSI → schema JSON mục 2 | Kết quả TC-32 | Đúng field `from/to/measured_dh_m/stations` |
| TC-34 | File GSI lỗi định dạng/rỗng | File hỏng | Raise lỗi rõ ràng, không crash pipeline |
| TC-35 | Import file Excel xuất từ Sprinter DataLoader (thay vì GSI) | File .xls mẫu | Parse đúng tương đương TC-33 |

> **Chưa triển khai** (Phase 6) — cần 1 file GSI/Excel mẫu thật từ Sprinter 250M trước khi viết `io/gsi_parser.py`.

### 6.4 Mobile Field App (mục 11)

| TC | Mô tả | Kỳ vọng |
|---|---|---|
| TC-40 | Nhập 1 trạm đo đủ BS/IS/FS | Tự tính đúng chênh cao trạm, hiển thị ngay |
| TC-41 | Nhập nhiều trạm liên tiếp trong 1 tuyến | Tự cộng dồn, tính đúng tổng chênh cao tuyến |
| TC-42 | Tuyến khép kín (điểm đầu = điểm cuối) | Tự tính Wh tuyến, so Wh(gh)=0.3√n, cảnh báo ngay tại app nếu vượt |
| TC-43 | Không có mạng khi nhập liệu | Dữ liệu vẫn lưu local, không mất, không yêu cầu mạng |
| TC-44 | Xuất dữ liệu ra JSON | File xuất đúng schema mục 2, import được vào `input_loader.py` không lỗi |
| TC-45 | Sửa/xoá 1 số đọc đã nhập trong trạm | Tự tính lại chênh cao trạm ngay, không cần nhập lại từ đầu |
| TC-46 | Có ≥ 2 dự án/công trình song song trên máy | Dữ liệu 2 dự án tách biệt, không lẫn |
| TC-47 | Cài đặt PWA trên Android (Chrome) | Hiện prompt "Add to Home Screen" hoặc cài qua menu, mở full-screen như app |
| TC-48 | Cài đặt PWA trên iOS (Safari) | Thêm qua Share → Add to Home Screen thành công, icon/tên hiển thị đúng theo manifest.json |
| TC-49 | Mở app khi không có mạng (cả 2 nền tảng) | Service Worker phục vụ giao diện từ cache, app mở bình thường, không lỗi trắng màn hình |
| TC-50 | Dữ liệu tồn tại sau khi tắt/mở lại app nhiều lần | Dữ liệu IndexedDB còn nguyên trên cả Android và iOS |
| TC-51 | Nhắc backup định kỳ | App hiển thị nhắc xuất file sau khi đóng 1 tuyến đo hoặc theo lịch đã cấu hình |

> **Chưa triển khai** (Phase 7) — dự án PWA riêng biệt, xem mục 11.

---

## 7. Trường hợp biên & xử lý lỗi cần lưu ý

- **Lưới phân mảnh** (có điểm/nhóm điểm không nối với điểm gốc nào) → dừng, báo lỗi rõ điểm nào bị cô lập.
- **Trị đo trùng lặp/đối hướng bất thường** (vd 2 lần đo A→B lệch nhau quá lớn) → cảnh báo trước khi đưa vào bình sai.
- **Vòng vượt sai số khép giới hạn** → không tự động loại bỏ trị đo; báo cáo rõ và yêu cầu người dùng quyết định (đo lại/loại bỏ thủ công), không "ép" bình sai qua.
- **Làm tròn hiển thị vs. tính toán nội bộ**: bảng trị đo hiển thị làm tròn 4 số thập phân (0.1mm) nhưng toàn bộ phép tính Wh/LSQ phải dùng giá trị đầy đủ độ chính xác (double), tránh sai lệch tích lũy như đã thấy khi đối chiếu thủ công (~0.1–0.2mm lệch do làm tròn hiển thị).
- **Số ẩn số ≥ số trị đo** → hệ vô định, báo lỗi thiếu trị đo dư thừa (lưới không có bậc tự do).

---

## 8-11. Việc còn mở / Nhập liệu Sprinter / Mobile App

Xem nguyên văn đầy đủ các mục 8 (câu hỏi mở đã chốt), 9 (TODO list gốc), 10
(GSI Import — Sprinter 250M) và 11 (Mobile Field App / PWA) trong bản đặc
tả gốc do người dùng cung cấp (giữ trong lịch sử hội thoại/commit message
của phiên tạo `binh_sai_do_cao/`). Tóm tắt trạng thái:

- Nhập liệu Sprinter 250M qua GSI/Excel (mục 10): **chưa triển khai**,
  cần file mẫu thật.
- Mobile Field App dạng PWA trên GitHub Pages (mục 11): **chưa triển
  khai**, là dự án/repo riêng biệt.
- Toàn bộ câu hỏi mở ở mục 8 của bản gốc đã được người dùng chốt trước khi
  giao việc cho phiên code này (không còn câu hỏi mở nào chặn Phase 0-5).
