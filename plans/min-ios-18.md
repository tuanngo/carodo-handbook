# Minimum iOS 18.0: audit và đề xuất migration

Trạng thái: **M1–M3 đã duyệt (owner, 2026-11-09); migration đã làm, kiểm và commit trong carodo-ios
(`3f017dc`, ADR 0018).** iOS 18 runtime **chưa được xác minh**: cần kiểm trên iPhone iOS 18 trước TestFlight; không
có máy thì báo release risk để owner quyết, không tự đánh dấu pass. Quyết định của owner: nâng minimum của cả Carodo từ iOS 17.0 lên **iOS 18.0**; mọi thứ cần iOS 26+
vẫn dùng availability check. Quyết định này thay cho đề xuất "min iOS 26" còn treo từ 2026-11-08 (glass nav).

## 1. Audit

| Hạng mục | Hiện trạng | Ảnh hưởng |
|---|---|---|
| Targets | `project.yml`: `options.deploymentTarget.iOS: "17.0"` và `IPHONEOS_DEPLOYMENT_TARGET: "17.0"` (base). App, widget (`CarodoWidgets`) và test kế thừa; không target nào tự đặt riêng | Sửa 2 dòng, `xcodegen generate` |
| Widget / Live Activity | Không có `#available` nào; WidgetKit, ActivityKit có trước iOS 17 | Không |
| `FoundationModels` | Weak link (iOS 26+); comment "iOS 17–25 still launch" | Giữ weak link; sửa comment |
| Code chỉ để chạy iOS 17 | 3 nhánh `#available(iOS 18.0, *)`: `PlatformCompatibility` (scroll geometry, `ScrollMetrics.isAvailable`), `Vehicle` (symbol `convertible.side.fill`). Fallback ở các nơi gọi: `JourneyStorySheet` (`isAtTop = false` khi không có scroll geometry), `AutoModeSheet` (medium cố định), `FloatingBarCollapse` | Bỏ nhánh và fallback; ~6 file, hành vi trên iOS 18+ không đổi |
| Nhánh iOS 26 | 17 check `#available(iOS 26.0, *)`, gom trong `PlatformCompatibility` | Giữ nguyên |
| Dependency | GRDB 7 (min iOS 13) | Không |
| CI | Không có `.github`, `ci_scripts`, Xcode Cloud. Kiểm tra chạy local qua `Taskfile.yml` | Không |
| Warnings | Clean `build-for-testing` (app, widget, test), ghi đè `IPHONEOS_DEPLOYMENT_TARGET` bằng command line, không sửa `project.yml`: **0 warning ở 17.0, 0 warning ở 18.0**, build thành công cả hai | Không có API nào bị deprecate ở iOS 18 mà Carodo đang dùng |
| SDK | iPhoneSimulator 27.2: min deployment target 15.0, recommended 17.0 | 18.0 hợp lệ |
| Docs (carodo-ios) | `AGENTS.md` (Stack), `README.md`, `docs/operations/setup.md:5`, `docs/design-system.md` (Shape: "Newer-than-iOS-17 APIs…"; dòng 458 coupé fallback), `docs/specs/navigation.md:22`, `docs/specs/auto-mode.md:76`, `docs/specs/places.md:203–204`, ADR 0012 (dòng 27, 36: "iOS 17–25") | Sửa câu chữ. Giữ nguyên các câu nói về **API** (`CKSyncEngine (iOS 17+)` trong `sync.md` và ADR 0005, `moped iOS 17+` trong `garage.md`, Shortcuts iOS 17+ trong `auto-mode.md:60`): vẫn đúng |
| Docs (workspace, handbook) | `AGENTS.md:46` của workspace; plan cũ trong handbook nhắc "iOS 17+" | Sửa workspace `AGENTS.md`; plan cũ là lịch sử, để nguyên |
| Quyết định | Không có ADR nào ghi deployment target | Thêm một ADR ngắn (AGENTS: một quyết định lâu dài thì có ADR) |

## 2. Phát hiện: iOS 18 không chạy được trên simulator của Xcode này

`xcodebuild -downloadPlatform iOS -buildVersion 18.6 | 18.5 | 18.4 | 18.0` trả về "not available for download"
với Xcode 27.2 (cùng lệnh với 26.0 thì bắt đầu tải; đã hủy). Runtime đang cài: 26.4 và 27.2.

Vậy iOS 18 (và 19–25, vốn không phát hành) chỉ kiểm được trên **iPhone thật chạy iOS 18**, hoặc bằng một Xcode
cũ hơn cài song song (chưa kiểm Xcode 27 có dùng được runtime 18 cài từ Xcode đó không). Khoảng trống này đã
có ở iOS 17. Nâng lên 18 không làm nó tệ hơn, nhưng cũng không đóng được nó. Muốn mọi phiên bản được hỗ trợ
đều kiểm được trên simulator thì minimum phải là iOS 26.

## 3. Migration tối thiểu đề xuất (một commit, sau khi owner duyệt)

1. `project.yml`: `17.0` → `18.0` (2 dòng); comment `FoundationModels` "iOS 18–25". `xcodegen generate`.
2. `PlatformCompatibility.swift`: `carodoOnScrollMetricsChange` gọi thẳng `onScrollGeometryChange`; bỏ
   `ScrollMetrics.isAvailable`; header "newer than the iOS 18 deployment target".
3. Nơi gọi: `JourneyStorySheet` (bỏ fallback `onAppear`), `AutoModeSheet`, `FloatingBarCollapse` (bỏ comment
   "before iOS 18"); `Vehicle.swift` (coupé dùng thẳng `convertible.side.fill`).
4. Docs như bảng trên + ADR mới `docs/decisions/0018-ios-18-minimum.md`; workspace `AGENTS.md`.
5. Kiểm tra: `task format`, `task lint`, `task warnings`, `task test`; ảnh chụp các màn có nhánh vừa bỏ (Journey
   story kéo xuống từ đỉnh, Auto Mode sheet tự đo chiều cao, thanh nổi Journeys thu gọn khi cuộn) trên 26.4
   và 27.2.

Không làm trong migration này: dùng thêm API iOS 18 mới; đụng nhánh iOS 26; Stop Location (prototype đã target
17, không ảnh hưởng).

## 4. Rủi ro

- **Rất thấp về code:** 0 warning mới, nhánh bị bỏ chỉ là fallback.
- **iOS 18 không được kiểm trên simulator** (mục 2). Cần một iPhone iOS 18 cho device check trước TestFlight,
  hoặc owner chấp nhận khoảng trống này.
- Trước phát hành chưa có người dùng iOS 17 nào bị bỏ lại.

## 5. Owner quyết

| # | Câu hỏi | Đề xuất |
|---|---|---|
| M1 | Duyệt migration ở mục 3 | Duyệt |
| M2 | iOS 18 không có simulator: dùng iPhone iOS 18 thật cho device check, chấp nhận khoảng trống, hay cân nhắc min iOS 26 | Giữ 18.0 (lợi ích của Slice 2 và giữ được người dùng iOS 18); thêm một device check iOS 18 trước TestFlight nếu có máy |
| M3 | Đề xuất "min iOS 26" từ 2026-11-08 coi như đóng | Đóng |
