# mobile-app — Sổ đo điện tử hiện trường (PWA)

Ứng dụng web (PWA) nhập số đọc mia BS/IS/FS ngoài công trường, tính chênh
cao trạm theo thời gian thực, cảnh báo sai số khép ngay tại chỗ khi tuyến
khép kín, và xuất dữ liệu ra JSON đúng schema của chương trình bình sai
chính (`../binh_sai_do_cao`). Đặc tả đầy đủ: xem `../SPEC.md` mục 11.

**Trạng thái: code-complete, đã test bằng Chromium headless (Playwright)
trong môi trường dev — chưa test trên thiết bị Android/iOS thật (TC-47 →
TC-51 của SPEC.md mục 6.4). Xem "Việc còn mở" bên dưới.**

## Chạy thử cục bộ

Không cần build tool — HTML/CSS/JS thuần. Chỉ cần 1 static server (Service
Worker yêu cầu HTTPS hoặc `localhost`):

```bash
cd mobile-app
python3 -m http.server 8000
# mở http://localhost:8000/index.html
```

## Kiến trúc

```
mobile-app/
├── index.html            # shell, đăng ký service worker
├── manifest.json          # Web App Manifest — start_url/scope tương đối (SPEC.md mục 11.7)
├── service-worker.js       # cache app shell, versioning theo CACHE_VERSION
├── css/style.css           # giao diện tương phản cao, chữ lớn, tap target lớn
├── js/
│   ├── db.js                # IndexedDB thuần (không phụ thuộc thư viện ngoài)
│   ├── closure.js           # port core/closure_check.py — Wh, Wh(gh), cờ "sát giới hạn"
│   ├── export.js            # xuất JSON (schema mục 2) / CSV, download hoặc Web Share API
│   └── app.js                # router hash-based + toàn bộ UI 5 màn hình
└── icons/                   # icon PWA (placeholder tự sinh — xem "Việc còn mở")
```

**Vì sao không dùng Dexie.js như SPEC.md gợi ý:** môi trường code phiên này
không tải được từ CDN (unpkg.com bị chặn ở tầng proxy mạng). IndexedDB
thuần không phức tạp hơn nhiều với ngần này object store, và loại bỏ hẳn
rủi ro phụ thuộc CDN cho 1 app bắt buộc phải chạy offline 100%.

## Data model (IndexedDB, khớp mục 11.5)

- `projects` — dự án
- `points` — điểm gốc (name, heightM) theo dự án
- `lines` — tuyến đo (fromPoint, toPoint) theo dự án; tuyến khép kín khi `fromPoint === toPoint`
- `stations` — trạm máy theo tuyến (bsPoint/bsReadingMm, fsPoint/fsReadingMm, isList[])

## Luồng màn hình

Gộp 2 màn "nhập trạm đo" và "tổng hợp tuyến" (mục 11.6, bước 3 & 4) thành
**1 màn duy nhất** (form nhập ở trên, danh sách trạm + Wh nếu khép kín ở
dưới) — chủ đích cho trải nghiệm hiện trường: đo xong trạm nào thấy ngay
tổng hợp, không phải chuyển màn liên tục.

## Xuất dữ liệu

`js/export.js` dựng đúng schema mục 2 của `SPEC.md`: mỗi **tuyến đo** trở
thành 1 `observation` (from/to/measured_dh_m = tổng Δh các trạm/stations =
tổng số trạm). File JSON xuất ra import thẳng được vào `input_loader.py`
của `binh_sai_do_cao` mà không cần sửa tay.

## Đã kiểm thử (Chromium headless qua Playwright, không phải thiết bị thật)

- Tạo dự án → thêm điểm gốc → tạo tuyến khép kín → nhập trạm đo → xem
  chênh cao tính real-time → lưu trạm → tổng hợp tuyến hiện đúng Wh/Wh(gh)
- Cảnh báo "Không đạt" hiện đúng khi Wh vượt Wh(gh)
- Xuất file JSON đúng schema, tải được qua `<a download>`
- Service Worker đăng ký thành công (`state: activated`), reload khi
  offline (`context.set_offline(true)`) vẫn hiển thị được app
- Không có lỗi console/page nào trong toàn bộ luồng trên

## Việc còn mở

1. **Icon placeholder**: `icons/*.png` do tôi tự vẽ đơn giản (không tải
   được asset ngoài từ CDN) — nên thay bằng icon/logo thật trước khi phát
   hành chính thức.
2. **Test trên thiết bị thật**: TC-47 → TC-51 (SPEC.md mục 6.4) — cài đặt
   PWA trên Android/Chrome và iOS/Safari thật, kiểm tra "Add to Home
   Screen", hoạt động full-screen, dữ liệu tồn tại sau nhiều lần tắt/mở —
   **chưa thể tự kiểm thử được vì không có thiết bị di động thật trong môi
   trường này.**
3. **GitHub Pages**: repo đã có sẵn, cần bật Pages trỏ vào nhánh
   `main`/thư mục `mobile-app` (hoặc deploy riêng) trong Settings — thao
   tác này cần thực hiện thủ công trên GitHub (quyền của tài khoản chủ
   repo, không nằm trong phạm vi GitHub App dùng cho phiên code này).
4. **Nhắc backup định kỳ** (mục 11.5, TC-51): hiện mới nhắc qua banner
   cảnh báo khi tuyến khép kín sát/vượt giới hạn; chưa có lịch nhắc định
   kỳ độc lập (ví dụ mỗi ngày/mỗi khi đóng app) — có thể bổ sung sau nếu
   thực tế sử dụng cho thấy cần thiết.
