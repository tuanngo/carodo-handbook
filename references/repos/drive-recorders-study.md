# Study: three open-source recorders (OutRun, Pilgrim, Driveline)

What three open-source iOS location recorders do that Carodo could learn from or improve on, read
against Carodo's source on 2026-11-12. Reference material, not a plan: each candidate below needs
a plan (and the owner's approval where it says so) before any code. A finding that ships lands in
`carodo-ios/docs/` in our own words, never as a link here.

| Repo | Commit read | Licence | What it is | Closeness |
|---|---|---|---|---|
| [timfraedrich/OutRun](https://github.com/timfraedrich/OutRun) | `e392753` (2026-11-10) | GPL-3.0 | Workout recorder (run, cycle, hike); Swift 6.2, SwiftData, `OutRunCore` package | Recording lifecycle, same Swift idioms |
| [walktalkmeditate/pilgrim-ios](https://github.com/walktalkmeditate/pilgrim-ios) | `b76e640e` (2026-10-29) | GPL-3.0 | Walking journal with voice and meditation; UIKit + Combine, CoreStore, Mapbox | Crash recovery, power, share privacy, written lessons |
| [dglancy/Driveline](https://github.com/dglancy/Driveline) | `155c7b7` (2026-10-23) | MIT | Drive recorder started by Shortcuts on car Bluetooth/CarPlay; SwiftData, iOS 26+, no packages | Same product space |

**Licence.** OutRun and Pilgrim are GPL-3.0: ideas only, never code. Driveline is MIT: code may be
copied only with its copyright and licence notice kept, and nothing below needs to be copied
(`ios.md`, Licence rules).

## 1. Already done in Carodo — do not re-propose

Checked in the source, so the next reader does not spend time on them again.

| Their idea | Where | Carodo today |
|---|---|---|
| Crash recovery from a JSON checkpoint written every 10–30 s | Pilgrim `WalkSessionGuard` | Stronger: every accepted fix goes to `trip_points` (GRDB, WAL) as it arrives, and launch reconciles unfinished trips (`TripRecovery`, iOS invariant 5). Pilgrim spends hundreds of lines guarding the checkpoint file (I/O queue, write/delete races) |
| Delete the recovery data only after the final save succeeds | Pilgrim `stop()` vs `deleteCheckpointFile()` | Same guarantee by construction: `pack` writes `trip_tracks` and deletes `trip_points` in one transaction (`GRDBJourneyRepository.swift:497-521`) |
| Points written straight to the store, map drawn after the drive | Driveline README "Why no live map" | Carodo persists first too; it does show a live map, with the per-frame cost handled by the Map follow work (`161de4d`) |
| `CLLocationUpdate.liveUpdates` + `CLBackgroundActivitySession` | Driveline `LocationStreaming.swift` | Rejected on purpose: a `liveUpdates` session started from an Auto Mode background wake was suspended within seconds; Carodo uses standard updates (`LocationSource.swift:12-16`). Keep this decision |
| Drop a fix with bad accuracy or older than a few seconds | Driveline `isUsable` (50 m, 5 s); OutRun `processLocation` | `RouteRecorder` filter with counted rejections (stale, accuracy, jumps) |
| Resume a drive finished minutes ago when driving starts again | Driveline `continueDriveIfRecentlyFinished` (30 min) | `WaitJoining` (Stop and wait), with a motion check on the gap and "Split here" |
| Merge two drives | Driveline `DriveMergeService`, same-day auto merge | `JourneyMerge` with refusals and the vehicle rule |
| Weather at start and end | Driveline `WeatherFetchService` | `Core/Weather/WeatherLookup.swift` |
| Share route: trim the ends, simplify with Ramer–Douglas–Peucker | Pilgrim `RouteTrimmer`, `RouteDownsampler` | `PrivacyZone`, `RouteSimplifier`, `DriveShapeMaker` |
| Barometric altitude | OutRun `AltitudeService` | `Core/Motion/Barometer.swift` |
| Version stamp on derived data | Driveline `categoryModelVersion`; Pilgrim's lesson (§3) | Mostly done: `recorder_version`, `narrative_version`, `trip_gaps.rules_version`, `geocoded_cells.lookup_version`, `trip_tracks.codec_version`. Two gaps: L4 |
| MetricKit subscriber | Driveline `MetricKitService` | `MetricKitStore` (energy); diagnostics not taken: L3 |
| Start a drive from Shortcuts / Siri | Driveline `StartDriveIntent` | `App/StartDriveIntent.swift` (`openAppWhenRun`) |
| GPX export | OutRun, Driveline | Specified (`docs/specs/account.md`, one GPX 1.1 per trip in the export), not built yet |

## 2. Candidates — learn or improve

Ordered by value to Carodo now. **Decision** names what the owner must approve (P6 contracts,
product). Effort is rough: S (a day), M (a few days), L (a week or more).

| # | Candidate | From | Value | Decision | Effort |
|---|---|---|---|---|---|
| L1 | Live Activity done right | Pilgrim, Driveline | High: planned in `drive-recording.md`, nothing built (`CarodoWidgets` holds only the bundle) | Product: what the Lock Screen shows | M |
| L2 | Thermal-aware GPS tier | Pilgrim | High: a phone on the windscreen, in sun, charging | None beyond a tracking threshold | S |
| L3 | MetricKit diagnostic payloads | Driveline (subscribes), Pilgrim (needs) | High for field tests: why iOS killed or hung the app | Log field classification | S |
| L4 | Two existence-only freshness checks | Pilgrim lesson | Medium: wrong data after a rule change, silently | Schema (P6), before TestFlight | S |
| L5 | `docs/solutions/` — one lesson per file | Pilgrim | Medium, compounding | New docs convention | S |
| L6 | End-drive intent + Live Activity button | Driveline | Medium | Product + P4 | S |
| L7 | Drive category with a versioned classifier | Driveline | Product idea | Product | M–L |
| L8 | Background processing for slow derivations | Driveline | Medium if launch work grows | P6: background mode + permitted ids | M |
| L9 | Per-drive feature table from `drive-data/` | Driveline `MLTrainingDataPrepTool` | Medium for tuning thresholds | None | S |
| L10 | App Store screenshots from UI tests | Pilgrim `ScreenshotTests` | Low now, high at release | None | M |
| L11 | Spotlight indexing of journeys | Driveline | Low | Product + P5 | S |
| L12 | CI on push (build, test, CodeQL) | Driveline | Low for a solo loop | Owner (cost, workflow) | S |
| L13 | Explicit legal-transition table | OutRun `WorkoutRecorderState.transition` | Low, check first | None | S |
| L14 | TipKit for hidden gestures | Driveline `UI/Tips` | Low | Product | S |

### L1 — Live Activity done right

What to take, from code that has already shipped and broken:

1. **End orphans at launch.** After a crash, force quit or OOM, iOS keeps showing the Live
   Activity with no session behind it (Pilgrim `endAllStaleActivities`, and `end()` walks
   `Activity<…>.activities` instead of trusting the one it remembers). In Carodo this belongs to
   launch reconciliation: an activity whose trip `TripRecovery` resumes is kept and updated;
   every other one is ended immediately.
2. **`staleDate` on every update.** When iOS suspends the app, the activity greys out as stale
   instead of showing figures that read as live ("Unknown is not zero"). Driveline passes `nil`
   and so can show a frozen distance as current; Pilgrim sets it to three update intervals.
3. **A pure push gate.** Pilgrim's `shouldPush(movedMeters:flagsChanged:secondsSinceLastPush:)`
   decides when to update: meaningful movement, a state flip, or a time floor. Pure, so tested on
   both sides of each threshold, and it keeps updates inside the ActivityKit budget.
4. **A frozen final frame.** On end, stop the timers and keep the last figures, so the frame the
   person sees reads "finished", not still counting.
5. **What the Lock Screen may show** (owner): the Lock Screen is visible to anyone near the phone.
   Driveline shows the start place name. Proposal: phase, elapsed time, distance and the stop stage
   (`StopDetector.stage`), no place names. Times are the person's own data shown back to them
   (a P9 exception), but a Lock Screen is seen by others too, so place names stay off it.

Needs a device check: update cadence while backgrounded, and orphan cleanup after a forced kill.

### L2 — Thermal-aware GPS tier

Pilgrim lowers GPS accuracy and widens the distance filter at battery ≤ 20 % / ≤ 5 % and at
`ProcessInfo.thermalState` `.serious` or worse, re-evaluated on
`thermalStateDidChangeNotification`. Carodo's tiering (`636d3d6`) reacts to Low Power Mode only.
A phone mounted on the windscreen in the sun while charging is the common case for a drive app,
and iOS throttles or kills a hot app.

Proposal: add the thermal state to `RecordingGPS` selection as an input of the pure tier rule
(injected, never read inside the rule), with tests on both sides; a tracking-log field for the
thermal state (classify it in `DiagnosticsLogFormat`); a row in the `docs/tracking.md` table.
Keep battery level out: Carodo's choice was "battery off" (`gps-accuracy-tiering`), and a car
charges the phone. Device check: a hot-phone drive.

### L3 — MetricKit diagnostic payloads

`MetricKitStore` reads `MXMetricPayload` (energy) only. `MXDiagnosticPayload` carries crash, hang,
CPU-exception and disk-write diagnostics with call stacks, delivered the next day, including for
terminations in the background, which is exactly what field tests cannot see. Proposal: keep the
latest diagnostics on device and show them in Developer (Diagnostics), with the call stack shared
only from Developer. Stacks carry no coordinates, but the payload's timestamps fall under P9:
Developer only.

### L4 — Two existence-only freshness checks

Pilgrim's lesson (§3, first entry): *changing how derived data is computed is a schema change,
even when its shape does not move*; a sweep whose per-item skip asks "does it exist" cannot see
data computed under old rules.

Carodo versions most of its derived data (§1). Two markers are existence-only timestamps:

- `trips.points_matched_at` — the journey-point matching sweep picks trips `WHERE points_matched_at
  IS NULL` (`GRDBJourneyRepository.swift:794`). A change to the matching rules never reaches a
  trip already matched.
- `trips.places_looked_up_at` — the place lookup picks `WHERE places_looked_up_at IS NULL`
  (`:734`). Cells are versioned (`geocoded_cells.lookup_version`), the trip's choice of cells is
  not.

Both are reset only by the join/split path (`:1430`). Pre-release the in-place schema and
reinstall hide this; after the first TestFlight build it becomes a silent bug. Proposal: a
version beside each marker (or one `derived_version` for the trip's place-related derivations),
read in the sweep's `WHERE`, decided with the move to versioned migrations (TD-6). Add the
rule itself to `docs/data-model.md`: a rule change bumps its version; a sweep selects by version,
never by presence.

### L5 — `docs/solutions/`: one lesson per file

Pilgrim keeps `docs/solutions/<slug>.md`, one hard-won lesson each, with frontmatter
(`title`, `date`, `category`, `module`, `problem_type`, `severity`, `applies_when`, `tags`) and
four sections: Context, Guidance, Why this matters, When to apply, plus Related (files, tests,
commits). The `applies_when` lines are what make it work: an agent about to change a sweep or a
cache greps them and finds the lesson before repeating the mistake. Their audit findings carry
IDs (`AF9`, `AF46`) quoted in code comments next to the fix.

Carodo's lessons are scattered today: "Five mistakes a source audit found here" in `AGENTS.md`,
"Map rules — learned the hard way" in `design-system.md`, the handbook's `audits/`, and the
`.remember` notes, which do not reach other sessions.

Proposal (owner, new docs convention):

- `carodo-ios/docs/solutions/` (and `carodo-app/docs/solutions/` later), one file per lesson, the
  frontmatter above, in English; the lesson in our words, never a link to the handbook.
- A lesson is written when a bug cost a device round trip, survived a review, or was fixed twice.
- `AGENTS.md` keeps the short checklist and points to `docs/solutions/`; the preflight adds
  "grep `applies_when` for the area you are about to touch".
- The handbook's `audits/` stays the record of each audit (what was found, which commit fixed
  it); the durable rule moves to `docs/solutions/` (the audits README already says a binding rule
  lands in the repo).
- First entries, from lessons already paid for: the `liveUpdates` suspension on a background wake
  (§1), the iOS 26.0 isolated-deinit crash (`9db0594`), the five audit mistakes, the map rules,
  and L4 itself.

### L6 — End-drive intent and a Live Activity button

Driveline exposes `Finish drive` as a `LiveActivityIntent`: it runs in the app's process, so the
Lock Screen button ends the drive without opening the app. Carodo has only `StartDriveIntent`.

P4 matters here: Driveline's onboarding asks people to wire "CarPlay disconnects → Finish drive",
which is exactly the rule Carodo refuses (a disconnect is not proof the drive ended). Proposal: an
End-drive intent for the Live Activity button and Siri, idempotent like `carodo://trip/start`;
Carodo's onboarding and help never suggest a disconnect automation (owner).

### L7 — Drive category with a versioned classifier

Driveline classifies each finished drive (`errand`, `urban`, `roadTrip`, `scenic`, `mixed`) with
an on-device Create ML model over 14 statistics: distance, duration, speed mean/variance, share of
time above 80 km/h, sustained high-speed segments, stops and stopped share, sinuosity, bearing
change per km, elevation gain/loss. Each drive stores the model version; a sweep reclassifies
drives from older versions.

For Carodo (product): a category could feed the narrative (ADR 0012), Journeys filters and the
Passport. Start with rules over `JourneyAnalysis` figures; consider a model only with enough
labelled drives. Whatever decides it stores its version (L4).

### L8 — Background processing for slow derivations

Driveline runs its sweeps (place names, weather backfill, reclassification) on foreground and
schedules a `BGProcessingTask` when the app goes to the background, cancelling on expiration.
Carodo derives at launch and on save. If launch work grows (the perf audit's concern), moving the
non-urgent sweeps to `BGProcessingTask` (on power, with network for lookups) is the iOS way.
P6: a `processing` background mode and `BGTaskSchedulerPermittedIdentifiers`. Measure first
(AGENT_WORKFLOW, a performance claim names its measurement).

### L9 — Per-drive feature table from `drive-data/`

Driveline's `MLTrainingDataPrepTool` turns a folder of GPX into one CSV row per drive. The same
idea over Carodo's pulled databases (a `task` beside `task replay`) gives one row per drive with
the figures our thresholds act on (stops, gaps, rejections, accuracy, speed spread), so a
threshold change is judged on every recorded drive at once. Output stays in `drive-data/` or the
scratchpad (Development data rules).

### L10 — App Store screenshots from UI tests

Pilgrim drives the app through `ScreenshotTests` on bundled GPX routes to produce store
screenshots. Carodo's DEBUG launch arguments (`-carodo.sampleData`, `-carodo.debugOpenJourney`)
already open every screen; a UI test that walks them in Light, Dark, a large Dynamic Type size
and Vietnamese would also produce the commit evidence `AGENTS.md` asks for. Synthetic routes only.

### L11 — Spotlight indexing

Driveline indexes finished drives (name, start and end place) so system search opens them.
For Carodo it collides with P5: place names would appear in system search on a shared or
unlocked phone. If wanted, opt-in, journey names only, removed on delete. Low priority.

### L12 — CI on push

Driveline runs build and test on GitHub Actions, plus CodeQL. Carodo's rule is "local carries the
weight"; macOS runner minutes cost money. If wanted, the smallest useful job is `task lint` +
`task test` on push to `main`. Owner.

### L13 — Explicit legal-transition table

OutRun lists the legal `(from, to)` pairs of its recorder state and throws
`.invalidStatusTransition` on any other. `DriveSessionManager.State` has six states; whether every
transition is guarded was not checked in this study. Worth a look in the next recording audit.

### L14 — TipKit

Driveline uses TipKit to surface features once. Candidates in Carodo: "Split here", replay
controls, merging. Product.

## 3. Pilgrim's written lessons, mapped to Carodo

| Lesson (`pilgrim-ios/docs/solutions/`) | The rule | Carodo |
|---|---|---|
| `derived-cache-semantics-are-schema.md` | A rule change that alters what stored derived data means is a schema change: bump a version even when the shape is unchanged; every freshness check (single read, bulk read, backfill skip) is version-aware; keep honest existence checks under their own name; prune stale-version orphans with an unfiltered scan | Mostly applied; two gaps (L4) |
| `corestore-queryattributes-uuid-string.md` | A cast that can only fail (`row["id"] as? UUID` on a column stored as text) compiles, warns nothing and returns empty; it survived two reviews and was found by a test comparing a snapshot's row count with seeded data | GRDB analogue: a raw-row read decoded to the wrong type folds into `nil` and reads as "nothing" ("Unknown is not zero"). Guard: repository tests assert counts against seeded rows, not only shapes |
| `avaudiorecorder-cannot-resume-across-interruption.md` | A recorder stopped by the system cannot resume into the same file; split interruptions by source and probe on `.ended` | No audio in Carodo. General form: decide on the event's source, not on the event alone (as P4 does for CarPlay) |

## 4. Not to adopt

- Combine pipelines, GCD queues, `Timer` on the main run loop, `print` logging (Pilgrim): against
  Carodo's concurrency and logging rules.
- Patching a third-party package in place (Pilgrim's Podfile edits CombineExt to fix a race).
- A self-made device token as the API credential (Pilgrim `X-Device-Token`): P7 requires App
  Attest.
- Shortcuts automations on disconnect to end a drive (Driveline): P4.
- SwiftData with CloudKit `.automatic` (Driveline), CoreStore (Pilgrim), and OutRun's
  CoreStore → SwiftData migration with its `Legacy/` folder: confirms ADR 0003 (GRDB).
- Saving every 30 s on a timer (Driveline `LocationDataRecorderService`): up to 30 s of fixes lost
  on a kill; Carodo's write per accepted fix is the stronger rule.

## 5. Suggested order

1. **L4 + L5 together** (S): write the first `docs/solutions/` entries, L4's rule among them; the
   schema part waits for the TD-6 decision.
2. **L2** (S): thermal input to the GPS tier; device drive.
3. **L3** (S): MetricKit diagnostics in Developer, before the next field test.
4. **L1 + L6** (M): Live Activity with orphan cleanup, `staleDate`, push gate, End button.
5. The rest as their features come up.
