# TD-2 — Apple Maps data kept or shown by Carodo: review record

Trạng thái: **ghi nhận, chưa sửa** (2026-11-09). Owner đã lên lịch: xem lại trước bản TestFlight đầu
tiên, cùng lúc với Privacy Report. Việc khắc phục **không** thuộc V2.3.3. File này tách
ba thứ: điều đã kiểm, chỗ còn phải diễn giải, và các luồng dữ liệu của Carodo bị ảnh hưởng. Đây là ghi
chép kỹ thuật, không phải ý kiến pháp lý.

## 1. Điều đã kiểm

**Apple Developer Program License Agreement, Attachment 6 (Apple Maps Service).** Đọc trên
developer.apple.com ngày 2026-11-09. Footer ghi Schedule 1 cập nhật ngày 29/10/2026. Bản ràng buộc là bản
đã chấp nhận trong tài khoản developer, nên phải đối chiếu lại ở đó.

| Điều | Trích nguyên văn (rút gọn) |
|---|---|
| §1.2 định nghĩa | "Map Data" means any content, data or information provided through the Apple Maps Service including … imagery, terrain data, latitude and longitude coordinates, transit data, points of interest and traffic data. |
| §1.2 | You will use the Apple Maps Service and Map Data only as necessary for providing services and functionality for Your Application. |
| §2.1 | Không được "remove, obscure or alter" bản quyền, thương hiệu, logo, ghi chú pháp lý, liên kết của Apple Maps. |
| §2.2 | Không bulk download, không "extract, scrape or reutilize"; không dùng Map Data "as part of any secondary or derived database". |
| §2.3 | Không "copy, modify, translate, create a derivative work of, publish or publicly display the Map Data" trừ khi được cho phép rõ. |
| §2.4 | Hiển thị Map Data trên bản đồ thì chỉ trên bản đồ Apple. Không "surface Map Data … without displaying the corresponding Apple map (e.g., if You surface an address result …, You must display the corresponding map with the address result)". |
| §2.5 | "Unless otherwise expressly permitted in writing by Apple, Map Data may not be cached, pre-fetched, or stored … other than on a temporary and limited basis solely as necessary (a) for Your use of the Apple Maps Service as permitted herein or in the MapKit … Documentation, and/or (b) to improve the performance … after which, in all cases, You must delete any such Map Data." |
| §2.7 | Apple có thể giới hạn số giao dịch qua MapKit hoặc thu hồi quyền truy cập; không công bố con số. |
| §4 | Ví dụ lý do thu hồi: "obscures or removes the Apple Maps logo or embedded links when displaying a map". |

**WWDC25 phiên 204, "Go further with MapKit"** (transcript): identifier của địa điểm "remain valid over
time"; "Identifiers can be persisted and shared"; "Place identifiers are still the best choice when you want
to persist a reference to a specific place". Cũng phiên đó: "we're deprecating CLGeocoder".

**SDK iOS 27.2 (Xcode 27.2, header):** `MKMapItem.identifier` và `MKMapItemIdentifier` có từ iOS 18.0.
`MKMapItem.Identifier` là `RawRepresentable` (chuỗi) và `Codable`. `MKMapItemRequest(mapItemIdentifier:)`
có từ iOS 18.0. `MKPointsOfInterestRequestMaxRadius` có từ iOS 14.

## 2. Chỗ còn phải diễn giải

1. Kết quả của `CLGeocoder` (Core Location) có phải là "Map Data provided through the Apple Maps Service"
   không. Điều khoản không nêu tên API. Hai API cùng một hệ thống phía sau (DTS nói trên diễn đàn), nên
   hướng an toàn là coi là có.
2. Câu "Identifiers can be persisted" trong một phiên WWDC có phải là "MapKit Documentation" hay "permitted
   in writing" theo §2.5 không.
3. Tên và tọa độ một POI mà **người dùng chọn rồi tự lưu** (tên trạm của fill-up) là Map Data hay là dữ liệu
   người dùng nhập. Điều khoản không có ngoại lệ nào cho trường hợp này.
4. Thế nào là "temporary and limited": một cache đến khi hệ điều hành xóa (Caches) có tính là tạm thời
   không; một cache vĩnh viễn trong SQLite thì gần như chắc chắn là không.
5. Tên phường hay tỉnh rút ra từ địa chỉ, hoặc một mã ISO 3166-2, có còn là Map Data không.
6. §2.4 áp dụng cho chữ địa chỉ trong danh sách hoặc tiêu đề khi không có bản đồ trên cùng màn hình.

Cách gỡ: hỏi Apple bằng văn bản (Developer Technical Support hoặc liên hệ pháp lý của Apple Developer), hoặc
thiết kế lại để không phụ thuộc vào cách diễn giải (mục 4).

## 3. Các luồng dữ liệu của Carodo bị ảnh hưởng (audit mã nguồn 2026-11-09)

| # | Dữ liệu | Nguồn Apple | Lưu ở đâu, bao lâu | Hiện ở đâu | Điều liên quan |
|---|---|---|---|---|---|
| 1 | `geocoded_cells`: phường, quận, tỉnh, đường, POI, quốc gia theo ô ~110 m | `CLGeocoder` | SQLite trên máy, **vĩnh viễn**, không sync | Nguồn của mục 2–5 | §2.5, §2.2 (một cơ sở dữ liệu suy ra?) |
| 2 | Tiêu đề journey ("P. Tân Mỹ → …") | từ 1 | Suy ra lúc đọc; `trips.start_cell`/`end_cell` là khóa | Danh sách Journeys, chi tiết (có bản đồ), widget? | §2.4 khi không có bản đồ |
| 3 | `trips.narrative`: câu tóm tắt chứa tên địa danh | từ 1, qua on-device model | SQLite, vĩnh viễn; không sync | Chi tiết journey | §2.5 (dạng phái sinh), §2.3 |
| 4 | Provinces Crossed, Passport (tỉnh đã đi qua) | từ 1 | Suy ra; tỉnh nằm trong cache | Chi tiết, Passport (có thể không có bản đồ) | §2.4, câu hỏi 5 |
| 5 | Vùng trên Feed (`DriveArea`, ISO 3166-2, opt-in) | từ 1 | Gửi backend khi publish (contract có, chưa nối) | Người khác xem, không có bản đồ | §2.4, câu hỏi 5, §1.2 |
| 6 | `fuel_logs.station_name` + tọa độ (ADR 0017) | `MKLocalPointsOfInterestRequest` | SQLite + iCloud (`FuelLog`, mã hóa), vĩnh viễn | Danh sách fill-up, chi tiết xe | §2.5, câu hỏi 3 |
| 7 | `places.poi_category` (và tên, nếu lấy từ gợi ý) | MapKit | SQLite + iCloud (`Place`) | Places, Passport | §2.5 (mức nhỏ) |
| 8 | `trip_gaps.route`, lead-in: đường Apple vẽ qua khoảng mất GPS | `MKDirections` | SQLite, vĩnh viễn; đi vào route hiển thị (KL-3), mà route này sync lên iCloud và **lên backend khi chia sẻ** (route đã trim) | Bản đồ chi tiết, trang chia sẻ (chưa làm) | §2.5, §2.2, §2.4 (trang web vẽ bản đồ gì?) |
| 9 | Ảnh map snapshot của danh sách và Passport | `MKMapSnapshotter` | `Caches/JourneyMaps/*.png`, hệ điều hành có thể xóa | Danh sách Journeys, Passport | §2.5 (imagery; có thể coi là tạm thời và để tăng hiệu năng, §2.5(b)) |
| 10 | Ảnh share card / preview link | snapshot hoặc tự vẽ | Chia sẻ ra ngoài; preview upload lên backend (spec, chưa làm) | Ứng dụng nhắn tin, web | §2.3 "publicly display", §2.1 logo trên ảnh |
| 11 | Journey Point trên Map: địa chỉ, Nearby POI, Find nearby | `CLGeocoder`, `MKLocalPointsOfInterestRequest`, `MKLocalSearch` | Chỉ trong bộ nhớ: địa chỉ và Find nearby theo focus, Nearby POI theo phiên app; chỉ **đọc** mục 1 | Preview có bản đồ | Đã thiết kế để hợp với §2.4, §2.5(b) |

## 4. Hướng xử lý cần quyết khi review (không làm bây giờ)

- Mục 1: đổi từ cache vĩnh viễn sang cache có hạn (ví dụ xóa sau N ngày), hoặc lưu kết quả đã rút gọn mà
  Carodo sinh ra (tên tỉnh làm nhãn của chính Carodo) nếu được xác nhận là được phép. Đồng thời xem lại
  Provinces Crossed và tiêu đề.
- Mục 6 và 7: lưu identifier của địa điểm (iOS 18+), còn tên là thứ người dùng xác nhận hoặc sửa; hoặc hỏi
  Apple.
- Mục 8: route do Apple vẽ không được lên backend (trang chia sẻ chỉ dùng điểm GPS đã ghi), hoặc phải
  chứng minh là được phép.
- Mục 10: giữ logo và ghi chú pháp lý trên mọi ảnh có nền bản đồ Apple; ảnh preview chỉ vẽ route trên nền
  không phải Apple.
- Một ADR ghi lại chính sách: "Map Data ở Carodo".

Liên quan: [journey-points.md](journey-points.md), `carodo-ios/docs/privacy.md`,
carodo-ios ADR 0017.
