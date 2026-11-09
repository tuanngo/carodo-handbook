# V2.3.2 — Smart Stops V1: kế hoạch triển khai

Trạng thái: **đã triển khai**, carodo-ios `365ceaa` (2026-11-09), sau một lượt review (sửa Merge sheet chọn sai chuyến liền kề, marker đọc bởi VoiceOver, giờ của khoảng nghỉ). Việc còn mở: `technical-debt.md` (TD-1, KL-1, PV-1, PV-2). Các quyết định cuối ở **mục 11**; chỗ nào khác mục 11 thì mục 11 thắng.
Nền tảng: V2.3.0 `fda2612` (`JourneyAnalysis.stopIntervals`, `RouteStop`, `TrackQuality`), bản sửa
"silent stop" `2760b84` (session khác, cùng hàm), quyết định ở mục G của
`journey-v2.3-enrichment-audit.md`.

## 0. Nguyên tắc: dữ liệu dẫn dắt, không gắn nhãn hoạt động

Mỗi dòng về một điểm dừng thuộc đúng **một trong ba mức**, và câu chữ phải cho thấy mức đó:

| Mức | Nguồn | Ví dụ (EN / VI) |
|---|---|---|
| **Đo được** (measured) | GPS: thời gian, thời lượng, vị trí nằm trong vòng tròn của một Saved Place, chờ giữa hai phần ghép | "Stopped 4 min" / "Dừng 4 phút"; "At Home" / "Tại Nhà"; "Waited 12 min" / "Chờ 12 phút" |
| **Ngữ cảnh chưa xác nhận** (context) | Nguồn ngoài (POI). **Không có trong V1** (không gọi MapKit) | (sau này) "Near a fuel station" / "Gần trạm xăng" |
| **Người dùng xác nhận** (confirmed) | Fill-up hoặc chi phí người dùng tự ghi | "Fill-up logged" / "Đã ghi đổ xăng" |

**Không bao giờ** có các nhãn Coffee/Fuel/Rest/Charging Stop suy ra từ thời lượng. Một lần dừng
4 phút chỉ là "Dừng 4 phút". Đây cũng là đầu vào sạch cho Journey Narrator sau này: nó chỉ được
nói những gì ở mức đo được hoặc đã xác nhận (ADR 0012 giữ nguyên; V1 không đổi Narrator).

## 1. Source hiện có sẽ tái sử dụng

| Cần | Đã có | File |
|---|---|---|
| Phân đoạn dừng (khoảng thời gian, vị trí bắt đầu, số fix, khoảng trống GPS dài nhất, kết thúc có ước tính không, dừng im lặng) | `JourneyAnalysis.stopIntervals`, `RouteStop`, `minimumStopS` (60 s), `maximumObservedGapS` (30 s) | `Core/Domain/JourneyDetails.swift` |
| Route đã replay mà mọi phân tích cùng đọc | `TripReplay.metrics`, `JourneyDetailAnalysisBuilder` (`@concurrent`) | `Core/Recording/TripReplay.swift`, `Core/Domain/JourneyDetailAnalysis.swift` |
| Điểm nằm trong Saved Place | `PlaceMatch.place(atLatitude:longitude:in:)`, `Place.contains`, `SavedPlaceMark` | `Core/Domain/Place.swift`, `JourneyDetails.swift` |
| Fill-up và chi phí đã gắn với chuyến | `DriveLogs.linked: [DriveLogItem]` (thời điểm `at`; fill-up có tọa độ trạm khi ghi tại chỗ) | `Core/Domain/DriveLog.swift`, đã tải trong `JourneyDetailViewModel` |
| Chờ đã ghép / đã Merge | `JoinedPart` (`stoppedAt`, `waitS`), `joinedParts(of:)`, đã tải cho menu Split | `Core/Repositories/Repositories.swift` |
| Hai journey liền kề | `mergeNeighbours(of:)`, `JourneyMerge.Pair`, `JourneyMerge.refusal`, `maxGapS` 6 h | `Core/Domain/JourneyMerge.swift`, đã tải cho Merge sheet |
| "Bắt đầu tại chỗ chuyến trước kết thúc" | `WaitJoin.Configuration.joinMaxDistanceM` (150 m), `joinMaxDistanceAutoStartM` (1.000 m) | `Core/Tracking/WaitJoin.swift` |
| Chất lượng GPS | `TrackQuality` | `Core/Domain/TrackQuality.swift` |

**Cách các màn hình đang dùng stop intervals (audit):**
- **Journey Detail / Route timeline**: chỉ có một dòng tóm tắt `StopSummary` ("2 điểm dừng · 4 phút") dưới mục kết thúc. Không có từng điểm dừng.
- **Trim**: `TrimTrack.stops` = `stopIntervals(≥ 60 s)`, dùng cho chip "Sau điểm dừng" và các mốc hít.
- **Stop bands** (tracking log): `stopIntervals(≥ 15 s)`.
- **Replay**: **không** dùng `stopIntervals`. `ReplayTimeline` rút gọn theo trạng thái "đang được giữ" của recorder (> 60 s). Đây là chỗ hai logic đang tách nhau (đã ghi từ V2.3.0). V1 **không** sửa Replay; mục 10 hỏi có hợp nhất ở bản sau không.
- **Recording và auto-finish** (`RouteRecorder`, `StopDetector`): không đụng.

## 2. Mô hình phân loại điểm dừng

Phân loại **theo bằng chứng**, không theo hoạt động. Một value thuần, không lưu:

```swift
/// One stop on a journey with what is known about it (docs/specs/journey-detail.md, Stops).
nonisolated struct JourneyStop: Identifiable, Equatable, Sendable {
    let stop: RouteStop                 // measured: interval, position, evidence (unchanged)
    let length: Length                  // measured: from StopBands' limits (1–5 min, ≥ 5 min)
    let wait: Wait?                     // measured: the wait between two joined or merged parts
    let place: SavedPlaceMark?          // measured: its position inside one of the person's places
    let logged: [DriveLogItem]          // confirmed: what the person logged at that stop
    let timing: Timing                  // measurement quality: .observed or .approximate (GPS gap)
}
```

- `Length`: dùng lại giới hạn của `StopBands` (`mediumS` 60 s, `longS` 300 s); không thêm ngưỡng thứ hai.
- `Wait`: khi khoảng thời gian của stop chứa ranh giới giữa hai phần (`JoinedPart.stoppedAt`).
- `Timing.approximate` khi `endIsEstimated`, hoặc khi stop chứa một khoảng trống GPS mà **không phải** dừng im lặng (xe có thể đã đi). Dừng im lặng (vị trí không đổi) vẫn là `observed`.
- **Không có** trường `activity`, `category` hay `guess`.

`JourneyStops.make(stops:places:logs:parts:)` là một hàm thuần, chỉ ghép dữ liệu (`Core/Domain/JourneyStops.swift`). Không phải detector mới: nó chỉ đọc `[RouteStop]`.

## 3. Quy tắc bằng chứng và độ tin cậy

| Bằng chứng | Quy tắc (giả thuyết, chỉnh được) | Mức |
|---|---|---|
| Thời lượng | `RouteStop.durationS`; có `≈` khi `timing == .approximate` | Đo được |
| Vị trí đại diện | Fix đầu của run (luôn là fix đã được chấp nhận, ≤ 50 m). Chỉ dùng để so với Saved Place; **không reverse geocode** trong V1 (mục 10) | Đo được |
| Saved Place | `PlaceMatch.place` tại vị trí đó. Chỉ là hình học (nằm trong vòng tròn), không nói làm gì ở đó | Đo được |
| Chờ ghép/Merge | Ranh giới phần nằm trong stop | Đo được |
| Fill-up/chi phí đã ghi | Item trong `driveLogs.linked` có `at` trong `[start − 5 phút, end + 5 phút]`, **hoặc** fill-up có tọa độ trạm trong 150 m quanh vị trí stop. Một item gắn **tối đa một** stop (gần nhất về thời gian); item không khớp stop nào vẫn hiện như hôm nay | Xác nhận |
| Chất lượng GPS | Không thành điểm số: chỉ quyết định `observed`/`approximate` | — |

Không có điểm "confidence" cho hoạt động, vì không suy ra hoạt động. Độ tin cậy ở đây là **độ tin
cậy của phép đo thời gian** (`timing`), tách riêng.

## 4. GPS gaps, trim, merge và split

- **GPS gaps:** đã xử lý trong `stopIntervals` (kết thúc ước tính sau khoảng trống > 30 s, dừng
  im lặng). `JourneyStops` chỉ đọc lại thành `timing`.
- **Trim:** phân tích chạy trên track đã cắt (như hôm nay). Một điểm dừng bị trim cắt đôi trở thành
  "chờ lúc đi" hoặc "đỗ xe" và không còn là stop (test V2.3.0 đã khóa hành vi này). Item đã ghi
  nằm ngoài phần giữ lại thì không gắn với stop nào.
- **Merge / Stop and wait:** track gồm mọi phần, mỗi phần một segment. Khoảng chờ giữa hai phần
  thành một stop có `wait`. Vị trí là chỗ chờ, không phải fix đầu của phần sau (V2.3.0 đã có test).
- **Split:** chỉ là đọc lại sau khi tách; không có trạng thái nào để dọn, vì không lưu gì.
- **Replay:** không đổi.

## 5. Between-Journey Stops: điều kiện

Hàm thuần `JourneyBreak.between(pair:earlierEnd:laterStart:)` trong `Core/Domain/JourneyBreak.swift`.
Nó **gọi** `JourneyMerge.refusal`, không chép quy tắc của Merge:

1. `JourneyMerge.refusal(pair) == nil`: liền kề, cả hai đã chắc chắn, cùng vai (lái/khách), xe
   tương thích, khoảng cách thời gian từ 0 tới 6 h. **Không đổi 6 h của Merge.**
2. Cả hai `rider == .driver`.
3. **Cùng xe**: cả hai đều có xe và là cùng một xe (chặt hơn Merge, vốn chấp nhận một bên không có
   xe; mục 10).
4. `pair.gapS ≤ 2 h` (`JourneyBreak.maximumBreakS`, quyết định của owner).
5. **Liên tục vị trí**: điểm cuối của chuyến trước và điểm đầu của chuyến sau cách nhau
   ≤ `WaitJoin.joinMaxDistanceM` (150 m), hoặc ≤ `joinMaxDistanceAutoStartM` (1.000 m) khi Auto Mode
   bắt đầu chuyến sau. **Dùng lại** đúng hai giá trị của Stop and wait (cùng nghĩa "bắt đầu lại ở
   chỗ chuyến trước dừng"). Điểm đầu và cuối lấy từ display route (luôn giữ hai đầu), không đọc
   raw track.
6. **Chất lượng dữ liệu**: chuyến nào chưa có điểm đầu/cuối (route rỗng) thì không gợi ý.

Kết quả là một fact đo được: "Nghỉ 25 phút trước chuyến này". Hành động **duy nhất**: mở Merge
sheet hiện có. Không tự Merge, không tạo mô hình Multi-leg.

## 6. Hiệu năng và caching

- `stopIntervals` đã chạy trong `JourneyDetailAnalysisBuilder` (ngoài main actor). V1 cho analysis
  giữ `[RouteStop]` (≥ 60 s) thay vì chỉ `StopSummary`, và `StopSummary` tính từ chính danh sách đó
  (không phân đoạn hai lần).
- `JourneyStops.make`: O(stops × (logs + places + parts)). Places tối đa 20, logs và parts mỗi chuyến
  chỉ vài cái, nên không đáng kể.
- `JourneyBreak`: dùng lại neighbours mà Merge sheet đã tải, **không thêm truy vấn**.
- **Không cache, không schema, không lưu.** Mọi thứ được tính lại khi mở trang, như các phân tích
  khác. Nếu `JourneyDetailCache` đang giữ analysis thì `[RouteStop]` đi theo cache đó.

## 7. Kiểm thử

**Unit test** (`JourneyStopsTests`, `JourneyBreakTests`; dữ liệu tổng hợp):
- Độ dài: hai phía của 60 s và 300 s.
- Saved Place: trong và ngoài vòng tròn; Saved Place riêng tư vẫn khớp (dữ liệu của chính người dùng).
- Item đã ghi: hai phía của ±5 phút; tọa độ trạm hai phía của 150 m; một item gần hai stop chỉ gắn
  một; item không khớp vẫn ở timeline.
- `timing`: dừng im lặng là `observed`; khoảng trống kiểu đường hầm là `approximate`; `endIsEstimated`.
- Joined wait và merged wait; trim cắt giữa stop; chuyến không có stop.
- Between: từng điều kiện của `JourneyMerge.refusal` vẫn chặn (pending, khác vai, khác xe, > 6 h);
  2 h hai phía; cùng xe; 150 m và 1.000 m hai phía; route rỗng; khách.
- Không câu chữ nào chứa tên hoạt động (test chuỗi trong catalog).

**Regression:**
- Tất cả test stop của V2.3.0 và của `2760b84` giữ nguyên kết quả.
- Đọc chuyến 312 km trong `drive-data/carodo/*.carodo` (file backup, không mã hóa) qua `BackupFile` trong
  tool replay, chỉ in số liệu: kỳ vọng 8 điểm dừng, 89 phút (như commit `2760b84`); in `JourneyStop`
  của từng điểm (thời lượng, có Saved Place không, có item không, `timing`) và các cặp Between nếu có.
- Dữ liệu thật **không** vào repo (P5).

**Screenshots** (khi có UI): Light/Dark, Dynamic Type lớn, tiếng Việt; chuyến không dừng, chuyến
8 điểm dừng, chuyến có Saved Place, có fill-up, có chờ ghép, có khoảng nghỉ giữa hai chuyến.

## 8. File dự kiến thay đổi

| File | Thay đổi |
|---|---|
| `Core/Domain/JourneyStops.swift` (mới) | `JourneyStop`, `JourneyStops.make` (thuần) |
| `Core/Domain/JourneyBreak.swift` (mới) | Điều kiện Between, gọi `JourneyMerge.refusal` |
| `Core/Domain/JourneyDetailAnalysis.swift` | Giữ `[RouteStop]`; `StopSummary` tính từ đó |
| `Features/Journeys/ViewModels/JourneyDetailViewModel.swift` | Ghép stops với places, logs, parts; break từ neighbours đã tải. **Session khác hay sửa file này**: chỉ stage hunk của mình |
| `Features/Journeys/Views/JourneyDetailSummarySections.swift` | Route timeline: một dòng mỗi stop (thời gian, thời lượng, ngữ cảnh đo được hoặc xác nhận); dòng nghỉ giữa hai chuyến kèm "Merge" |
| `Resources/Localization/Journeys.xcstrings` | Câu chữ EN/VI theo mục 0 |
| `CarodoTests/JourneyStopsTests.swift`, `JourneyBreakTests.swift` (mới), `DriveDataReplayTests.swift` (đọc `.carodo`) | Test |
| `docs/specs/journey-detail.md` | Mục Route timeline: stops, ba mức bằng chứng, khoảng nghỉ |
| `docs/architecture.md` | Bảng thuật toán: "Stops on the way" thêm phần ghép bằng chứng; Between-Journey |

**Không đổi:** schema, sync, `RouteRecorder`, `StopDetector`, `JourneyMerge`, `WaitJoin`, Replay,
Narrator, Trim (vẫn đọc `stopIntervals`), MapKit/WeatherKit.

## 9. Acceptance criteria

1. Mỗi stop ≥ 60 s trên Route timeline có thời gian và thời lượng; con số khớp `StopSummary`, Trim
   và stop bands (cùng một phân đoạn).
2. Không câu nào gọi tên một hoạt động nếu người dùng chưa ghi lại.
3. Stop tại Saved Place hiện tên nơi đó; fill-up đã ghi trong khoảng thời gian của stop hiện "Đã ghi
   đổ xăng" ở chính stop đó, không bị liệt kê lần thứ hai.
4. Thời lượng không chắc chắn (do mất GPS) có `≈`.
5. Hai chuyến thỏa mục 5 hiện "Nghỉ N phút" ở cả hai trang chi tiết, kèm hành động Merge (sheet hiện
   có). Không thỏa thì không hiện gì.
6. Chuyến 312 km: 8 điểm dừng, 89 phút, đọc được từng điểm.
7. `task lint`, `task warnings`, `task test` pass; screenshots như mục 7. Không đổi schema, sync,
   recording, Replay, Narrator.

## 10. Cần owner duyệt

1. **Dòng nào hiện trên Route timeline:** mọi stop ≥ 1 phút (chuyến phố có thể 8–10 dòng), hay
   stop ≥ 5 phút thành dòng riêng còn stop ngắn gộp thành "và 6 lần dừng ngắn · 9 phút"?
   Đề xuất: **gộp** (giữ bố cục editorial gọn).
2. **Ghép item với stop:** ±5 phút và 150 m có hợp lý không?
3. **Tên khu vực cho stop không phải Saved Place** ("Dừng 12 phút · P. Tân Mỹ") cần reverse geocode
   từng stop (gửi tọa độ cho Apple, mở rộng bảng trong `docs/privacy.md`). Đề xuất: **chưa làm ở V1**.
4. **Between-Journey cùng xe:** bắt buộc cả hai có xe và giống nhau (đề xuất), hay theo Merge (chấp
   nhận một bên không có xe)?
5. **Liên tục vị trí:** dùng lại 150 m / 1.000 m của Stop and wait (đề xuất), hay nới cho road trip
   (ví dụ đỗ xe ở bãi khác phía bên kia trạm dừng)?
6. **Khoảng nghỉ hiện ở đâu:** chỉ trong trang chi tiết của hai chuyến (đề xuất), hay cả danh sách
   Journeys (để sau)?
7. **Replay:** giữ logic rút gọn riêng (V1), hay lên kế hoạch cho Replay đọc `stopIntervals` ở bản
   sau để không còn hai định nghĩa?
8. **Tool replay đọc `.carodo`:** đồng ý thêm (chỉ dev, chỉ in số liệu)?

## 11. Quyết định đã chốt (owner, 2026-11-09)

### 11.1 Ba mức bằng chứng (giữ nguyên mục 0)

Đo được / Gợi ý chưa xác nhận (chỉ có khi làm POI Discovery) / Người dùng xác nhận. Một khoản đã
ghi là **fact đã xác nhận**; việc **ghép** khoản đó vào một stop cụ thể là suy luận của Carodo, chỉ
làm khi bằng chứng đủ (11.3). Không bao giờ có nhãn Coffee/Fuel/Charging/Rest Stop.

### 11.2 Trình bày trên Route timeline

- Một dòng riêng cho stop **≥ 5 phút** (`StopBands.longS`), cho stop có khoản đã ghi được ghép vào,
  và cho chờ giữa hai phần ghép. Mỗi stop đúng **một dòng**: khoản đã ghép nằm trong dòng của stop,
  không lặp lại thành dòng riêng.
- Stop 1 tới dưới 5 phút: gộp thành một câu "N lần dừng ngắn · X" **chỉ khi có từ 2 lần trở lên**.
  Câu gộp không có vị trí và không phải một stop.
- 5 phút chỉ là quy tắc **trình bày**: `stopIntervals`, `StopBands`, Trim giữ nguyên.
- Câu chữ: "Dừng 12 phút", "Tại Nhà · 8 phút", "Chờ giữa hai chặng · 25 phút", thời lượng ước tính
  thì "khoảng". Không hiện accuracy, confidence hay version. Không có placeholder rỗng.

### 11.3 Ghép khoản đã ghi với stop (thay dòng "Fill-up/chi phí" ở mục 3)

Chỉ xét các khoản **đã liên kết với journey** (`driveLogs.linked`, liên kết do người dùng tạo). Với
mỗi khoản:
1. **Thời gian** của khoản phải nằm trong stop, nới 60 s (giờ người dùng nhập tròn tới phút).
2. Fill-up có **tọa độ trạm** (ghi tại chỗ): còn phải cách vị trí stop ≤ 150 m. Có cả hai yếu tố thì
   cả hai đều phải đạt.
3. Chỉ có thời gian (chi phí, fill-up không có tọa độ): ghép khi đó là một khoản phát sinh lúc đứng
   yên (fill-up, chi phí) **và chỉ có đúng một stop ứng viên**.
4. Từ hai ứng viên trở lên, hoặc không có ứng viên nào: **không ghép**. Khoản vẫn hiện như hôm nay.
Không tạo fill-up, chi phí hay Saved Place mới.

### 11.4 Không có network mới

Không reverse geocode, không MapKit Nearby, không request mới. Chỉ dữ liệu offline và những gì
Journey Detail đã tải.

### 11.5 Between-Journey

- `JourneyMerge.refusal == nil` (gọi hàm, không chép), cả hai là người lái, **cùng một xe đã xác
  định** (không gợi ý khi một bên thiếu xe), khoảng nghỉ ≤ 2 h. Giữ 6 h của Merge thủ công.
- Liên tục vị trí: **150 m khi người dùng bắt đầu chuyến sau, 1.000 m khi Auto Mode bắt đầu**. Đúng
  ngữ nghĩa của Stop and wait, dùng chung một hàm với Stop and wait (tách khỏi `WaitJoin.verdict`,
  không chép). Không nới cho road trip.
- Điểm đầu và cuối là fix đã ghi thật: bỏ phần lead-in (trước `startedAt`) của display route. Thiếu
  điểm thì không gợi ý.
- Chỉ hiện trong Journey Detail. Hành động duy nhất là mở Merge sheet hiện có.

### 11.6 Technical debt: Replay Stop Alignment

Replay rút gọn stop theo trạng thái "đang được giữ" của recorder (thêm "dừng im lặng" ở
`29f39f7`), không đọc `stopIntervals`. Cần audit: phần nào cùng nghiệp vụ (một stop đã hoàn tất trên
dòng thời gian) thì dùng chung; phần nào khác (trạng thái chuyển động tức thời khi phát) thì giữ
riêng. Không sửa trong V2.3.2 (Replay thuộc session khác).

### 11.7 Developer replay đọc `.carodo`

Chỉ khi dev, chỉ đọc, chỉ in số liệu tổng hợp, không tọa độ. Baseline chuyến 312 km: 8 stops / 89
phút. Nếu khác baseline thì phân tích nguyên nhân, không sửa thuật toán cho khớp số.

## 12. Phase sau: Journey Points (V2.3.3)

Đã làm theo hướng cuối của owner: [journey-points.md](journey-points.md).
