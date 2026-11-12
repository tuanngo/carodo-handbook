# Master plan — what comes next (2026-11-12, updated 2026-11-13)

One ordered list of the work between today and the first TestFlight build, so each new session
starts from the same picture. Each line points to the plan that holds its detail; this file keeps
only the order, the owner's reason and the state. Update the state column when a step lands.

Owner's decision (2026-11-12): a "wow" first, for motivation and to have something to show:
cinematic 3D Replay and a short exported intro video. Then the TestFlight gates. Refactors ride
along with the work that touches each file, never as a big-bang pass while sessions run in
parallel.

## Order

| # | Track | Step | Detail | State |
|---|---|---|---|---|
| 0 | In flight | Commit M04 (place visits by start coordinates) from the Places/Map session | [technical-debt.md](technical-debt.md) TD-20 | In progress |
| 1 | **Wow** | W1: replay stop alignment (TD-1), so labels and highlights agree with the journal | [cinematic-replay.md](cinematic-replay.md#wow-track-owner-2026-11-12) | Done 2026-11-12 (carodo-ios 969ba51) |
| 2 | **Wow** | W2: R.2B contextual camera, one behaviour at a time (Rest, Hairpin, Terrain), each proven on device drives | cinematic-replay.md, Wow track | Rest done 2026-11-12 (carodo-ios ba17a06); the Reveal done 2026-11-13 (b525900, Hairpin and Junction as one); Terrain Reveal deferred until after W3 (owner) |
| 3 | **Wow** | W3: video spike: how to turn the `MKMapView` replay into frames (ReplayKit capture vs per-frame snapshot) | cinematic-replay.md, Wow track | Next |
| 4 | **Wow** | W4: Cinematic Recap (a 30–60 s edit) and a 9:16 video export, privacy trim on | cinematic-replay.md, Wow track | Planned |
| 5 | TestFlight gate | TD-19: iOS 18 runtime, run the tests there; decide the minimum iOS if the deinit crash repeats | technical-debt.md TD-19 | Open |
| 6 | TestFlight gate | TD-6: freeze `v1_initial`, versioned non-destructive migrations with upgrade tests | technical-debt.md TD-6 | Open |
| 7 | TestFlight gate | TD-2: Apple Maps data terms (also covers map imagery inside an exported video) | [apple-maps-data-review.md](apple-maps-data-review.md) | Open |
| 8 | TestFlight gate | TD-20: rest of the source audit (backend track: H03, M06–M09, L09–L12) | [../audits/2026-11-12-carodo-source-audit.md](../audits/2026-11-12-carodo-source-audit.md) | Open |
| 9 | Device proof | One batch of real drives covering the open pending validations (GPS, Auto Mode, onboarding, live map, places, Feed, replay R.1 checks) | technical-debt.md, Pending validations | Open |
| 10 | Release prep | Privacy Report, `CollectedDataTypes`, widget "Ready" state, Dynamic Type cap (TD-16) | technical-debt.md | Open |

## Study follow-ups (drive-recorders-study §5)

From [`../references/repos/drive-recorders-study.md`](../references/repos/drive-recorders-study.md).
L2–L4 detail, approved decisions (D2.1 no, D2.2 no, D3.1 Developer only, D4.1 yes) and acceptance:
[`study-followups-thermal-diagnostics-derived.md`](study-followups-thermal-diagnostics-derived.md).
W3 tries the offline, fixed-step capture first (study §6).

| Item | What is left | State (2026-11-13) |
|---|---|---|
| **L2** hot-phone GPS | Desk check on the iPhone ([field test](../field-tests/2026-11-13-hot-phone-gps.md), steps 3–5, Xcode Device Conditions), then commit **only** its 12 carodo-ios files: `Carodo/App/DependencyContainer.swift`, `Core/Diagnostics/{BatteryMonitor,DiagnosticsLogFormat,TrackingLog}.swift`, `Core/Recording/{DriveSessionManager,RecordingGPS}.swift`, `CarodoTests/{DeveloperModeTests,RecordingGPSTests,TrackingLogFieldsTests}.swift`, `docs/tracking.md`, `docs/specs/developer-mode.md`, `docs/operations/device-testing.md`. Suggested message: `feat(tracking): a hot phone gives up navigation accuracy` | Built, uncommitted; lint, warnings, 1,990 tests pass; **PV-17** |
| **L3** MetricKit exits and diagnostics | Build per the plan: exit reasons from `applicationExitMetrics`, `MXDiagnosticPayload` kept (20 files, 2 MB), Developer → Crashes and hangs, `MetricKitStore` observed; screenshots (Light, Dark, large type, Vietnamese); a PV row when built | Next; must ship before step 9 |
| **L4** versioned place sweeps | Build with TD-6 (step 6): `places_version`, `points_version` replace the two `_at` columns; `setPlaceKeys` syncs only on a changed cell; the rule in `docs/data-model.md`. One `CONFIRM=erase` on the iPhones | Approved, waits for step 6 |
| L9 per-drive feature table | A `task` over `drive-data/` printing one row per drive (stops, gaps, rejections, accuracy, speed spread) | When the step 9 batch is pulled |
| L1 + L6 Live Activity, End button | Own plan: orphan cleanup at launch, `staleDate`, push gate, frozen last frame, no place names on the Lock Screen; End-drive intent, never suggested for a disconnect | After the wow track (product decisions) |
| L5 `docs/solutions/` | Built from [`lessons-inbox.md`](lessons-inbox.md) | At about ten lessons or before the first TestFlight build |
| L10 store screenshots from UI tests | — | Release prep (step 10) |
| L7, L8, L11–L14 | — | As their features come up |

**Every pull of drive data sweeps every `Waiting` PV row** in [`technical-debt.md`](technical-debt.md#pending-validations),
not only the drive's script ([`../field-tests/README.md`](../field-tests/README.md), Rules), so step 9
is a sweep of PV-1…PV-17 on one batch.

## Refactors that ride along (no step of their own)

Done in the same session as the next feature that edits the file, one `refactor:` commit each:

- `MainTabView.swift` (1,125 lines): extract the drive start/finish flow first (TD-13).
- ~~`GRDBJourneyRepository.swift` (1,950 lines): split by query family~~ — done 2026-11-12 (7260c5f): seven files, 322 lines left for the screens' reads.
- ~~`Repositories.swift` (1,122 lines): one protocol per file~~ — done 2026-11-12 (7260c5f): one file per repository, the trip stores together.
- `LoadState` declared in ten view models (TD-10); DEBUG launch arguments in 26 files (TD-14).
- Perf only where measured: TD-12 done 2026-11-12 (b39f20c); perf audit 11, 12, 14 done (53edd24, b39f20c, cc2b501); 13 needs the iPhone.

## Why this order

- The wow track builds on R.1 and R.2A, which are done; it does not touch the schema or the API,
  so it can run while the gates wait.
- The gates (5–8) are each small, but every tester build depends on them; none should slip past
  the wow track's end.
- Device proof (9) gathers into one or two drives what is otherwise checked one feature at a time.
