# V2.3.1 — Driving Dynamics Shadow Mode: kế hoạch triển khai

Trạng thái: **kế hoạch, chờ owner duyệt** (2026-11-08). Chưa có code.
Nền tảng: V2.3.0 (`fda2612`: `JourneyAnalysis.stopIntervals`, `TrackQuality`, `Percentiles`, quy tắc
"Derived insights and enrichment" trong `docs/architecture.md`). Quyết định của owner: mục G của
`journey-v2.3-enrichment-audit.md`.

## 0. Phạm vi

**Làm:** một phân tích thuần, chạy **một lần sau khi lưu chuyến**, đo gia tốc/giảm tốc dọc theo
hướng chạy từ tốc độ Doppler của GPS, ghi **một dòng** vào tracking log (Developer mode). Công cụ
`task replay` tính lại cùng phân tích trên các database kéo từ iPhone để nghiên cứu phân bố.

**Không làm:** UI, safety score, kết luận về hành vi lái, cornering, Core Motion, lưu kết quả vào
database, schema, sync, đổi `RouteRecorder`/recording/distance, Between-Journey Smart Stops.

## 1. Thuật toán và cách xử lý độ bất định của GPS

### 1.1 Đầu vào

Các fix đã được chấp nhận của **chính chuyến vừa lưu** (`StoredTrip.samples`, raw track), không
phải route đã replay: route giữ tốc độ = 0 khi xe đứng ở chỗ dừng, làm méo đạo hàm. Dynamics đọc
dữ liệu thô, **không lọc lại vị trí** (không trùng logic với `RouteRecorder`, vì bộ lọc đó đã
quyết định fix nào được giữ).

### 1.2 Độ dốc tốc độ theo cửa sổ: hồi quy tuyến tính có trọng số

Audit cho thấy lấy hiệu tốc độ giữa hai fix liền nhau (1 s) là nhiễu: 18 "phanh gấp" giả, không
cái nào kéo dài quá một bước. Thay vào đó, với mỗi fix `i` lấy cửa sổ **căn giữa, rộng W = 3 s**
(giả thuyết, chỉnh được) và ước lượng độ dốc `a` của `v(t)` bằng **bình phương tối thiểu có trọng
số** `wₖ = 1/σₖ²`, với `σₖ = speedAccuracy` của fix:

- `a = Σw(t−t̄)(v−v̄) / Σw(t−t̄)²`, sai số `σₐ = √(1 / Σw(t−t̄)²)`.
- Tương đương đạo hàm Savitzky–Golay bậc 1 (thuật toán mà `docs/architecture.md` đã ghi là
  "Reference"), có thêm trọng số theo độ chính xác: một fix tốc độ kém kéo kết quả ít hơn.
- Tính bằng **hai con trỏ và tổng chạy** (Σw, Σwt, Σwv, Σwt², Σwtv): O(n) cho cả chuyến, không
  lưu mảng trung gian.

**Lưu ý trung thực:** `speedAccuracy` của Core Location không được Apple định nghĩa là 1σ, và sai
số giữa các fix liên tiếp tương quan với nhau (bộ lọc Kalman bên trong). Vì vậy `σₐ` là **chỉ số
tương đối** để xếp hạng và lọc, không phải khoảng tin cậy thống kê đúng nghĩa. Bài test thực tế
(mục 7.3) sẽ hiệu chỉnh nó.

### 1.3 Một cửa sổ chỉ hợp lệ khi

- mọi fix trong cửa sổ cùng `segment` (không qua pause hay ranh giới phần ghép);
- mọi khoảng giữa hai fix ≤ `TrackQuality.Configuration.regularIntervalS` (1,5 s): **dùng lại** định
  nghĩa nhịp đều của V2.3.0, không đặt ngưỡng thứ hai. Có khoảng trống GPS thì không có cửa sổ;
- ít nhất 3 fix, tất cả có tốc độ ≥ 0 và speed accuracy đã biết;
- speed accuracy của từng fix ≤ `maxSpeedAccuracyMps` (giả thuyết 2,5 m/s, khoảng p75 của dữ liệu
  audit);
- tốc độ lớn nhất trong cửa sổ ≥ `minimumSpeedMps` (giả thuyết 3 m/s ≈ 11 km/h): bỏ nhiễu khi đứng
  yên, nhưng vẫn giữ pha phanh tới lúc dừng hẳn (đầu cửa sổ còn đang chạy).

### 1.4 Sự kiện (chỉ ô tô, ngưỡng nghiên cứu)

**Schmitt trigger** trên chuỗi độ dốc của các cửa sổ hợp lệ liên tiếp:

| | Vào | Ra | Thời lượng tối thiểu | Gộp |
|---|---|---|---|---|
| Giảm tốc | `a ≤ −2,94 m/s²` (−0,30 g) | `a > −1,47` (một nửa) | ≥ 2 tâm cửa sổ liên tiếp (~1 s) | hai sự kiện cách nhau < 2 s là một |
| Tăng tốc | `a ≥ +2,75 m/s²` (+0,28 g) | `a < +1,37` | như trên | như trên |

Một sự kiện kết thúc ngay khi gặp cửa sổ không hợp lệ (khoảng trống GPS, segment mới): **không bao
giờ nối qua chỗ mất GPS**.

Hai mức, đều chỉ để ghi log:
- **candidate**: ước lượng điểm vượt ngưỡng;
- **confident**: cận gần ngưỡng nhất vẫn vượt, `a + k·σₐ ≤ −2,94` (phanh) hoặc `a − k·σₐ ≥ +2,75`
  (tăng tốc), với `k = 1` là giả thuyết.

Với dữ liệu audit (3 s, giảm tốc lớn nhất 2,29 m/s²), dự kiến **0 candidate** trên các chuyến
thường. Đó là kết quả mong đợi, không phải lỗi.

## 2. Ô tô và xe máy

| | Ô tô (`car`) | Xe máy (`motorbike`) | Xe đạp, không gán xe |
|---|---|---|---|
| Phân tích phân bố | Có | Có | Không (log `skipped`) |
| Ngưỡng sự kiện | −0,30 g / +0,28 g, **ngưỡng nghiên cứu** | **Không có** (`nil`): chỉ ghi phân bố | — |
| Cửa sổ, lọc cửa sổ | Mặc định 1.3 | Cùng giá trị lúc đầu, cấu hình riêng để chỉnh sau | — |

- Loại xe lấy từ `Vehicle.vehicleClass` của xe gán cho chuyến (đã có sẵn). Không gán xe thì không
  đoán: bỏ qua.
- Đo bằng tốc độ GPS chứ không đọc cảm biến điện thoại, nên điện thoại để trong túi hay gắn trên
  xe máy không ảnh hưởng.
- Cấu hình theo loại xe là một giá trị `Configuration` có `byClass`, đặt trong `TrackingRules`
  (nơi duy nhất chứa ngưỡng chỉnh được), không phải một protocol hay class riêng.

## 3. Quality gating và confidence

Ba lớp tách biệt:

1. **Đủ điều kiện của journey** (cổng có/không, không phải điểm số): chuyến đã chắc chắn
   (`!isPending`), `rider == .driver`, loại xe là `car` hoặc `motorbike`. Đây là đúng điều kiện
   "sure + driven" mà `JourneyMerge` dùng; nếu điều kiện đó đã là một hàm đọc được thì dùng lại,
   nếu đang nằm trong `JourneyMerge.refusal` thì tách ra một predicate trên `Journey` để cả hai
   cùng đọc (không chép).
2. **Độ tin cậy của phép đo** (journey): từ `TrackQuality` của chuyến. Cổng riêng của dynamics
   (giả thuyết):
   - `regularIntervalShare ≥ 0,9`;
   - `trustedMovingSpeedShare ≥ 0,7`;
   - `speedAccuracy.p50 ≤ 2,0 m/s`.

   Không đạt thì log `skipped reason=quality(cadence|trusted|speedAcc)`. Trên 18 chuyến audit,
   khoảng 4 chuyến sẽ bị loại vì `trusted < 0,7`. Thêm một điểm `measure conf=0.00…1.00` tính bằng
   **`DriveConfidence.ramp/score`** có sẵn (không tạo công thức mới).
3. **Độ tin cậy của từng sự kiện**: `DriveConfidence.score` trên các đặc trưng: biên vượt ngưỡng
   chia cho `σₐ`, số cửa sổ liên tiếp, độ phủ fix trong cửa sổ, speed accuracy trung bình. Log
   bằng `conf=` như mọi quyết định khác của engine.

Không có điểm nào mô tả người lái; log chỉ nói về phép đo.

## 4. Thu thập phân bố mà không tăng dữ liệu lưu

- **Không lưu gì mới vào database.** Mỗi chuyến chỉ ghi **một dòng tracking log**. Log đã có giới
  hạn dung lượng (`GRDBTrackingLog` xóa dòng cũ), không có tọa độ và không có thời điểm của sự kiện
  (P5, P9):
  ```
  dynamics v1 class=car windows=1180 measure conf=0.82 brake p50=0.2 p99=1.2 max=2.3 accel p99=1.3 max=2.7 candidates=0/0 confident=0/0
  dynamics v1 skipped reason=passenger|pending|bicycle|noVehicle|quality(trusted)
  ```
- Percentile dùng `Percentiles` (nearest rank) của V2.3.0, không viết helper thứ hai.
- Phân bố đầy đủ (histogram theo bin 0,25 m/s², gộp theo loại xe) **chỉ tạo trong `task replay`**,
  tính lại từ raw track đã có. Không lưu ở đâu cả, chỉ in ra lúc chạy tool.
- Kết quả đều tính lại được từ raw track. Đổi thuật toán thì chạy lại `task replay`, không cần
  migration.

## 5. Chạy shadow mà không ảnh hưởng recording hoặc UI

- **Khi nào:** trong `writer.onSettled` (`CarodoApp.swift`), ngay sau `logMotion(forTrip:)`. Đây
  là chỗ các dòng log sau khi lưu đã nằm (`motion`, `ride`), sau khi chuyến đã ghi xong và đóng
  transaction. Không chạm `LocationSource → RouteRecorder → TripWriter`.
- **Cách chạy:** `DependencyContainer.logDrivingDynamics(forTrip:)` đọc chuyến (`storedTrip`), đọc
  journey (rider, pending, xe) và xe (loại), rồi gọi phân tích thuần `@concurrent` (ngoài main
  actor) và ghi log. Có `guard !isErasingLocalData` và đếm `activeDataWork` như `logMotion`. Lỗi
  đọc thì không ghi gì (không log "0 sự kiện" thay cho "không biết").
- **Chuyến còn pending lúc lưu** (Auto Mode chưa xác nhận): log `skipped reason=pending`. Phương
  án tối giản: **không** thêm hook khi xác nhận sau; `task replay` sẽ tính các chuyến này với trạng
  thái cuối cùng tại thời điểm kéo DB. Nếu muốn log cả lúc xác nhận thì cần một hook thứ hai: em
  đề xuất để sau.
- **Không UI**, không đổi màn hình nào. Developer view chỉ thêm một nhóm hiển thị cấu hình
  `dynamics` cạnh `StopDetector` (đọc từ `TrackingRules`), giống các nhóm hiện có.

## 6. Versioning, hiệu năng, pin

- `DrivingDynamics.version = 1`, in trong mỗi dòng log. Tăng version mỗi khi đổi bất kỳ quy tắc nào
  (cửa sổ, cổng, ngưỡng). Lịch sử version ghi trong bảng ở `docs/tracking.md`. Không lưu kết quả nên
  không cần tính lại chuyến cũ trên máy.
- **Hiệu năng:** O(n), hai con trỏ; một giờ lái ≈ 3.600 fix, tính trong vài mili-giây, ngoài main
  actor, một lần mỗi chuyến. Chi phí lớn nhất là một lần đọc và giải nén track (khoảng 25 KB với
  một giờ lái).
- **Pin:** không cảm biến mới, không mạng, không thêm khi đang ghi. Tác động không đo được so với
  phần ghi chuyến.

## 7. Kiểm thử và validation

### 7.1 Unit test với dữ liệu tổng hợp (`DrivingDynamicsTests`)

Dữ liệu tổng hợp tất định, nhiễu từ một bộ sinh số giả ngẫu nhiên có seed cố định trong test.
Không dùng track thật.

- Chạy đều 15 m/s cộng nhiễu ±σ: 0 candidate; độ dốc p50 ≈ 0.
- Ramp phanh −3,5 m/s² trong 3 s: 1 sự kiện phanh, đúng thời lượng; ở −2,5 m/s²: 0 (cả hai phía
  ngưỡng vào).
- Hysteresis: dao động quanh ngưỡng chỉ cho 1 sự kiện; hai ramp cách nhau 1,5 s gộp thành một,
  cách nhau 3 s là hai.
- Spike một fix (giống audit): 0 sự kiện.
- Khoảng trống GPS hoặc ranh giới segment giữa ramp: không có cửa sổ qua chỗ đó, không sự kiện nối
  qua.
- Fix không có tốc độ hoặc speed accuracy > ngưỡng: cửa sổ bị loại.
- Trọng số: một fix accuracy kém lệch tốc độ thì kéo độ dốc ít hơn một fix accuracy tốt.
- Xe máy: ramp mạnh vẫn cho 0 sự kiện (không có ngưỡng) nhưng có trong phân bố.
- Xe đạp, hành khách, pending, không xe: `skipped` với đúng lý do.
- Cổng chất lượng: hai phía của 0,9 / 0,7 / 2,0.
- Mô phỏng độ trễ của Core Location (ramp đi qua bộ lọc mũ): đo mức đỉnh bị làm phẳng, ghi lại
  trong test như một **đặc tả đã biết** chứ không phải một ngưỡng.
- `DriveConfidenceTests`: hai hàm confidence mới, hai phía mỗi mốc.
- Tracking log: dòng `dynamics` không có tọa độ, không có thời điểm sự kiện.
- O(n): 100.000 fix chạy dưới một giới hạn thời gian rộng (bảo vệ khỏi lỡ tay viết O(n²)).

### 7.2 Regression trên dữ liệu thật (`task replay`)

- Thêm cột: loại xe, đủ điều kiện hay lý do bỏ qua, số cửa sổ, p99/max phanh và tăng tốc,
  candidate/confident. Cuối bảng in histogram gộp theo loại xe.
- Kỳ vọng trên các chuyến đã kéo: 0 candidate cho ô tô, phân bố gần với audit. Mỗi candidate xuất
  hiện đều được xem lại bằng trip report (không có tọa độ).

### 7.3 Kiểm thử thực tế có kiểm soát (sau khi code xong)

- **Chỉ ở khu vực kín, có phép, không có xe khác; không bao giờ trên đường công cộng.** Người lái
  có kinh nghiệm, tốc độ thấp.
- **Tham chiếu:** đầu đọc OBD-II ghi tốc độ xe ≥ 5 Hz, hoặc một GNSS 10 Hz. Đồng bộ thời gian bằng
  một mốc chung (bắt đầu chuyến Carodo và đánh dấu trên app tham chiếu cùng lúc).
- **Ô tô:** từ 40 km/h, mỗi mức 5 lần: phanh nhẹ (~0,15 g), vừa (~0,3 g), mạnh (~0,5 g); tăng tốc
  tương tự trong giới hạn xe.
- **Xe máy:** chỉ phanh nhẹ và vừa, có đồ bảo hộ.
- **Đo:** đỉnh độ dốc của Carodo so với đỉnh tham chiếu (hệ số bị làm phẳng, độ trễ); recall và
  precision của candidate/confident theo từng mức; có hiệu chỉnh `k` và `σₐ` được không.
- Kết quả ghi vào kế hoạch này. Chỉ sau đó mới bàn tới ngưỡng chính thức hoặc hiển thị.

### 7.4 Shadow trên chuyến thường

2–4 tuần lái hằng ngày trên 3 iPhone, cả ô tô lẫn xe máy; `task pull-db` rồi `task replay`. Dùng
phân bố theo loại xe để đề xuất ngưỡng cho xe máy.

**V2.3.1 coi là xong khi:** code và test pass (`task lint`, `task warnings`, `task test`), replay
chạy được, docs cập nhật. Dòng log trên iPhone thật sau một chuyến là **device check còn phải làm**.
Không có tiêu chí precision ở V2.3.1: đó là điều kiện cho quyết định hiển thị sau này.

## 8. File thay đổi

| File | Thay đổi | Lý do |
|---|---|---|
| `Carodo/Core/Domain/DrivingDynamics.swift` (mới) | Phân tích thuần: cửa sổ, độ dốc có trọng số, phân bố, sự kiện, lý do bỏ qua, `version` | Một trách nhiệm, tất định, test được |
| `Carodo/Core/Tracking/TrackingRules.swift` | Thêm cấu hình `dynamics` (theo loại xe) | Ngưỡng chỉnh được nằm một chỗ |
| `Carodo/Core/Tracking/DriveConfidence.swift` | Hai hàm: measurement confidence, event confidence | Dùng lại `ramp/score`, không tạo công thức mới |
| `Carodo/Core/Domain/Journey.swift` (có thể) và `Carodo/Core/Domain/JourneyMerge.swift` | Tách predicate "sure + driven" nếu đang nằm riêng trong `JourneyMerge` | Không chép quy tắc Merge |
| `Carodo/Core/Diagnostics/TrackingLog.swift` | Kind `.dynamics` và hàm tạo dòng log | Log không tọa độ |
| `Carodo/App/DependencyContainer.swift` | `logDrivingDynamics(forTrip:)` | Cùng chỗ với `logMotion`/`logRide` |
| `Carodo/App/CarodoApp.swift` | Một dòng gọi trong `onSettled` sau `logMotion` | Chạy một lần sau khi lưu |
| `Carodo/Features/Developer/Views/DeveloperView.swift` | Nhóm hiển thị cấu hình `dynamics` | Xem ngưỡng đang dùng |
| `CarodoTests/DrivingDynamicsTests.swift` (mới), `DriveConfidenceTests`, `DiagnosticsLogTests`, `TrackingRulesTests` | Test mục 7.1 | |
| `CarodoTests/DriveDataReplayTests.swift` | Cột dynamics và histogram theo loại xe | Công cụ nghiên cứu, mục 7.2 |
| `docs/tracking.md` | Mục "Driving dynamics (shadow)": bảng ngưỡng, cổng, version | Ngưỡng là giả thuyết, có bảng như các mục khác |
| `docs/architecture.md` | Chuyển dòng "Harsh braking…" từ Reference sang bảng đã xây (shadow, hồi quy có trọng số); cornering vẫn ở Reference, ghi rõ bị chặn với GPS | Một thuật toán cho một bài toán |
| `docs/operations/device-testing.md` | Quy trình test có kiểm soát (7.3) | Đang có thay đổi chưa commit của session khác: chỉ stage hunk của mình |

**Không đổi:** schema, sync, `RouteRecorder`, `StopDetector`, `TripReplay`, `RideProfile`, UI người
dùng, quyền truy cập, dependency.

## 9. Trùng lặp: dùng lại hay cố ý giữ riêng

- **Dùng lại:** `TrackQuality` (cổng chất lượng và định nghĩa nhịp đều); `Percentiles`;
  `DriveConfidence.ramp/score`; `LocationSample.trustedSpeed` (khi cần); điều kiện "sure + driven"
  của Merge; `Vehicle.vehicleClass`; hàm đọc `storedTrip`.
- **Cố ý giữ riêng:** `RideProfile.accelRms` (RMS của chênh lệch tốc độ 1 s, dùng để **đoán loại xe**
  trong log `ride`). Nó trả lời câu hỏi khác và đang được log; đổi nó sẽ làm đổi số liệu đang dùng.
  Ghi chú trong docs rằng hai số này không so sánh trực tiếp được. `SlowMoving` (làm mượt trung bình
  30 s để tìm đoạn kẹt xe) cũng là bài toán khác.
- **Nguy cơ lệch thuật toán:** nếu sau này Replay hoặc Journey Detail muốn hiện "phanh mạnh" thì
  phải đọc kết quả của `DrivingDynamics`, không tự tính lại.

## 10. Rủi ro

- `speedAccuracy` không phải 1σ và sai số tương quan → `σₐ` chỉ là chỉ số tương đối, cần hiệu chỉnh
  ở 7.3.
- Bộ lọc của Core Location có thể làm phẳng đỉnh phanh → GPS-only có thể không bao giờ đủ để thấy
  phanh gấp. Shadow Mode trả lời câu này mà không có rủi ro cho người dùng.
- `rider = driver` là mặc định, không phải xác nhận → một số chuyến hành khách không đánh dấu sẽ lọt
  vào. Chấp nhận được khi chỉ ghi log.
- Chuyến pending lúc lưu không có dòng log trên máy (chỉ có trong replay).

## 11. Cần owner xác nhận khi duyệt

1. Chấp nhận phương án tối giản cho chuyến pending (chỉ có trong replay), chưa thêm hook lúc xác
   nhận?
2. Cửa sổ 3 s là cửa sổ chính; `task replay` so sánh thêm 2 s và 5 s để chọn. Đồng ý?
