# Roadmap

## V2.2

1. V2.2 — Contextual Journey & Story
Đang triển khai · Hoàn thiện dữ kiện, địa giới và narrative.
2. V2.2A.1 — Journey Identity & Context
Core implemented, UI polish.
3. V2.2A.2 — Adaptive Elevation
Done (2026-11-07); device checks open.
4. V2.2A.3 — Provinces Crossed: Current phase.
5. V2.2A.4 — Contextual Summary
Deterministic narrative.
5. V2.2B — Intelligent Journey Story Apple Foundation Models.

## V2.3R — Cinematic Journey Replay (trước Enrichment, plan: plans/cinematic-replay.md)

1. R.1	Cinematic Route Replay	Replay full-screen, Follow camera, timeline, distance/speed
2. R.2	Camera & Terrain	Cinematic Director (Follow, Reveal, Highlight), địa hình
3. R.3	Replay Highlights & Sharing	Highlights, Cinematic Recap 30–60 s, video

## V2.3 — Journey Enrichment (sau V2.3R)

Đánh số theo những gì đã làm (audit: plans/journey-v2.3-enrichment-audit.md). Nhãn cũ V2.3A–D: A và B
thành V2.3.2–V2.3.3, C và D ở cuối.

1. V2.3.0	Foundation	Một phân đoạn dừng (`stopIntervals`), `TrackQuality`. Done `fda2612`
2. V2.3.1	Driving Dynamics Shadow	Đo và log, không hiện. Done `7ffb515` (plans/driving-dynamics-shadow.md)
3. V2.3.2	Smart Stops V1	Stop trên Route Timeline, nghỉ giữa hai journey, không nhãn hoạt động. Done `365ceaa` (plans/smart-stops-v1.md)
4. V2.3.3	Journey Points	Start, End, Stop, Break mở trên Map; Nearby POI tự động, nhiều nhất một, không lưu. Slice 1 Map: done (`3aa3e25`, `e027155`). Slice 2 Nearby POI: done (`f66dcfa`), chờ PV-13. Slice 3 Start/End: done (`193d6ca`). Sau đó: Journey Point lịch sử trên Footprints (plans/journey-points.md)
5. V2.3.4	Walking Evidence	Core Motion trong lúc dừng (đi bộ = rời xe), đọc và lưu sớm sau drive vì Core Motion chỉ giữ ~7 ngày trên máy ghi (audit, bảng B và rủi ro C.3). Chưa thu sớm; quyết định lại trước bản TestFlight đầu tiên (plans/journey-points.md §6)
6. V2.3.5	Fuel & Charging Suggestions	Kết nối stop với Fuel Log: mở form fill-up điền sẵn, người dùng lưu (audit §G.4)
7. V2.3.6	Geographic Milestones	Cross-Border Milestones, lịch sử khám phá địa giới
