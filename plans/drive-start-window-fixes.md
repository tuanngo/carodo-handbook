# Drive start: keep the detection window's way out

Status: **approved** (owner, 2026-11-18: D1–D4 as recommended; D5 answered). Slice 1 in progress.

## 1. Problem

The owner's drive of 2026-11-18 (Auto Mode, motorbike, 07:05–07:37, `4fa149ea`, pulled
`drive-data/carodo-20261118-074135-tuanngo-iphone.sqlite`) begins its recorded GPS **582 m** from
where the bike was parked. The same shape in every pulled Auto Mode drive since 2026-11-16:

| Drive | Window | Window fixes | Roll-out kept | `fromParkedM` |
|---|---|---|---|---|
| 2026-11-16 16:19 | 3 s | 4 | 0 (`windowStart`) | 210 |
| 2026-11-16 16:40 | 6 s | 9 | 0 (`slow`) | 610 |
| 2026-11-17 11:49 | 17 s | 18 | 0 (`slow`) | 460 |
| 2026-11-18 07:05 | **169 s** (extended) | **170** | 0 (`slow`) | 580 |

Two losses add up:

1. **Before the window opens** (all four drives): iOS wakes Carodo only after the phone leaves the
   150 m parking circle, and late. Nothing in the window can recover it; today the lead-in
   (`GapHealing.LeadIn`) draws it after the save.
2. **Inside the window** (07:05 only, but the largest): 170 real fixes over 169 s, 230 m net
   (`detection … netM=230 slow=148 rolling=15 maxKmh=27`), were dropped. Rule B (the roll-out)
   walks back from the 4-fix run and stops at the first fix under 7.2 km/h or with an untrusted
   speed: here the fix one second before the run. The window's fixes are kept nowhere, so the way
   out is lost for good.

What the saved drive shows today (checked in the pulled database): its summary **does** include a
lead-in, 976 m, from another drive's recorded road (`trip_gaps`, `start_sequence = -1`,
`healed`); recorded track 7,297 m + 976 m ≈ the stored 8,219 m. The lead-in's road wanders: its
distance from the parking spot goes 0 → 178 → 161 → 202 → 197 → 159 → 261 → … → 582 m, so it
probably is not the road ridden. Its time is invented (8 m/s, departure 07:06:23). The share card's
route and the replay video draw recorded fixes only (carodo-ios `5a864f5`, `2aef339`), so there the
drive starts 582 m out.

**Assumed, not checked:** which of these the owner saw as "about 500 m lost" (map, card, replay or
the distance). The plan fixes the cause (fixes dropped) rather than one screen; D5 asks.

## 2. What the code does today

- `Core/Tracking/DetectionWindow.swift`, `rollOutReading`: walking back from the run, a fix joins
  only if usable, at a trusted 2.0 m/s or more, and within 5 s of the next; anything else ends it
  (`RollOutEnd`). docs/tracking.md, Auto Mode detection, rule B.
- `Core/Tracking/AutoModeCoordinator.swift`, `startDrive`: seeds the session with roll-out + run;
  logs `leadIn candidate … stoppedBy=`; `windowFixes` are then discarded.
- `AutoModeCoordinator.detectionStarted`: asks Core Motion once (`recentActivity(minutes: 2)`) as the
  window opens; the answer is a summary (`RecentActivity`), not per-second readings.
- `Core/Recording/GapHealing.swift`, lead-in: from the parking spot (or a place) to the drive's
  first fix, 100–1,500 m, the person's own recorded road first, else Apple; time at the first fix's
  speed, never under 8 m/s.
- `Core/Diagnostics/DriveDiagnostics.swift`: after the save, Core Motion from the drive's start
  (`walkBeforeS=0` for 07:05: no walk just before the start).

## 3. Proposal

**B2: the window's way out joins the drive.** On confirmation, walk back from the run over the
window's fixes, **slow fixes included**, and stop at the first of:

| End | Value (hypothesis) | Why |
|---|---|---|
| A walk | Core Motion reads walking or running (confident) at that fix's time | the person walking to the vehicle is not the drive (why rule B refused slow fixes) |
| A dwell | 30 s or more with every usable fix within 15 m | waiting by the vehicle before leaving; also a phone still indoors |
| A hole | over 10 s with no usable fix | today 5 s, which a crawl in a covered alley breaks |
| Inaccurate or stale | as today | |
| The window's start | as today | |

Core Motion: one query at confirmation for the window's span, per-reading (the same
`MotionActivityQuerying.readings(from:to:)` `DriveDiagnostics` uses), not a second query per fix.
With no Motion access, B2 falls back to today's B (no way to tell a walk from a crawl).

Then the lead-in has less to invent: it routes from the parking spot to the first **prepended**
fix (`GapHealing` reads the drive's first fix, unchanged), and the departure time comes from a real
fix whenever B2 reached the window's start.

**Slices (each one commit, proven):**

1. **Shadow.** Compute B2 beside B and log it on the debug `leadIn candidate` line
   (`b2Fixes=… b2M=… b2StoppedBy=walk|dwell|gap|inaccurate|stale|windowStart`) and the window's
   walking seconds on `detection` (`walkS=…`). Nothing recorded changes. Tests on both sides of
   each end. Proof: two or three Auto Mode drives on the iPhone, read from the log.
2. **On.** B2 seeds the drive; B's rows in docs/tracking.md replaced. Tests: a 170-fix crawl is
   kept whole; a walk then a ride keeps only the ride; a dwell cuts; a hole over 10 s cuts.
   Proof: a drive whose `fromParkedM` drops by about the window's way out.
3. **Optional, separate: a lead-in that backtracks is refused.** A borrowed road whose distance
   from the origin falls back by more than 50 m is not the way out (07:05's falls 43 m, then
   rises); fall back to Apple or the straight line. Only if D4 says so.

## 4. Decisions for the owner

- **D1 — slow fixes join the drive when Core Motion says no walk** (B2). Recommend **yes**: the
  07:05 window lost 230 m of real fixes to a single slow reading.
- **D2 — shadow first** (slice 1), on for real after two or three drives agree. Recommend **yes**:
  the thresholds are guesses and the window's fixes cannot be replayed from any pulled database.
- **D3 — no Motion access falls back to today's B.** Recommend **yes**: a walk prepended to a drive
  is worse than metres missing (the lead-in still draws them).
- **D4 — slice 3 (backtracking lead-in)**: recommend **later**, after slice 2 shows how much lead-in
  is left to draw.
- **D5 — what "about 500 m lost" was.** Answered (owner, 2026-11-18): the journey showed a late
  start, then seemed to correct itself: the lead-in drawn by the pass after the save. Slice 2
  keeps real fixes where the lead-in now invents a road and a time.

## 5. Scope and non-goals

In: rule B in `DetectionWindow`, its use in `AutoModeCoordinator.startDrive`, the `leadIn
candidate` and `detection` log fields, docs/tracking.md (rule B row, log fields), tests in
`CarodoTests/Core/Tracking/DetectionWindowTests.swift` and `AutoModeTests.swift`.

Out: the wake latency itself (the parking circle's 150 m and iOS's delay: no rule in the window
reaches before it opens); a smaller parking circle; keeping the window's fixes when the window does
not confirm; storing window fixes for debugging (a schema change); the lead-in's own rules (except
slice 3 if approved). No schema, API, permission or dependency change.

## 6. Acceptance

- Slice 1: unit tests for each B2 end on both sides of its threshold; `task lint`, `task warnings`,
  `task test` pass; the debug fields classified (`TrackingLogFieldsTests`).
- Slice 2: on the next long-window drive, `prependedM` close to the window's `netM` path and the
  saved drive's `fromParkedM` smaller by it; `walkBeforeS` and the ride line show no walk joined; a
  short-window drive (3–17 s) unchanged. Device check required: the simulator cannot crawl a
  motorbike out of an alley.
