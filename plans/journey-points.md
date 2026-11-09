# V2.3.3 — Journey Points, Nearby POI, Footprints

Trạng thái (2026-11-09): **Slice 1 và Slice 2 đã làm; Slice 3 (Start/End) là bước tiếp theo.** Đây là plan duy nhất của
V2.3.3. Hành vi đã làm nằm ở carodo-ios `docs/` (nguồn sự thật); plan này chỉ ghi phạm vi, quyết định của owner, điều
còn chờ.

## 1. Product

**Carodo ghi nhớ những con đường chúng ta đã đi và những nơi chúng ta đã dừng lại. Apple Maps giúp gọi tên những địa
điểm gần đó.**

- **Journey:** GPS, tuyến đường, hành trình; có Start, End, Stop và Break.
- **Map:** khám phá một Journey Point. Hiện vị trí GPS do Carodo ghi nhận hoặc suy ra; Apple Maps bổ sung địa chỉ và
  Nearby POI khi có thể.
- **Footprints:** bản đồ lịch sử những con đường đã đi và những nơi đã dừng, trên layer Footprints hiện có, không thêm
  Map Mode.

## 2. Thuật ngữ

Định nghĩa canonical: carodo-ios `docs/specs/domain.md` (Vocabulary). Chỉ dùng: **Journey**, **Journey Point** (Start /
End / Stop / Break), **GPS Position**, **Nearby POI**, **Footprints**, **Saved Place**.

- Nearby POI là nơi Apple Maps tìm thấy gần GPS Position: "Near / Gần", không bao giờ "At / Tại". Không phải check-in,
  không phải nơi đã ghé, không thành Saved Place.
- Saved Place giữ nghĩa hiện tại (do người dùng lưu; privacy, Auto Mode).
- Cột `geocoded_cells.poi` (`areasOfInterest` của reverse geocode) không phải Nearby POI và không phải nơi đã ghé.

## 3. Slices

| Slice | Nội dung | Trạng thái |
|---|---|---|
| 1 | Stop và Break mở trên Map tab: focus, GPS marker, vòng tròn vị trí (`StopPosition`), preview native, Find nearby places, tách khỏi Live Map | Done: `3aa3e25` (bản fullScreenCover), `e027155` (Map tab) |
| 2 | Nearby POI tự động cho Stop và Break | Done: `f66dcfa`. Chờ PV-13 |
| 3 | Start và End mở trên Map | Next, chưa duyệt code |

### Slice 2 (đã làm)

Spec canonical: carodo-ios `docs/specs/journey-detail.md`, Where a stop was (preview, Nearby POI, Find nearby);
`docs/specs/navigation.md`, Journey points on the Map (focus, marker, camera); `docs/privacy.md` (request gửi gì cho
Apple); ADR 0015.

Tóm tắt quyết định (owner, 2026-11-09): mở Journey Point trên Map là yêu cầu; kiểm privacy trước (fail closed), rồi gửi
**một** request; `StopPlaceResolver` gọi tên **nhiều nhất một** POI khi đủ năm điều kiện (đủ bằng chứng vị trí, không phải
trạm công cộng/bãi đỗ, gộp trùng tên, đủ gần, không mơ hồ). Không score, không ranking, không Confirm/Change/Remove. Cache
trong RAM theo Journey Point cho phiên app; không persistent cache, không schema, không sync, không `.carodo`. Find nearby
places giữ làm khám phá phụ.

Lý do giữ năm điều kiện: replay Apple thật trên 24 stop dev: nới điều kiện thì gọi tên 9/24, trong đó 3 sai (tiệm tạp
hóa, văn phòng ở đèn đỏ). Ngưỡng hiện tại: 0/24, đúng lý do (14 stop import thưa fix, 10 stop Carodo 1–3 phút ở phố đông
với 2–4 nơi trong 6–20 m). **Chưa được xác nhận hiệu quả**: chưa có stop ≥ 5 phút do Carodo ghi (PV-13).

### Slice 3 (Start/End, tiếp theo)

Quyết định của owner (2026-11-09):

- Start và End là Journey Point như Stop và Break: cùng `JourneyPoint`, cùng đường mở Map.
- **Start có GPS ghi được:** tìm Nearby POI qua cùng cổng privacy và chất lượng.
- **Start ước tính** (Auto Mode lead-in vẽ từ chỗ đỗ tới fix đầu, `missedStartM`): vẫn xem được trên Map, **không** tự
  tìm POI; UI nói rõ đây là vị trí ước tính. `JourneyPoint` mang nguồn vị trí (recorded / estimated).
- **End:** một fix (fix cuối được giữ), dùng cổng của Break: accuracy ≤ 20 m, xét trên 25 m.
- GPS không đủ điều kiện tìm POI không bao giờ làm mất việc xem vị trí trên Map.
- Địa chỉ lấy từ `trips.start_cell` / `end_cell` (`geocoded_cells`, đã có khi lưu journey); không reverse geocode lại.
- Theo journey đã trim (như trang chi tiết). Saved Place riêng tư: không địa chỉ, không tìm, không gửi gì.
- Tối ưu nhỏ đi kèm: giữ địa chỉ reverse geocode trong `StopPlaceMemory` (RAM, như Nearby POI), vì hôm nay mở lại cùng
  một stop trong phiên là geocode lại. Không schema, không framework mới.

## 4. Footprints (sau V2.3.3)

Thêm Start, End, Stop, Break lịch sử lên Footprints: zoom xa gom cụm, zoom gần marker riêng, chạm marker xem thời gian,
vị trí và journey; Nearby POI chỉ khi người dùng mở điểm đó. Nguồn là journey/GPS/Smart Stops của Carodo, không phải
Apple Maps. Ý nghĩa explored area giữ nguyên. Theo nguyên tắc History at scale (navigation.md).

Đã biết (audit 2026-11-09): stop không lưu, tính lại từ raw track khoảng 4,5 ms mỗi 1.000 fix (Debug, simulator); 2.000
chuyến ước khoảng 1,5 s optimized, một lần, ngoài main actor. Đủ cho một lần dựng rồi giữ trong bộ nhớ theo phiên bản
journey, chỉ cho các journey cắt vùng nhìn; chỉ đề xuất bảng dẫn xuất (P6) nếu đo trên iPhone thấy chậm. Journey Point
chưa có danh tính bền (TD-5). Chưa đo: CPU của Map khi có nhiều annotation.

## 5. Audit (2026-11-09)

**`geocoded_cells`:** giữ nguyên schema và nghĩa.
- Journey Detail: tên Start/End = `start_cell` / `end_cell` JOIN `geocoded_cells`, `PlaceNaming` ghi sau khi lưu journey.
  Trang không request gì cho stop.
- Consumer khác: Provinces Crossed (đọc, ghi các ô bisection hỏi), Passport (đọc).
- Map (focus một điểm): đọc cache trước, chỉ đọc; thiếu thì `CLGeocoder` trực tiếp, không ghi lại, không giữ RAM →
  trùng request khi mở lại cùng stop (sửa ở Slice 3, §3).
- `poi`: lưu, chưa màn hình nào đọc.

**Map performance: không cần đổi.** Routes, Heatmap, Footprints đã tải theo vùng nhìn (có đệm, theo tile), chỉ khi camera
dừng, chi tiết theo zoom, huỷ request cũ, cache theo revision, cập nhật tăng dần; giữ toàn bộ display route trong bộ nhớ
(~8 MB cho 2.000 chuyến, đã đo). Focus một điểm: không vẽ lịch sử, câu trả lời muộn bị bỏ (`addressRequest`), cache
Nearby POI tránh request lặp do re-render, Live Map riêng. Nguyên tắc ghi ở navigation.md (History at scale).

## 6. Điều còn chờ

- **PV-12:** Journey Point trên Map trên iPhone thật. **PV-13:** Nearby POI trên stop ≥ 5 phút do Carodo ghi.
- **TD-2:** dữ liệu Apple Maps lưu trên máy ([apple-maps-data-review.md](apple-maps-data-review.md)), trước TestFlight.
- **TD-3, TD-4, TD-5:** hai truy vấn POI; drive import không có nguồn gốc; Journey Point chưa có danh tính bền.
- **Walking Evidence (V2.3.4):** Core Motion chỉ giữ ~7 ngày trên máy ghi; quyết định thu sớm trước TestFlight đầu tiên.
